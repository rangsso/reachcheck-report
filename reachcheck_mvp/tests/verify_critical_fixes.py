
import sys
import os
import unittest
import re

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from normalizer import normalize_address, normalize_category_for_ai
from comparator import compare_data, ConsistencyResult

class TestCriticalFixes(unittest.TestCase):
    def test_address_normalization_strict(self):
        # 1. Country Removal
        raw = "Republic of Korea, Seoul, Yongsan-gu"
        norm = normalize_address(raw)
        self.assertNotIn("Republic of Korea", norm)
        self.assertIn("Seoul", norm) # Should keep city
        
        # 2. Parentheses Removal
        raw_parens = "Seoul (South) Yongsan-gu (Building A)"
        norm_parens = normalize_address(raw_parens)
        self.assertNotIn("Building", norm_parens)
        self.assertNotIn("South", norm_parens)
        
        # 3. Details Removal (Floor, Suite)
        raw_detail = "Seoul Yongsan-gu Hangang-daero 100 1F"
        norm_detail = normalize_address(raw_detail)
        self.assertNotIn("1F", norm_detail)
        
        raw_korean = "서울 영등포구 당산동 3가 101호 B1"
        norm_korean = normalize_address(raw_korean)
        self.assertNotIn("101호", norm_korean)
        self.assertNotIn("B1", norm_korean)
        
        print(f"[TEST] Norm: {raw_detail} -> {norm_detail}")

    def test_address_comparator_core_token(self):
        # Case A: Jibun vs Road (Match)
        # Naver: "서울 영등포구 당산동1가 53-4"
        # Google: "대한민국 서울특별시 영등포구 영등포로 143"
        # Kakao: "서울 영등포구 당산동1가 53-4"
        
        sources_mix = {
            "naver": {"address": "서울 영등포구 당산동1가 53-4"},
            "google": {"address": "대한민국 서울특별시 영등포구 영등포로 143"},
            "kakao": {"address": "서울 영등포구 당산동1가 53-4"}
        }
        
        results = compare_data(sources_mix)
        addr_res = next(r for r in results if r.field_name == "Address")
        self.assertEqual(addr_res.status, "Match", f"Jibun vs Road should Match. Got {addr_res.status}")
        
        # Case B: Different Gu -> Mismatch
        sources_diff_gu = {
             "naver": {"address": "서울 영등포구 당산동"},
             "google": {"address": "서울 강남구 당산동"},
             "kakao": {"address": "서울 강남구 당산동"}
        }
        results_gu = compare_data(sources_diff_gu)
        addr_gu = next(r for r in results_gu if r.field_name == "Address")
        self.assertEqual(addr_gu.status, "Mismatch", "Different Gu must Mismatch")

        # Case C: Same Type, Same Token -> Match
        sources_same = {
            "naver": {"address": "서울 영등포구 영등포로 143"},
            "google": {"address": "서울 영등포구 영등포로 143 1층"}, # 1층 removed
            "kakao": {"address": "서울 영등포구 영등포로 143"}
        }
        results_same = compare_data(sources_same)
        addr_same = next(r for r in results_same if r.field_name == "Address")
        self.assertEqual(addr_same.status, "Match", "Same address must Match")
        
        # Case D: Same Type, Different Token -> Mismatch
        sources_diff_num = {
             "naver": {"address": "서울 영등포구 영등포로 143"},
             "google": {"address": "서울 영등포구 영등포로 999"},
             "kakao": {"address": "서울 영등포구 영등포로 999"}
        }
        results_num = compare_data(sources_diff_num)
        addr_num = next(r for r in results_num if r.field_name == "Address")
        self.assertEqual(addr_num.status, "Mismatch", "Same road different number must Mismatch")

    def test_phone_mismatch_message(self):
        sources = {
            "naver": {"phone": "0507-1234-5678"},
            "google": {"phone": "02-1234-5678"},
            "kakao": {"phone": "02-1234-5678"}
        }
        results = compare_data(sources)
        phone_res = next(r for r in results if r.field_name == "Phone")
        
        self.assertEqual(phone_res.status, "Mismatch")
        self.assertIn("번호 다름", phone_res.details)
        self.assertIn("대표번호", phone_res.details)

    def test_category_normalization(self):
        self.assertIsNone(normalize_category_for_ai("Establishment"))
        # valid non-ignored string should return itself
        self.assertEqual(normalize_category_for_ai("primary_school"), "primary_school")
        self.assertEqual(normalize_category_for_ai("Restaurant"), "식당")

if __name__ == '__main__':
    unittest.main()
