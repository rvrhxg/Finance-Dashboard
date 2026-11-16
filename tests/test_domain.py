import unittest
from datetime import date
from app.domain import ValidationError,money_to_kopecks,summarize,validate_period


class FinanceRules(unittest.TestCase):
    def test_exact_decimal_money_and_invalid_values(self):
        self.assertEqual(money_to_kopecks("1250,99"),125099)
        self.assertEqual(money_to_kopecks("0.01"),1)
        for value in ["NaN","Infinity","-1","0","1.001","abc",True,1.5]:
            with self.assertRaises(ValidationError):
                money_to_kopecks(value)

    def test_summary_and_no_income_ratio(self):
        self.assertEqual(summarize([{"kind":"income","amount_kopecks":100000},{"kind":"expense","amount_kopecks":25000}]),{"income_kopecks":100000,"expense_kopecks":25000,"balance_kopecks":75000,"savings_rate_percent":75.0})
        self.assertIsNone(summarize([{"kind":"expense","amount_kopecks":1}])["savings_rate_percent"])
        self.assertEqual(summarize([])["balance_kopecks"],0)

    def test_invalid_period(self):
        with self.assertRaises(ValidationError):
            validate_period(date(2026,2,1),date(2026,1,1))
