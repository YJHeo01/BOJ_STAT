import io
import json
import os
import unittest
from unittest.mock import Mock, patch

import requests

from clients.http_session import build_retry_session
from clients.solvedac_client import SolvedAcClient
from models.user_stats import SolvedUserData


PROFILE = {"solvedCount": 42, "voteCount": 5, "tier": 8, "class": 2}
EXPECTED = SolvedUserData(solvedCount=42, voteCount=5, tier=8, classValue=6)


def response(status, body):
    result = requests.Response()
    result.status_code = status
    result._content = body
    return result


class SolvedAcClientTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock(spec=requests.Session)
        self.client = SolvedAcClient(
            session=self.session, client_id="test-id", client_secret="test-secret"
        )

    def test_fetches_one_encoded_path_with_app_credentials(self):
        self.session.get.return_value = response(200, json.dumps(PROFILE).encode())
        result = self.client.fetch_user_data("a/b?#한")

        self.assertEqual(result, EXPECTED)
        self.session.get.assert_called_once_with(
            "https://solved.ac/api/v4/users/a%2Fb%3F%23%ED%95%9C",
            headers={
                "Accept": "application/json",
                "x-client-id": "test-id",
                "x-client-secret": "test-secret",
            },
            timeout=(3.05, 10),
            allow_redirects=False,
        )

    def test_invalid_path_segments_do_not_send_requests(self):
        for handle in ("", ".", "..", "a" * 65):
            with self.subTest(handle=handle):
                self.assertTrue(self.client.fetch_user_data(handle).has_error)
        self.session.get.assert_not_called()

    @patch.dict(
        os.environ,
        {"SOLVEDAC_CLIENT_ID": "env-id", "SOLVEDAC_CLIENT_SECRET": "env-secret"},
    )
    def test_reads_credentials_from_environment_for_omitted_arguments(self):
        self.session.get.return_value = response(200, json.dumps(PROFILE).encode())
        for kwargs, expected_id in (
            ({}, "env-id"),
            ({"client_id": "override"}, "override"),
        ):
            with self.subTest(kwargs=kwargs):
                client = SolvedAcClient(session=self.session, **kwargs)
                self.assertEqual(client.fetch_user_data("handle"), EXPECTED)
                headers = self.session.get.call_args.kwargs["headers"]
                self.assertEqual(headers["x-client-id"], expected_id)
                self.assertEqual(headers["x-client-secret"], "env-secret")

    def test_missing_or_explicitly_empty_credentials_do_not_send_requests(self):
        cases = [
            ({}, {}),
            ({"SOLVEDAC_CLIENT_ID": "env-id"}, {}),
            ({"SOLVEDAC_CLIENT_SECRET": "env-secret"}, {}),
            (
                {"SOLVEDAC_CLIENT_SECRET": "env-secret"},
                {"client_id": "id", "client_secret": ""},
            ),
            ({}, {"client_id": "   ", "client_secret": "secret"}),
        ]
        for environment, kwargs in cases:
            with self.subTest(environment=environment, kwargs=kwargs), patch.dict(
                os.environ, environment, clear=True
            ):
                with self.assertLogs("clients.solvedac_client", level="WARNING"):
                    client = SolvedAcClient(session=self.session, **kwargs)
                    self.assertTrue(client.fetch_user_data("handle").has_error)
        self.session.get.assert_not_called()

    def test_only_structured_not_found_is_a_successful_empty_profile(self):
        body = {"error": {"code": "USER_NOT_FOUND", "message": "User not found."}}
        self.session.get.return_value = response(404, json.dumps(body).encode())
        self.assertEqual(self.client.fetch_user_data("handle"), SolvedUserData())

        for body in (
            b"<html>not found</html>",
            b"null",
            b"{}",
            b'{"error":"not found"}',
            b'{"error":{"code":404,"message":"User not found."}}',
            b'{"error":{"code":"USER_NOT_FOUND"}}',
            b'{"error":{"code":"USER_NOT_FOUND","message":"not found","details":[]}}',
        ):
            with self.subTest(body=body):
                self.session.get.return_value = response(404, body)
                self.assertTrue(self.client.fetch_user_data("handle").has_error)

    def test_unreadable_responses_and_http_errors_are_failures(self):
        for status, body in (
            (200, b"invalid JSON"),
            (200, b"{}"),
            (302, b""),
            (401, b""),
            (403, b""),
            (429, b""),
            (503, b""),
        ):
            with self.subTest(status=status, body=body):
                self.session.get.return_value = response(status, body)
                self.assertTrue(self.client.fetch_user_data("handle").has_error)

    def test_logs_do_not_include_credentials_or_response_body(self):
        self.session.get.side_effect = [
            requests.Timeout("timeout with test-secret"),
            response(403, b"sensitive response content"),
        ]
        with self.assertLogs("clients.solvedac_client", level="WARNING") as logs:
            self.assertTrue(self.client.fetch_user_data("handle").has_error)
            self.assertTrue(self.client.fetch_user_data("handle").has_error)
        messages = "\n".join(logs.output)
        self.assertIn("403", messages)
        for value in ("test-id", "test-secret", "sensitive response content"):
            self.assertNotIn(value, messages)


class SolvedAcRetryTests(unittest.TestCase):
    def fetch_with_responses(self, statuses):
        # Mock only the socket: requests and urllib3 still perform their own HTTP retries.
        replies = iter(statuses)

        def connect(connection):
            status = next(replies)
            payload = json.dumps(PROFILE).encode() if status == 200 else b"{}"
            retry_after = "Retry-After: 2\r\n" if status == 429 else ""
            headers = (
                f"HTTP/1.1 {status} Test response\r\n{retry_after}"
                f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n"
            )
            connection.sock = Mock()
            connection.sock.makefile.return_value = io.BytesIO(
                headers.encode() + payload
            )
            connection.is_verified = True

        with build_retry_session() as session:
            session.trust_env = False
            client = SolvedAcClient(
                session=session, client_id="id", client_secret="secret"
            )
            with patch(
                "urllib3.connection.HTTPSConnection.connect",
                autospec=True,
                side_effect=connect,
            ) as opened, patch("time.sleep") as sleep:
                result = client.fetch_user_data("handle")
        self.assertEqual(opened.call_count, len(statuses))
        return result, sleep

    def test_rate_limit_retries_after_requested_delay(self):
        result, sleep = self.fetch_with_responses([429, 200])
        self.assertEqual(result, EXPECTED)
        sleep.assert_called_once_with(2)

    def test_server_errors_exhaust_three_retries(self):
        result, _ = self.fetch_with_responses([503] * 4)
        self.assertTrue(result.has_error)

    def test_authentication_errors_are_not_retried(self):
        for status in (401, 403):
            with self.subTest(status=status):
                result, sleep = self.fetch_with_responses([status])
                self.assertTrue(result.has_error)
                sleep.assert_not_called()
