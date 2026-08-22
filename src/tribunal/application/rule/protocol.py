from pathlib import Path

_PROMPT_DIR = Path(__file__).parent / "prompts"


def adjudicator_prompt() -> str:
    """Rule Adjudicator Protocol の prompt を読む。"""
    return (_PROMPT_DIR / "adjudicator.md").read_text(encoding="utf-8")
