import unittest
from decimal import Decimal

from product_total import calculate_total


class CalculateTotalTests(unittest.TestCase):
    def test_multiple_items(self):
        items = [
            {"price": 12.50, "quantity": 2},
            {"price": 3.20, "quantity": 3},
        ]
        self.assertEqual(calculate_total(items), Decimal("34.60"))

    def test_empty_items(self):
        self.assertEqual(calculate_total([]), Decimal("0.00"))

    def test_decimal_prices(self):
        items = [{"price": Decimal("0.10"), "quantity": 3}]
        self.assertEqual(calculate_total(items), Decimal("0.30"))

    def test_rounds_to_two_decimal_places(self):
        items = [{"price": "1.005", "quantity": 1}]
        self.assertEqual(calculate_total(items), Decimal("1.00"))

    def test_negative_price_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "商品单价不能为负数"):
            calculate_total([{"price": -1, "quantity": 1}])

    def test_negative_quantity_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "商品数量不能为负数"):
            calculate_total([{"price": 1, "quantity": -1}])

    def test_missing_required_field_raises_key_error(self):
        with self.assertRaisesRegex(KeyError, "price 和 quantity"):
            calculate_total([{"price": 1}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
