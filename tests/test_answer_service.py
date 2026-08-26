import pytest

from tribunal.application.answer_service import AnswerService, StrategyUnavailable
from tribunal.domain.answer import Answer, Source


class StubRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def answer(self, question: str, *, game_id: str | None = None) -> Answer:
        self.calls.append((question, game_id))
        return Answer(text="盗賊は 7 が出たときに動かす。", sources=[Source("rulebook", "f://1")])


def test_ask_delegates_to_retriever() -> None:
    """タグ付きなら注記が付かないので、retriever の戻り値がそのまま返る。"""
    retriever = StubRetriever()

    answer = AnswerService(retriever).ask("ルール: カタンの盗賊は?")

    assert answer.text == "盗賊は 7 が出たときに動かす。"
    assert answer.sources == [Source("rulebook", "f://1")]
    assert retriever.calls == [("カタンの盗賊は?", None)]


def test_ask_passes_game_id_through() -> None:
    """game_id は keyword-only。Phase 1 ではユーザーが明示する前提。"""
    retriever = StubRetriever()

    AnswerService(retriever).ask("ルール: 盗賊は?", game_id="catan")

    assert retriever.calls == [("盗賊は?", "catan")]


def test_answer_sources_default_is_not_shared() -> None:
    """sources の default が instance 間で共有されない（field(default_factory) の確認）。"""
    a = Answer(text="a")
    b = Answer(text="b")

    a.sources.append(Source(title="rulebook", uri="r2://catan/rulebook.pdf"))

    assert b.sources == []


class RecordingRetriever:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[tuple[str, str | None]] = []

    def answer(self, question: str, *, game_id: str | None = None) -> Answer:
        self.calls.append((question, game_id))
        return Answer(text=self.text)


def test_strategy_tag_routes_to_strategy_retriever() -> None:
    rule, strategy = RecordingRetriever("rule"), RecordingRetriever("strategy")

    answer = AnswerService(rule, strategy_retriever=strategy).ask("戦略: 序盤のおすすめ")

    assert answer.text == "strategy"
    assert strategy.calls == [("序盤のおすすめ", None)]
    assert rule.calls == []


def test_untagged_question_gets_a_note_about_the_routing() -> None:
    """タグなしのときは、どちらとして処理したかを添える（arch §39）。"""
    answer = AnswerService(RecordingRetriever("rule")).ask("盗賊はどう動かす?")

    assert answer.text.startswith("rule")
    assert "ルールとして回答しました" in answer.text


def test_tagged_question_gets_no_note() -> None:
    answer = AnswerService(RecordingRetriever("rule")).ask("ルール: 盗賊はどう動かす?")

    assert answer.text == "rule"


def test_ambiguous_falls_back_to_rule() -> None:
    """rule 質問を strategy で答えると非公式資料でルールを語ることになる（arch §39）。"""
    rule, strategy = RecordingRetriever("rule"), RecordingRetriever("strategy")

    answer = AnswerService(rule, strategy_retriever=strategy).ask("このドラフトのルールは?")

    assert answer.text.startswith("rule")
    assert strategy.calls == []


def test_strategy_without_store_raises_instead_of_answering_from_rule() -> None:
    """Store 未整備時に rule 資料で戦略を語らない（arch §8 の trust boundary）。"""
    rule = RecordingRetriever("rule")

    with pytest.raises(StrategyUnavailable):
        AnswerService(rule).ask("戦略: 序盤のおすすめ")

    assert rule.calls == []
