import logging
import uuid
from datetime import datetime
from pathlib import Path

from src.const import SCHEDULER, QUESTIONS_DATABASE
from linebot.v3.messaging import (
    ApiClient,
    TextMessage,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest
)
from pydantic import StrictStr

from src.database.question import Question
from src.line import CONFIGURATION

LOGGER = logging.getLogger(__name__)

TODAY_QUESTION: Question | None = None
RAN_OUT_QUESTIONS = "We ran out of questions!!!"
USER_IDS_FILE = Path("user_ids.txt")
GROUP_IDS_FILE = Path("group_ids.txt") 

def get_user_ids() -> list[str]:
    if USER_IDS_FILE.exists():
        with open(USER_IDS_FILE, "r") as file:
            return [line.strip() for line in file.readlines()]
    return []


def add_user_id(user_id: str):
    user_ids = set(get_user_ids())
    if user_id not in user_ids:
        with open(USER_IDS_FILE, "a") as file:
            file.write(f"{user_id}\n")


def get_group_ids() -> list[str]:
    if GROUP_IDS_FILE.exists():
        with open(GROUP_IDS_FILE, "r") as file:
            return [line.strip() for line in file.readlines()]
    return []


def add_group_id(group_id: str):
    group_ids = set(get_group_ids())
    if group_id not in group_ids:
        with open(GROUP_IDS_FILE, "a") as file:
            file.write(f"{group_id}\n")


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
    user_ids = get_user_ids()
    group_ids = get_group_ids()

    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)

        for user_id in user_ids:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[
                            TextMessage(text=f"距離學測還有 {countdown()} 天"),
                            TextMessage(text="這是今天的練習題:"),
                            TextMessage(text=StrictStr(make_question())),
                        ]
                    )
                )
                LOGGER.info(f"問題已發送至用戶 {user_id}")
            except Exception as e:
                LOGGER.error(f"發送至用戶 {user_id} 時出現錯誤: {e}")

        for group_id in group_ids:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=group_id,
                        messages=[
                            TextMessage(text=f"距離學測還有 {countdown()} 天"),
                            TextMessage(text="這是今天的練習題:"),
                            TextMessage(text=StrictStr(make_question())),
                        ]
                    )
                )
                LOGGER.info(f"問題已發送至群組 {group_id}")
            except Exception as e:
                LOGGER.error(f"發送至群組 {group_id} 時出現錯誤: {e}")


def send_answer():
    user_ids = get_user_ids()
    group_ids = get_group_ids()

    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)

        for user_id in user_ids:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[
                            TextMessage(text="今天題目的答案是:"),
                            TextMessage(text=StrictStr(make_answer())),
                        ]
                    )
                )
                LOGGER.info(f"答案已發送至用戶 {user_id}")
            except Exception as e:
                LOGGER.error(f"發送至用戶 {user_id} 時出現錯誤: {e}")

        for group_id in group_ids:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=group_id,
                        messages=[
                            TextMessage(text="今天題目的答案是:"),
                            TextMessage(text=StrictStr(make_answer())),
                        ]
                    )
                )
                LOGGER.info(f"答案已發送至群組 {group_id}")
            except Exception as e:
                LOGGER.error(f"發送至群組 {group_id} 時出現錯誤: {e}")


def handle_message(event):
    user_message = event.message.text
    source_type = event.source.type

    if source_type == "group":
        group_id = event.source.group_id
        if user_message == "開啟通知":
            add_group_id(group_id)
            reply_text = "此群組已成功啟用通知功能！"
    elif source_type == "user":
        user_id = event.source.user_id
        if user_message == "開啟通知":
            add_user_id(user_id)
            reply_text = "您已成功啟用通知功能！"
    else:
        reply_text = "目前不支援此類型的來源。"

    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


def register():
    SCHEDULER.register(send_question, "08:00", True)
    SCHEDULER.register(send_answer, "10:00", True)
