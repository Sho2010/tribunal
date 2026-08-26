import logging
import os
import re
from typing import Any

from fastapi import FastAPI, Request, Response
from slack_bolt import App, Say
from slack_bolt.adapter.fastapi import SlackRequestHandler

from tribunal.application.answer_service import AnswerService, StrategyUnavailable
from tribunal.application.rule.protocol import adjudicator_prompt
from tribunal.application.strategy.protocol import analyst_prompt
from tribunal.domain.answer import Answer
from tribunal.infra.openai.file_search_retriever import (
    STRATEGY_STORE_ENV,
    FileSearchRetriever,
)

logger = logging.getLogger(__name__)

ACCEPTED_REPLY = "🎲 調べています…"
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
            say(text=ACCEPTED_REPLY, thread_ts=thread_ts)
            answer = answer_service.ask(question)
            logger.info("answer generated: %d chars", len(answer.text))
            say(text=_format(answer), thread_ts=thread_ts)
        except StrategyUnavailable as exc:
            logger.info("strategy unavailable: %r", question)
            say(text=str(exc), thread_ts=thread_ts)
        except Exception:
            logger.exception("failed to respond: %r", question)
            say(text=ERROR_REPLY, thread_ts=thread_ts)

    # ack は 3 秒以内に返す必要がある。回答生成はそれより長いので lazy 側で走らせる。
    bolt_app.event("app_mention")(ack=lambda ack: ack(), lazy=[respond_to_mention])

    return bolt_app


def _format(answer: Answer) -> str:
    """回答本文に出典を添える。"""
    if not answer.sources:
        return answer.text
    citations = "\n".join(f"• {source.title}" for source in answer.sources)
    return f"{answer.text}\n\n*出典*\n{citations}"


def _default_service() -> AnswerService:
    """env から AnswerService を組み立てる。"""
    strategy = None
    # Strategy Store は未整備でよい。未設定なら strategy 判定時に StrategyUnavailable。
    if os.environ.get(STRATEGY_STORE_ENV):
        strategy = FileSearchRetriever.for_strategy(analyst_prompt())
    return AnswerService(
        FileSearchRetriever.for_rule(adjudicator_prompt()),
        strategy_retriever=strategy,
    )


def register(
    app: FastAPI,
    *,
    verify_token: bool = True,
    answer_service: AnswerService | None = None,
) -> None:
    """FastAPI に POST /slack/events を mount する。"""
    # env を読むのはここから。import しただけで SLACK_* / OPENAI_* を要求しないため。
    service = answer_service or _default_service()
    handler = SlackRequestHandler(_build_bolt_app(service, verify_token=verify_token))

    @app.post("/slack/events")
    async def slack_events(req: Request) -> Response:
        return await handler.handle(req)
