import ipaddress
from functools import wraps

from quart import render_template
from quart import request

from src.const import APP, SCHEDULER
from src.database import question
from src.database.limiter import rate_limited


def local_only(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Get client IP
        client_ip = request.remote_addr

        # List of allowed IPs/ranges
        allowed_ips = [
            '127.0.0.1',  # localhost
            '::1',  # localhost IPv6
            '192.168.0.0/16',  # typical local network range
            '10.0.0.0/8',  # private network range
        ]

        # Check if client IP is in allowed ranges
        is_allowed = False
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            for allowed_ip in allowed_ips:
                try:
                    if '/' in allowed_ip:
                        network = ipaddress.ip_network(allowed_ip)
                        if client_ip_obj in network:
                            is_allowed = True
                            break
                    elif client_ip == allowed_ip:
                        is_allowed = True
                        break
                except ValueError:
                    continue

        except ValueError:
            return "", 404

        if not is_allowed:
            return "", 404

        return f(*args, **kwargs)

    return decorated_function


## Register routers ###
@APP.route("/", methods=["GET"])
async def hello_world():
    return "OK", 200


@APP.route("/teapot", methods=["GET"])
async def teapot():
    return await render_template("teapot.html"), 418


from src import line

APP.route("/line_bot_webhook", methods=["POST"])(line.webhook.callback)

#######################

## Register scheduler ##

line.daily.register()


########################


def run():
    SCHEDULER.start()
    APP.run(host="0.0.0.0", port=8000, debug=True)
