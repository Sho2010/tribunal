import pytest

from tribunal.adapters.slack.app import _strip_mention


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("<@U123456> 盗賊のルールは?", "盗賊のルールは?"),
        ("  <@U123456>   盗賊のルールは?  ", "盗賊のルールは?"),
        ("<@U123456>", ""),
        ("mention なしの質問", "mention なしの質問"),
        ("", ""),
        # 先頭以外の mention は本文の一部として残す
        ("これは <@U123456> のこと?", "これは <@U123456> のこと?"),
    ],
)
def test_strip_mention(raw: str, expected: str) -> None:
    assert _strip_mention(raw) == expected


def test_slack_adapter_is_importable_without_env() -> None:
    """module import だけでは SLACK_* を要求しない（env 読み込みは register() の中）。"""
    import importlib

    import tribunal.adapters.slack.app as slack_app

    importlib.reload(slack_app)  # env 未設定のまま再 import しても落ちない
