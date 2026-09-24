import pytest

from tribunal.application.answer_service import AnswerService, GameUnresolved
from tribunal.application.pipeline.game import GameResolver
from tribunal.domain.answer import Answer
from tribunal.domain.game import GameIdentity, GameStores

IDENTITIES = {
    "nusfjord": GameIdentity(
        name="Nusfjord", aliases=("ヌースフィヨルド",), identifying_terms=("長老", "Banquet Table")
    ),
    "agricola": GameIdentity(
        name="Agricola", aliases=("アグリコラ",), identifying_terms=("小進歩", "Harvest")
    ),
}

BOTH_WITH_RULE = {
    "nusfjord": GameStores(rule="vs_nusfjord_rule", strategy=""),
    "agricola": GameStores(rule="vs_agricola_rule", strategy=""),
}

ONLY_NUSFJORD_WITH_RULE = {
    "nusfjord": GameStores(rule="vs_nusfjord_rule", strategy=""),
    "agricola": GameStores(rule="", strategy=""),
}


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def answer(self, question: str, *, vector_store_id: str) -> Answer:
        self.calls.append((question, vector_store_id))
        return Answer(text="rule")


def _service(rule: RecordingRetriever, stores: dict[str, GameStores]) -> AnswerService:
    return AnswerService(
        rule, RecordingRetriever(), stores=stores, resolver=GameResolver(IDENTITIES)
    )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("ヌースフィヨルドの長老は?", ["nusfjord"]),
        ("agricola の収穫は?", ["agricola"]),
        ("長老は何人まで雇える?", ["nusfjord"]),
        ("banquet table の皿は?", ["nusfjord"]),
        ("アグリコラで長老みたいなカードある?", ["agricola"]),
        ("アグリコラとヌースフィヨルドどっちが重い?", ["nusfjord", "agricola"]),
        ("手番の順番は?", []),
    ],
    ids=["alias", "name-case", "term", "term-case", "name-beats-term", "two-names", "none"],
)
def test_candidates(question: str, expected: list[str]) -> None:
    assert GameResolver(IDENTITIES).candidates(question) == expected


def test_named_game_is_answered_from_its_store() -> None:
    rule = RecordingRetriever()

    _service(rule, BOTH_WITH_RULE).ask("ルール: アグリコラの収穫は?")

    assert rule.calls == [("アグリコラの収穫は?", "vs_agricola_rule")]


def test_multiple_candidates_are_asked_back_with_their_names() -> None:
    rule = RecordingRetriever()

    with pytest.raises(GameUnresolved, match="Nusfjord / Agricola"):
        _service(rule, BOTH_WITH_RULE).ask("長老と小進歩の関係は?")

    assert rule.calls == []


def test_named_game_without_rule_store_is_not_replaced_by_another_game() -> None:
    """名指しされたゲームの資料が無いとき、Rule Store を持つ唯一のゲームで答えない。"""
    rule = RecordingRetriever()

    with pytest.raises(GameUnresolved, match="Agricola のルール資料"):
        _service(rule, ONLY_NUSFJORD_WITH_RULE).ask("アグリコラの収穫は?")

    assert rule.calls == []


def test_no_candidate_falls_back_to_the_only_game_with_rule_store() -> None:
    rule = RecordingRetriever()

    _service(rule, ONLY_NUSFJORD_WITH_RULE).ask("ルール: 手番の順番は?")

    assert rule.calls == [("手番の順番は?", "vs_nusfjord_rule")]


def test_explicit_game_id_wins_over_the_question() -> None:
    rule = RecordingRetriever()

    _service(rule, BOTH_WITH_RULE).ask("ルール: 長老は?", game_id="agricola")

    assert rule.calls == [("長老は?", "vs_agricola_rule")]
