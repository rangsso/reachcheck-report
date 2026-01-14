
import requests
from bs4 import BeautifulSoup

def check_search_scraping():
    query = "스타벅스 강남R"
    url = f"https://search.naver.com/search.naver?query={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers)
        print(f"[Search] Status: {resp.status_code}")
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Look for snippets
            # Common selectors: .biz_name_area, .dHbCL (phone class often changes)
            # Try finding text with 02- or 010-
            text = soup.get_text()
            if "02-" in text or "1522-3232" in text:
                print("[Search] Phone number pattern found in text")
            else:
                print("[Search] Phone number pattern NOT found")
                
            # Try specific selector if known (often flaky)
            # In user request: "가게 정보 카드 영역"
    except Exception as e:
        print(f"[Search] Error: {e}")

if __name__ == "__main__":
    check_search_scraping()
