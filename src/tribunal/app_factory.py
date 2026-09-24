import logging

from fastapi import FastAPI

from tribunal.application.answer_service import AnswerService
from tribunal.application.rule.protocol import adjudicator_prompt
from tribunal.application.strategy.protocol import analyst_prompt
from tribunal.infra.openai.file_search_retriever import FileSearchRetriever
from tribunal.knowledge.games import load_game_stores

logger = logging.getLogger(__name__)

PLATFORMS = ("slack",)


def create_app(
    platforms: list[str],
    *,
    verify_credentials: bool = True,
    answer_service: AnswerService | None = None,
) -> FastAPI:
    """有効化する platform の adapter を mount した FastAPI app を返す。"""
    unknown = [p for p in platforms if p not in PLATFORMS]
    if unknown:
        raise ValueError(f"unknown platform: {unknown[0]!r}")

    app = FastAPI(title="boardgame-ai")

    @app.get("/")
    def health() -> dict[str, object]:
        return {"status": "ok", "platforms": platforms}

    if not platforms:
        return app

    service = answer_service or _default_service()
    for platform in platforms:
        if platform == "slack":
            # 遅延 import: 有効化していない platform の依存 / env を要求しない。
            from tribunal.adapters.slack.app import register as register_slack

            register_slack(app, service, verify_token=verify_credentials)
        logger.info("registered adapter: %s", platform)

    return app


def _default_service() -> AnswerService:
    """games.yaml の Store ID から AnswerService を組み立てる。"""
    return AnswerService(
        FileSearchRetriever(adjudicator_prompt()),
        FileSearchRetriever(analyst_prompt()),
        stores=load_game_stores(),
    )
