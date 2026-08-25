import unittest
from decimal import Decimal

from total_price import calculate_total_price


class CalculateTotalPriceTests(unittest.TestCase):
    def test_multiple_items(self):
        items = [
            {"price": "19.99", "quantity": 2},
            {"price": "5.50", "quantity": 3},
        ]
        self.assertEqual(calculate_total_price(items), Decimal("56.48"))

    def test_discount_and_tax(self):
        items = [{"price": "100.00", "quantity": 2}]
        result = calculate_total_price(items, discount="0.10", tax_rate="0.06")
        self.assertEqual(result, Decimal("190.80"))

    def test_empty_items(self):
        self.assertEqual(calculate_total_price([]), Decimal("0.00"))

    def test_rounds_to_two_decimal_places(self):
        items = [{"price": "0.335", "quantity": 1}]
        self.assertEqual(calculate_total_price(items), Decimal("0.34"))

    def test_rejects_negative_price(self):
        with self.assertRaisesRegex(ValueError, "price must be non-negative"):
            calculate_total_price([{"price": -1, "quantity": 1}])

    def test_rejects_negative_quantity(self):
        with self.assertRaisesRegex(ValueError, "quantity must be non-negative"):
            calculate_total_price([{"price": 1, "quantity": -1}])

    def test_rejects_invalid_discount(self):
        with self.assertRaisesRegex(ValueError, "discount must be between 0 and 1"):
            calculate_total_price([], discount="1.01")

    def test_rejects_negative_tax_rate(self):
        with self.assertRaisesRegex(ValueError, "tax_rate must be non-negative"):
            calculate_total_price([], tax_rate="-0.01")


if __name__ == "__main__":
    unittest.main()
