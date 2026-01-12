# ReachCheck MVP

AI·검색·지도 환경에서 **가게가 어떻게 인식되고 있는지**를
실제 플랫폼 응답 기준으로 비교·진단하는 리포트 생성 MVP입니다.

본 프로젝트는 **국내 로컬 비즈니스(소상공인)** 를 대상으로
검색·지도·AI 추천 단계에서 발생하는 **정보 불일치와 신뢰 리스크**를
근거 기반으로 보여주는 것을 목표로 합니다.

---

## 핵심 기능 (MVP 범위)

### 1. 장소 검색 (Search)

* 상호명 입력 시 후보 리스트 반환
* 현재 지원 소스:

  * Google Places (Text Search)
  * Naver Local Search
  * Kakao Local Search

### 2. 데이터 수집 (Collect)

* 플랫폼별 가게 정보 수집

  * 이름
  * 주소
  * 전화번호
  * 영업시간 (가능한 경우)
  * 평점 / 리뷰 수 (Google 기준)

### 3. 비교·진단 (Analyze)

* 플랫폼 간 정보 **일치 / 불일치(Match / Mismatch)** 판정
* 필드별 비교 대상:

  * name
  * address
  * phone
  * opening hours
* 각 판정은 **원본 값(evidence)** 을 함께 보존

### 4. 리포트 생성 (Report)

* Page 1–4 구조의 HTML 리포트 생성
* PDF는 환경 제약으로 HTML fallback 사용

---

## 프로젝트 구조

```
reachcheck_mvp/
├── src/
│   ├── api.py          # FastAPI endpoints
│   ├── collector.py   # Google / Naver / Kakao data collectors
│   ├── analyzer.py    # Normalization & comparison logic
│   ├── report.py      # Jinja2 report rendering
│   ├── models.py      # Data schemas
│   └── main.py        # CLI entry (optional)
├── output/
│   └── report.html    # Generated report
├── test_*.py          # API test scripts
├── .env               # API keys (gitignored)
└── README.md
```

---

## 환경 변수 (.env)

```env
# Google
GOOGLE_MAPS_API_KEY=your_key

# Naver
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret

# Kakao
KAKAO_REST_API_KEY=your_rest_key
```

※ `.env` 파일은 반드시 `.gitignore`에 포함되어야 합니다.

---

## 실행 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 서버 실행 (FastAPI)

```bash
uvicorn reachcheck_mvp.src.api:app --reload
```

### 3. 장소 검색 테스트

```bash
curl -G "http://127.0.0.1:8000/places/search" \
  --data-urlencode "q=영등포구청 맛집"
```

### 4. 리포트 생성

```bash
curl -X POST "http://127.0.0.1:8000/report" \
  -H "Content-Type: application/json" \
  -d '{"place_id":"PLACE_ID","source":"google"}' > report.html
```

```bash
open report.html
```

---

## 현재 제한 사항 (MVP)

* PDF 렌더링은 시스템 라이브러리(cairo/pango) 제약으로 HTML fallback 사용
* AI 응답(ChatGPT/Gemini 등)은 현재 mock 데이터

---

## 설계 원칙

* **판정은 코드가 한다**
  AI는 설명과 해석만 담당
* **모든 불일치는 근거(evidence)를 가진다**
* 국내 기준 서비스:
  * Naver / Kakao 우선
  * Google은 AI 검색 관점 보조 채널

---

## 다음 단계 (Planned)

* evidence 기반 mismatch 엔진 고도화
* Page 1 “근거 표” 시각화 강화
* 리뷰 텍스트 분석 기반 Risk / Opportunity 자동 생성
* PDF 렌더링 안정화 (Playwright)
* Next.js 프론트엔드 연동
