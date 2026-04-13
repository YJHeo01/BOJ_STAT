import logging

import requests

from clients.http_session import DEFAULT_TIMEOUT, build_retry_session
from models.user_stats import BojUserData
from parsers.boj_profile_parser import BojProfileParser

logger = logging.getLogger(__name__)
BOJ_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
)


class BojClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        parser: BojProfileParser | None = None,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    ):
        self.session = session or build_retry_session()
        self.parser = parser or BojProfileParser()
        self.timeout = timeout

    def fetch_user_data(self, username: str) -> BojUserData:
        boj_url = f"https://www.acmicpc.net/user/{username}"
        headers = {"User-Agent": BOJ_USER_AGENT}
        try:
            response = self.session.get(boj_url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.error(f"Failed to fetch BOJ user page for '{username}': {exc}")
            return BojUserData.failure()

        if response.status_code != 200:
            logger.warning(
                "BOJ user page request failed for '%s' with status %s",
                username,
                response.status_code,
            )
            return BojUserData.failure()
        return self.parser.parse(response.text)
