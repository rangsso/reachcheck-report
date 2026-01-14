from playwright.sync_api import sync_playwright

print("Starting Playwright check...")
try:
    with sync_playwright() as p:
        print("Launching Chromium (headless=True)...")
        browser = p.chromium.launch(headless=True)
        print("Browser launched.")
        page = browser.new_page()
        page.goto("https://search.naver.com")
        print("Page loaded.")
        browser.close()
    print("Playwright check passed.")
except Exception as e:
    print(f"Playwright check failed: {e}")
