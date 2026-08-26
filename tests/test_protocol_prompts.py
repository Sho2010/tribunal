from tribunal.application.rule.protocol import adjudicator_prompt
from tribunal.application.strategy.protocol import analyst_prompt


def test_adjudicator_prompt_is_readable() -> None:
    assert adjudicator_prompt().strip()


def test_analyst_prompt_is_readable() -> None:
    assert analyst_prompt().strip()


def test_analyst_prompt_declares_answer_shape() -> None:
    """Strategy 回答は 前提 / 評価軸 / 複数候補 / trade-off を明示する（arch §24）。"""
    prompt = analyst_prompt()

    for section in ("前提", "評価軸", "候補", "trade-off"):
        assert section in prompt
