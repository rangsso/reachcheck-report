import os
import sys
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# Log env loading status (value check)
if NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
    print("[-] Naver API Keys loaded successfully.")
else:
    print("[!] Naver API Keys MISSING.")

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collector import DataCollector
from analyzer import Analyzer
from report import ReportGenerator

app = FastAPI(title="ReachCheck API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
# Mount outputs directory explicitly
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

class ReportRequest(BaseModel):
    place_id: str = "" # Optional now if using Naver flow
    store_name: str
    address: str = ""
    road_address: str = ""
    tel: str = ""
    naver_link: str = "" # To be used as ID or source
    mapx: str = ""
    mapy: str = ""

from resolver import StoreResolver

@app.post("/report")
async def generate_report(request: ReportRequest):
    try:
        # 1. Resolve Store ID if not provided, or verify provided one
        resolver = StoreResolver()
        place_id = request.place_id
        store_name = request.store_name
        
        # If place_id is "auto" or empty, try to resolve from name
        if not place_id or place_id == "auto":
             resolved_id = resolver.resolve(store_name)
             if not resolved_id:
                 raise HTTPException(status_code=404, detail=f"Could not resolve store: {store_name}")
             place_id = resolved_id

        # 2. Collect (This saves snapshot automatically)
        collector = DataCollector()
        
        # Build Naver Seed from Request
        naver_seed = {
            "store_name": request.store_name,
            "address": request.address,
            "road_address": request.road_address,
            "tel": request.tel,
            "naver_link": request.naver_link,
            "mapx": request.mapx,
            "mapy": request.mapy
        }
        
        # Use Naver Seed if link or map coordinates provided (heuristic for Naver source)
        if request.naver_link or request.mapx:
             snapshot = collector.collect(store_name, place_id=place_id, naver_seed=naver_seed)
        else:
             snapshot = collector.collect(store_name, place_id=place_id)
        
        # 3. Analyze (Using Snapshot)
        analysis_result = collector.mock_analysis(snapshot)
        
        # 4. Process Report Data
        analyzer = Analyzer()
        
        # Quick Fix: Create legacy StoreInfo from StoreSchema
        from models import StoreInfo
        legacy_store_info = StoreInfo(
            name=snapshot.standard_info.name,
            address=snapshot.standard_info.address,
            phone=snapshot.standard_info.phone,
            category=snapshot.standard_info.category,
            place_id=snapshot.standard_info.id
        )
        
        report_data = analyzer.process(legacy_store_info, analysis_result)
        
        # 5. Generate HTML/PDF
        generator = ReportGenerator()
        filename = f"{snapshot.store_id}_report.pdf" # Use actual ID
        
        output_path = generator.generate(report_data, filename=filename) 
        
        # Copy to outputs
        basename = os.path.basename(output_path)
        dest_pdf = os.path.join(OUTPUTS_DIR, basename)
        if os.path.abspath(output_path) != os.path.abspath(dest_pdf):
            import shutil
            shutil.copy(output_path, dest_pdf)
            
        # HTML sidecar
        html_src = output_path.replace('.pdf', '.html')
        html_basename = basename.replace('.pdf', '.html')
        dest_html = os.path.join(OUTPUTS_DIR, html_basename)
        
        if os.path.exists(html_src) and os.path.abspath(html_src) != os.path.abspath(dest_html):
             shutil.copy(html_src, dest_html)
             
        base_url = "http://localhost:8000" # In prod this should be dynamic
        
        # Return HTML content directly if requested, or URL
        # Prompt requirement: "HTML string or {html: ...}"
        # Let's return JSON with HTML URL + Content for flexibility
        
        with open(dest_html, "r", encoding="utf-8") as f:
            html_content = f.read()

        return {
            "snapshot_id": snapshot.store_id + "_" + snapshot.timestamp,
            "report_pdf_url": f"{base_url}/outputs/{basename}",
            "report_html_url": f"{base_url}/outputs/{html_basename}",
            "html_content": html_content
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/places/search")
def search_places(q: str = Query(..., min_length=1)):
    try:
        collector = DataCollector()
        candidates = collector.search_for_picker(q)
        return candidates # Returns list directly as per requirements
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/naver")
def search_naver(query: str = Query(..., min_length=1)):
    """
    Proxy to Naver Local Search API
    Returns normalized list of candidates.
    """
    print(f"[DEBUG] /search/naver called with query: {query}")

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return JSONResponse(
            status_code=500, 
            content={"error": "NAVER_AUTH_ERROR", "message": "Server configuration error"}
        )
        
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": 5, "sort": "random"} 
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        
        if resp.status_code == 401:
            return JSONResponse(status_code=401, content={"error": "NAVER_AUTH_ERROR"})
            
        data = resp.json()
        items = data.get("items", [])
        
        if not items:
            return JSONResponse(status_code=200, content=[]) # Empty list
            
        results = []
        for item in items:
            # Normalize fields
            name = item.get('title', '').replace('<b>', '').replace('</b>', '')
            
            # Use appropriate address
            addr = item.get("address")
            road_addr = item.get("roadAddress")
            
            results.append({
                "name": name,
                "category": item.get("category"),
                "address": addr,
                "roadAddress": road_addr,
                "tel": item.get("telephone", ""),
                "mapx": item.get("mapx"),
                "mapy": item.get("mapy"),
                "link": item.get("link"),
                "source_url": item.get("link")
            })
            
        return results
        
    except Exception as e:
        print(f"[!] Naver search proxy error: {e}")
        return JSONResponse(status_code=500, content={"error": "NAVER_UNKNOWN_ERROR", "detail": str(e)})

@app.get("/")
def health_check():
    return {"status": "ok", "service": "ReachCheck MVP"}
