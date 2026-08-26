from pathlib import Path

_PROMPT_DIR = Path(__file__).parent / "prompts"


def analyst_prompt() -> str:
    """Strategy Analyst Protocol の prompt を読む。"""
    return (_PROMPT_DIR / "analyst.md").read_text(encoding="utf-8")
