from datetime import datetime

from clients.boj_client import BojClient
from clients.solvedac_client import SolvedAcClient
from models.user_stats import DEFAULT_CACHE_DATE, UserStats
from repositories.user_stats_repository import UserStatsRepository


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
            self.repository.add(user_stats)

        current_date = datetime.now().isoformat()[:10]
        if not user_stats.is_stale(current_date):
            return user_stats

        boj_data = self.boj_client.fetch_user_data(username)
        if boj_data.is_failure:
            return user_stats

        solved_data = self.solvedac_client.fetch_user_data(username)
        if solved_data.has_error:
            return user_stats

        refreshed_user_stats = UserStats.from_sources(
            username,
            boj_data,
            solved_data,
            current_date,
        )
        self.repository.update(refreshed_user_stats)
        return refreshed_user_stats
