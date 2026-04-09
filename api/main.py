import logging
import sys

from models.user_stats import UserStats
from repositories.user_stats_repository import UserStatsRepositoryError
from services.user_stats_service import UserStatsService

logger = logging.getLogger(__name__)

def main(username):
    ret_value = UserStats.empty(username)
    service = UserStatsService()
    try:
        ret_value = service.get_user_stats(username)
    except UserStatsRepositoryError as e:
        logger.error(f"Repository error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    return ret_value
    
if __name__ == "__main__":
    main(sys.argv[1])
