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
class Classified:
    """判定結果と、タグを除去した質問文。"""

    intent: Intent
    question: str
    tagged: bool


class IntentClassifier(Protocol):
    """質問文から intent を判定する。"""

    def classify(self, question: str) -> Classified: ...


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


class KeywordIntentClassifier:
    """明示タグ → rule keyword → strategy keyword → 既定 Rule の順で判定する。"""

    def classify(self, question: str) -> Classified:
        stripped = _STRATEGY_TAG.sub("", question, count=1)
        if stripped != question:
            return Classified(Intent.STRATEGY, stripped.strip(), tagged=True)

        stripped = _RULE_TAG.sub("", question, count=1)
        if stripped != question:
            return Classified(Intent.RULE, stripped.strip(), tagged=True)

        text = question.strip()
        # rule を先に見る。「強い制約ですか」のように strategy 語を含む rule 質問を拾うため。
        is_rule = any(keyword in text for keyword in RULE_KEYWORDS)
        is_strategy = any(keyword.lower() in text.lower() for keyword in STRATEGY_KEYWORDS)

        if is_rule and is_strategy:
            return Classified(Intent.AMBIGUOUS, text, tagged=False)
        if is_rule:
            return Classified(Intent.RULE, text, tagged=False)
        if is_strategy:
            return Classified(Intent.STRATEGY, text, tagged=False)
        return Classified(Intent.RULE, text, tagged=False)
