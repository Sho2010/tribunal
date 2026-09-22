import pytest

from tribunal.application.pipeline.intent import (
    Classification,
    Intent,
    IntentClassifierChain,
    IntentQuery,
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
    """タグは検索クエリに混ぜない。原文は残す。"""
    result = TagIntentClassifier().classify(IntentQuery.of(raw))

    assert result.intent is Intent.STRATEGY
    assert result.query.question == expected
    assert result.query.original == raw
    assert result.tagged is True


@pytest.mark.parametrize(
    "raw",
    ["ルール: 家族を増やせる?", "rule:家族を増やせる?", "[ルール] 家族を増やせる?"],
)
def test_rule_tag_is_recognized(raw: str) -> None:
    result = TagIntentClassifier().classify(IntentQuery.of(raw))

    assert result.intent is Intent.RULE
    assert result.tagged is True


def test_tag_is_only_recognized_at_line_start() -> None:
    """本文中の言及をタグとして拾わない。"""
    result = TagIntentClassifier().classify(IntentQuery.of("この戦略: について教えて"))

    assert result.intent is Intent.AMBIGUOUS
    assert result.tagged is False


def test_strategy_keyword_routes_to_strategy() -> None:
    result = KeywordIntentClassifier().classify(IntentQuery.of("序盤の定石を教えて"))

    assert result.intent is Intent.STRATEGY
    assert result.tagged is False


def test_rule_keyword_routes_to_rule() -> None:
    result = KeywordIntentClassifier().classify(IntentQuery.of("この効果は強制ですか"))

    assert result.intent is Intent.RULE
    assert result.tagged is False


def test_both_keywords_is_ambiguous_with_matched_keywords_as_hint() -> None:
    result = KeywordIntentClassifier().classify(IntentQuery.of("このドラフトのルールは?"))

    assert result.intent is Intent.AMBIGUOUS
    assert result.query.hints == ("keyword: rule=ルール strategy=ドラフト",)


def test_no_keyword_is_ambiguous_without_hint() -> None:
    result = KeywordIntentClassifier().classify(IntentQuery.of("盗賊はどう動かす?"))

    assert result.intent is Intent.AMBIGUOUS
    assert result.query.hints == ()


def test_with_hint_appends_without_mutating() -> None:
    query = IntentQuery.of("q").with_hint("a")

    updated = query.with_hint("b")

    assert updated.hints == ("a", "b")
    assert query.hints == ("a",)


class FixedClassifier:
    def __init__(self, intent: Intent) -> None:
        self.intent = intent
        self.received: list[IntentQuery] = []

    def classify(self, query: IntentQuery) -> Classification:
        self.received.append(query)
        return Classification(self.intent, query.with_hint(self.intent.value), tagged=False)


def test_chain_returns_first_non_ambiguous_result() -> None:
    first = FixedClassifier(Intent.AMBIGUOUS)
    second = FixedClassifier(Intent.STRATEGY)
    third = FixedClassifier(Intent.RULE)

    result = IntentClassifierChain(first, second, third).classify(IntentQuery.of("q"))

    assert result.intent is Intent.STRATEGY
    assert third.received == []


def test_chain_passes_annotated_query_to_next_classifier() -> None:
    first = FixedClassifier(Intent.AMBIGUOUS)
    second = FixedClassifier(Intent.RULE)

    IntentClassifierChain(first, second).classify(IntentQuery.of("q"))

    assert second.received == [IntentQuery(original="q", question="q", hints=("ambiguous",))]


def test_chain_falls_back_to_rule_keeping_accumulated_query() -> None:
    chain = IntentClassifierChain(TagIntentClassifier(), KeywordIntentClassifier())

    result = chain.classify(IntentQuery.of("  このドラフトのルールは?  "))

    assert result.intent is Intent.RULE
    assert result.tagged is False
    assert result.query.question == "このドラフトのルールは?"
    assert result.query.hints == ("keyword: rule=ルール strategy=ドラフト",)


def test_tag_wins_over_keyword_in_chain() -> None:
    chain = IntentClassifierChain(TagIntentClassifier(), KeywordIntentClassifier())

    result = chain.classify(IntentQuery.of("ルール: ドラフトの定石は?"))

    assert result.intent is Intent.RULE
    assert result.query.question == "ドラフトの定石は?"
    assert result.tagged is True
