import requests
import bs4

def debug_tier1(query):
    url = "https://search.naver.com/search.naver"
    params = {"query": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Fetching {url} for query='{query}'...")
    resp = requests.get(url, params=params, headers=headers)
    print(f"Status: {resp.status_code}")
    
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved debug.html")
    
    soup = bs4.BeautifulSoup(resp.text, "html.parser")
    
    # Check for direct Place url links
    links = soup.select('a[href*="place.naver.com"]')
    print(f"Found {len(links)} links containing 'place.naver.com':")
    for link in links[:5]:
        print(f" - href: {link.get('href')}")
        print(f"   text: {link.get_text(strip=True)[:30]}...")

    # Check for Snippets classes
    # Common classes: .review_content, .dsc_txt, .text_area
    snippets = soup.select('.review_content, .dsc_txt, .text_area, .review_txt, .api_txt_lines')
    print(f"Found {len(snippets)} potential snippets:")
    for s in snippets[:5]:
        print(f" - {s.get_text(strip=True)[:50]}...")

if __name__ == "__main__":
    debug_tier1("스타벅스 강남R점")
