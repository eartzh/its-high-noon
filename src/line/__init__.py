from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
)

from src.const import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET

# Initialize handler and configuration
HANDLER = WebhookHandler(LINE_CHANNEL_SECRET)
CONFIGURATION = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

from .webhook import callback
from .daily import register