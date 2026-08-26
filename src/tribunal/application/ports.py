from typing import Protocol

from tribunal.domain.answer import Answer


class Retriever(Protocol):
    """Vector Store を検索して回答を組み立てる。"""

    def answer(self, question: str, *, game_id: str | None = None) -> Answer: ...
