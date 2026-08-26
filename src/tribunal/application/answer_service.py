from tribunal.application.ports import Retriever
from tribunal.domain.answer import Answer


class AnswerService:
    """Chat platform に依存しない問い合わせ処理。Chat adapter が触ってよい唯一の入口。"""

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def ask(self, question: str, *, game_id: str | None = None) -> Answer:
        return self._retriever.answer(question, game_id=game_id)
