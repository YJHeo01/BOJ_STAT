import sqlite3
from typing import Optional

from models.user_stats import UserStats

CREATE_USERS_TABLE_QUERY = '''
    CREATE TABLE IF NOT EXISTS users (
        handle VARCHAR(51) PRIMARY KEY,
        solvedCount INTEGER,
        createdCount VARCHAR(7),
        reviewedCount VARCHAR(7),
        fixedCount INTEGER,
        voteCount INTEGER,
        tier INTEGER,
        class INTEGER,
        date CHAR(10)
    )
'''

SELECT_USER_BY_HANDLE_QUERY = "SELECT * FROM users WHERE handle = ?"
INSERT_USER_QUERY = "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)"
UPDATE_USER_QUERY = """
    UPDATE users
    SET solvedCount=?, createdCount=?, reviewedCount=?, fixedCount=?, voteCount=?, tier=?, class=?, date=?
    WHERE handle=?
"""


class UserStatsRepositoryError(Exception):
    pass


class UserStatsRepository:
    def __init__(self, db_path: str = "user_data.db"):
        self.db_path = db_path

    def find_by_handle(self, handle: str) -> Optional[UserStats]:
        try:
            with sqlite3.connect(self.db_path) as connection:
                self._ensure_table(connection)
                cursor = connection.cursor()
                cursor.execute(SELECT_USER_BY_HANDLE_QUERY, (handle,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return UserStats.from_db_row(row)
        except sqlite3.Error as exc:
            raise UserStatsRepositoryError(
                f"Failed to load user stats for '{handle}'."
            ) from exc

    def add(self, user_stats: UserStats) -> None:
        try:
            with sqlite3.connect(self.db_path) as connection:
                self._ensure_table(connection)
                connection.execute(INSERT_USER_QUERY, user_stats.to_insert_params())
        except sqlite3.Error as exc:
            raise UserStatsRepositoryError(
                f"Failed to create user stats for '{user_stats.handle}'."
            ) from exc

    def update(self, user_stats: UserStats) -> None:
        try:
            with sqlite3.connect(self.db_path) as connection:
                self._ensure_table(connection)
                connection.execute(UPDATE_USER_QUERY, user_stats.to_update_params())
        except sqlite3.Error as exc:
            raise UserStatsRepositoryError(
                f"Failed to update user stats for '{user_stats.handle}'."
            ) from exc

    @staticmethod
    def _ensure_table(connection: sqlite3.Connection) -> None:
        connection.execute(CREATE_USERS_TABLE_QUERY)
