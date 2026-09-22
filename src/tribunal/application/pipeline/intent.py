import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Intent(Enum):
    """質問をどちらの protocol で処理するか。"""

    RULE = "rule"
    STRATEGY = "strategy"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Classification:
    """判定結果と、タグを除去した質問文。"""

    intent: Intent
    question: str
    tagged: bool


class IntentClassifier(Protocol):
    """質問文から intent を判定する。決められなければ AMBIGUOUS を返す。"""

    def classify(self, question: str) -> Classification: ...


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

    def classify(self, question: str) -> Classification:
        stripped = _STRATEGY_TAG.sub("", question, count=1)
        if stripped != question:
            return Classification(Intent.STRATEGY, stripped.strip(), tagged=True)

        stripped = _RULE_TAG.sub("", question, count=1)
        if stripped != question:
            return Classification(Intent.RULE, stripped.strip(), tagged=True)

        return Classification(Intent.AMBIGUOUS, question.strip(), tagged=False)


class KeywordIntentClassifier:
    """rule / strategy の keyword のうち、片方だけが含まれていればそちらと判定する。"""

    def classify(self, question: str) -> Classification:
        text = question.strip()
        is_rule = any(keyword in text for keyword in RULE_KEYWORDS)
        is_strategy = any(keyword.lower() in text.lower() for keyword in STRATEGY_KEYWORDS)

        if is_rule and not is_strategy:
            return Classification(Intent.RULE, text, tagged=False)
        if is_strategy and not is_rule:
            return Classification(Intent.STRATEGY, text, tagged=False)
        return Classification(Intent.AMBIGUOUS, text, tagged=False)


class IntentClassifierChain:
    """AMBIGUOUS 以外が返るまで順に判定し、誰も決められなければ Rule にする。"""

    def __init__(self, *classifiers: IntentClassifier) -> None:
        self._classifiers = classifiers

    def classify(self, question: str) -> Classification:
        for classifier in self._classifiers:
            classification = classifier.classify(question)
            if classification.intent is not Intent.AMBIGUOUS:
                return classification
        # rule 質問を strategy で答えると非公式資料でルールを語ることになる。
        return Classification(Intent.RULE, question.strip(), tagged=False)
