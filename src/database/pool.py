import logging
from typing import Any, List, Tuple

import psycopg2
from psycopg2.pool import SimpleConnectionPool

LOGGER = logging.getLogger("db.pool")


class ConnectionPool:
    def __init__(self, dbname: str, user: str, password: str, host: str = 'localhost', port: int = 5432):
        """Initialize database connection."""
        try:
            LOGGER.info(f"Connecting to database {dbname}@{host}:{port}")
            self.pool = SimpleConnectionPool(
                dbname=dbname, user=user, password=password, host=host, port=port,
                minconn=1, maxconn=16
            )
        except psycopg2.Error as e:
            raise Exception(f"Unable to connect to database: {e}")

    def close(self):
        self.pool.closeall()

    def execute(self, query: str, args: List[str]) -> List[Tuple[Any, ...]]:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, args)
                conn.commit()

                return cur.fetchall()

        except psycopg2.Error as e:
            conn.rollback()
            raise Exception(f"Unable to execute query: {e}")
        finally:
            self.pool.putconn(conn)
