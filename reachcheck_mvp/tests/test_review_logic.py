import unittest
from src.collector import DataCollector
from src.models import ReviewPhrase

class TestReviewLogic(unittest.TestCase):
    def setUp(self):
        self.collector = DataCollector()

    def test_analyze_reviews_basic(self):
        # Mock texts
        texts = [
            "정말 맛있어요! 사장님 친절해요.",
            "가격이 좀 비싸요 ㅠㅠ",
            "웨이팅이 너무 길어서 힘들었어요.",
            "음식이 깔끔하고 맛있어요.",
            "재방문 의사 있습니다. 추천해요!",
            "주차하기가 너무 불편해요.",
            "직원분들이 불친절해서 실망했어요.", 
            "인테리어가 예쁘고 사진 찍기 좋아요.",
            "여기 진짜 맛집 인정합니다.",
            "사람이 많아서 시끄러워요."
        ]
        
        # Expected:
        # Top: 맛있어요, etc.
        # Pain: 비싸요(비싸), 웨이팅, 불편해요(불편), 불친절, 시끄러워요(시끄)
        
        top, pain = self.collector._analyze_reviews(texts)
        
        print("\n[Test] Top Phrases:", top)
        print("[Test] Pain Phrases:", pain)
        
        # Check Top Phrases
        # "맛있어요" should be there
        top_texts = [p.text for p in top]
        self.assertTrue(any("맛있어요" in t for t in top_texts))
        
        # Check Pain Phrases
        # Should detect "비싸", "웨이팅", "불편", "불친절", "시끄" related
        pain_texts = [p.text for p in pain]
        self.assertTrue(any("비싸" in p for p in pain_texts))
        self.assertTrue(any("웨이팅" in p for p in pain_texts))
        
    def test_filtering_rules(self):
        texts = [
            "이벤트 참여합니다.", # Blacklist '이벤트'
            "협찬 받아서 작성한 리뷰입니다.", # Blacklist '협찬'
            "사장님 서비스 감사합니다.", # Blacklist '사장님', '서비스'
            "짧음", # Length < 6
            "이것은 아주 아주 아주 아주 아주 아주 아주 아주 아주 아주 아주 아주 긴 리뷰입니다.", # Length > 30 (maybe)
        ]
        
        top, pain = self.collector._analyze_reviews(texts)
        self.assertEqual(len(top), 0, "Should filter out blacklisted/short/long texts")

    def test_suffix_filter(self):
        texts = [
            "맛있어", # No proper ending (informal/unfinished?) vs '요'
            "최고임", # '임' -> valid, but len(3) < 6 -> FILTERED
            "다시 갈거다", # '다' -> valid, len(6) -> PASS
            "정말 별로네", # '네' -> valid, len(6) -> PASS
        ]
        
        top, pain = self.collector._analyze_reviews(texts)
        passed = [p.text for p in top + pain]
        
        # "최고임" should be filtered by length
        self.assertFalse(any("최고임" in t for t in passed))
        
        # "다시 갈거다" should pass
        self.assertTrue(any("다시 갈거다" in t for t in passed))
        
        # "정말 별로네" should pass and be in PAIN (keyword: 별로)
        pain_texts = [p.text for p in pain]
        self.assertTrue(any("정말 별로네" in t for t in pain_texts))

if __name__ == '__main__':
    unittest.main()
