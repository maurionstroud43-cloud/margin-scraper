import unittest

from app import parse_price, score_item


class ScoringTests(unittest.TestCase):
    def test_parse_price_handles_currency(self):
        self.assertEqual(parse_price("$1,249.99"), 1249.99)

    def test_score_item_returns_margin_item(self):
        current = [20, 24, 22, 21, 26, 30]
        sold = [45, 50, 47, 52, 44, 49]
        item = score_item(current, sold, "demo")
        self.assertIsNotNone(item)
        self.assertGreater(item.margin_percent, 50)
        self.assertEqual(item.query, "demo")


if __name__ == "__main__":
    unittest.main()
