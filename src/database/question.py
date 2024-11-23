import dataclasses
from typing import Optional, Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor
import logging

LOGGER = logging.getLogger("db.question")

@dataclasses.dataclass
class Question:
    id: str
    subject: str
    description: str
    opts: str
    ans: str
    explanation: Optional[str]
    details: Optional[str]

    @classmethod
    def from_dict(cls, question_dict: Dict[str, Any]) -> "Question":
        return cls(**question_dict)

    def make_question(self):
        return f"{self.description}\n\n{self.opts}"

    def make_answer(self):
        return f"Ans:{self.ans}\n\n{self.explanation}"

    def make_full(self):
        return f"{self.make_question()}\n\n{self.make_answer()}\n\n{self.details}"


class QuestionsManager:
    """A database manager for handling quiz questions.

    This class provides methods to create, retrieve, update, and search quiz questions
    in a PostgreSQL database. It handles all database operations related to question
    management.


    Examples:
        >>> questions_db = QuestionsManager(
        ...     dbname='your_db_name',
        ...     user='your_user',
        ...     password='your_password'
        ... )

        >>> # Create a new question
        >>> new_question_id = questions_db.create_question(
        ...     subject="Python",
        ...     description="What is a decorator in Python?",
        ...     opts="A) A function modifier\\nB) A class\\nC) A variable type\\nD) A loop construct",
        ...     ans="A",
        ...     explanation="A decorator is a design pattern that allows you to modify "
        ...                "the functionality of a function by wrapping it in another function.",
        ...     details="Difficulty: intermediate\\nTopic: Functions\\nMore info: https://www.geeksforgeeks.org/decorators-in-python/"
        ... )

        >>> # Retrieve a question
        >>> question = questions_db.get_question(new_question_id)

        >>> # Update a question
        >>> questions_db.update_question(
        ...     question_id=new_question_id,
        ...     explanation="Updated explanation..."
        ... )

        >>> # Search questions
        >>> python_questions = questions_db.search_questions("Python")

    Note:
        All database operations are handled internally by the class methods.
        Proper error handling should be implemented when using these methods.
    """

    _returned_questions = set()

    def __init__(self, dbname: str, user: str, password: str, host: str = 'localhost', port: int = 5432):
        """Initialize database connection."""
        try:
            LOGGER.info(f"Connecting to database {dbname}@{host}:{port}")
            self.conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        except psycopg2.Error as e:
            raise Exception(f"Unable to connect to database: {e}")

    def disconnect(self) -> None:
        """Close database connection."""
        self.conn.close()

    def create_question(self, subject: str, description: str, opts: str,
                        ans: str, explanation: Optional[str] = None,
                        details: Optional[str] = None):
        """
        Create a new question in the database.
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO questions (subject, description, opts, ans, explanation, details)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cur.execute(query, (
                    subject,
                    description,
                    opts,
                    ans,
                    explanation,
                    details
                ))

                self.conn.commit()

        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Error creating question: {e}")

    def get_question(self, question_id: int) -> Optional[Question]:
        """Retrieve a question by its ID."""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM questions WHERE id = %s"
                cur.execute(query, (question_id,))
                question = cur.fetchone()

                if question:
                    return Question.from_dict(dict(question))
                return None
        except psycopg2.Error as e:
            raise Exception(f"Error retrieving question: {e}")

    def update_question(self, question_id: int, **kwargs) -> bool:
        """
        Update a question's fields.
        Pass any field you want to update as a keyword argument.
        """
        valid_fields = {'subject', 'description', 'opts', 'ans', 'explanation', 'details'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not update_fields:
            return False

        try:
            with self.conn.cursor() as cur:
                set_clause = ', '.join([
                    f"{field} = %s" for field in update_fields.keys()
                ])
                values = list(update_fields.values())

                query = f"""
                    UPDATE questions 
                    SET {set_clause}
                    WHERE id = %s
                """
                cur.execute(query, values + [question_id])
                self.conn.commit()
                return cur.rowcount > 0
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Error updating question: {e}")

    def delete_question(self, question_id: int) -> bool:
        """Delete a question by its ID."""
        try:
            with self.conn.cursor() as cur:
                query = "DELETE FROM questions WHERE id = %s"
                cur.execute(query, (question_id,))
                self.conn.commit()
                return cur.rowcount > 0
        except psycopg2.Error as e:
            self.conn.rollback()
            raise Exception(f"Error deleting question: {e}")

    def get_questions_by_subject(self, subject: str) -> list[Question]:
        """Retrieve all questions for a given subject."""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM questions WHERE subject = %s ORDER BY id"
                cur.execute(query, (subject,))
                questions = cur.fetchall()
                return [Question.from_dict(dict(q)) for q in questions]
        except psycopg2.Error as e:
            raise Exception(f"Error retrieving questions: {e}")

    def search_questions(self, search_term: str) -> list[Question]:
        """Search questions by subject or description."""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT * FROM questions 
                    WHERE subject ILIKE %s OR description ILIKE %s
                    ORDER BY id
                """
                search_pattern = f'%{search_term}%'
                cur.execute(query, (search_pattern, search_pattern))
                questions = cur.fetchall()
                return [Question.from_dict(dict(q)) for q in questions]
        except psycopg2.Error as e:
            raise Exception(f"Error searching questions: {e}")

    def random_question(self, reset_if_exhausted: bool = True) -> Optional[Question]:
        """
        Retrieve a random question that hasn't been returned before.

        Args:
            reset_if_exhausted (bool): If True, reset the tracking of returned questions
                when all questions have been returned. If False, return None when all
                questions have been returned.

        Returns:
            Optional[Dict[str, Any]]: A randomly selected question as a dictionary that
            hasn't been returned before, or None if all questions have been returned
            and reset_if_exhausted is False.

        Raises:
            Exception: If there's an error executing the database query.
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # First, check the total number of questions
                cur.execute("SELECT COUNT(*) FROM questions")
                total_questions = cur.fetchone()['count']


                # If all questions have been returned
                if len(self._returned_questions) >= total_questions:
                    if reset_if_exhausted:
                        self._returned_questions.clear()
                    else:
                        return None

                # Get a random question that hasn't been returned yet
                query = """
                    SELECT * FROM questions 
                    WHERE id NOT IN %(returned_ids)s
                    ORDER BY RANDOM() 
                    LIMIT 1
                """

                # If no questions have been returned yet, don't include WHERE clause
                if not self._returned_questions:
                    query = """
                        SELECT * FROM questions 
                        ORDER BY RANDOM() 
                        LIMIT 1
                    """
                    cur.execute(query)
                else:
                    cur.execute(query, {'returned_ids': tuple(self._returned_questions)})

                question = cur.fetchone()

                if question:
                    question_dict = dict(question)
                    self._returned_questions.add(question_dict['id'])
                    return Question.from_dict(question_dict)
                return None

        except psycopg2.Error as e:
            raise Exception(f"Error retrieving random question: {e}")

    def reset_returned_questions(self) -> None:
        """
        Reset the tracking of returned questions, allowing all questions to be returned again.
        """
        self._returned_questions.clear()


    def get_all_subject(self) -> List[str]:
        """Retrieve all subjects."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT DISTINCT subject FROM questions")
                total_subjects = cur.fetchall()

                return [x for x, in total_subjects]

        except psycopg2.Error as e:
            raise Exception(f"Error retrieving random question: {e}")
