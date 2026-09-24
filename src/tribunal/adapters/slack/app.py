import logging
import os
import re
import time
from typing import Any

from fastapi import FastAPI, Request, Response
from slack_bolt import Ack, App, Say
from slack_bolt.adapter.fastapi import SlackRequestHandler

from tribunal.application.answer_service import AnswerService, Unanswerable
from tribunal.domain.answer import Answer
from tribunal.infra.sprites import task_hold

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

    def _hold_name(event: dict[str, Any]) -> str:
        return f"slack-answer-{event.get('thread_ts') or event.get('ts')}"

    def ack_and_hold(ack: Ack, event: dict[str, Any]) -> None:
        # ack を返し終えると inbound request が切れた扱いになり、Sprite は pause して
        # よくなる。lazy 側で取りに行くと間に合わないので、ここで hold を立てる。
        task_hold.acquire(_hold_name(event))
        ack()

    def respond_to_mention(event: dict[str, Any], say: Say) -> None:
        question = _strip_mention(event.get("text", ""))
        thread_ts = event.get("thread_ts") or event.get("ts")
        logger.info("app_mention received: %r", question)
        try:
            started = time.monotonic()
            say(text=ACCEPTED_REPLY, thread_ts=thread_ts)
            logger.info("accepted reply posted in %.2fs", time.monotonic() - started)
            answer = answer_service.ask(question)
            logger.info("answer generated: %d chars", len(answer.text))
            say(text=_format(answer), thread_ts=thread_ts)
        except Unanswerable as exc:
            logger.info("%s: %r", type(exc).__name__, question)
            say(text=str(exc), thread_ts=thread_ts)
        except Exception:
            logger.exception("failed to respond: %r", question)
            say(text=ERROR_REPLY, thread_ts=thread_ts)
        finally:
            task_hold.release(task_hold.sanitize_name(_hold_name(event)))

    # ack は 3 秒以内に返す必要がある。回答生成はそれより長いので lazy 側で走らせる。
    bolt_app.event("app_mention")(ack=ack_and_hold, lazy=[respond_to_mention])

    return bolt_app


def _format(answer: Answer) -> str:
    """回答本文に出典を添える。"""
    if not answer.sources:
        return answer.text
    citations = "\n".join(f"• {source.title}" for source in answer.sources)
    return f"{answer.text}\n\n*出典*\n{citations}"


def register(
    app: FastAPI,
    answer_service: AnswerService,
    *,
    verify_token: bool = True,
) -> None:
    """FastAPI に POST /slack/events を mount する。"""
    # env を読むのはここから。import しただけで SLACK_* を要求しないため。
    handler = SlackRequestHandler(_build_bolt_app(answer_service, verify_token=verify_token))

    @app.post("/slack/events")
    async def slack_events(req: Request) -> Response:
        return await handler.handle(req)
