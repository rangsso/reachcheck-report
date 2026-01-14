
import requests
import json

PLACE_ID = "11579737"

def check_v5_api():
    print(f"[-] Checking v5 API for {PLACE_ID}...")
    url = f"https://map.naver.com/v5/api/sites/summary/{PLACE_ID}?lang=ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://map.naver.com/"
    }
    try:
        resp = requests.get(url, headers=headers)
        print(f"[v5] Status: {resp.status_code}")
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"[v5] Name: {data.get('name')}")
                print(f"[v5] Phone: {data.get('phone')}")
            except:
                print("[v5] JSON decode failed")
        else:
            print(f"[v5] Failed: {resp.status_code}")
    except Exception as e:
        print(f"[v5] Error: {e}")

if __name__ == "__main__":
    check_v5_api()
