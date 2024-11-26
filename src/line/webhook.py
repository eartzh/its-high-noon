import dataclasses
import logging
import random
from typing import Optional

from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource, GroupSource
from pydantic import StrictStr, StrictBool
from quart import request, abort

from src.const import I18N
from src.database import user
from src.i18n import Keys, Langs
from src.line import HANDLER, CONFIGURATION
from src.line.cmd import CommandBuilder, UnknownCommandError, MissingArgumentsError, NoCommandError

LOGGER = logging.getLogger("line-webhook")


async def callback():
    """Handle LINE webhook callbacks."""
    try:
        signature = request.headers["X-Line-Signature"]
        body = await request.get_data(as_text=True)

        LOGGER.info("Received webhook: length=%d", len(body))

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


def send_reply(event: MessageEvent, reply_text: str, quote_token=Optional[str]) -> None:
    """Send a reply message to LINE."""

    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                notificationDisabled=StrictBool(False),
                messages=[
                    TextMessage(
                        text=StrictStr(reply_text),
                        quickReply=None,
                        quoteToken=StrictStr(quote_token) if quote_token else None,
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
    lang: Langs
    quote_token: Optional[str]


@HANDLER.add(MessageEvent, message=TextMessageContent)
def message(event: MessageEvent) -> None:
    """Handle incoming text messages."""
    try:
        LOGGER.debug("Received request: %s", event)

        user_id = None
        if isinstance(event.source, UserSource) or isinstance(event.source, GroupSource):
            user_id = event.source.user_id
            loading_animate(user_id)
            user.create(user_id)

        ctx = ProcessContext(
            event,
            user_id,
            Langs.from_str(user.get_lang(user_id)),
            None
        )
        LOGGER.debug(
            "Context: user_id=%s, lang=%s",
            ctx.user_id, ctx.lang
        )

        reply = process_message(ctx)

        if not reply:
            return

        LOGGER.debug("Sent reply: %s", reply)
        send_reply(event, reply, ctx.quote_token)

    except Exception as e:
        LOGGER.error("Error processing message: %s", str(e), exc_info=True)
        # Send a generic error message to user
        send_reply(event, I18N.get(Keys.PROCESSING_ERROR))


CMD = CommandBuilder()


def cmd_help(ctx):
    return I18N.get(Keys.CMD_HELP, ctx.lang)


def cmd_toggle(ctx):
    status = user.toggle_enabled(ctx.user_id)
    if status:
        return I18N.get(Keys.CMD_TOGGLE_ENABLE, ctx.lang)
    else:
        return I18N.get(Keys.CMD_TOGGLE_DISABLE, ctx.lang)


def cmd_lang(ctx, lang: Optional[str] = None):
    if not lang:
        return I18N.get(Keys.AVAILABLE_LANGS, ctx.lang).format(
            ", ".join(map(lambda l: l.value, Langs))
        )

    # validate lang
    lang = Langs.try_from_str(lang)

    if lang is None:
        return I18N.get(Keys.AVAILABLE_LANGS, ctx.lang).format(
            ", ".join(map(lambda l: l.value, Langs))
        )

    lang = lang.value

    user.set_lang(ctx.user_id, lang)
    return I18N.get(Keys.SET_LANG, ctx.lang).format(lang)


def cmd_echo(ctx, msg, ):
    return msg


def cmd_6(ctx):
    return "6"


def cmd_roll(ctx):
    return random.randint(1, 6)


def cmd_scream(ctx):
    return I18N.get(Keys.CMD_SCREAM, ctx.lang)


def cmd_ping(ctx):
    return "pong"


CMD.register_command("help", cmd_help)
CMD.register_command("toggle", cmd_toggle)
CMD.register_command("lang", cmd_lang, [], ["lang"])
CMD.register_command("echo", cmd_echo, ["msg"])
CMD.register_command("6", cmd_6)
CMD.register_command("114", cmd_6)
CMD.register_command("roll", cmd_roll)
CMD.register_command("scream", cmd_scream)
CMD.register_command("ping", cmd_ping)


def process_message(ctx: ProcessContext) -> str | None:
    """Process incoming message and generate reply."""
    # A text event
    if isinstance(ctx.event.message, TextMessageContent):
        text = ctx.event.message.text.strip()
        ctx.quote_token = ctx.event.message.quote_token
        LOGGER.debug(
            "Received text message: text=%s, user_id=%s, lang=%s",
            text, ctx.user_id, ctx.lang
        )

        if text.startswith("/"):
            try:
                return CMD.parse_and_execute(text[1:], ctx)
            except NoCommandError:
                return "owob"
            except UnknownCommandError:
                return I18N.get(Keys.CMD_UNKNOWN, ctx.lang)
            except MissingArgumentsError as e:
                return I18N.get(Keys.MISSING_ARGS, ctx.lang).format(str(e.missing_args))

        elif ("ouo" in text.lower()
              or "owo" in text.lower()
              or "uwu" in text.lower()):
            return "Ciallo (∠·ω )⌒★"

    return None
