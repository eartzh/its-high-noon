import logging
import uuid
from datetime import datetime

from src.const import SCHEDULER, QUESTIONS_DATABASE
from linebot.v3.messaging import (
    ApiClient,
    BroadcastRequest, TextMessage,
    MessagingApi, Message, ValidateMessageRequest
)
from pydantic import StrictStr, StrictBool

from src.database.question import Question
from src.line import CONFIGURATION

LOGGER = logging.getLogger(__name__)

TODAY_QUESTION: Question | None = None

RAN_OUT_QUESTIONS = "We ran out of questions!!!"


def make_question() -> str:
    LOGGER.info("Making question")
    global TODAY_QUESTION
    TODAY_QUESTION = QUESTIONS_DATABASE.random_question(True)
    return TODAY_QUESTION.make_question() if TODAY_QUESTION else RAN_OUT_QUESTIONS


def make_answer() -> str:
    LOGGER.info("Making answer")
    global TODAY_QUESTION
    return TODAY_QUESTION.make_answer() if TODAY_QUESTION else RAN_OUT_QUESTIONS


def countdown() -> int:
    gsat_data = datetime(2025, 1, 18)
    today = datetime.now()
    return (gsat_data - today).days


def send_question():
    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        result = line_bot_api.broadcast(
            broadcast_request=BroadcastRequest(
                messages=[
                    TextMessage(
                        text=StrictStr(str(countdown())),
                        emojis=None, quoteToken=None, quickReply=None
                    )
                    , TextMessage(
                        text=StrictStr(make_question()),
                        emojis=None, quoteToken=None, quickReply=None
                    )],
                notificationDisabled=StrictBool(False)
            ),
            x_line_retry_key=StrictStr(str(uuid.uuid4())),
        )


def send_answer():
    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.broadcast(
            broadcast_request=BroadcastRequest(
                messages=[TextMessage(
                    text=StrictStr(make_answer()),
                    emojis=None,
                    quoteToken=None,
                    quickReply=None
                )],
                notificationDisabled=StrictBool(False)
            ),
            x_line_retry_key=StrictStr(str(uuid.uuid4())),
        )


def register():
    SCHEDULER.register(send_question, "08:00", True)
    SCHEDULER.register(send_answer, "10:00", True)
