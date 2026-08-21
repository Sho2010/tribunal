import pytest


@pytest.fixture
def slack_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack adapter が要求する環境変数をダミー値で用意する。

    ダミー値で通るのは `create_app(..., verify_credentials=False)` と併用する場合のみ。
    既定では slack_bolt が App 生成時に `auth.test` を叩いて token を検証するため、
    ネットワークアクセスが発生し BoltError になる。
    """
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-signing-secret")
