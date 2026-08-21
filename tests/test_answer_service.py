from tribunal.application.answer_service import FIXED_REPLY, AnswerService
from tribunal.domain.answer import Answer, Source


def test_ask_returns_answer() -> None:
    answer = AnswerService().ask("カタンの盗賊のルールは?")

    assert isinstance(answer, Answer)
    assert answer.text == FIXED_REPLY


def test_ask_accepts_game_id() -> None:
    """game_id は keyword-only。Phase 1 ではユーザーが明示する前提。"""
    answer = AnswerService().ask("盗賊のルールは?", game_id="catan")

    assert answer.text == FIXED_REPLY


def test_answer_sources_default_is_not_shared() -> None:
    """sources の default が instance 間で共有されない（field(default_factory) の確認）。"""
    a = Answer(text="a")
    b = Answer(text="b")

    a.sources.append(Source(title="rulebook", uri="r2://catan/rulebook.pdf"))

    assert b.sources == []
