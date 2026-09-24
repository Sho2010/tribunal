import pytest

from tribunal.application.answer_service import AnswerService, GameUnresolved, StrategyUnavailable
from tribunal.domain.answer import Answer, Source
from tribunal.domain.game import GameStores

ONE_GAME = {"catan": GameStores(rule="vs_catan_rule", strategy="vs_catan_strategy")}


class RecordingRetriever:
    def __init__(self, text: str, sources: list[Source] | None = None) -> None:
        self.text = text
        self.sources = sources or []
        self.calls: list[tuple[str, str]] = []

    def answer(self, question: str, *, vector_store_id: str) -> Answer:
        self.calls.append((question, vector_store_id))
        return Answer(text=self.text, sources=self.sources)


def _service(
    rule: RecordingRetriever | None = None,
    strategy: RecordingRetriever | None = None,
    stores: dict[str, GameStores] | None = None,
) -> AnswerService:
    return AnswerService(
        rule or RecordingRetriever("rule"),
        strategy or RecordingRetriever("strategy"),
        stores=ONE_GAME if stores is None else stores,
    )


def test_ask_delegates_to_retriever() -> None:
    """タグ付きなら注記が付かないので、retriever の戻り値がそのまま返る。"""
    rule = RecordingRetriever("盗賊は 7 が出たときに動かす。", [Source("rulebook", "f://1")])

    answer = _service(rule=rule).ask("ルール: カタンの盗賊は?")

    assert answer.text == "盗賊は 7 が出たときに動かす。"
    assert answer.sources == [Source("rulebook", "f://1")]
    assert rule.calls == [("カタンの盗賊は?", "vs_catan_rule")]


def test_answer_sources_default_is_not_shared() -> None:
    """sources の default が instance 間で共有されない（field(default_factory) の確認）。"""
    a = Answer(text="a")
    b = Answer(text="b")

    a.sources.append(Source(title="rulebook", uri="r2://catan/rulebook.pdf"))

    assert b.sources == []


def test_strategy_tag_routes_to_the_games_strategy_store() -> None:
    rule, strategy = RecordingRetriever("rule"), RecordingRetriever("strategy")

    answer = _service(rule, strategy).ask("戦略: 序盤のおすすめ")

    assert answer.text == "strategy"
    assert strategy.calls == [("序盤のおすすめ", "vs_catan_strategy")]
    assert rule.calls == []


def test_untagged_question_gets_a_note_about_the_routing() -> None:
    """タグなしのときは、どちらとして処理したかを添える。"""
    answer = _service().ask("盗賊はどう動かす?")

    assert answer.text.startswith("rule")
    assert "ルールとして回答しました" in answer.text


def test_tagged_question_gets_no_note() -> None:
    answer = _service().ask("ルール: 盗賊はどう動かす?")

    assert answer.text == "rule"


def test_ambiguous_falls_back_to_rule() -> None:
    """rule 質問を strategy で答えると非公式資料でルールを語ることになる。"""
    rule, strategy = RecordingRetriever("rule"), RecordingRetriever("strategy")

    answer = _service(rule, strategy).ask("このドラフトのルールは?")

    assert answer.text.startswith("rule")
    assert strategy.calls == []


def test_strategy_without_store_raises_instead_of_answering_from_rule() -> None:
    """Store 未整備時に rule 資料で戦略を語らない。"""
    rule, strategy = RecordingRetriever("rule"), RecordingRetriever("strategy")
    stores = {"catan": GameStores(rule="vs_catan_rule", strategy="")}

    with pytest.raises(StrategyUnavailable):
        _service(rule, strategy, stores).ask("戦略: 序盤のおすすめ")

    assert rule.calls == []
    assert strategy.calls == []


def test_game_id_selects_that_games_store() -> None:
    rule = RecordingRetriever("rule")
    stores = {
        "catan": GameStores(rule="vs_catan_rule", strategy=""),
        "agricola": GameStores(rule="vs_agricola_rule", strategy=""),
    }

    _service(rule, stores=stores).ask("ルール: 収穫は?", game_id="agricola")

    assert rule.calls == [("収穫は?", "vs_agricola_rule")]


def test_multiple_games_without_game_id_are_not_searched_together() -> None:
    rule = RecordingRetriever("rule")
    stores = {
        "catan": GameStores(rule="vs_catan_rule", strategy=""),
        "agricola": GameStores(rule="vs_agricola_rule", strategy=""),
    }

    with pytest.raises(GameUnresolved):
        _service(rule, stores=stores).ask("ルール: 収穫は?")

    assert rule.calls == []


def test_unknown_game_id_is_unresolved() -> None:
    with pytest.raises(GameUnresolved):
        _service().ask("ルール: 収穫は?", game_id="agricola")


def test_game_without_rule_store_is_not_a_candidate() -> None:
    """rule が未設定のゲームは数えないので、残る 1 ゲームに解決される。"""
    rule = RecordingRetriever("rule")
    stores = {
        "catan": GameStores(rule="vs_catan_rule", strategy=""),
        "agricola": GameStores(rule="", strategy="vs_agricola_strategy"),
    }

    _service(rule, stores=stores).ask("ルール: 盗賊は?")

    assert rule.calls == [("盗賊は?", "vs_catan_rule")]


def test_no_rule_store_fails_at_construction() -> None:
    """Strategy Store があっても Rule Store の代わりにしない。"""
    with pytest.raises(ValueError):
        _service(stores={"catan": GameStores(rule="", strategy="vs_catan_strategy")})
