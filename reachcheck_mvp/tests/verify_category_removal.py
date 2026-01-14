
import sys
import os
import unittest
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from collector import DataCollector
from analyzer import Analyzer
from models import SnapshotData, StoreSchema, AnalysisResult

class TestCategoryRemoval(unittest.TestCase):
    def setUp(self):
        os.environ["LLM_PROVIDER"] = "mock"

    def test_search_keyword_and_intro(self):
        collector = DataCollector()
        
        # Mock Snapshot with Category Path
        store = StoreSchema(id="test", name="KimbapHeaven", address="Seoul", phone="010", category="Food", lat=0, lng=0, hours="", description="", source_url="")
        
        snapshot = SnapshotData(
            store_id="test",
            timestamp="20240101",
            standard_info=store,
            raw_naver={"category_path": "Food > Kimbap"},
            raw_google={}, raw_kakao={},
            llm_responses={},
            missing_fields=[], mismatch_fields=[], field_provenance={}, search_candidates={}, errors={}
        )
        
        # Test Mock Analysis logic (search_keyword derivation)
        # We need to run mock_analysis
        result = collector.mock_analysis(snapshot)
        
        # Verify AI Intro Sentence
        # Should be: "{store_name}은(는) {area}에서 꾸준히 언급되는 장소입니다."
        # Area from "Seoul" -> "Seoul" (first 2 words)
        expected_intro = "KimbapHeaven은(는) Seoul에서 꾸준히 언급되는 장소입니다."
        self.assertEqual(result.ai_intro_sentence, expected_intro)
        
        # Verify AI Prompts (Mock Responses)
        # Should contain "Kimbap" (last part of Food > Kimbap)
        responses = result.ai_responses.get("ChatGPT", []) # Mock puts it in ChatGPT? Check code.
        # Code puts mock in all engines.
        
        self.assertTrue(len(responses) > 0)
        q1 = responses[0]["question"]
        print(f"Generated Question 1: {q1}")
        
        # Expect "Seoul에서 추천할 만한 Kimbap이 있나요?"
        self.assertIn("Kimbap", q1)
        self.assertIn("Seoul", q1)
        self.assertNotIn("Food", q1) # Should use Kimbap not Food (category) if search_keyword logic works
        
    def test_default_search_keyword(self):
        collector = DataCollector()
        store = StoreSchema(id="test", name="GeneralStore", address="Busan", phone="010", category="General", lat=0, lng=0, hours="", description="", source_url="")
        
        snapshot = SnapshotData(
            store_id="test",
            timestamp="20240101",
            standard_info=store,
            raw_naver={}, # No category path
            raw_google={}, raw_kakao={},
            llm_responses={},
            missing_fields=[], mismatch_fields=[], field_provenance={}, search_candidates={}, errors={}
        )
        
        result = collector.mock_analysis(snapshot)
        responses = result.ai_responses.get("ChatGPT", [])
        q1 = responses[0]["question"]
        print(f"Generated Question 1 (Default): {q1}")
        
        # Expect "Busan에서 추천할 만한 식당이 있나요?" (Default keyword)
        self.assertIn("식당", q1)
        self.assertNotIn("General", q1)

    def test_analyzer_no_override(self):
        analyzer = Analyzer()
        # Setup result with correct intro
        res = AnalysisResult(
            map_accuracy=100, ai_mention_rate=100, map_summary="", ai_summary="", 
            map_statuses=[], ai_statuses=[], consistency_results=[], risks=[], opportunities=[], improvements=[],
            ai_intro_sentence="Correct Intro",
            ai_responses={}, field_provenance={}
        )
        store = StoreSchema(id="test", name="Test", address="", phone="", category="WrongCat", lat=0, lng=0, hours="", description="", source_url="")
        
        # from models import StoreInfo # Compatible shim used in api.py, but Analyzer uses StoreInfo usually? 
        # Analyzer.process expects store object.
        
        final_report = analyzer.process(store, res)
        
        # Check if intro sentence is preserved
        self.assertEqual(final_report.analysis.ai_intro_sentence, "Correct Intro")
        
if __name__ == '__main__':
    unittest.main()
