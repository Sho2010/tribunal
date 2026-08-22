from tribunal.application.answer_service import AnswerService
from tribunal.domain.answer import Answer, Source


class StubRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def answer(self, question: str, *, game_id: str | None = None) -> Answer:
        self.calls.append((question, game_id))
        return Answer(text="盗賊は 7 が出たときに動かす。", sources=[Source("rulebook", "f://1")])


def test_ask_delegates_to_retriever() -> None:
    retriever = StubRetriever()

    answer = AnswerService(retriever).ask("カタンの盗賊のルールは?")

    assert answer.text == "盗賊は 7 が出たときに動かす。"
    assert answer.sources == [Source("rulebook", "f://1")]
    assert retriever.calls == [("カタンの盗賊のルールは?", None)]


def test_ask_passes_game_id_through() -> None:
    """game_id は keyword-only。Phase 1 ではユーザーが明示する前提。"""
    retriever = StubRetriever()

    AnswerService(retriever).ask("盗賊のルールは?", game_id="catan")

    assert retriever.calls == [("盗賊のルールは?", "catan")]


def test_answer_sources_default_is_not_shared() -> None:
    """sources の default が instance 間で共有されない（field(default_factory) の確認）。"""
    a = Answer(text="a")
    b = Answer(text="b")

    a.sources.append(Source(title="rulebook", uri="r2://catan/rulebook.pdf"))

    assert b.sources == []
