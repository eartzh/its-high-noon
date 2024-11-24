import logging
import uuid
from datetime import datetime

from src.const import SCHEDULER, QUESTIONS_DATABASE, USERS_DATABASE
from linebot.v3.messaging import (
    ApiClient,
    BroadcastRequest, TextMessage,
    MessagingApi, MulticastRequest
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


def send_msgs(msgs):
    targets = USERS_DATABASE.get_enabled_users()
    splited_targets = [targets[i:i + 500] for i in range(0, len(targets), 500)]

    requests = ([
        MulticastRequest(
            messages=msgs,
            to=t,
            notificationDisabled=None,
            customAggregationUnits=None
        ) for t in splited_targets])

    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        for req in requests:
            line_bot_api.multicast(req, x_line_retry_key=StrictStr(str(uuid.uuid4())))


def send_question():
    send_msgs([TextMessage(
        text=StrictStr(make_question()),
        emojis=None,
        quoteToken=None,
        quickReply=None
    )])


def send_answer():
    send_msgs([TextMessage(
        text=StrictStr(make_answer()),
        emojis=None,
        quoteToken=None,
        quickReply=None
    )])


def register():
    SCHEDULER.register(send_question, "08:00", True)
    SCHEDULER.register(send_answer, "10:00", True)
