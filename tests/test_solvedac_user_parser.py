import unittest

from models.user_stats import SolvedUserData
from parsers.solvedac_user_parser import SolvedAcUserParser


class SolvedAcUserParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = SolvedAcUserParser()
        self.profile = {"solvedCount": 122, "voteCount": 17, "tier": 8, "class": 3}

    def test_only_badge_and_cache_fields_are_consumed(self):
        expected = SolvedUserData(solvedCount=122, voteCount=17, tier=8, classValue=9)
        for extra in ({}, {"classPlus": False}, {"classPlus": True}, {"classPlus": None}):
            with self.subTest(extra=extra):
                self.assertEqual(self.parser.parse(self.profile | extra), expected)

    def test_boundary_values(self):
        for tier, class_number, expected_tier in ((None, 0, 0), (0, 0, 0), (31, 10, 31)):
            with self.subTest(tier=tier, class_number=class_number):
                result = self.parser.parse(
                    {"solvedCount": 0, "voteCount": 0, "tier": tier, "class": class_number}
                )
                expected = SolvedUserData(tier=expected_tier, classValue=class_number * 3)
                self.assertEqual(result, expected)

    def test_all_consumed_fields_are_required_including_nullable_tier(self):
        for field in self.profile:
            with self.subTest(missing=field):
                incomplete = self.profile.copy()
                del incomplete[field]
                with self.assertRaises(ValueError):
                    self.parser.parse(incomplete)

    def test_rejects_malformed_profiles(self):
        for profile in (None, [], "profile", 1):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.parser.parse(profile)

    def test_rejects_invalid_numeric_fields(self):
        invalid_values = {
            "solvedCount": (None, False, -1, 1.0, "17"),
            "voteCount": (None, True, -1, 1.5, "0"),
            "tier": (True, -1, 32, 8.0, "8"),
            "class": (None, False, -1, 11, 3.0, "3"),
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.parser.parse(self.profile | {field: value})
