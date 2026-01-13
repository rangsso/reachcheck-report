# ReachCheck Report E2E (Naver First)

Naver-centric E2E flow for Store Analysis.
Search Naver → Select → Analyze → View Report.

## Project Structure

```
reachcheck-report/
  reachcheck_mvp/              # Backend
    src/                       # Source code
  web/                         # Frontend (Next.js)
    app/
    components/
  README.md
```

## How to Run

### 1. Backend

Navigate to `reachcheck_mvp`:

```bash
cd reachcheck_mvp
# Install Dependencies
pip install -r requirements.txt
# Run Server
uvicorn api:app --reload --app-dir src --port 8000
```
- API Docs: http://localhost:8000/docs

### 2. Frontend

Navigate to `web`:

```bash
cd web
# Install Dependencies
npm install
# Run Development Server
npm run dev
```
- Open http://localhost:3000 to start.

### 3. Environment Variables

**Backend (`.env`)**
```env
NAVER_CLIENT_ID=your_id
NAVER_CLIENT_SECRET=your_secret
GOOGLE_MAPS_API_KEY=your_key
KAKAO_REST_API_KEY=your_key
```

**Frontend (`web/.env.local`)**
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_NAVER_MAPS_KEY=your_ncp_key # For Map (Optional)
```

## Testing

**Naver Search (Backend Proxy)**
```bash
curl "http://localhost:8000/search/naver?query=스타벅스"
```

**Generate Report**
```bash
curl -X POST "http://localhost:8000/report" \
  -H "Content-Type: application/json" \
  -d '{"store_name": "Test Store", "address": "Seoul..."}'
```

## Notes
- Frontend Map pins may not appear for Naver results due to coordinate system differences (KATECH vs WGS84). This is expected in MVP.
- Analysis prioritizes Naver data as the source of truth.
