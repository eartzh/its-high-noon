from datetime import datetime, timedelta
from functools import wraps
from threading import Lock

from flask import request, jsonify

from src.const import DATABASE

REQUESTS_PER_MINUTE = 30
__LOCK = Lock()


def init_db():
    DATABASE.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id SERIAL PRIMARY KEY,
                    ip_address VARCHAR(45) NOT NULL,
                    endpoint VARCHAR(255) NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ip_address, endpoint)
                );

                CREATE INDEX IF NOT EXISTS idx_ip_endpoint ON rate_limits(ip_address, endpoint);
                """)


def _clean_old_records():
    # Clean records older than the window
    DATABASE.execute("""
            DELETE FROM rate_limits 
            WHERE window_start < %s
        """, (datetime.now() - timedelta(minutes=1),)
                     )


def is_rate_limited(ip_address, endpoint):
    with __LOCK:  # Thread safety for connection handling

        # Clean old records first
        _clean_old_records()

        # Check existing record
        result = DATABASE.execute("""
                        SELECT request_count, window_start 
                        FROM rate_limits 
                        WHERE ip_address = %s AND endpoint = %s
                    """, (ip_address, endpoint))

        result = result[0] if result else None
        current_time = datetime.now()

        if result is None:
            # First request from this IP for this endpoint
            DATABASE.execute("""
                            INSERT INTO rate_limits (ip_address, endpoint)
                            VALUES (%s, %s)
                        """, (ip_address, endpoint))

            return False

        window_start = result['window_start']
        request_count = result['request_count']

        # Check if we're in a new window
        if current_time - window_start > timedelta(minutes=1):
            DATABASE.execute("""
                            UPDATE rate_limits 
                            SET request_count = 1, window_start = CURRENT_TIMESTAMP
                            WHERE ip_address = %s AND endpoint = %s
                        """, (ip_address, endpoint))

            return False

        # Check if limit exceeded
        if request_count >= REQUESTS_PER_MINUTE:
            return True

        # Increment counter
        DATABASE.execute("""
                        UPDATE rate_limits 
                        SET request_count = request_count + 1
                        WHERE ip_address = %s AND endpoint = %s
                    """, (ip_address, endpoint))

        return False


def rate_limited(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        ip_address = request.remote_addr
        endpoint = request.path

        if is_rate_limited(ip_address, endpoint):
            return jsonify({
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": "60 seconds"
            }), 429

        return f(*args, **kwargs)

    return wrapped
