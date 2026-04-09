import logging
import sys
from datetime import datetime

from api.boj_user_page import boj_user_data
from api.solved_user_page import solved_user_data
from models.user_stats import DEFAULT_CACHE_DATE, UserStats
from repositories.user_stats_repository import UserStatsRepository, UserStatsRepositoryError

logger = logging.getLogger(__name__)

def main(username):
    ret_value = UserStats.empty(username)
    repository = UserStatsRepository()
    try:
        current_date = datetime.now().isoformat()[:10]

        stats = repository.find_by_handle(username)
        if stats is None:
            ret_value = UserStats.empty(username, date=DEFAULT_CACHE_DATE)
            repository.add(ret_value)
        else:
            ret_value = stats

        if ret_value.is_stale(current_date):
            boj_data = boj_user_data(username)
            if boj_data.is_failure:
                return ret_value

            solved_data = solved_user_data(username)
            if solved_data.has_error:
                return ret_value

            ret_value = UserStats.from_sources(username, boj_data, solved_data, current_date)
            repository.update(ret_value)
    except UserStatsRepositoryError as e:
        logger.error(f"Repository error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    return ret_value
    
if __name__ == "__main__":
    main(sys.argv[1])
