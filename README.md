# ReachCheck Report E2E

Minimal E2E flow for Store Analysis.
Search store → select from map → analyze → view report (PDF + HTML).

## Project Structure

```
reachcheck-report/
  reachcheck_mvp/              # Backend
    src/                       # Source code
    snapshots/                 # JSON snapshots
    outputs/                   # Generated reports
  web/                         # Frontend (React + Vite)
    src/
    package.json
    .env
  README.md
```

## How to Run

### 1. Backend

Navigate to `reachcheck_mvp`:

```bash
cd reachcheck_mvp
# Install Dependencies (if not already)
pip install -r requirements.txt
# Run Server
uvicorn api:app --reload --app-dir src --port 8000
```

- API Docs: http://localhost:8000/docs
- Reports served at: http://localhost:8000/outputs/

### 2. Frontend (Next.js)

Navigate to `web`:

```bash
cd web
# Install Dependencies
npm install
# Run Development Server
npm run dev
```

- Open http://localhost:3000 to start the flow.

### 3. Environment Variables

**Backend (`.env`)**
Requires Google, Naver, Kakao API Keys.

**Frontend (`web/.env.local`)**
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_KAKAO_MAP_KEY=YOUR_KAKAO_JS_KEY # (Optional: Defaults to REST key if using provided setup)
```
*Note: The frontend currently uses the REST Key as a fallback for the JS SDK, which may work depending on key configuration. For best results, use a dedicated Javascript Key.*

## E2E Flow

1. **Search**: Enter a store name (e.g. "Starbucks Gangnam") in the search bar.
2. **Select**: Choose a candidate from the list or click a pin on the map.
3. **Analyze**: Click "Generate Report". This triggers data collection and analysis.
4. **View**: Download the PDF or view the HTML report directly in the browser.

## Features

- **ReachCheck MVP Backend**:
  - `GET /places/search`: Kakao Local Search
  - `POST /report`: Generates snapshots and report files
  - `STATIC /outputs`: Serves generated files
- **React Frontend**:
  - Kakao Maps integration
  - Interactive Store Picker
  - Real-time Analysis status
