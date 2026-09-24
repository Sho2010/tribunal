import pytest

from tribunal.application.answer_service import AnswerService
from tribunal.domain.answer import Answer
from tribunal.domain.game import Game, GameStores


@pytest.fixture
def slack_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack adapter の register() が要求する環境変数をダミー値で用意する。

    ダミー値で通るのは `create_app(..., verify_credentials=False)` と併用する場合のみ。
    既定では slack_bolt が App 生成時に `auth.test` を叩いて token を検証するため、
    ネットワークアクセスが発生し BoltError になる。
    """
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-signing-secret")


class _StubRetriever:
    def answer(self, question: str, *, vector_store_id: str) -> Answer:
        return Answer(text="stub")


class _StubResolver:
    def resolve(self, question: str, *, game_id: str | None = None) -> Game:
        return Game(
            id="catan",
            name="Catan",
            aliases=(),
            identifying_terms=(),
            stores=GameStores(rule="vs_test", strategy=""),
        )


@pytest.fixture
def answer_service() -> AnswerService:
    """OpenAI を呼ばない AnswerService。"""
    return AnswerService(_StubRetriever(), _StubRetriever(), resolver=_StubResolver())
