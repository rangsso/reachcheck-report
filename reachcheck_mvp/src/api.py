import os
import sys
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collector import DataCollector
from analyzer import Analyzer
from report import ReportGenerator

app = FastAPI(title="ReachCheck API")

class ReportRequest(BaseModel):
    place_id: str
    store_name: str = "Unknown Store"

@app.post("/report", response_class=HTMLResponse)
async def generate_report(request: ReportRequest):
    try:
        # 1. Collect
        collector = DataCollector()
        # Accept explicit place_id from request
        store_info = collector.collect(request.store_name, place_id=request.place_id)
        
        analysis_result = collector.mock_analysis(store_info)
        
        # 2. Analyze
        analyzer = Analyzer()
        report_data = analyzer.process(store_info, analysis_result)
        
        # 3. Generate HTML
        # We want the raw HTML string, not just a file path.
        # Modifying ReportGenerator to support string return or reading the file back.
        
        generator = ReportGenerator()
        # Generate to a temporary or standard location
        filename = f"{request.place_id}_report.pdf" 
        # Note: Our ReportGenerator currently returns a path (PDF or HTML fallback)
        output_path = generator.generate(report_data, filename=filename)
        
        # If it returned an HTML path (fallback), read it
        if output_path.endswith('.html'):
            with open(output_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return html_content
        
        # If it returned a PDF path, we might technically want to return that,
        # but user asked for HTML output for now.
        # Let's force HTML generation in ReportGenerator on the fly or read the html side-effect file.
        # The ReportGenerator.generate method saves an HTML sidecar.
        html_sidecar_path = output_path.replace('.pdf', '.html')
        if os.path.exists(html_sidecar_path):
             with open(html_sidecar_path, "r", encoding="utf-8") as f:
                html_content = f.read()
             return html_content
             
        return "Error: Could not retrieve HTML content."

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/places/search")
def search_places(q: str = Query(..., min_length=1)):
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API Key not configured.")
        
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": q,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "ko"
    }
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if "results" not in data:
             return {"candidates": []}
             
        candidates = []
        for item in data["results"][:5]:  # Top 5
            candidates.append({
                "place_id": item.get("place_id"),
                "name": item.get("name"),
                "formatted_address": item.get("formatted_address")
            })
            
        return {"candidates": candidates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def health_check():
    return {"status": "ok", "service": "ReachCheck MVP"}
