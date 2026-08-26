from tribunal.application.pipeline.intent import (
    Classified,
    Intent,
    IntentClassifier,
    KeywordIntentClassifier,
)
from tribunal.application.ports import Retriever
from tribunal.domain.answer import Answer

RULE_NOTE = "（ルールとして回答しました。戦略の質問なら「戦略:」を付けてください）"
STRATEGY_NOTE = "（戦略として回答しました。ルールの質問なら「ルール:」を付けてください）"
STRATEGY_UNAVAILABLE = (
    "戦略の質問と判定しましたが、戦略資料がまだ整備されていないため回答できません。"
)


class StrategyUnavailable(Exception):
    """Strategy retriever が構成されていない。"""


class AnswerService:
    """Chat platform に依存しない問い合わせ処理。Chat adapter が触ってよい唯一の入口。"""

    def __init__(
        self,
        retriever: Retriever,
        *,
        strategy_retriever: Retriever | None = None,
        classifier: IntentClassifier | None = None,
    ) -> None:
        self._retriever = retriever
        self._strategy_retriever = strategy_retriever
        self._classifier = classifier or KeywordIntentClassifier()

    def ask(self, question: str, *, game_id: str | None = None) -> Answer:
        classified = self._classifier.classify(question)
        if classified.intent is Intent.STRATEGY:
            return self._ask_strategy(classified, game_id=game_id)
        # AMBIGUOUS は Rule に倒す。rule 質問を strategy で答えると非公式資料で
        # ルールを語ることになる（arch §39）。
        return self._ask_rule(classified, game_id=game_id)

    def _ask_rule(self, classified: Classified, *, game_id: str | None) -> Answer:
        answer = self._retriever.answer(classified.question, game_id=game_id)
        return _with_note(answer, RULE_NOTE if not classified.tagged else None)

    def _ask_strategy(self, classified: Classified, *, game_id: str | None) -> Answer:
        if self._strategy_retriever is None:
            raise StrategyUnavailable(STRATEGY_UNAVAILABLE)
        answer = self._strategy_retriever.answer(classified.question, game_id=game_id)
        return _with_note(answer, STRATEGY_NOTE if not classified.tagged else None)


def _with_note(answer: Answer, note: str | None) -> Answer:
    """タグなしで投げられたとき、どちらとして処理したかを添える。"""
    if note is None:
        return answer
    return Answer(text=f"{answer.text}\n\n{note}", sources=answer.sources)
