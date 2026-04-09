import logging
import sqlite3
import sys
from datetime import datetime

from api.boj_user_page import boj_user_data
from api.solved_user_page import solved_user_data
from models.user_stats import DEFAULT_CACHE_DATE, UserStats

logger = logging.getLogger(__name__)

def main(username):
    ret_value = UserStats.empty(username)
    connection = None
    try:
        current_date = datetime.now().isoformat()[:10]

        connection = sqlite3.connect("user_data.db")
        cursor = connection.cursor()
        cursor.execute('''
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
        ''')

        cursor.execute("SELECT * FROM users WHERE handle = ?", (username,))

        stats = cursor.fetchone()

        if stats is None:
            ret_value = UserStats.empty(username, date=DEFAULT_CACHE_DATE)
            cursor.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", ret_value.to_insert_params())
            connection.commit()
        else:
            ret_value = UserStats.from_db_row(stats)

        if ret_value.is_stale(current_date):
            boj_data = boj_user_data(username)
            if boj_data.is_failure:
                return ret_value

            solved_data = solved_user_data(username)
            if solved_data.has_error:
                return ret_value

            ret_value = UserStats.from_sources(username, boj_data, solved_data, current_date)
            cursor.execute(
                "UPDATE users SET solvedCount=?, createdCount=?, reviewedCount=?, fixedCount=?, voteCount=?, tier=?, class=?, date=? WHERE handle=?",
                ret_value.to_update_params()
            )
            connection.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if connection:
            connection.rollback()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if connection:
            connection.close()
    return ret_value
    
if __name__ == "__main__":
    main(sys.argv[1])
