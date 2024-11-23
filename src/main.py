from quart import render_template

from src.const import APP, SCHEDULER


@APP.route("/", methods=["GET"])
async def hello_world():
    return "OK", 200


@APP.route("/teapot", methods=["GET"])
async def teapot():
    return await render_template("teapot.html"), 418


## Register routers ###
from src import line

APP.route("/line_bot_webhook", methods=["POST"])(line.webhook.callback)

APP.route("/db/question", methods=["GET"])(line.daily.make_question)
APP.route("/db/answer", methods=["GET"])(line.daily.make_answer)

#######################

## Register scheduler ##

line.daily.register()


########################


def run():
    SCHEDULER.start()
    APP.run(host="0.0.0.0", port=8000, debug=True)
