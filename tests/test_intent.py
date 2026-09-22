import pytest

from tribunal.application.pipeline.intent import (
    Classification,
    Intent,
    IntentClassifierChain,
    KeywordIntentClassifier,
    TagIntentClassifier,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("戦略: 序盤のおすすめ", "序盤のおすすめ"),
        ("戦略:序盤のおすすめ", "序盤のおすすめ"),
        ("戦略：序盤のおすすめ", "序盤のおすすめ"),
        ("strategy: 序盤のおすすめ", "序盤のおすすめ"),
        ("[戦略] 序盤のおすすめ", "序盤のおすすめ"),
        ("[strategy] 序盤のおすすめ", "序盤のおすすめ"),
        ("  [ 戦略 ]  序盤のおすすめ", "序盤のおすすめ"),
    ],
)
def test_strategy_tag_is_stripped_from_question(raw: str, expected: str) -> None:
    """タグは検索クエリに混ぜない。"""
    result = TagIntentClassifier().classify(raw)

    assert result.intent is Intent.STRATEGY
    assert result.question == expected
    assert result.tagged is True


@pytest.mark.parametrize(
    "raw",
    ["ルール: 家族を増やせる?", "rule:家族を増やせる?", "[ルール] 家族を増やせる?"],
)
def test_rule_tag_is_recognized(raw: str) -> None:
    result = TagIntentClassifier().classify(raw)

    assert result.intent is Intent.RULE
    assert result.tagged is True


def test_tag_is_only_recognized_at_line_start() -> None:
    """本文中の言及をタグとして拾わない。"""
    result = TagIntentClassifier().classify("この戦略: について教えて")

    assert result.intent is Intent.AMBIGUOUS
    assert result.tagged is False


def test_strategy_keyword_routes_to_strategy() -> None:
    result = KeywordIntentClassifier().classify("序盤の定石を教えて")

    assert result.intent is Intent.STRATEGY
    assert result.tagged is False


def test_rule_keyword_routes_to_rule() -> None:
    result = KeywordIntentClassifier().classify("この効果は強制ですか")

    assert result.intent is Intent.RULE
    assert result.tagged is False


@pytest.mark.parametrize("raw", ["このドラフトのルールは?", "盗賊はどう動かす?"])
def test_both_or_no_keywords_is_ambiguous(raw: str) -> None:
    result = KeywordIntentClassifier().classify(raw)

    assert result.intent is Intent.AMBIGUOUS


class FixedClassifier:
    def __init__(self, intent: Intent) -> None:
        self.intent = intent
        self.calls: list[str] = []

    def classify(self, question: str) -> Classification:
        self.calls.append(question)
        return Classification(self.intent, f"{self.intent.value}:{question}", tagged=True)


def test_chain_returns_first_non_ambiguous_result() -> None:
    first = FixedClassifier(Intent.AMBIGUOUS)
    second = FixedClassifier(Intent.STRATEGY)
    third = FixedClassifier(Intent.RULE)

    result = IntentClassifierChain(first, second, third).classify("q")

    assert result == Classification(Intent.STRATEGY, "strategy:q", tagged=True)
    assert first.calls == ["q"]
    assert third.calls == []


def test_chain_falls_back_to_rule_when_nobody_decides() -> None:
    chain = IntentClassifierChain(FixedClassifier(Intent.AMBIGUOUS))

    result = chain.classify("  盗賊はどう動かす?  ")

    assert result == Classification(Intent.RULE, "盗賊はどう動かす?", tagged=False)


def test_tag_wins_over_keyword_in_chain() -> None:
    chain = IntentClassifierChain(TagIntentClassifier(), KeywordIntentClassifier())

    result = chain.classify("ルール: ドラフトの定石は?")

    assert result.intent is Intent.RULE
    assert result.question == "ドラフトの定石は?"
    assert result.tagged is True
