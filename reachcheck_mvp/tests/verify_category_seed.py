
import sys
import os
import unittest
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from collector import DataCollector
from normalizer import is_valid_category_for_display
from models import SnapshotData, StoreSchema

class TestCategorySeed(unittest.TestCase):
    def test_infer_category_priority(self):
        collector = DataCollector()
        
        # Scenario 1: Seed has category_path (Highest Priority)
        naver_seed = {"category_path": "Food > Korean > Bibimbap", "category": "General Food"}
        naver_data = {"category": "Restaurant"}
        kakao_data = {"category_name": "Food > Western"}
        google_data = {"category": "Eatery"}
        
        cat, source = collector._infer_category(naver_data, kakao_data, google_data, naver_seed)
        self.assertEqual(cat, "Food > Korean > Bibimbap")
        self.assertEqual(source, "naver_seed_path")
        
        # Scenario 2: Seed has only category
        naver_seed_2 = {"category": "Seed Category"}
        cat2, source2 = collector._infer_category(naver_data, kakao_data, google_data, naver_seed_2)
        self.assertEqual(cat2, "Seed Category")
        self.assertEqual(source2, "naver_seed")
        
        # Scenario 3: No Seed, use Naver Data
        cat3, source3 = collector._infer_category(naver_data, kakao_data, google_data, None)
        self.assertEqual(cat3, "Restaurant")
        
        # Scenario 4: No Seed, No Naver, use Kakao
        cat4, source4 = collector._infer_category({}, kakao_data, google_data, None)
        self.assertEqual(cat4, "Western") # Last part of "Food > Western"
        
        # Scenario 5: Google Fallback
        cat5, source5 = collector._infer_category({}, {}, google_data, None)
        self.assertEqual(cat5, "Eatery")
        
        # Scenario 6: All Empty -> Return empty string (NOT "Unknown")
        cat6, source6 = collector._infer_category({}, {}, {}, None)
        self.assertEqual(cat6, "")

    def test_visibility_logic(self):
        # Visible
        self.assertTrue(is_valid_category_for_display("Korean Food"))
        self.assertTrue(is_valid_category_for_display("Cafe"))
        
        # Hidden
        self.assertFalse(is_valid_category_for_display("Establishment"))
        self.assertFalse(is_valid_category_for_display("Point of Interest"))
        self.assertFalse(is_valid_category_for_display("UNKNOWN"))
        self.assertFalse(is_valid_category_for_display("업종 정보 없음"))
        self.assertFalse(is_valid_category_for_display(""))
        self.assertFalse(is_valid_category_for_display(None))

if __name__ == '__main__':
    unittest.main()
