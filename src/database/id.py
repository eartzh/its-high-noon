import psycopg2
from psycopg2.extras import RealDictCursor
import logging

LOGGER = logging.getLogger("db.notification")


class NotificationManager:
    """A database manager for handling user and group notifications."""

    def __init__(self, dbname: str, user: str, password: str, host: str = 'localhost', port: int = 5432):
        """Initialize database connection."""
        try:
            LOGGER.info(f"Connecting to database {dbname}@{host}:{port}")
            self.conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        except psycopg2.Error as e:
            raise Exception(f"Unable to connect to database: {e}")

        self.create_tables_if_not_exist()

    def create_tables_if_not_exist(self):
        """Ensure the users and groups tables exist."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT UNIQUE NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS groups_ (
                        group_id TEXT UNIQUE NOT NULL
                    );
                """)
                self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Error creating tables: {e}")

    def disconnect(self) -> None:
        """Close database connection."""
        self.conn.close()

    # Methods for Users
    def get_all_users(self) -> list[str]:
        """Retrieve all user IDs."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users;")
                return [row[0] for row in cur.fetchall()]
        except psycopg2.Error as e:
            raise Exception(f"Error retrieving users: {e}")

    def add_user(self, user_id: str) -> None:
        """Add a user ID to the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING;
                """, (user_id,))
                self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Error adding user: {e}")

    # Methods for Groups
    def get_all_groups(self) -> list[str]:
        """Retrieve all group IDs."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT group_id FROM groups;")
                return [row[0] for row in cur.fetchall()]
        except psycopg2.Error as e:
            raise Exception(f"Error retrieving groups: {e}")

    def add_group(self, group_id: str) -> None:
        """Add a group ID to the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO groups (group_id)
                    VALUES (%s)
                    ON CONFLICT (group_id) DO NOTHING;
                """, (group_id,))
                self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Error adding group: {e}")
