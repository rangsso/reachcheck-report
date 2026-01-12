import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

keys = [
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "KAKAO_REST_API_KEY",
]

for k in keys:
    v = os.getenv(k)
    print(k, "OK" if v else "MISSING")
