import logging
import os
import re

from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

from tribunal.application.answer_service import AnswerService

logger = logging.getLogger(__name__)

# HTTP Events モード: bot token で API 呼び出し、signing secret で受信リクエストを署名検証。
# （app-level token は Socket Mode 専用なので不要）
bolt_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

_answer_service = AnswerService()

_MENTION_RE = re.compile(r"^\s*<@[^>]+>\s*")


def _strip_mention(text: str) -> str:
    """先頭の <@U123456> mention を取り除いて質問本文だけにする。"""
    return _MENTION_RE.sub("", text or "").strip()


@bolt_app.event("app_mention")
def handle_app_mention(event, say):
    question = _strip_mention(event.get("text", ""))
    logger.info("app_mention received: %r", question)
    answer = _answer_service.ask(question)
    # 元メッセージがスレッド内ならそのスレッドへ、そうでなければ元メッセージにぶら下げる
    say(text=answer.text, thread_ts=event.get("thread_ts") or event.get("ts"))


_handler = SlackRequestHandler(bolt_app)


def register(app: FastAPI) -> None:
    """FastAPI アプリに Slack エンドポイントをマウントする。

    Slack の Event Subscriptions の Request URL には
    `https://<host>/slack/events` を設定する（URL verification challenge にも応答する）。
    """

    @app.post("/slack/events")
    async def slack_events(req: Request):
        return await _handler.handle(req)
