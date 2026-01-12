import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# 1. 현재 파일 기준으로 .env 명시적으로 로드
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# 2. API Key 로드 확인
KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not KEY:
    raise SystemExit("GOOGLE_MAPS_API_KEY not found. Check .env location and name.")

# 3. 테스트 쿼리
query = "영등포구청 맛집"

url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
params = {
    "query": query,
    "language": "ko",
    "key": KEY,
}

# 4. 요청
r = requests.get(url, params=params, timeout=20)
data = r.json()

# 5. 결과 출력
print("status:", data.get("status"))
if data.get("error_message"):
    print("error_message:", data.get("error_message"))

results = data.get("results", [])[:5]
for i, item in enumerate(results, 1):
    print(f"\n[{i}] {item.get('name')}")
    print("  place_id:", item.get("place_id"))
    print("  address :", item.get("formatted_address"))
