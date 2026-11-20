import sqlite3
from contextlib import closing, contextmanager

from models.user_stats import BojUserData, DEFAULT_CACHE_DATE, SolvedUserData, UserStats

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

CREATE_SOURCE_TABLE_QUERY = """
    CREATE TABLE IF NOT EXISTS user_source_cache (
        handle TEXT PRIMARY KEY,
        boj_updated_on TEXT,
        solved_updated_on TEXT,
        boj_solved_count INTEGER,
        solved_solved_count INTEGER
    )
"""
SELECT_USER_BY_HANDLE_QUERY = """
    SELECT u.handle, u.solvedCount, u.createdCount, u.reviewedCount, u.fixedCount,
           u.voteCount, u.tier, u.class, u.date, s.boj_updated_on, s.solved_updated_on,
           s.boj_solved_count, s.solved_solved_count
    FROM users AS u LEFT JOIN user_source_cache AS s USING (handle)
    WHERE u.handle = ?
"""
INSERT_USER_QUERY = "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)"
UPDATE_USER_QUERY = """
    UPDATE users
    SET solvedCount=?, createdCount=?, reviewedCount=?, fixedCount=?, voteCount=?, tier=?, class=?, date=?
    WHERE handle=?
"""
UPSERT_SOURCE_QUERY = """
    INSERT INTO user_source_cache (
        handle, boj_updated_on, solved_updated_on, boj_solved_count, solved_solved_count
    ) VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(handle) DO UPDATE SET
        boj_updated_on=excluded.boj_updated_on, solved_updated_on=excluded.solved_updated_on,
        boj_solved_count=excluded.boj_solved_count, solved_solved_count=excluded.solved_solved_count
"""


class UserStatsRepositoryError(Exception):
    pass


class UserStatsRepository:
    def __init__(self, db_path: str = "user_data.db"):
        self.db_path = db_path

    @contextmanager
    def _connect(self):
        try:
            with closing(sqlite3.connect(self.db_path)) as connection, connection:
                connection.execute(CREATE_USERS_TABLE_QUERY)
                connection.execute(CREATE_SOURCE_TABLE_QUERY)
                yield connection
        except sqlite3.Error as exc:
            raise UserStatsRepositoryError(f"Could not access the user stats cache: {exc}") from exc

    @staticmethod
    def _find(connection: sqlite3.Connection, handle: str) -> UserStats | None:
        row = connection.execute(SELECT_USER_BY_HANDLE_QUERY, (handle,)).fetchone()
        return UserStats.from_db_row(row) if row is not None else None

    def find_by_handle(self, handle: str) -> UserStats | None:
        with self._connect() as connection:
            return self._find(connection, handle)

    @staticmethod
    def _store(connection: sqlite3.Connection, stats: UserStats, *, insert: bool) -> None:
        params = stats.to_insert_params()
        if insert:
            connection.execute(INSERT_USER_QUERY, params)
        else:
            updated = connection.execute(UPDATE_USER_QUERY, (*params[1:], stats.handle))
            if updated.rowcount == 0:
                return
        connection.execute(UPSERT_SOURCE_QUERY, (
            stats.handle, stats.boj_updated_on, stats.solved_updated_on,
            stats.boj_solved_count, stats.solved_solved_count,
        ))

    def add(self, user_stats: UserStats) -> None:
        with self._connect() as connection:
            self._store(connection, user_stats, insert=True)

    def update(self, user_stats: UserStats) -> None:
        with self._connect() as connection:
            self._store(connection, user_stats, insert=False)

    def merge_refresh(
        self, handle: str, current_date: str,
        boj_data: BojUserData | None, solved_data: SolvedUserData | None,
    ) -> UserStats:
        with self._connect() as connection:
            # Network calls finish before this transaction. Another request may have
            # refreshed either source in the meantime.
            connection.execute("BEGIN IMMEDIATE")
            previous = self._find(connection, handle)
            current = previous or UserStats.empty(handle, date=DEFAULT_CACHE_DATE)
            if current.boj_updated_on and current.boj_updated_on >= current_date:
                boj_data = None
            if current.solved_updated_on and current.solved_updated_on >= current_date:
                solved_data = None
            if boj_data is None and solved_data is None:
                return current
            merged = current.apply_refresh(current_date, boj_data, solved_data)
            self._store(connection, merged, insert=previous is None)
            return merged
