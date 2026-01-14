
import sys
import os
import unittest
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from models import SnapshotData, StoreSchema, AnalysisResult, ConsistencyResult
from analyzer import Analyzer
from collector import DataCollector

class TestLogicAndProvenance(unittest.TestCase):
    def test_phone_warning_logic(self):
        # Case 1: Phone Missing in Standard -> "Not Registered" Warning
        scheme_missing = StoreSchema(id="1", name="Test", address="Addr", phone="", category="Food", lat=0, lng=0, hours="", description="")
        
        # Case 2: Phone Present but Mismatch -> "Mismatch" Warning
        scheme_mismatch = StoreSchema(id="2", name="Test", address="Addr", phone="010-1234-5678", category="Food", lat=0, lng=0, hours="", description="")
        
        analyzer = Analyzer()
        
        # Mock Analysis Result
        mock_res_missing = AnalysisResult(
            map_accuracy=0, ai_mention_rate=0, map_summary="", ai_summary="", map_statuses=[], ai_statuses=[], 
            consistency_results=[ConsistencyResult("Phone", "Match", {}, "Matches")], # Even if consistency says Match (e.g. all empty), Analyzer checks standard phone
            risks=[], opportunities=[], improvements=[], ai_intro_sentence="", ai_responses={}
        )
        
        report_data_missing = analyzer.process(scheme_missing, mock_res_missing)
        self.assertIn("등록되지 않아", report_data_missing.action_summary['warning'])
        
        mock_res_mismatch = AnalysisResult(
             map_accuracy=0, ai_mention_rate=0, map_summary="", ai_summary="", map_statuses=[], ai_statuses=[], 
            consistency_results=[ConsistencyResult("Phone", "Mismatch", {}, "Mismatch found")],
            risks=[], opportunities=[], improvements=[], ai_intro_sentence="", ai_responses={}
        )
        report_data_mismatch = analyzer.process(scheme_mismatch, mock_res_mismatch)
        self.assertIn("다르게 표시되어", report_data_mismatch.action_summary['warning'])

    def test_infer_category(self):
        collector = DataCollector()
        
        # Test 1: Naver Seed Priority
        c, s = collector._infer_category({}, {}, {}, {"category": "SeedCat"})
        self.assertEqual(c, "SeedCat")
        self.assertEqual(s, "naver_seed")
        
        # Test 2: Kakao Inference
        c, s = collector._infer_category({"category": "일반 매장"}, {"category_name": "음식점 > 한식 > 국밥"}, {}, None)
        self.assertEqual(c, "국밥")
        self.assertEqual(s, "kakao")
        
        # Test 3: Google Fallback
        c, s = collector._infer_category({"category": "일반 매장"}, {}, {"category": "Restaurant"}, None)
        self.assertEqual(c, "Restaurant")
        self.assertEqual(s, "google")

if __name__ == '__main__':
    unittest.main()
