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
    """先頭の <@U123456> mention を取り除く。"""
    return _MENTION_RE.sub("", text or "").strip()


def _build_bolt_app(answer_service: AnswerService, *, verify_token: bool = True) -> App:
    """slack_bolt の App を組み立てて listener を登録する。"""
    # App() は生成時に auth.test を叩く。verify_token=False にしないとダミー token で BoltError。
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
        say(text=answer.text, thread_ts=event.get("thread_ts") or event.get("ts"))

    return bolt_app


def register(app: FastAPI, *, verify_token: bool = True) -> None:
    """FastAPI に POST /slack/events を mount する。"""
    # env を読むのはここから。import しただけで SLACK_* を要求しないため。
    handler = SlackRequestHandler(_build_bolt_app(AnswerService(), verify_token=verify_token))

    @app.post("/slack/events")
    async def slack_events(req: Request) -> Response:
        return await handler.handle(req)
