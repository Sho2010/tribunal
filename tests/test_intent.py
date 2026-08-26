import pytest

from tribunal.application.pipeline.intent import Intent, KeywordIntentClassifier


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
    result = KeywordIntentClassifier().classify(raw)

    assert result.intent is Intent.STRATEGY
    assert result.question == expected
    assert result.tagged is True


@pytest.mark.parametrize(
    "raw",
    ["ルール: 家族を増やせる?", "rule:家族を増やせる?", "[ルール] 家族を増やせる?"],
)
def test_rule_tag_wins_over_strategy_keyword(raw: str) -> None:
    result = KeywordIntentClassifier().classify(raw)

    assert result.intent is Intent.RULE
    assert result.tagged is True


def test_tag_is_only_recognized_at_line_start() -> None:
    """本文中の言及をタグとして拾わない。"""
    result = KeywordIntentClassifier().classify("この戦略: について教えて")

    assert result.tagged is False


def test_strategy_keyword_routes_to_strategy() -> None:
    result = KeywordIntentClassifier().classify("序盤の定石を教えて")

    assert result.intent is Intent.STRATEGY
    assert result.tagged is False


def test_rule_keyword_is_checked_before_strategy() -> None:
    """strategy 語を含む rule 質問を取りこぼさない。"""
    result = KeywordIntentClassifier().classify("この効果は強制ですか")

    assert result.intent is Intent.RULE


def test_both_keywords_is_ambiguous() -> None:
    result = KeywordIntentClassifier().classify("このドラフトのルールは?")

    assert result.intent is Intent.AMBIGUOUS


def test_no_keyword_defaults_to_rule() -> None:
    result = KeywordIntentClassifier().classify("盗賊はどう動かす?")

    assert result.intent is Intent.RULE
    assert result.tagged is False
