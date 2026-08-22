from typing import Protocol

from tribunal.domain.answer import Answer


class RuleRetriever(Protocol):
    """Rule Store を検索して回答を組み立てる。"""

    def answer(self, question: str, *, game_id: str | None = None) -> Answer: ...
