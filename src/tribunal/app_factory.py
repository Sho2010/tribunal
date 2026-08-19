import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_app(platforms: list[str]) -> FastAPI:
    """有効化する chat platform の adapter を選んで FastAPI app を組む合成の中心。

    domain / application は platform 非依存で共通。ここで adapter を mount するだけ。
    adapter の import を遅延させることで、有効化した platform の依存/環境変数だけを要求する。
    """
    app = FastAPI(title="boardgame-ai")

    @app.get("/")
    def health():
        return {"status": "ok", "platforms": platforms}

    for platform in platforms:
        if platform == "slack":
            from tribunal.adapters.slack.app import register as register_slack

            register_slack(app)
        # 注: Discord は Gateway 方式（mention/自由文に反応）に寄せる方針。
        #     Gateway は websocket 常時接続で FastAPI に mount できないため、ここには入れず
        #     独立 entrypoint（src/entrypoints/discord.py, 別 service）として動かす。
        #     ※ Discord 対応自体を見送る可能性あり。
        else:
            raise ValueError(f"unknown platform: {platform!r}")
        logger.info("registered adapter: %s", platform)

    return app
