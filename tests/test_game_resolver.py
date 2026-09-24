import pytest

from tribunal.application.pipeline.game import CatalogGameResolver
from tribunal.application.unanswerable import GameUnresolved
from tribunal.domain.game import Game, GameStores


def _catalog(nusfjord_rule: str = "vs_nusfjord_rule", agricola_rule: str = "") -> dict[str, Game]:
    return {
        "nusfjord": Game(
            id="nusfjord",
            name="Nusfjord",
            aliases=("ヌースフィヨルド",),
            identifying_terms=("長老", "Banquet Table"),
            stores=GameStores(rule=nusfjord_rule, strategy=""),
        ),
        "agricola": Game(
            id="agricola",
            name="Agricola",
            aliases=("アグリコラ",),
            identifying_terms=("小進歩", "Harvest"),
            stores=GameStores(rule=agricola_rule, strategy=""),
        ),
    }


def _resolve(question: str, *, game_id: str | None = None, **catalog: str) -> str:
    return CatalogGameResolver(_catalog(**catalog)).resolve(question, game_id=game_id).id


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("ヌースフィヨルドの長老は?", "nusfjord"),
        ("agricola の収穫は?", "agricola"),
        ("長老は何人まで雇える?", "nusfjord"),
        ("banquet table の皿は?", "nusfjord"),
        ("アグリコラで長老みたいなカードある?", "agricola"),
    ],
    ids=["alias", "name-case", "term", "term-case", "name-beats-term"],
)
def test_resolves_from_the_question(question: str, expected: str) -> None:
    assert _resolve(question) == expected


def test_named_game_is_returned_even_without_rule_store() -> None:
    """Rule Store を持つ唯一のゲームに差し替えない。答えられるかは呼び出し側が判定する。"""
    assert _resolve("アグリコラの収穫は?") == "agricola"


def test_multiple_candidates_are_unresolved_with_their_names() -> None:
    with pytest.raises(GameUnresolved, match="Nusfjord / Agricola"):
        _resolve("アグリコラとヌースフィヨルドどっちが重い?")


def test_no_candidate_falls_back_to_the_only_game_with_rule_store() -> None:
    assert _resolve("手番の順番は?") == "nusfjord"


def test_no_candidate_with_multiple_rule_stores_is_unresolved() -> None:
    """複数ゲームの Store をまとめて検索しない。"""
    with pytest.raises(GameUnresolved):
        _resolve("手番の順番は?", agricola_rule="vs_agricola_rule")


def test_no_candidate_without_any_rule_store_is_unresolved() -> None:
    with pytest.raises(GameUnresolved):
        _resolve("手番の順番は?", nusfjord_rule="")


def test_explicit_game_id_wins_over_the_question() -> None:
    assert _resolve("ヌースフィヨルドの長老は?", game_id="agricola") == "agricola"


def test_unknown_game_id_is_unresolved() -> None:
    with pytest.raises(GameUnresolved):
        _resolve("収穫は?", game_id="catan")
