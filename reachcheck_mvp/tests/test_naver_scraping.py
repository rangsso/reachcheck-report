
import pytest
import os
from unittest.mock import MagicMock, patch
from src.collector import DataCollector

# Fixture for a data collector instance
@pytest.fixture
def collector():
    return DataCollector()

class TestNaverScraping:
    
    def test_normalization(self, collector):
        # 1. 02 case
        assert collector._normalize_and_validate_phone("021234567") == "02-123-4567"
        assert collector._normalize_and_validate_phone("0212345678") == "02-1234-5678"
        # 2. 010 case
        assert collector._normalize_and_validate_phone("01012345678") == "010-1234-5678"
        # 3. 031 case
        assert collector._normalize_and_validate_phone("0311234567") == "031-123-4567"
        # 4. 1588 case
        assert collector._normalize_and_validate_phone("15881234") == "1588-1234"
        # 5. Invalid
        assert collector._normalize_and_validate_phone("123") is None
        assert collector._normalize_and_validate_phone("010-123-45") is None

    @patch('src.collector.sync_playwright')
    def test_fetch_naver_map_detail_playwright_mock(self, mock_playwright, collector):
        # Mocking Playwright flow
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value.new_page.return_value = mock_page
        
        # Scenario: Selector found
        mock_element = MagicMock()
        mock_element.text_content.return_value = "02-1234-5678"
        mock_page.wait_for_selector.return_value = mock_element
        
        phone = collector.fetch_naver_map_detail("12345")
        assert phone == "02-1234-5678"
        
    @patch('src.collector.requests.get')
    def test_fetch_naver_search_web_mock(self, mock_get, collector):
        # Mocking requests
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # HTML with phone in text
        mock_resp.text = "<html><body><div class='biz_info'>02-9999-8888</div></body></html>"
        mock_get.return_value = mock_resp
        
        phone = collector.fetch_naver_search_web("Starbucks")
        assert phone == "02-9999-8888"

    @pytest.mark.network
    def test_integration_real_store(self, collector):
        """
        Real network test.
        Uses Starbucks Gangnam R (11579737) which is stable.
        """
        # Place ID might need to be verified if it changes, but usually stable.
        pid = "11579737" 
        print(f"Testing Real Scraping for {pid}...")
        phone = collector.fetch_naver_map_detail(pid)
        print(f"Fetched Phone: {phone}")
        
        # Fallback to search if map detail fails in test env (e.g. anti-bot)
        if not phone:
             print("Map Detail failed, trying Search...")
             phone = collector.fetch_naver_search_web("스타벅스 강남R")
             print(f"Search Fetched Phone: {phone}")
             
        assert phone is not None
        # Starbucks Gangnam usually 1522-3232
        assert "1522" in phone or "02" in phone
