import logging
import uuid
from datetime import datetime

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
from src.database.id import NotificationManager

LOGGER = logging.getLogger(__name__)

TODAY_QUESTION: Question | None = None
RAN_OUT_QUESTIONS = "We ran out of questions!!!"

notification_manager = NotificationManager(
    dbname="your_dbname",
    user="your_username",
    password="your_password",
    host="your_host",
    port=5432
)

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
    user_ids = notification_manager.get_all_users()
    group_ids = notification_manager.get_all_groups()

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
                LOGGER.info(f"Question sent to user {user_id}")
            except Exception as e:
                LOGGER.error(f"Error sending message to user {user_id}: {e}")

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
                LOGGER.info(f"Question sent to group {group_id}")
            except Exception as e:
                LOGGER.error(f"Error sending message to group {group_id}: {e}")


def send_answer():
    user_ids = notification_manager.get_all_users()
    group_ids = notification_manager.get_all_groups()

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
                LOGGER.info(f"Answer sent to user {user_id}")
            except Exception as e:
                LOGGER.error(f"Error sending message to user {user_id}: {e}")

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
                LOGGER.info(f"Answer sent to group {group_id}")
            except Exception as e:
                LOGGER.error(f"Error sending message to group {group_id}: {e}")


def handle_message(event):
    user_message = event.message.text
    source_type = event.source.type

    if source_type == "group":
        group_id = event.source.group_id
        if user_message == "開啟通知":
            notification_manager.add_group(group_id)
            reply_text = "此群組已成功啟用通知功能！"
    elif source_type == "user":
        user_id = event.source.user_id
        if user_message == "開啟通知":
            notification_manager.add_user(user_id)
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
