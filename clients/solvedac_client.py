import logging

import requests

from clients.http_session import DEFAULT_TIMEOUT, build_retry_session
from models.user_stats import SolvedUserData
from parsers.solvedac_user_parser import SolvedAcUserParser

logger = logging.getLogger(__name__)


class SolvedAcClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        parser: SolvedAcUserParser | None = None,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    ):
        self.session = session or build_retry_session()
        self.parser = parser or SolvedAcUserParser()
        self.timeout = timeout

    def fetch_user_data(self, username: str) -> SolvedUserData:
        url = "https://solved.ac/api/v3/user/show"
        querystring = {"handle": username}
        headers = {
            "x-solvedac-language": "",
            "Accept": "application/json",
        }
        try:
            response = self.session.get(
                url,
                headers=headers,
                params=querystring,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.error(f"Failed to fetch solved.ac user data for '{username}': {exc}")
            return SolvedUserData.failure()

        if response.status_code == 200:
            return self.parser.parse(response.json())
        if response.status_code == 404:
            return SolvedUserData()

        logger.warning(
            "solved.ac user request failed for '%s' with status %s",
            username,
            response.status_code,
        )
        return SolvedUserData.failure()
