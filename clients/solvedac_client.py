import logging
import os
from urllib.parse import quote

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
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.session = session or build_retry_session()
        self.parser = parser or SolvedAcUserParser()
        self.timeout = timeout
        if client_id is None:
            client_id = os.getenv("SOLVEDAC_CLIENT_ID")
        if client_secret is None:
            client_secret = os.getenv("SOLVEDAC_CLIENT_SECRET")
        self._headers = None
        if (client_id or "").strip() and (client_secret or "").strip():
            self._headers = {
                "Accept": "application/json",
                "x-client-id": client_id,
                "x-client-secret": client_secret,
            }
        else:
            logger.error("Missing solved.ac credentials: check SOLVEDAC_CLIENT_ID and SOLVEDAC_CLIENT_SECRET")

    def fetch_user_data(self, username: str) -> SolvedUserData:
        if self._headers is None:
            return SolvedUserData.failure()
        if not 1 <= len(username) <= 64 or username in (".", ".."):
            logger.warning("Invalid solved.ac profile handle")
            return SolvedUserData.failure()

        url = f"https://solved.ac/api/v4/users/{quote(username, safe='')}"
        try:
            response = self.session.get(
                url,
                headers=self._headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            logger.warning("solved.ac profile request for %r failed (%s)", username, type(exc).__name__)
            return SolvedUserData.failure()

        if response.status_code in (200, 404):
            try:
                payload = response.json()
                if response.status_code == 200:
                    return self.parser.parse(payload)
                if self._is_error_response(payload):
                    return SolvedUserData()
                raise ValueError("Invalid 404 error envelope")
            except (ValueError, RecursionError) as exc:
                logger.warning(
                    "Invalid solved.ac profile response for %r (HTTP %s, %s)",
                    username, response.status_code, type(exc).__name__,
                )
                return SolvedUserData.failure()

        logger.warning(
            "solved.ac profile request for %r failed (HTTP %s)",
            username,
            response.status_code,
        )
        return SolvedUserData.failure()

    @staticmethod
    def _is_error_response(payload: object) -> bool:
        # The profile endpoint documents 404 as user not found, without a fixed error code.
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return False
        details = error.get("details", {})
        return (
            isinstance(error.get("code"), str)
            and isinstance(error.get("message"), str)
            and isinstance(details, dict)
            and all(isinstance(value, (str, int, float)) for value in details.values())
        )
