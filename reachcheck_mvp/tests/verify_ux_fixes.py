
import sys
import os
import unittest
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from normalizer import format_display_address
from analyzer import Analyzer
from models import AnalysisResult, ConsistencyResult, StoreSchema, ReportData

class TestUXFixes(unittest.TestCase):
    def test_format_display_address(self):
        # Test Case 1: Standard Google Format
        raw1 = "Republic of Korea, Seoul, Yongsan-gu, Hangang-daero 100"
        expected1 = "Seoul, Yongsan-gu, Hangang-daero 100"
        self.assertEqual(format_display_address(raw1), expected1)
        
        # Test Case 2: Korean Prefix
        raw2 = "대한민국 서울특별시 영등포구"
        expected2 = "서울특별시 영등포구"
        self.assertEqual(format_display_address(raw2), expected2)
        
        # Test Case 3: Other variation
        raw3 = "Korea, Republic of, Seoul"
        expected3 = "Seoul"
        self.assertEqual(format_display_address(raw3), expected3)
        
        # Test Case 4: No change needed
        raw4 = "Seoul, Gangnam-gu"
        self.assertEqual(format_display_address(raw4), raw4)

    def test_analyzer_summary_logic(self):
        analyzer = Analyzer()
        
        # setup basic store
        store = StoreSchema(
            id="test", name="Fanpan", address="Seoul", phone="0507-1234", category="Cafe",
            lat=0, lng=0, hours="", description="", source_url=""
        )
        
        # Case 1: Phone Mismatch (but Phone Exists) -> No Summary Warning about Phone
        # We simulate "Phone Mismatch" status.
        consistency = [
            ConsistencyResult(field_name="Phone", status="Mismatch", evidence={"naver":"0507","google":"02"}, details="Mismatch"),
            ConsistencyResult(field_name="Address", status="Match", evidence={}, details="Match"),
            ConsistencyResult(field_name="Name", status="Match", evidence={}, details="Match")
        ]
        
        an_result = AnalysisResult(
            consistency_results=consistency,
            ai_mention_rate=100.0,
            ai_summary="", map_summary="", ai_intro_sentence="", risks=[], opportunities=[], improvements=[],
            map_statuses=[], ai_statuses=[], # REQUIRED
            ai_responses={}, field_provenance={}, map_accuracy=100
        )
        
        report = analyzer.process(store, an_result)
        
        # Assert Action Summary is NOT related to Phone
        print(f"[TEST] Mismatch Summary: {report.action_summary['warning']}")
        self.assertNotIn("전화번호가 등록되지 않아", report.action_summary["warning"])
        self.assertNotIn("전화번호가 다릅니다", report.action_summary["warning"]) 
        # Should fall back to default ("불안정하게 노출") or AI warning if low. Here generic default.
        
        # Case 2: All Phones Empty -> Show Warning
        store_empty = StoreSchema(
            id="test", name="NoPhone", address="Seoul", phone="", category="Cafe",
            lat=0, lng=0, hours="", description="", source_url=""
        )
        consistency_empty = [
            ConsistencyResult(field_name="Phone", status="Missing", evidence={"naver":None,"google":None}, details="Missing"),
             ConsistencyResult(field_name="Address", status="Match", evidence={}, details="Match")
        ]
        an_result_empty = AnalysisResult(
            consistency_results=consistency_empty,
             ai_mention_rate=100.0,
            ai_summary="", map_summary="", ai_intro_sentence="", risks=[], opportunities=[], improvements=[],
            map_statuses=[], ai_statuses=[], # REQUIRED
            ai_responses={}, field_provenance={}, map_accuracy=100
        )
        
        report_empty = analyzer.process(store_empty, an_result_empty)
        print(f"[TEST] Empty Summary: {report_empty.action_summary['warning']}")
        self.assertIn("전화번호가 등록되지 않아", report_empty.action_summary["warning"])

if __name__ == '__main__':
    unittest.main()
