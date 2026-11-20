import unittest

from models.user_stats import BojUserData
from parsers.boj_profile_parser import BojProfileParser


class BojProfileParserTests(unittest.TestCase):
    def test_profile_with_contributions(self):
        html = """
            <table id="statics">
                <tr><th>맞은 문제</th><td><a>1693</a></td></tr>
                <tr><th>만든 문제</th><td><a>7</a></td></tr>
                <tr><th>문제를 검수</th><td><a>12</a></td></tr>
            </table>
        """
        self.assertEqual(BojProfileParser().parse(html), BojUserData(1693, "7", "12", 0))

    def test_profile_with_no_contributions(self):
        html = '<table id="statics"><tr><th>맞은 문제</th><td>0</td></tr></table>'
        self.assertEqual(BojProfileParser().parse(html), BojUserData(0, "0", "0", 0))

    def test_present_row_must_have_a_value(self):
        for label in ("만든 문제", "문제를 검수"):
            for cell in ("", "<td> </td>"):
                with self.subTest(label=label, cell=cell):
                    html = f"""
                        <table id="statics">
                            <tr><th>맞은 문제</th><td>5</td></tr>
                            <tr><th>{label}</th>{cell}</tr>
                        </table>
                    """
                    self.assertTrue(BojProfileParser().parse(html).is_failure)
