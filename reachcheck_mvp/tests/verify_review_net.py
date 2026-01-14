import pytest
import os
import sys
# Ensure src is in path for imports within collector
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from models import ReviewStats
from collector import DataCollector

@pytest.mark.network
def test_naver_review_collection_real():
    """
    Real network test against a known entity.
    WARNING: This hits Naver. Only run locally.
    """
    collector = DataCollector()
    
    # Target: "스타벅스 강남R점" (Starbucks Gangnam Reserve) 
    # Usually has plenty of reviews.
    store_name = "스타벅스 강남R점"
    
    print(f"\n[Test] Collecting reviews for {store_name}...")
    print(f"[Info] Playwright available: {collector.playwright_available}")
    
    # We pass a dummy Naver seed just in case, or None
    stats = collector.collect_reviews(store_name, place_id="TEST-NET-001", naver_seed=None)
    
    if stats and stats.review_count > 0:
        print(f"\n[Result] Source used: {stats.source}")
        print(f"Review Count: {stats.review_count}")
        print(f"Fallback used: {stats.fallback_used}")
        print(f"Debug Code: {stats.debug_code}")
        print(f"Notes: {stats.notes}")
    
    if stats.top_phrases:
        print("Top Phrases:")
        for p in stats.top_phrases:
            print(f" - {p.text} ({p.count})")
            
    if stats.pain_phrases:
        print("Pain Phrases:")
        for p in stats.pain_phrases:
            print(f" - {p.text} ({p.count})")
            
    if stats.sample_reviews:
        print("Samples:")
        for s in stats.sample_reviews:
            print(f" [{s.type}] {s.text[:50]}...")

    # Assertions
    # Note: Search might fail if IP blocked, but assuming working env:
    if stats.source != "error":
        # We expect some result or at least a "no_reviews" empty state, not crash
        assert isinstance(stats, ReviewStats)
    else:
        pytest.fail(f"Collection returned error source. Notes: {stats.notes}")

if __name__ == "__main__":
    test_naver_review_collection_real()
