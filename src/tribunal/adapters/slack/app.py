import logging
import os
import re
from typing import Any

from fastapi import FastAPI, Request, Response
from slack_bolt import App, Say
from slack_bolt.adapter.fastapi import SlackRequestHandler

from tribunal.application.answer_service import AnswerService
from tribunal.application.rule.protocol import adjudicator_prompt
from tribunal.domain.answer import Answer
from tribunal.infra.openai.rule_retriever import OpenAIRuleRetriever

logger = logging.getLogger(__name__)

ERROR_REPLY = "回答の生成に失敗しました。"

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

    def respond_to_mention(event: dict[str, Any], say: Say) -> None:
        question = _strip_mention(event.get("text", ""))
        thread_ts = event.get("thread_ts") or event.get("ts")
        logger.info("app_mention received: %r", question)
        try:
            answer = answer_service.ask(question)
        except Exception:
            logger.exception("failed to answer: %r", question)
            say(text=ERROR_REPLY, thread_ts=thread_ts)
            return
        say(text=_format(answer), thread_ts=thread_ts)

    # ack は 3 秒以内に返す必要がある。回答生成はそれより長いので lazy 側で走らせる。
    bolt_app.event("app_mention")(ack=lambda ack: ack(), lazy=[respond_to_mention])

    return bolt_app


def _format(answer: Answer) -> str:
    """回答本文に出典を添える。"""
    if not answer.sources:
        return answer.text
    citations = "\n".join(f"• {source.title}" for source in answer.sources)
    return f"{answer.text}\n\n*出典*\n{citations}"


def register(
    app: FastAPI,
    *,
    verify_token: bool = True,
    answer_service: AnswerService | None = None,
) -> None:
    """FastAPI に POST /slack/events を mount する。"""
    # env を読むのはここから。import しただけで SLACK_* / OPENAI_* を要求しないため。
    service = answer_service or AnswerService(OpenAIRuleRetriever.from_env(adjudicator_prompt()))
    handler = SlackRequestHandler(_build_bolt_app(service, verify_token=verify_token))

    @app.post("/slack/events")
    async def slack_events(req: Request) -> Response:
        return await handler.handle(req)
