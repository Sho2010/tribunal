import re
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol


class Intent(Enum):
    """質問をどちらの protocol で処理するか。"""

    RULE = "rule"
    STRATEGY = "strategy"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class IntentQuery:
    """classifier に渡す質問。前の classifier の整形結果と hint を引き継ぐ。"""

    original: str
    question: str
    hints: tuple[str, ...] = ()

    @classmethod
    def of(cls, text: str) -> "IntentQuery":
        return cls(original=text, question=text.strip())

    def with_question(self, question: str) -> "IntentQuery":
        return replace(self, question=question)

    def with_hint(self, hint: str) -> "IntentQuery":
        return replace(self, hints=(*self.hints, hint))


@dataclass(frozen=True)
class Classification:
    """判定結果と、判定した classifier が整形・注釈した後の query。"""

    intent: Intent
    query: IntentQuery
    tagged: bool


class IntentClassifier(Protocol):
    """質問から intent を判定する。決められなければ AMBIGUOUS を返す。"""

    def classify(self, query: IntentQuery) -> Classification: ...


_STRATEGY_TAG = re.compile(
    r"^\s*(?:\[\s*(?:戦略|strategy)\s*\]|(?:戦略|strategy)\s*[:：])\s*", re.I
)
_RULE_TAG = re.compile(r"^\s*(?:\[\s*(?:ルール|rule)\s*\]|(?:ルール|rule)\s*[:：])\s*", re.I)

RULE_KEYWORDS = (
    "ルール",
    "裁定",
    "合法",
    "できますか",
    "できる？",
    "可能ですか",
    "強制",
    "任意",
    "処理",
    "タイミング",
    "順番",
)

STRATEGY_KEYWORDS = (
    "定石",
    "評価",
    "おすすめ",
    "どっちが強い",
    "強いですか",
    "有利",
    "ドラフト",
    "pick",
    "シナジー",
    "コンボ",
    "戦略",
    "方針",
    "期待値",
)


class TagIntentClassifier:
    """行頭の明示タグで判定し、タグを質問文から除去する。"""

    def classify(self, query: IntentQuery) -> Classification:
        text = query.question
        stripped = _STRATEGY_TAG.sub("", text, count=1)
        if stripped != text:
            return Classification(
                Intent.STRATEGY, query.with_question(stripped.strip()), tagged=True
            )

        stripped = _RULE_TAG.sub("", text, count=1)
        if stripped != text:
            return Classification(Intent.RULE, query.with_question(stripped.strip()), tagged=True)

        return Classification(Intent.AMBIGUOUS, query, tagged=False)


class KeywordIntentClassifier:
    """rule / strategy の keyword のうち、片方だけが含まれていればそちらと判定する。"""

    def classify(self, query: IntentQuery) -> Classification:
        text = query.question
        lowered = text.lower()
        rule_hits = [keyword for keyword in RULE_KEYWORDS if keyword in text]
        strategy_hits = [keyword for keyword in STRATEGY_KEYWORDS if keyword.lower() in lowered]

        if rule_hits or strategy_hits:
            hint = f"keyword: rule={','.join(rule_hits)} strategy={','.join(strategy_hits)}"
            query = query.with_hint(hint)

        if rule_hits and not strategy_hits:
            return Classification(Intent.RULE, query, tagged=False)
        if strategy_hits and not rule_hits:
            return Classification(Intent.STRATEGY, query, tagged=False)
        return Classification(Intent.AMBIGUOUS, query, tagged=False)


class IntentClassifierChain:
    """AMBIGUOUS 以外が返るまで順に判定し、誰も決められなければ Rule にする。"""

    def __init__(self, *classifiers: IntentClassifier) -> None:
        self._classifiers = classifiers

    def classify(self, query: IntentQuery) -> Classification:
        for classifier in self._classifiers:
            classification = classifier.classify(query)
            if classification.intent is not Intent.AMBIGUOUS:
                return classification
            query = classification.query
        # rule 質問を strategy で答えると非公式資料でルールを語ることになる。
        return Classification(Intent.RULE, query, tagged=False)
