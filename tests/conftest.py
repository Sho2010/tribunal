import pytest


@pytest.fixture
def slack_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack adapter の register() が要求する環境変数をダミー値で用意する。

    ダミー値で通るのは `create_app(..., verify_credentials=False)` と併用する場合のみ。
    既定では slack_bolt が App 生成時に `auth.test` を叩いて token を検証するため、
    ネットワークアクセスが発生し BoltError になる。
    """
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-signing-secret")
    # OpenAI client は生成時に API key を要求する（呼び出し時ではない）。
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("TRIBUNAL_RULE_VECTOR_STORE_ID", "vs_test")
