import os
import requests
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY")
if not KAKAO_KEY:
    raise SystemExit("KAKAO_REST_API_KEY missing (.env 확인)")

q = "영등포구청 맛집"
url = "https://dapi.kakao.com/v2/local/search/keyword.json"
headers = {"Authorization": f"KakaoAK {KAKAO_KEY}"}
params = {"query": q, "size": 5}

r = requests.get(url, headers=headers, params=params, timeout=20)

print("HTTP:", r.status_code)
print("Content-Type:", r.headers.get("content-type"))
print("Raw:", r.text[:300])  # 너무 길까봐 300자만

try:
    data = r.json()
except Exception as e:
    raise SystemExit(f"JSON 파싱 실패: {e}")

print("meta:", data.get("meta"))
print("errorType:", data.get("errorType"))
print("message:", data.get("message"))

docs = data.get("documents", [])
print("documents_count:", len(docs))

for i, d in enumerate(docs, 1):
    print(f"\n[{i}] {d.get('place_name')}")
    print("  id:", d.get("id"))
    print("  address:", d.get("road_address_name") or d.get("address_name"))
    print("  phone:", d.get("phone"))
