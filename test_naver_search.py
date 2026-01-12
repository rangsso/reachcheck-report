import os
import requests
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    raise SystemExit("NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not found in .env")

query = "영등포구청 맛집"
url = "https://openapi.naver.com/v1/search/local.json"

headers = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

params = {
    "query": query,
    "display": 5,
    "sort": "random"
}

r = requests.get(url, headers=headers, params=params, timeout=20)
print("HTTP:", r.status_code)

data = r.json()
print("total:", data.get("total"))

items = data.get("items", [])
for i, item in enumerate(items, 1):
    print(f"\n[{i}] {item.get('title').replace('<b>', '').replace('</b>', '')}")
    print("  address:", item.get("roadAddress") or item.get("address"))
    print("  category:", item.get("category"))
    print("  link:", item.get("link"))
