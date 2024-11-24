from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from src.database.id import NotificationManager
from pydantic import StrictStr, StrictBool
from quart import request, abort

import logging
from src.line import HANDLER, CONFIGURATION

LOGGER = logging.getLogger("line-webhook")


async def callback():
    """Handle LINE webhook callbacks."""
    try:
        signature = request.headers["X-Line-Signature"]
        body = await request.get_data(as_text=True)

        LOGGER.info("Received webhook: length=%d", len(body))
        LOGGER.trace("Request body: %s", body)

        HANDLER.handle(body, signature)
        return "OK", 200

    except KeyError:
        LOGGER.error("Missing X-Line-Signature header")
        abort(400, description="Missing X-Line-Signature header")

    except InvalidSignatureError:
        LOGGER.error("Invalid signature")
        abort(401, description="Invalid signature")

    except Exception as e:
        LOGGER.error("Unexpected error: %s", str(e), exc_info=True)
        abort(500, description="Internal server error")


def send_reply(event: MessageEvent, reply_text: StrictStr) -> None:
    """Send a reply message to LINE."""

    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                notificationDisabled=StrictBool(False),
                messages=[
                    TextMessage(
                        text=reply_text,
                        quickReply=None,
                        quoteToken=None,
                    )
                ],
            ),
            async_req=True
        )


@HANDLER.add(MessageEvent, message=TextMessageContent)
def message_text(event: MessageEvent) -> None:
    """Handle incoming text messages."""
    try:
        received: str = event.message.text
        LOGGER.debug("Received text: %s", received)

        reply = process_message(received)
        LOGGER.debug("Sent reply: %s", reply)

        send_reply(event, reply)

    except Exception as e:
        LOGGER.error("Error processing message: %s", str(e), exc_info=True)
        # Send a generic error message to user
        send_reply(event, "Sorry, I couldn't process your message. Please try again later.")


def process_message(event: MessageEvent) -> StrictStr:
    """Process incoming message and generate reply."""
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

    return reply_text


