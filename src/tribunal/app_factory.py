import logging

from fastapi import FastAPI

from tribunal.application.answer_service import AnswerService

logger = logging.getLogger(__name__)


def create_app(
    platforms: list[str],
    *,
    verify_credentials: bool = True,
    answer_service: AnswerService | None = None,
) -> FastAPI:
    """有効化する platform の adapter を mount した FastAPI app を返す。"""
    app = FastAPI(title="boardgame-ai")

    @app.get("/")
    def health() -> dict[str, object]:
        return {"status": "ok", "platforms": platforms}

    for platform in platforms:
        if platform == "slack":
            # 遅延 import: 有効化していない platform の依存 / env を要求しない。
            from tribunal.adapters.slack.app import register as register_slack

            register_slack(app, verify_token=verify_credentials, answer_service=answer_service)
        else:
            raise ValueError(f"unknown platform: {platform!r}")
        logger.info("registered adapter: %s", platform)

    return app
