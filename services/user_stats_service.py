import logging
from datetime import datetime

from clients.boj_client import BojClient
from clients.solvedac_client import SolvedAcClient
from models.user_stats import DEFAULT_CACHE_DATE, UserStats
from repositories.user_stats_repository import UserStatsRepository

logger = logging.getLogger(__name__)


class UserStatsService:
    def __init__(
        self,
        repository: UserStatsRepository | None = None,
        boj_client: BojClient | None = None,
        solvedac_client: SolvedAcClient | None = None,
    ):
        self.repository = repository or UserStatsRepository()
        self.boj_client = boj_client or BojClient()
        self.solvedac_client = solvedac_client or SolvedAcClient()

    def get_user_stats(self, username: str) -> UserStats:
        user_stats = self.repository.find_by_handle(username)
        if user_stats is None:
            user_stats = UserStats.empty(username, date=DEFAULT_CACHE_DATE)

        today = datetime.now().date().isoformat()
        if user_stats.solved_updated_on != today:
            solved = self.solvedac_client.fetch_user_data(username)
            if not solved.has_error:
                user_stats = self.repository.merge_refresh(username, today, None, solved)
                logger.info("Refreshed solved.ac stats for %r on %s", username, today)
        if user_stats.boj_updated_on != today:
            boj = self.boj_client.fetch_user_data(username)
            if not boj.is_failure:
                user_stats = self.repository.merge_refresh(username, today, boj, None)
                logger.info("Refreshed BOJ stats for %r on %s", username, today)
        return user_stats
