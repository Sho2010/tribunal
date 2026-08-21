import logging
import os
import re
from typing import Any

from fastapi import FastAPI, Request, Response
from slack_bolt import App, Say
from slack_bolt.adapter.fastapi import SlackRequestHandler

from tribunal.application.answer_service import AnswerService

logger = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"^\s*<@[^>]+>\s*")


def _strip_mention(text: str) -> str:
    """先頭の <@U123456> mention を取り除いて質問本文だけにする。"""
    return _MENTION_RE.sub("", text or "").strip()


def _build_bolt_app(answer_service: AnswerService, *, verify_token: bool = True) -> App:
    """slack_bolt の App を組み立てて listener を登録する。

    環境変数の読み込みはこの関数の中でだけ行う（module import 時ではない）。
    import 時に読むと、Slack を有効化していない文脈や test から
    import しただけで SLACK_* が必須になってしまうため。

    verify_token=False で `auth.test` による起動時の token 検証を止める。
    App() はデフォルトでこの API を叩くので、test では無効化しないと
    ネットワークアクセスが発生し、ダミー token で BoltError になる。
    """
    # HTTP Events モード: bot token で API 呼び出し、signing secret で受信リクエストを署名検証。
    # （app-level token は Socket Mode 専用なので不要）
    bolt_app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        signing_secret=os.environ["SLACK_SIGNING_SECRET"],
        token_verification_enabled=verify_token,
    )

    @bolt_app.event("app_mention")
    def handle_app_mention(event: dict[str, Any], say: Say) -> None:
        question = _strip_mention(event.get("text", ""))
        logger.info("app_mention received: %r", question)
        answer = answer_service.ask(question)
        # 元メッセージがスレッド内ならそのスレッドへ、そうでなければ元メッセージにぶら下げる
        say(text=answer.text, thread_ts=event.get("thread_ts") or event.get("ts"))

    return bolt_app


def register(app: FastAPI, *, verify_token: bool = True) -> None:
    """FastAPI アプリに Slack エンドポイントをマウントする。

    Slack の Event Subscriptions の Request URL には
    `https://<host>/slack/events` を設定する（URL verification challenge にも応答する）。
    """
    handler = SlackRequestHandler(_build_bolt_app(AnswerService(), verify_token=verify_token))

    @app.post("/slack/events")
    async def slack_events(req: Request) -> Response:
        return await handler.handle(req)
