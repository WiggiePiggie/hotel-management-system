import unittest
from utils import valid_date, valid_date_range, nights_between, calc_total

class DateAndPriceTests(unittest.TestCase):
    def test_valid_date(self):
        self.assertTrue(valid_date("2027-07-01"))
        self.assertFalse(valid_date("2027-02-30"))

    def test_valid_date_range(self):
        self.assertTrue(valid_date_range("2027-07-01", "2027-07-03"))
        self.assertFalse(valid_date_range("2027-07-03", "2027-07-01"))
        self.assertFalse(valid_date_range("2027-07-01", "2027-07-01"))

    def test_nights(self):
        self.assertEqual(nights_between("2027-07-01", "2027-07-04"), 3)

    def test_total(self):
        self.assertEqual(calc_total(100, "2027-07-01", "2027-07-04"), 300)

if __name__ == "__main__":
    unittest.main()
