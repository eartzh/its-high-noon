import dataclasses
import logging
from typing import Optional

from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource
from pydantic import StrictStr, StrictBool
from quart import request, abort

from src.const import USERS_DATABASE, I18N
from src.i18n import Keys
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


def loading_animate(chat_id: str) -> None:
    """Send a loading animation to LINE."""
    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.show_loading_animation(show_loading_animation_request=ShowLoadingAnimationRequest(
            loadingSeconds=20,
            chatId=StrictStr(chat_id)
        ))


#########################################################

@dataclasses.dataclass
class ProcessContext:
    event: MessageEvent
    user_id: Optional[str]
    lang: Optional[str]


@HANDLER.add(MessageEvent, message=TextMessageContent)
def message(event: MessageEvent) -> None:
    """Handle incoming text messages."""
    try:
        LOGGER.debug("Received request: %s", event)

        user_id = None
        if isinstance(event.source, UserSource):
            user_id = event.source.user_id
            loading_animate(user_id)
            USERS_DATABASE.add_user(user_id)

        ctx = ProcessContext(event, user_id, USERS_DATABASE.get_user_lang(user_id))

        reply = process_message(ctx)

        LOGGER.debug("Sent reply: %s", reply)
        send_reply(event, reply)

    except Exception as e:
        LOGGER.error("Error processing message: %s", str(e), exc_info=True)
        # Send a generic error message to user
        send_reply(event, I18N.get(Keys.PROCESSING_ERROR))


def process_message(ctx: ProcessContext) -> StrictStr:
    """Process incoming message and generate reply."""
    # A text event
    if isinstance(ctx.event.message, TextMessageContent):
        if ctx.event.message.text.startswith("/"):
            cmd, args = ctx.event.message.text.split(" ", 1)
            return cmd_dispatch(cmd[1:], args, ctx)

    return ""


def cmd_dispatch(cmd: str, args: str, ctx: ProcessContext) -> str:
    match cmd:
        case "help":
            return I18N.get(Keys.CMD_HELP, ctx.lang)
        case "toggle":
            status = USERS_DATABASE.toggle_enabled()
            if status:
                return I18N.get(Keys.CMD_TOGGLE_ENABLE, ctx.lang)
            else:
                return I18N.get(Keys.CMD_TOGGLE_DISABLE, ctx.lang)
        case _:
            return I18N.get(Keys.CMD_UNKNOWN, ctx.lang)
