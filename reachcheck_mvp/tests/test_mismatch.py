import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from normalizer import normalize_phone, normalize_name, normalize_address
from comparator import compare_data

class TestMismatchEngine(unittest.TestCase):
    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("02-1234-5678"), "0212345678")
        self.assertEqual(normalize_phone("+82-10-1234-5678"), "01012345678")
        self.assertEqual(normalize_phone("031 123 4567"), "0311234567")

    def test_normalize_name(self):
        self.assertEqual(normalize_name("Starbucks Gangnam"), "StarbucksGangnam")
        self.assertEqual(normalize_name("스타벅스 (강남점)"), "스타벅스")
        self.assertEqual(normalize_name("버거킹 강남지점"), "버거킹강남")

    def test_compare_match(self):
        sources = {
            "google": {"name": "Test Cafe", "phone": "02-1111-2222"},
            "naver": {"name": "Test Cafe (Branch)", "phone": "0211112222"},
        }
        results = compare_data(sources)
        name_res = next(r for r in results if r.field_name == "Name")
        phone_res = next(r for r in results if r.field_name == "Phone")
        
        self.assertEqual(name_res.status, "Match")
        self.assertEqual(phone_res.status, "Match")

    def test_compare_mismatch(self):
        sources = {
            "google": {"phone": "02-1111-2222"},
            "naver": {"phone": "02-9999-8888"},
        }
        results = compare_data(sources)
        phone_res = next(r for r in results if r.field_name == "Phone")
        self.assertEqual(phone_res.status, "Mismatch")

if __name__ == '__main__':
    unittest.main()
