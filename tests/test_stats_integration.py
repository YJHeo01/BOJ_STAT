import base64
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import Mock, patch
from xml.etree import ElementTree

import requests

from clients.boj_client import BojClient
from clients.solvedac_client import SolvedAcClient
from models.user_stats import DEFAULT_CACHE_DATE, BojUserData, SolvedUserData, UserStats
from repositories.user_stats_repository import UserStatsRepository
from services.user_stats_service import UserStatsService


class StatsIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        db_path = Path(directory.name) / "user_data.db"
        # Seed the schema and an actual v3-style decorated CLASS before opening the repository.
        self.legacy = UserStats("legacy", 85, "4", "6", 8, 17, 12, 14, "2026-11-19")
        with closing(sqlite3.connect(db_path)) as db, db:
            db.execute("""
                CREATE TABLE users (
                    handle VARCHAR(51) PRIMARY KEY, solvedCount INTEGER,
                    createdCount VARCHAR(7), reviewedCount VARCHAR(7),
                    fixedCount INTEGER, voteCount INTEGER, tier INTEGER,
                    class INTEGER, date CHAR(10)
                )
            """)
            db.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("legacy", 85, "4", "6", 8, 17, 12, 14, "2026-11-19"),
            )
            db.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("placeholder", 0, "0", "0", 0, 0, 0, 0, DEFAULT_CACHE_DATE),
            )
        self.repository = UserStatsRepository(str(db_path))
        self.boj = Mock(spec=BojClient)
        self.boj.fetch_user_data.return_value = BojUserData(110, "2", "3", 5)
        self.session = Mock(spec=requests.Session)
        self.response = Mock(spec=requests.Response)
        self.session.get.return_value = self.response
        self.response.status_code = 200
        self.response.json.return_value = {
            "solvedCount": 120, "voteCount": 37, "tier": None, "class": 4, "classPlus": True
        }
        solved = SolvedAcClient(session=self.session, client_id="test-id", client_secret="test-secret")
        self.service = UserStatsService(self.repository, self.boj, solved)
        clock = patch("services.user_stats_service.datetime")
        self.clock = clock.start()
        self.clock.now.return_value = datetime(2026, 11, 20, 10)
        self.addCleanup(clock.stop)

    def test_legacy_row_is_refreshed_then_served_from_todays_cache(self):
        today = "2026-11-20"
        expected = UserStats("legacy", 120, "2", "3", 5, 37, 0, 12, today, today, today, 110, 120)
        self.assertEqual(self.repository.find_by_handle("legacy").classValue, self.legacy.classValue)
        self.assertEqual(self.service.get_user_stats("legacy"), expected)
        self.assertEqual(self.repository.find_by_handle("legacy"), expected)
        self.assertEqual(self.service.get_user_stats("legacy"), expected)
        self.boj.fetch_user_data.assert_called_once_with("legacy")
        self.session.get.assert_called_once()

    def test_new_user_keeps_larger_boj_solved_count(self):
        self.response.json.return_value["solvedCount"] = 100
        today = "2026-11-20"
        expected = UserStats("new", 110, "2", "3", 5, 37, 0, 12, today, today, today, 110, 100)
        self.assertEqual(self.service.get_user_stats("new"), expected)
        self.assertEqual(self.repository.find_by_handle("new"), expected)

    def test_solved_only_on_cold_cache_then_boj_recovers(self):
        today = "2026-11-20"
        self.boj.fetch_user_data.return_value = BojUserData.failure()
        expected = UserStats("new", 120, None, None, None, 37, 0, 12,
                             DEFAULT_CACHE_DATE, None, today, None, 120)
        self.assertEqual(self.service.get_user_stats("new"), expected)
        self.assertEqual(self.repository.find_by_handle("new"), expected)
        self.boj.fetch_user_data.return_value = BojUserData(111, "7", "12", 0)
        recovered = self.service.get_user_stats("new")
        self.assertEqual((recovered.createdCount, recovered.reviewedCount, recovered.date), ("7", "12", today))
        self.assertEqual(self.service.get_user_stats("new"), recovered)
        self.session.get.assert_called_once()
        self.assertEqual(self.boj.fetch_user_data.call_count, 2)

    def test_boj_only_on_cold_cache_then_solved_recovers(self):
        today = "2026-11-20"
        self.response.status_code = 429
        expected = UserStats("new", 110, "2", "3", 5, None, None, None,
                             DEFAULT_CACHE_DATE, today, None, 110, None)
        self.assertEqual(self.service.get_user_stats("new"), expected)
        self.assertEqual(self.repository.find_by_handle("new"), expected)
        self.response.status_code = 200
        recovered = self.service.get_user_stats("new")
        self.assertEqual((recovered.voteCount, recovered.solvedCount, recovered.date), (37, 120, today))
        self.assertEqual(self.service.get_user_stats("new"), recovered)
        self.boj.fetch_user_data.assert_called_once_with("new")
        self.assertEqual(self.session.get.call_count, 2)

    def test_corrected_solved_count_can_decrease_next_day(self):
        self.assertEqual(self.service.get_user_stats("new").solvedCount, 120)
        self.clock.now.return_value = datetime(2026, 11, 21, 6)
        self.boj.fetch_user_data.return_value = BojUserData(105, "2", "3", 5)
        self.response.json.return_value["solvedCount"] = 101
        self.assertEqual(self.service.get_user_stats("new").solvedCount, 105)
        self.assertEqual(self.session.get.call_count, 2)
        self.assertEqual(self.boj.fetch_user_data.call_count, 2)

    def test_overlapping_source_writes_keep_both_results(self):
        today = "2026-11-20"
        ready = Barrier(2)

        def save_source(boj, solved):
            ready.wait(timeout=5)
            self.repository.merge_refresh("new", today, boj, solved)

        with ThreadPoolExecutor(max_workers=2) as workers:
            one = workers.submit(save_source, BojUserData(110, "7", "12", 0), None)
            two = workers.submit(save_source, None, SolvedUserData(120, 40, 21, 21))
            one.result()
            two.result()
        current = self.repository.find_by_handle("new")
        self.assertEqual((current.boj_solved_count, current.solved_solved_count, current.date),
                         (110, 120, today))
        self.assertEqual((current.createdCount, current.reviewedCount, current.voteCount), ("7", "12", 40))
        late = self.repository.merge_refresh("new", "2026-11-19", BojUserData(111, "6", "9", 2), None)
        self.assertEqual(late, current)

    def test_boj_non_profile_http_200_preserves_contributions_and_cache_date(self):
        cached = UserStats("contributor", 1693, "7", "12", 1, 187, 21, 21, "2026-11-19")
        self.repository.add(cached)
        session = Mock(spec=requests.Session)
        self.service.boj_client = BojClient(session=session)
        for html in (
            "<html><title>로그인</title><form><input type='password'></form></html>",
            "<html><title>BOJ 서비스 점검</title></html>",
            "<html><table><tr><th>사용자</th><td>contributor</td></tr></table></html>",
        ):
            with self.subTest(html=html):
                session.get.return_value = Mock(spec=requests.Response, status_code=200, text=html)
                actual = self.service.get_user_stats(cached.handle)
                self.assertEqual((actual.createdCount, actual.reviewedCount, actual.fixedCount), ("7", "12", 1))
                self.assertEqual((actual.voteCount, actual.tier, actual.solvedCount), (37, 0, 1693))
                self.assertEqual((actual.boj_updated_on, actual.solved_updated_on, actual.date),
                                 (cached.date, "2026-11-20", cached.date))
                self.assertEqual(self.repository.find_by_handle(cached.handle), actual)
        self.session.get.assert_called_once()

    def test_solved_ac_errors_preserve_legacy_row_and_date(self):
        cases = [(200, {"solvedCount": 999}), (401, {}), (403, {}), (404, {}), (429, {}), (503, {})]
        for status, payload in cases:
            with self.subTest(status=status):
                self.response.status_code = status
                self.response.json.return_value = payload
                actual = self.service.get_user_stats("legacy")
                self.assertEqual((actual.voteCount, actual.tier, actual.classValue), (17, 12, 14))
                self.assertEqual((actual.solvedCount, actual.createdCount, actual.reviewedCount), (110, "2", "3"))
                self.assertEqual((actual.date, actual.solved_updated_on), (self.legacy.date, self.legacy.date))
                self.assertEqual(self.repository.find_by_handle("legacy"), actual)
        self.boj.fetch_user_data.assert_called_once_with("legacy")

    def test_404_for_unknown_profile_stores_boj_only_stats(self):
        self.response.status_code = 404
        self.response.json.return_value = {"error": {"code": "USER_NOT_FOUND", "message": "User not found."}}
        today = "2026-11-20"
        expected = UserStats("legacy", 110, "2", "3", 5, 0, 0, 0, today, today, today, 110, 0)
        self.assertEqual(self.service.get_user_stats("legacy"), expected)
        self.assertEqual(self.repository.find_by_handle("legacy"), expected)

    def test_unstorable_count_preserves_cached_badge(self):
        self.response.json.return_value["voteCount"] = 2**63
        actual = self.service.get_user_stats("legacy")
        self.assertEqual((actual.voteCount, actual.solved_updated_on), (self.legacy.voteCount, self.legacy.date))
        self.assertEqual(self.repository.find_by_handle("legacy"), actual)

    def test_failed_lookups_do_not_turn_legacy_placeholder_into_real_zeroes(self):
        self.response.status_code = 503
        self.boj.fetch_user_data.return_value = BojUserData.failure()
        expected = UserStats.empty("placeholder", date=DEFAULT_CACHE_DATE)
        self.assertEqual(self.service.get_user_stats("placeholder"), expected)
        self.assertEqual(self.repository.find_by_handle("placeholder"), expected)

    def test_partial_badge_distinguishes_unknown_from_real_zero(self):
        with patch("logging.FileHandler"), patch("logging.basicConfig"):
            import app

        self.boj.fetch_user_data.return_value = BojUserData.failure()
        self.response.json.return_value["voteCount"] = 0
        with patch.object(app, "user_stats_service", self.service):
            response = app.app.test_client().get("/v2/en/placeholder")
        self.assertEqual(response.status_code, 200)
        svg = ElementTree.fromstring(response.data)
        texts = [node.text for node in svg.findall("{http://www.w3.org/2000/svg}text")]
        fields = dict(zip(texts[1::2], texts[2::2]))
        self.assertEqual(fields["Authored Problems"], "—")
        self.assertEqual(fields["Reviewed Problems"], "—")
        self.assertEqual(fields["Fixed Problems"], "—")
        self.assertEqual(fields["Solved Problems"], "120")
        self.assertEqual(fields["Rating Contributions"], "0")

    def test_badge_routes_render_refreshed_stats_and_null_tier_image(self):
        # Importing the app normally sets up its process-wide logging and opens app.log.
        with patch("logging.FileHandler"), patch("logging.basicConfig"):
            import app

        routes = {
            "/legacy": "난이도 기여:",
            "/user/legacy": "난이도 기여:",
            "/v2/en/legacy": "Rating Contributions",
            "/v2/ko/legacy": "난이도 기여",
        }
        tier_png = (Path(__file__).resolve().parents[1] / "tier_image" / "0.png").read_bytes()
        tier_uri = "data:image/png;base64," + base64.b64encode(tier_png).decode("ascii")
        with patch.object(app, "user_stats_service", self.service):
            client = app.app.test_client()
            for path, label in routes.items():
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.mimetype, "image/svg+xml")
                    self.assertEqual(response.headers["Cache-Control"], "public, max-age=3600")
                    svg = ElementTree.fromstring(response.data)
                    texts = [node.text for node in svg.findall("{http://www.w3.org/2000/svg}text")]
                    self.assertIn(label, texts)
                    self.assertEqual(texts[texts.index(label) + 1], "37")
                    if path.startswith("/v2/"):
                        self.assertIn("120", texts)
                        image = svg.find("{http://www.w3.org/2000/svg}image")
                        self.assertIsNotNone(image)
                        self.assertEqual(image.get("{http://www.w3.org/1999/xlink}href"), tier_uri)
        self.boj.fetch_user_data.assert_called_once_with("legacy")
        self.session.get.assert_called_once()
