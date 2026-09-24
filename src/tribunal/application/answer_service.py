from tribunal.application.pipeline.game import GameResolver
from tribunal.application.pipeline.intent import (
    Classification,
    Intent,
    IntentClassifier,
    IntentClassifierChain,
    IntentQuery,
    KeywordIntentClassifier,
    TagIntentClassifier,
)
from tribunal.application.ports import Retriever
from tribunal.application.unanswerable import RuleUnavailable, StrategyUnavailable
from tribunal.domain.answer import Answer
from tribunal.domain.game import Game

RULE_NOTE = "（ルールとして回答しました。戦略の質問なら「戦略:」を付けてください）"
STRATEGY_NOTE = "（戦略として回答しました。ルールの質問なら「ルール:」を付けてください）"
RULE_UNAVAILABLE = "{name} のルール資料がまだ整備されていないため回答できません。"
STRATEGY_UNAVAILABLE = (
    "戦略の質問と判定しましたが、戦略資料がまだ整備されていないため回答できません。"
)


class AnswerService:
    """Chat platform に依存しない問い合わせ処理。Chat adapter が触ってよい唯一の入口。"""

    def __init__(
        self,
        rule_retriever: Retriever,
        strategy_retriever: Retriever,
        *,
        resolver: GameResolver,
        classifier: IntentClassifier | None = None,
    ) -> None:
        self._resolver = resolver
        self._rule_retriever = rule_retriever
        self._strategy_retriever = strategy_retriever
        self._classifier = classifier or IntentClassifierChain(
            TagIntentClassifier(), KeywordIntentClassifier()
        )

    def ask(self, question: str, *, game_id: str | None = None) -> Answer:
        game = self._resolver.resolve(question, game_id=game_id)
        # Rule Store の無いゲームは、戦略の質問にも回答しない。
        if not game.stores.rule:
            raise RuleUnavailable(RULE_UNAVAILABLE.format(name=game.name))
        classification = self._classifier.classify(IntentQuery.of(question))
        if classification.intent is Intent.STRATEGY:
            return self._ask_strategy(classification, game)
        return self._ask_rule(classification, game)

    def _ask_rule(self, classification: Classification, game: Game) -> Answer:
        answer = self._rule_retriever.answer(
            classification.query.question, vector_store_id=game.stores.rule
        )
        return _with_note(answer, RULE_NOTE if not classification.tagged else None)

    def _ask_strategy(self, classification: Classification, game: Game) -> Answer:
        if not game.stores.strategy:
            raise StrategyUnavailable(STRATEGY_UNAVAILABLE)
        answer = self._strategy_retriever.answer(
            classification.query.question, vector_store_id=game.stores.strategy
        )
        return _with_note(answer, STRATEGY_NOTE if not classification.tagged else None)


def _with_note(answer: Answer, note: str | None) -> Answer:
    """タグなしで投げられたとき、どちらとして処理したかを添える。"""
    if note is None:
        return answer
    return Answer(text=f"{answer.text}\n\n{note}", sources=answer.sources)
