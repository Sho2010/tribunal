from collections.abc import Mapping

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
from tribunal.domain.answer import Answer
from tribunal.domain.game import GameStores

RULE_NOTE = "（ルールとして回答しました。戦略の質問なら「戦略:」を付けてください）"
STRATEGY_NOTE = "（戦略として回答しました。ルールの質問なら「ルール:」を付けてください）"
STRATEGY_UNAVAILABLE = (
    "戦略の質問と判定しましたが、戦略資料がまだ整備されていないため回答できません。"
)
GAME_UNRESOLVED = "どのゲームについての質問か特定できないため回答できません。"


class Unanswerable(Exception):
    """回答を生成せずに、理由をユーザーへ返す。"""


class StrategyUnavailable(Unanswerable):
    """そのゲームの Strategy Store が設定されていない。"""


class GameUnresolved(Unanswerable):
    """質問の対象ゲームを 1 つに決められない。"""


class AnswerService:
    """Chat platform に依存しない問い合わせ処理。Chat adapter が触ってよい唯一の入口。"""

    def __init__(
        self,
        rule_retriever: Retriever,
        strategy_retriever: Retriever,
        *,
        stores: Mapping[str, GameStores],
        classifier: IntentClassifier | None = None,
    ) -> None:
        self._stores = stores
        self._rule_retriever = rule_retriever
        self._strategy_retriever = strategy_retriever
        self._classifier = classifier or IntentClassifierChain(
            TagIntentClassifier(), KeywordIntentClassifier()
        )

    def ask(self, question: str, *, game_id: str | None = None) -> Answer:
        stores = self._resolve_game(game_id)
        classification = self._classifier.classify(IntentQuery.of(question))
        if classification.intent is Intent.STRATEGY:
            return self._ask_strategy(classification, stores)
        return self._ask_rule(classification, stores)

    def _resolve_game(self, game_id: str | None) -> GameStores:
        # Rule Store の無いゲームは回答対象にしない。
        if game_id is None:
            candidates = [s for s in self._stores.values() if s.rule]
            if len(candidates) != 1:
                raise GameUnresolved(GAME_UNRESOLVED)
            return candidates[0]
        stores = self._stores.get(game_id)
        if stores is None or not stores.rule:
            raise GameUnresolved(GAME_UNRESOLVED)
        return stores

    def _ask_rule(self, classification: Classification, stores: GameStores) -> Answer:
        answer = self._rule_retriever.answer(
            classification.query.question, vector_store_id=stores.rule
        )
        return _with_note(answer, RULE_NOTE if not classification.tagged else None)

    def _ask_strategy(self, classification: Classification, stores: GameStores) -> Answer:
        if not stores.strategy:
            raise StrategyUnavailable(STRATEGY_UNAVAILABLE)
        answer = self._strategy_retriever.answer(
            classification.query.question, vector_store_id=stores.strategy
        )
        return _with_note(answer, STRATEGY_NOTE if not classification.tagged else None)


def _with_note(answer: Answer, note: str | None) -> Answer:
    """タグなしで投げられたとき、どちらとして処理したかを添える。"""
    if note is None:
        return answer
    return Answer(text=f"{answer.text}\n\n{note}", sources=answer.sources)
