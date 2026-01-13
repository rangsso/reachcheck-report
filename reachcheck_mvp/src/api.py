import os
import sys
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    place_id: str
    store_name: str = "Unknown Store"

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
        filename = f"{place_id}_report.pdf" # This ensures unique per place, or use snapshot ID
        # User wants generated snapshot ID in response, let's use that for uniqueness if we want
        # But requirement says "snapshot_id" in response.
        # Let's ensure output path is correct.
        
        output_path = generator.generate(report_data, filename=filename) 
        # API should assume generator saves to correct place. 
        # For safety, let's move it to OUTPUTS_DIR if not there, or ensure generator uses it.
        # Existing generator likely saves to current dir or outputs. 
        # Let's verify report logic later, but for now assume it returns a path.
        
        # We need to construct the URL.
        # Assuming output_path is absolute or relative to run dir.
        # We need to place it in strictly defined 'outputs/' dir for StaticFiles.
        
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
        
        return {
            "snapshot_id": snapshot.store_id + "_" + snapshot.timestamp,
            "report_pdf_url": f"{base_url}/outputs/{basename}",
            "report_html_url": f"{base_url}/outputs/{html_basename}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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


@app.get("/")
def health_check():
    return {"status": "ok", "service": "ReachCheck MVP"}
