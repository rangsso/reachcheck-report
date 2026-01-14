import random
import os
import requests
from dotenv import load_dotenv
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
from models import (
    StoreInfo, MapChannelStatus, AIEngineStatus, ConsistencyResult, 
    ReviewAnalysis, ReportData, AnalysisResult, StatusColor,
    ReviewStats, ReviewPhrase, ReviewSample
)
import bs4
import re
import json
import time
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright


from pathlib import Path

# Explicitly load .env from project root
# current file is in src/, project root is 2 levels up
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

# Set HEADLESS to True for production/headless modes
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"

from comparator import compare_data
from normalizer import normalize_name, normalize_address, normalize_phone

from models import SnapshotData
from normalizer import normalize_store_data
from snapshot_manager import SnapshotManager

# Error constants
ERR_SEARCH_NO_RESULT = "SEARCH_NO_RESULT"
ERR_AUTH_ERROR = "AUTH_ERROR"
ERR_PARSING_ERROR = "PARSING_ERROR"
ERR_RATE_LIMIT = "RATE_LIMIT"
ERR_UNKNOWN_ERROR = "UNKNOWN_ERROR"

class DataCollector:
    def __init__(self):
        self.snapshot_manager = SnapshotManager()
        self.playwright_available = False
        self.headless = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
        self._ensure_playwright_browsers()

    def _ensure_playwright_browsers(self):
        """Check if playwright is importable."""
        try:
            import playwright
            from playwright.sync_api import sync_playwright
            self.playwright_available = True
        except ImportError:
            self.playwright_available = False
            print("[WARN] Playwright not found. Skipping map detail scraping.")

    def _normalize_and_validate_phone(self, phone_str: str) -> str:
        if not phone_str:
            return None
        # Remove non-digits
        digits = re.sub(r'\D', '', phone_str)
        
        # Valid length check (Relaxed to support National 8, Mobile 10-11, 050x 11-12)
        if len(digits) < 8 or len(digits) > 12:
            return None
            
        # Format Logic
        
        # 050, 0505, 0507 (11-12 digits)
        if digits.startswith("050"):
            if len(digits) == 11: # 0507-1234-5678
                return f"{digits[:4]}-{digits[4:8]}-{digits[8:]}"
            elif len(digits) == 12: # 050X-XXXX-XXXX
                return f"{digits[:4]}-{digits[4:8]}-{digits[8:]}"
                
        # 02 (Seoul)
        if digits.startswith("02"):
            if len(digits) == 9: # 02-333-4444
                return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
            elif len(digits) == 10: # 02-3333-4444
                return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
                
        # Mobile / Other Area Codes (010, 031, 032, 042, etc.)
        # Usually 0xx-xxx-xxxx (10) or 0xx-xxxx-xxxx (11)
        if digits.startswith("0") and len(digits) in [10, 11]:
            # 3-3-4 or 3-4-4
            if len(digits) == 10:
                return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            else:
                 return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        
        # National number 1588-XXXX (8 digits)
        if len(digits) == 8 and (digits.startswith("15") or digits.startswith("16") or digits.startswith("18")):
             return f"{digits[:4]}-{digits[4:]}"
             
        # Fallback: if starts with 0 and length is appropriate, just format loosely
        if digits.startswith("0") and len(digits) >= 9:
             # Best effort
             return phone_str # Return original if we can't parse strictly but looks vaguely valid? 
             # Or construct a dash format? logic: 0xx-xxxx-xxxx
             pass

        return None

    def fetch_naver_map_detail(self, place_id: str) -> str:
        """
        Strategy 1: Playwright Scraping (Headless)
        Uses async_playwright to avoid conflict with running event loop.
        """
        if not self.playwright_available:
             return None

        # Fix: Sync API crashes in asyncio loop. Switch to Async API or subprocess.
        # Since this is likely called from async path (FastAPI), we should use async_playwright.
        # BUT fetch_naver_map_detail is synchronous.
        # To avoid massive refactor, we wrap async logic in a synchonous runner using asyncio.run
        # UNLESS there is already an event loop running.
        # API calls this synchronously?
        # Actually, `api.py` calls `collector.collect` inside `async def generate_report`.
        # So `collect` is running in a thread pool (FastAPI default for def) or main loop?
        # `generate_report` is `async def`, so `collector = DataCollector()` runs in loop.
        # `snapshot = collector.collect(...)` is sync!
        # This blocks the loop. 
        # Standard fix: Use sync_playwright but it fails if loop is running?
        # "Playwright Sync API inside the asyncio loop."
        
        # Solution: Use `async_playwright` and run it via `asyncio.run_coroutine_threadsafe`? 
        # Or better: make `collect` async. But that ripples.
        # Quickest Fix for MVP: Run scrape in a separate process or thread that doesn't share loop.
        # Or just use the hack: nest_asyncio? No.
        
        # Refactoring to use subprocess to run a script? No, too complex.
        # Let's try to use sync_playwright but explicitly handle the loop issue?
        # Actually, if we are in `async def`, we shouldn't block.
        # Correct approach: `collect` should be async.
        # But let's assume we can't change signature easily right now.
        
        # Workaround: Use a fresh thread for Playwright.
        # Sync Playwright complains if *current thread* has a loop.
        # Since `uvicorn` runs on main thread, and `async def` runs on it.
        
        from playwright.sync_api import sync_playwright
        import threading
        import queue

        result_queue = queue.Queue()

        def _scrape_thread(pid, q):
            try:
                with sync_playwright() as p:
                    browser_args = {}
                    if self.headless:
                        browser_args['headless'] = True
                    
                    browser = p.chromium.launch(**browser_args)
                    page = browser.new_page()
                    # Anti-detect
                    page.set_extra_http_headers({
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    })
                    
                    url = f"https://map.naver.com/p/entry/place/{pid}"
                    print(f"[-] Fetching Naver Map Detail via Playwright for {pid}...")
                    
                    try:
                        page.goto(url, timeout=15000, wait_until="domcontentloaded")
                        
                        # Strategy: 1. Try a[href^="tel:"] globally (sometimes works without frame)
                        # Strategy: 2. Find Entry Iframe
                        
                        # Global check first
                        try:
                            tel_el = page.query_selector('a[href^="tel:"]')
                            if tel_el:
                                t = tel_el.text_content()
                                q.put(t)
                                browser.close()
                                return
                        except: pass
                        
                        # Iframe Search
                        target_frame = None
                        # Wait for any frame? Just wait for selector in entryIframe
                        try:
                            # Try explicit ID first
                            frame_handle = page.wait_for_selector("#entryIframe", timeout=10000)
                            if frame_handle:
                                target_frame = frame_handle.content_frame()
                        except:
                            # Fallback: traverse frames
                            for f in page.frames:
                                if "entry" in f.url or "entryIframe" == f.name:
                                    target_frame = f
                                    break
                        
                        if target_frame:
                            # Selector sequence
                            for sel in ['a[href^="tel:"]', '.xl_text:has-text("0")']:
                                try:
                                    el = target_frame.wait_for_selector(sel, timeout=5000)
                                    if el:
                                        t = el.text_content()
                                        q.put(t)
                                        browser.close()
                                        return
                                except: continue
                        
                        # Fail
                        q.put(None)
                        
                    except Exception as e:
                        print(f"[FAIL][Playwright] Scrape Error: {e}")
                        q.put(None)
                    finally:
                        browser.close()
            except Exception as e:
                print(f"[FAIL][Playwright] Thread Error: {e}")
                q.put(None)

        t = threading.Thread(target=_scrape_thread, args=(place_id, result_queue))
        t.start()
        t.join()
        
        raw_text = result_queue.get()
        if raw_text:
             return self._normalize_and_validate_phone(raw_text)
        return None

    def fetch_naver_search_web(self, query: str) -> str:
        """
        Strategy 2: Naver Search Scraping (requests + bs4)
        """
        print(f"[-] Fetching Naver Search Web for {query}...")
        url = "https://search.naver.com/search.naver"
        params = {"query": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code != 200:
                print(f"[FAIL][SearchScraping] Status {resp.status_code}")
                return None
            
            soup = bs4.BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text()
            
            # Regex to support:
            # 1. Standard: 02-123-4567, 010-1234-5678 (3 parts)
            # 2. National: 1588-1234 (2 parts)
            # We use finding all numbers and then normalizing.
            
            # Find Pattern A: (0\d{1,2}|050\d)-?(\d{3,4})-?(\d{4})
            matches_a = re.findall(r'(?<!\d)(0\d{1,2}|050\d)-?(\d{3,4})-?(\d{4})(?!\d)', text)
            for m in matches_a:
                full = f"{m[0]}-{m[1]}-{m[2]}"
                valid = self._normalize_and_validate_phone(full)
                if valid: return valid
            
            # Find Pattern B: (1\d{3})-?(\d{4})
            matches_b = re.findall(r'(?<!\d)(1\d{3})-?(\d{4})(?!\d)', text)
            for m in matches_b:
                full = f"{m[0]}-{m[1]}"
                valid = self._normalize_and_validate_phone(full)
                if valid: return valid
                    
        except Exception as e:
            print(f"[FAIL][SearchScraping] {e}")
            
        return None

    def fetch_naver_search_extended(self, query: str):
         # ... (existing)
         pass 

    def _infer_category(self, naver_data: dict, kakao_data: dict, google_data: dict, naver_seed: dict = None) -> tuple:
        """
        Infers the category and source.
        Priority: 
        1. Naver Seed / Data
        2. Kakao (category_name or group_name)
        3. Google (types mapping)
        """
        # 1. Naver
        # 1. Naver Seed (High Priority)
        if naver_seed:
            if naver_seed.get("category_path"):
                return naver_seed.get("category_path"), "naver_seed_path"
            if naver_seed.get("category"):
                return naver_seed.get("category"), "naver_seed"
                
        # 1-1. Naver Data
        if naver_data and naver_data.get("category") and naver_data["category"] != "일반 매장":
            return naver_data.get("category"), "naver_data"
            
        # 2. Kakao
        if kakao_data:
            # Kakao often has "category_name" like "음식점 > 양식 > 이탈리안"
            # Or "category_group_name" like "음식점"
            cat = kakao_data.get("category_name")
            if cat:
                # Take the last part? or full? usage depends.
                # "음식점 > 양식 > 이탈리안" -> "이탈리안" for specificity
                parts = cat.split(">")
                return parts[-1].strip(), "kakao"
                
            cat_group = kakao_data.get("category_group_name")
            if cat_group:
                return cat_group, "kakao"
        
        # 3. Google
        if google_data and google_data.get("category") and google_data["category"] != "Unknown":
            return google_data.get("category"), "google"
            
        return "", "none" # Return empty per user request (no default generic)

    def collect(self, store_name: str, place_id: str = None, naver_seed: dict = None) -> SnapshotData:
        # ... (start of collect)
        google_data = {}
        naver_data = {}
        kakao_data = {}
        
        errors = {}
        search_candidates = {}
        
        failure_logs = []

        # -----------------------------------------------------------------
        # 1. NAVER PHONE ACQUISITION (PRIORITY 1)
        # -----------------------------------------------------------------
        # We need a phone number. We will use the strategies in order.
        
        naver_phone = None
        naver_phone_source = "unknown"
        current_naver_id = place_id
        
        # Strategy 1: Map Detail Scraping (Source of Truth)
        if current_naver_id and not current_naver_id.startswith("NID-") and not current_naver_id.startswith("PID-"):
             raw_pw_phone = self.fetch_naver_map_detail(current_naver_id)
             norm_pw_phone = self._normalize_and_validate_phone(raw_pw_phone) if raw_pw_phone else None
             
             print(f"[PHONE][RESULT] store={store_name} place_id={place_id}")
             print(f"[PHONE][Playwright] raw={raw_pw_phone} normalized={norm_pw_phone}")
             
             if norm_pw_phone:
                 naver_phone = norm_pw_phone
                 naver_phone_source = "playwright"
             else:
                 failure_logs.append(f"[DetailScrape] Failed for ID {current_naver_id}")
        
        # Strategy 2: Search Web Scraping
        if not naver_phone:
            # Construct query
            q = f"{store_name}"
            if naver_seed and naver_seed.get("address"):
                 # Append district for better accuracy e.g "Starbucks Gangnam"
                 addr_parts = naver_seed.get("address").split()
                 if len(addr_parts) > 1:
                     q += f" {addr_parts[1]}"
            
            raw_search_phone = self.fetch_naver_search_web(q)
            norm_search_phone = self._normalize_and_validate_phone(raw_search_phone) if raw_search_phone else None
            
            print(f"[PHONE][Search] raw={raw_search_phone} normalized={norm_search_phone}")
            
            if norm_search_phone:
                naver_phone = norm_search_phone
                naver_phone_source = "search"
            else:
                failure_logs.append(f"[SearchScrape] Failed for query {q}")

        # Strategy 3: API Extended Search (Legacy)
        if not naver_phone and NAVER_CLIENT_ID:
             _, cand, _ = self.fetch_naver_search_extended(store_name)
             if cand:
                 # Check first candidate
                 val = cand[0].get("phone")
                 norm = self._normalize_and_validate_phone(val)
                 print(f"[PHONE][API] raw={val} normalized={norm}")
                 if norm:
                     naver_phone = norm
                     naver_phone_source = "api"
             if not naver_phone:
                 failure_logs.append("[SearchAPI] No phone in API results")
        
        # FATAL CHECK
        if not naver_phone:
             error_msg = f"FATAL: Could not obtain phone number for {store_name}. Logs: {'; '.join(failure_logs)}"
             print(error_msg)
             # Raising exception as requested
             raise Exception(error_msg)
        
        print(f"[PHONE][FINAL] phone={naver_phone} source={naver_phone_source}")
             
        # -----------------------------------------------------------------
        # Continue with Normal Flow (Populate Data)
        # -----------------------------------------------------------------

        # 1. Base Identity (from Naver if available)
        if naver_seed:
            # MVP: Use normalized Naver data as seed
            # naver_seed comes from frontend (ReportRequest fields)
            print(f"[-] Using Naver Seed for {store_name}")
            # Address Priority: Road Address > Address
            final_address = naver_seed.get("road_address") or naver_seed.get("address")
            
            naver_data = {
                "name": naver_seed.get("store_name"),
                "address": final_address,
                "phone": naver_phone, # Inject robustly fetched phone
                "category": naver_seed.get("category"), 
                "link": naver_seed.get("naver_link"),
                "mapx": naver_seed.get("mapx"),
                "mapy": naver_seed.get("mapy")
            }
            # Use link or synthesized ID
            if not place_id:
                place_id = f"NID-{abs(hash(store_name + str(naver_data['address'])))}"
        
        elif not place_id:
             place_id = f"PID-{random.randint(10000, 99999)}"

        # 2. Kakao Search
        if KAKAO_REST_API_KEY:
            k_data, k_candidates, k_error = self.fetch_kakao_search_extended(store_name)
            if k_data:
                kakao_data = k_data
            if k_candidates:
                search_candidates["Kakao"] = k_candidates
            if k_error:
                errors["Kakao"] = k_error
        else:
            errors["Kakao"] = ERR_AUTH_ERROR

        # 3. Google Data
        if place_id and not place_id.startswith("PID-") and not place_id.startswith("NID-") and GOOGLE_MAPS_API_KEY:
             try:
                 print(f"[-] Fetching details for Place ID: {place_id}")
                 store_info = self.fetch_google_details(place_id, store_name)
                 google_data = {
                     "name": store_info.name,
                     "address": store_info.address,
                     "phone": store_info.phone,
                     "category": store_info.category,
                     "lat": 0.0, "lng": 0.0
                 }
             except Exception as e:
                 print(f"[!] Google API failed: {e}. Fallback to mock.")
                 errors["Google"] = ERR_UNKNOWN_ERROR
                 google_data = {"name": store_name, "address": "Seoul, Mock Address", "phone": "02-1234-5678", "category": "General"}
        elif GOOGLE_MAPS_API_KEY:
             try:
                 # Re-use search logic
                 url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                 params = {"query": store_name, "key": GOOGLE_MAPS_API_KEY, "language": "ko"}
                 resp = requests.get(url, params=params)
                 g_res = resp.json()
                 if g_res.get("results"):
                     top = g_res["results"][0]
                     google_data = {
                         "name": top.get("name"),
                         "address": top.get("formatted_address"),
                         "place_id": top.get("place_id"),
                         # Extract category from types
                         "category": top.get("types")[0] if top.get("types") else "Unknown"
                     }
                 else:
                     errors["Google"] = ERR_SEARCH_NO_RESULT
             except Exception as e:
                 errors["Google"] = f"SEARCH_FAIL: {str(e)}"
        else:
             google_data = {
                 "name": store_name, 
                 "address": "Seoul, Mock Address", 
                 "phone": "02-1234-5678",
                 "category": "일반 매장"
             }

        # 4. Naver Data Check
        if not naver_data and NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
             if naver_phone_source == "api" and not naver_data:
                  pass
        elif not naver_data:
             errors["Naver"] = ERR_AUTH_ERROR
             
        # Force update phone
        if naver_data:
            naver_data["phone"] = naver_phone
        
        # LOGGING
        self._log_source_data("GOOGLE", google_data)
        self._log_source_data("NAVER", naver_data)
        self._log_source_data("KAKAO", kakao_data)
        
        # INF_CATEGORY
        from normalizer import normalize_category_for_ai
        
        raw_cat, cat_source = self._infer_category(naver_data, kakao_data, google_data, naver_seed)
        
        # FIX: Do not fallback to raw_cat if normalizer returns None (which means it's ignored/invalid)
        cat = normalize_category_for_ai(raw_cat)
        
        if not cat:
             # If ignored ("Establishment") or empty, treated as None
             # Analyzer will handle None (AI Q1 fallback)
             # But for Report Display? "업종 정보 없음" might be better than "Establishment".
             # However, Analyzer logic checks `if not cat or cat == "업종 정보 없음"`.
             pass # cat is None
        
        # If we really want "업종 정보 없음" for display:
        if not cat:
             # cat = "업종 정보 없음" 
             # Wait, if I set it to "업종 정보 없음", then Analyzer sees it as valid string?
             # Analyzer logic: `if not cat or cat == "업종 정보 없음": ...` -> fallback Q1.
             # So setting generic string is safe for AI prompts.
             # And better for Display than "None".
             cat = "업종 정보 없음"
        
        print(f"[CATEGORY] Inferred: {cat} (Source: {cat_source}, Raw: {raw_cat})")
        
        # 5. Normalize & Snapshot
        if naver_data:
             from models import StoreSchema
             standard_info = StoreSchema(
                 id=place_id,
                 name=naver_data.get("name", store_name),
                 address=naver_data.get("address", ""),
                 phone=naver_data.get("phone", ""),
                 category=cat, # INJECT NORMALIZED CATEGORY
                 lat=0.0, lng=0.0,
                 hours="",
                 description="",
                 source_url=naver_data.get("link", "") or naver_data.get("source_url", "")
             )
        else:
             standard_info = normalize_store_data(place_id, google_data, naver_data, kakao_data)
             standard_info.category = cat # Update inferred
        
        # 6. Field Status Analysis
        missing_fields = []
        if not standard_info.name: missing_fields.append("name")
        if not standard_info.address: missing_fields.append("address")
        if not standard_info.phone: missing_fields.append("phone")
        if not standard_info.category or standard_info.category == "업종 정보 없음": missing_fields.append("category")  
        
        mismatch_fields = []
        if naver_data and kakao_data:
            if normalize_name(naver_data.get("name","")) != normalize_name(kakao_data.get("name","")):
                mismatch_fields.append("name_naver_kakao")
            if normalize_phone(naver_data.get("phone","")) != normalize_phone(kakao_data.get("phone","")):
                mismatch_fields.append("phone_naver_kakao") 

        # DATA PROVENANCE UPDATE
        from normalizer import format_display_address, is_valid_category_for_display
        
        field_provenance = {
            "standard_source": "naver_seed" if naver_seed else "discovered",
            "phone_source": naver_phone_source,
            "category_source": cat_source,
            "fields": {
                "name": {"standard": standard_info.name, "sources": {"naver": naver_data.get("name"), "kakao": kakao_data.get("name"), "google": google_data.get("name")}},
                "address": {"standard": standard_info.address, "sources": {"naver": naver_data.get("address"), "kakao": kakao_data.get("address"), "google": format_display_address(google_data.get("address"))}},
                "phone": {"standard": standard_info.phone, "sources": {"naver": naver_data.get("phone"), "kakao": kakao_data.get("phone"), "google": google_data.get("phone")}},
                "category": {
                    "standard": standard_info.category, 
                    "sources": {"naver": naver_data.get("category"), "kakao": kakao_data.get("category_name"), "google": google_data.get("category")}
                }
            }
        }
        
        snapshot = SnapshotData(
            store_id=place_id,
            timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
            standard_info=standard_info,
            raw_google=google_data,
            raw_naver=naver_data,
            raw_kakao=kakao_data,
            llm_responses={},
            missing_fields=missing_fields,
            mismatch_fields=mismatch_fields,
            field_provenance=field_provenance,
            search_candidates=search_candidates,
            errors=errors
        )
        
        # 7. Collect Review Insights (New)
        try:
             # Use robust ID for caching key
             review_cache_id = place_id if place_id and not place_id.startswith("PID-") else f"STORE_{store_name}"
             snapshot.review_insights = self.collect_reviews(store_name, review_cache_id, naver_seed)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Review] Collection Failed: {e}")
            snapshot.review_insights = ReviewStats(
                source="error", review_count=0, top_phrases=[], pain_phrases=[], sample_reviews=[], 
                fallback_used="error", notes=[str(e)],
                debug_code=f"CRASH:{str(e)[:30]}"
            )

        # Save immediately
        self.snapshot_manager.save(snapshot)
        
        return snapshot
    
    # -------------------------------------------------------------------------
    # REVIEW COLLECTION & SCRAPING (NEW)
    # -------------------------------------------------------------------------

    def _sleep_random(self):
        """Rate limiting to prevent blocking."""
        time.sleep(random.uniform(0.7, 1.8))

    def _get_review_cache_path(self, store_id: str) -> Path:
        cache_dir = Path(__file__).resolve().parent.parent / "snapshots" / "cache"
        os.makedirs(cache_dir, exist_ok=True)
        # Sanitize store_id
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', store_id)
        return cache_dir / f"reviews_{safe_id}.json"

    def _load_cached_reviews(self, store_id: str) -> ReviewStats:
        path = self._get_review_cache_path(store_id)
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check validity (24 hours)
            collected_at = datetime.fromisoformat(data.get("collected_at"))
            if datetime.now() - collected_at > timedelta(hours=24):
                return None
                
            # Reconstruct objects
            return ReviewStats(
                source=data["source"],
                review_count=data["review_count"],
                top_phrases=[ReviewPhrase(**p) for p in data["top_phrases"]],
                pain_phrases=[ReviewPhrase(**p) for p in data["pain_phrases"]],
                sample_reviews=[ReviewSample(**s) for s in data["sample_reviews"]],
                fallback_used=data["fallback_used"],
                notes=data.get("notes", [])
            )
        except Exception as e:
            print(f"[CACHE] Read failed: {e}")
            return None

    def _save_review_cache(self, store_id: str, stats: ReviewStats):
        path = self._get_review_cache_path(store_id)
        try:
            data = {
                "source": stats.source,
                "review_count": stats.review_count,
                "top_phrases": [vars(p) for p in stats.top_phrases],
                "pain_phrases": [vars(p) for p in stats.pain_phrases],
                "sample_reviews": [vars(s) for s in stats.sample_reviews],
                "fallback_used": stats.fallback_used,
                "notes": stats.notes,
                "collected_at": datetime.now().isoformat()
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CACHE] Save failed: {e}")

    def _analyze_reviews(self, texts: List[str]) -> tuple[List[ReviewPhrase], List[ReviewPhrase]]:
        """
        Rule-based phrase extraction.
        1. Split by .!?
        2. Filter by length (6-30) & Blacklist & Suffix
        3. Simple normalization
        4. Count & Pain point extraction
        """
        # Constants
        BLACKLIST = ["이벤트", "협찬", "쿠폰", "블로그", "체험단", "방문", "리뷰", "사장님", "성지", "작성", "문의", "예약", "서비스", "주차", "위치", "건물", "층", "역", "출구"]
        VALID_SUFFIXES = ["요", "니다", "음", "함", "임", "다", "거", "게", "죠", "네", "요.", "다."]
        # Refined Pain Keywords (Avoid single chars like '짜' matching '진짜')
        PAIN_KEYWORDS = ["별로", "아쉽", "불친절", "느리", "오래", "웨이팅", "대기", "비싸", "짜요", "짜서", "싱거", "좁아", "좁은", "시끄", "불편", "실망", "더러", "지저분", "냄새"]
        
        # print(f"[DEBUG] Active PAIN_KEYWORDS: {PAIN_KEYWORDS}")

        phrases = []
        pain_candidates = []
        
        for text in texts:
            # 1. Cleanup
            # User request: "Minimize emoji removal, focus on trim"
            # We remove only control chars and Korean Jamo (ㅋㅋ, ㅠㅠ) which are noise for phrase extraction
            clean_text = re.sub(r'[ㄱ-ㅎ]+', '', text) 
            
            # 2. Split (keep punctuation for splitting)
            sentences = re.split(r'[\.\!\?\n]', clean_text)
            
            for s in sentences:
                s = s.strip()
                if not s: continue
                
                # Length Filter
                if len(s) < 6 or len(s) > 30: continue
                
                # Blacklist Filter
                if any(bad in s for bad in BLACKLIST): continue
                
                # Suffix Filter (Must end with 'complete' Korean verb form approx)
                if not any(s.endswith(suffix) for suffix in VALID_SUFFIXES): continue
                
                # Pain Point Check (Before Normalize)
                if any(pk in s for pk in PAIN_KEYWORDS):
                    pain_candidates.append(s)
                else:
                    phrases.append(s)

        # Count
        top_counter = Counter(phrases)
        pain_counter = Counter(pain_candidates)
        
        # Convert to objects
        top_phrases = [ReviewPhrase(text=k, count=v) for k, v in top_counter.most_common(5)]
        pain_phrases = [ReviewPhrase(text=k, count=v) for k, v in pain_counter.most_common(3)]
        
        return top_phrases, pain_phrases

    def _fetch_place_url_tier1(self, query: str) -> tuple[Optional[str], List[str], int, str]:
        """
        Search Naver -> Return (place_url, snippets_list, status_code, blocked_reason)
        """
        self._sleep_random()
        print(f"[-] [Tier 1] Searching Naver for Place URL: {query}")
        
        url = "https://search.naver.com/search.naver"
        params = {"query": query}
        # [REVIEW][T1] Logging
        # Harden Headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.naver.com/"
        }
        
        place_url = None
        snippets = []
        status_code = 0
        response_len = 0
        blocked_reason = "none"
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=5, allow_redirects=True)
            status_code = resp.status_code
            response_len = len(resp.text)
            
            # Check blockage
            if status_code != 200:
                blocked_reason = f"http_{status_code}"
                
            # Content checks for captcha/block
            if "captcha" in resp.text or "비정상적인 접근" in resp.text:
                 blocked_reason = "captcha_detected"
            
            if status_code == 200 and blocked_reason == "none":
                soup = bs4.BeautifulSoup(resp.text, "html.parser")
                
                # 1. Find Place Link (Regex Strategy)
                import re
                
                # Pattern: Direct links or map scripts
                patterns = [
                    r'place\.naver\.com/restaurant/(\d+)',
                    r'place\.naver\.com/place/(\d+)',
                    r'place\.naver\.com/hospital/(\d+)',
                    r'place\.naver\.com/hairshop/(\d+)'
                ]
                
                found_id = None
                found_cat = "restaurant" # Default
                
                for p in patterns:
                    match = re.search(p, resp.text)
                    if match:
                        found_id = match.group(1)
                        if "hairshop" in p: found_cat = "hairshop"
                        elif "hospital" in p: found_cat = "hospital"
                        break
                
                if found_id:
                    place_url = f"https://place.naver.com/{found_cat}/{found_id}" 
                else:
                     # Fallback link scan
                     links = soup.select('a[href*="place.naver.com"]')
                     for link in links:
                         href = link.get('href')
                         if "/place/" in href or "/restaurant" in href:
                             place_url = href
                             break
                
                # 2. Snippets
                possible_snippets = soup.select('.review_content, .dsc_txt, .text_area, .review_txt') 
                for s in possible_snippets:
                    t = s.get_text(strip=True)
                    if len(t) > 10:
                        snippets.append(t)
                        
        except Exception as e:
            blocked_reason = f"error_{str(e)}"
            
        # Log Result
        print(f"[REVIEW][T1] url={url} query={query} status={status_code} bytes={response_len} blocked={blocked_reason} found_url={place_url is not None} snippets={len(snippets)}")
        
        return place_url, snippets, status_code, blocked_reason

    def _fetch_reviews_tier2(self, place_url: str) -> List[str]:
        """
        Visit place_url -> Try to fetch reviews from static HTML or standard endpoints.
        Note: place.naver.com is a React app. Static HTML might be empty.
        We check if we can get initial state or if we need to infer the review URL.
        """
        self._sleep_random()
        print(f"[-] [Tier 2] Visiting Place URL: {place_url}")
        
        reviews = []
        try:
            # Construct Review URL if possible
            # if /restaurant/{id} -> /restaurant/{id}/review
            review_url = place_url
            if "/home" in place_url:
                review_url = place_url.replace("/home", "/review")
            elif not place_url.endswith("/review"):
                # If query params exist?
                if "?" in place_url:
                    parts = place_url.split("?")
                    review_url = parts[0] + "/review?" + parts[1]
                else:
                    review_url = place_url + "/review"

            headers = {
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                 "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                 "Referer": "https://m.place.naver.com/"
            }
            
            # Fix URL: Ensure correct generic review path if possible
            # But usually we just GET the main place URL and look for state, or generic /review
            # The most robust for Review Text is actually visiting the place main or review sub-page.
            
            resp = requests.get(review_url, headers=headers, timeout=5, allow_redirects=True)
            status_code = resp.status_code
            response_len = len(resp.text)
            
            if status_code != 200:
                print(f"[REVIEW][T2] url={review_url} status={status_code} blocked=http_error reviews=0")
                return []
                
            # Apollo State Search
            import json
            apollo_found = False
            
            # 1. Check for window.__APOLLO_STATE__
            script_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', resp.text)
            if script_match:
                apollo_found = True
                try:
                    json_str = script_match.group(1)
                    # We can try to parse, but regexing the string is faster and more robust against schema changes for just text extraction
                    # Look for "contents": "review text" or "body": "review text"
                    # In Naver Place, it's often "contents" or "body"
                    
                    # Pattern strategy
                    # "body":"..." or "contents":"..."
                    bodies = re.findall(r'"(body|contents)"\s*:\s*"(.*?)"', json_str)
                    for key, val in bodies:
                        # Clean up escaped chars
                        val = val.replace('\\"', '"').replace('\\n', ' ').strip()
                        if len(val) > 10: # Min length
                            reviews.append(val)
                            
                except Exception as je:
                    print(f"[Tier 2] JSON Parse Error: {je}")

            # 2. Fallback: Static HTML (SSR)
            if not reviews:
                 soup = bs4.BeautifulSoup(resp.text, "html.parser")
                 candidates = soup.select(".zPfVt, .n56if, .review_txt, .txt")
                 for c in candidates:
                     t = c.get_text(strip=True)
                     if len(t) > 10:
                         reviews.append(t)
            
            review_count = len(reviews)
            blocked_reason = "none"
            if "captcha" in resp.text: blocked_reason = "captcha"
            
            print(f"[REVIEW][T2] url={review_url} status={status_code} bytes={response_len} blocked={blocked_reason} apollo={apollo_found} reviews={review_count}")
            
        except Exception as e:
            print(f"[REVIEW][T2] Error: {e}")
            
        return list(set(reviews))

    # -------------------------------------------------------------------------
    # REVIEW TEXT VALIDATION & PARSING HELPERS
    # -------------------------------------------------------------------------
    
    def _is_valid_review_text(self, text: str) -> bool:
        """
        Minimal validation to filter out obvious non-review content.
        Designed to be permissive - we want reviews!
        """
        if not text or len(text) < 10 or len(text) > 500:
            return False
        
        # Must have SOME Korean characters
        if not re.search(r'[가-힣]', text):
            return False
        
        # Exclude pure username patterns (all alphanumeric, short)
        if re.match(r'^[a-zA-Z0-9_]+$', text.strip()) and len(text.strip()) < 25:
            return False
        
        # Exclude pure date patterns
        if re.match(r'^\d{2,4}[\./]\d{1,2}[\./]\d{1,2}', text.strip()):
            return False
        
        # Exclude single weekday
        if text.strip() in ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']:
            return False
        
        # Exclude obvious UI buttons
        ui_patterns = ['공유하기', '신고하기', '복사하기', '길찾기', '예약하기', '영수증 인증']
        if any(text.strip() == pattern for pattern in ui_patterns):
            return False
        
        return True
    
    def _parse_apollo_state(self, html_content: str) -> List[Dict[str, str]]:
        """
        Parse __APOLLO_STATE__ or __NEXT_DATA__ from Naver Place mobile page.
        Returns list of dicts with 'body' and optionally 'date', 'author'.
        """
        reviews = []
        
        try:
            # Try __APOLLO_STATE__ first
            apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', html_content, re.DOTALL)
            if apollo_match:
                apollo_data = json.loads(apollo_match.group(1))
                
                # Iterate through Apollo cache keys
                for key, value in apollo_data.items():
                    if isinstance(value, dict):
                        # Look for review-like structures
                        # Common fields: body, contents, reviewText, contentText
                        body = None
                        date = None
                        
                        for field in ['body', 'contents', 'reviewText', 'contentText', 'comment']:
                            if field in value and isinstance(value[field], str):
                                body = value[field]
                                break
                        
                        # Extract date if available
                        for date_field in ['visitDate', 'createdDate', 'date']:
                            if date_field in value and isinstance(value[date_field], str):
                                date = value[date_field]
                                break
                        
                        if body:
                            reviews.append({'body': body, 'date': date})
                
                if reviews:
                    print(f"[Apollo] Extracted {len(reviews)} reviews from __APOLLO_STATE__")
                    return reviews
            
            # Try __NEXT_DATA__ as fallback
            next_match = re.search(r'__NEXT_DATA__\s*=\s*({.+?});', html_content, re.DOTALL)
            if next_match:
                next_data = json.loads(next_match.group(1))
                
                # Navigate through typical Next.js structure
                # props.pageProps.dehydratedState.queries[].state.data.reviews
                if 'props' in next_data:
                    self._extract_reviews_from_nested(next_data['props'], reviews)
                
                if reviews:
                    print(f"[NextData] Extracted {len(reviews)} reviews from __NEXT_DATA__")
                    return reviews
        
        except Exception as e:
            print(f"[Apollo Parse Error] {e}")
        
        return reviews
    
    def _extract_reviews_from_nested(self, data: Any, reviews: List[Dict]) -> None:
        """Recursively search for review structures in nested JSON"""
        if isinstance(data, dict):
            # Check if this looks like a review object
            if any(key in data for key in ['body', 'contents', 'reviewText', 'contentText']):
                body = None
                date = None
                
                for field in ['body', 'contents', 'reviewText', 'contentText']:
                    if field in data and isinstance(data[field], str):
                        body = data[field]
                        break
                
                for date_field in ['visitDate', 'createdDate', 'date']:
                    if date_field in data and isinstance(data[date_field], str):
                        date = data[date_field]
                        break
                
                if body:
                    reviews.append({'body': body, 'date': date})
            
            # Recurse into nested structures
            for value in data.values():
                self._extract_reviews_from_nested(value, reviews)
        
        elif isinstance(data, list):
            for item in data:
                self._extract_reviews_from_nested(item, reviews)


    def _collect_reviews_playwright(self, query: str, direct_url: str = None) -> tuple[List[str], Optional[str], List[dict]]:
        """
        Tier 4: Playwright-based extraction.
        If direct_url is provided, skip search and go directly.
        Returns (reviews, place_url, keyword_stats)
        """
        if not self.playwright_available:
            return [], None, []
            
        print(f"[-] [Playwright] Launching Browser for {query} (DirectURL={direct_url is not None})...")
        
        # Run Playwright in a separate thread to avoid asyncio event loop conflict
        from concurrent.futures import ThreadPoolExecutor
        
        def _run_playwright_sync():
            """Internal function to run Playwright synchronously in a separate thread"""
            reviews = []
            keyword_stats = []
            final_url = None
            
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # Launch options for stability
                browser = p.chromium.launch(headless=self.headless)
                # Use iPhone emulation for Mobile View (critical for reviewing)
                iphone_13 = p.devices['iPhone 13']
                context = browser.new_context(
                    **iphone_13,
                    locale='ko-KR'
                )
                page = context.new_page()
                
                try:
                    # 1. Navigation
                    # TIMEOUT INCREASED to 30s as per user issues
                    if direct_url:
                        print(f"[-] [Playwright] Direct Navigation: {direct_url}")
                        page.goto(direct_url, timeout=30000)
                        page.wait_for_load_state("domcontentloaded")
                        final_url = direct_url
                    else:
                        # Search Flow
                        print(f"[-] [Playwright] Searching: {query}")
                        page.goto(f"https://m.search.naver.com/search.naver?query={query}", timeout=30000)
                        
                        # Find Place Link
                        # In mobile search, it's usually a generic container or "place" blocks
                        link_locator = None
                        try:
                            # Try finding a link that contains place.naver.com/restaurant
                            # This selector is heuristic
                            candidates = page.locator("a[href*='place.naver.com']").all()
                            if not candidates:
                                 print("[-] [Playwright] No place links found in search")
                                 return [], None, []
                                 
                            for cand in candidates:
                                href = cand.get_attribute("href")
                                if href and ("/restaurant/" in href or "/place/" in href):
                                    link_locator = cand
                                    break
                                    
                            if not link_locator:
                                 # Fallback: Just take first
                                 link_locator = candidates[0]

                            # Click
                            if link_locator:
                                with page.expect_popup(timeout=30000) as popup_info:
                                    link_locator.click()
                                place_page = popup_info.value
                                place_page.wait_for_load_state("domcontentloaded")
                                page = place_page # Switch context
                                final_url = page.url
                        except Exception as e:
                             # Fallback mechanism: use current page if no new page opened (mobile SPA sometimes)
                             final_url = page.url
                             print(f"[!] Playwright Search Navigation Warning: {e}")

                    # 2. Review Extraction (Mobile Page)
                    # Ensure we are on /review tab
                    if "/review" not in page.url:
                        try:
                            # Naver Mobile usually has tabs: 홈, 메뉴, 리뷰, 사진...
                            # Selector for '리뷰' tab
                            review_tab = page.locator("a span", has_text=re.compile("리뷰|방문자리뷰")).first
                            if review_tab.is_visible():
                                review_tab.click()
                                page.wait_for_timeout(2000)
                        except:
                            pass
                    
                    # Scroll a bit
                    for _ in range(3):
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(500)

                    # ---------------------------------------------------------
                    # NEW: Keyword Stats Extraction (Specific to Naver Mobile)
                    # ---------------------------------------------------------
                    try:
                        # Look for the characteristic list items with progress bars or stats
                        # Often `li` containing text and a count number
                        # We look for elements that explicitly contain quotes or specialized keyword classes
                        # Heuristic: Find elements with text like "음식이 맛있어요"
                        
                        # Try specific container selector for "Keyword Reviews"
                        # Usually: div[class*="review_stat"] or similar.
                        # FallbackGeneric: List items with text + number
                        
                        # Allow fuzzy finding
                        # Iterate through visible list items
                        possible_items = page.locator("li").all()
                        
                        for item in possible_items:
                            text = item.inner_text()
                            if not text: continue
                            lines = text.split('\n')
                            
                            # Keyword stats usually appear as:
                            # "음식이 맛있어요"
                            # "120"
                            if len(lines) >= 2:
                                kw = lines[0].strip()
                                cnt_str = lines[1].strip()
                                
                                # Validate Keyword (Korean, meaningful length)
                                if len(kw) < 2 or len(kw) > 30: continue
                                
                                # Validate Count (must be digits)
                                # Remove commas or '명'
                                cnt_clean = re.sub(r'[^0-9]', '', cnt_str)
                                if cnt_clean.isdigit():
                                    count = int(cnt_clean)
                                    # Filter out likely menu items (if price is present, usually > 1000 won format, but simple count is usually < 10000)
                                    if count > 0:
                                        keyword_stats.append({"text": kw, "count": count})
                                        if len(keyword_stats) >= 10: break
                                        
                    except Exception as ks_e:
                        print(f"[-] [Playwright] Keyword stats extraction failed: {ks_e}")

                    # ---------------------------------------------------------
                    # Text Extraction - Broad selection with smart filtering
                    # ---------------------------------------------------------
                    # Cast a wide net, let validation filter out noise
                    elements = page.locator("span, div, p").all()
                    for el in elements:
                        try:
                            t = el.inner_text().strip()
                            if self._is_valid_review_text(t):
                                reviews.append(t)
                        except:
                            continue
                    
                    reviews = list(set(reviews))
                    print(f"[-] [Playwright] Extracted {len(reviews)} validated reviews, {len(keyword_stats)} keywords")
                    
                except Exception as e:
                    print(f"[!] Playwright Execution Error: {e}")
                finally:
                    browser.close()
                    
            return reviews, final_url, keyword_stats
        
        # Execute in thread pool to avoid asyncio conflict
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_playwright_sync)
                return future.result(timeout=90)  # 90 second timeout
        except Exception as e:
            print(f"[!] ThreadPool execution failed: {e}")
            return [], None, []

    def collect_reviews(self, store_name: str, place_id: str, naver_seed: dict = None) -> ReviewStats:
        """
        Main method for Review Insights (Mobile-First Strategy)
        """
        # 0. Cache Check
        cache_key = place_id if place_id and not place_id.startswith("PID-") else f"STORE_{store_name}"
        cached = self._load_cached_reviews(cache_key)
        if cached:
            print(f"[-] [Review] Using Cached Data for {cache_key}")
            return cached
            
        print(f"[-] [Review] Collecting Reviews for {store_name}...")
        
        collected_texts = []
        source_used = "none"
        fallback_used = "none"
        notes = []
        debug_code = "init"
        
        # ---------------------------------------------------------------------
        # Tier 0: Seed Parsing (Get ID)
        # ---------------------------------------------------------------------
        found_id = None
        
        # Try extract from seed link first
        if naver_seed and "naver_link" in naver_seed:
            s_link = naver_seed["naver_link"]
            # Patterns: entry/place/123, restaurant/123
            import re
            m = re.search(r'/(place|restaurant|hospital|hairshop)/(\d+)', s_link)
            if m:
                found_id = m.group(2)
                debug_code = "t0:seed_id"
                print(f"[-] [Review] Found ID from seed: {found_id}")

        # If no ID, Tier 4 (Search) is actually Tier 0.5 here
        if not found_id:
             try:
                 # Fast search for ID only
                 _, __, ___, ____ = self._fetch_place_url_tier1(store_name) # Reuse search to find ID logic internally?
                 # Actually _fetch_place_url_tier1 returns URL. We parse ID from it.
                 url, _snippets, s_code, _blocked = self._fetch_place_url_tier1(store_name)
                 
                 if url:
                     m = re.search(r'/(place|restaurant|hospital|hairshop)/(\d+)', url)
                     if m:
                         found_id = m.group(2)
                         debug_code = "t0:search_id"
                 else:
                     debug_code = f"t0:search_fail_{s_code}"
             except Exception as e:
                 debug_code = "t0:search_error"
        
        # ---------------------------------------------------------------------
        # Tier 1: Mobile Requests with Apollo State Parsing
        # ---------------------------------------------------------------------
        if found_id:
            # Try generic restaurant path first, usually redirects if wrong category
            # m.place.naver.com is robust
            mobile_url = f"https://m.place.naver.com/restaurant/{found_id}/review"
            
            try:
                # 1. Requests
                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                    "Referer": "https://m.place.naver.com/"
                }
                resp = requests.get(mobile_url, headers=headers, timeout=5, allow_redirects=True)
                
                if resp.status_code == 200:
                    # TIER 1A: Try Apollo State JSON first (PRIORITY)
                    apollo_reviews = self._parse_apollo_state(resp.text)
                    
                    if apollo_reviews:
                        # Extract and validate review bodies
                        for review in apollo_reviews:
                            body = review.get('body', '')
                            if self._is_valid_review_text(body):
                                collected_texts.append(body)
                        
                        if len(collected_texts) >= 5:
                            source_used = "naver_apollo_state"
                            debug_code += "_t1:apollo_ok"
                            notes.append(f"Apollo State: {len(collected_texts)} clean reviews")
                    
                    # TIER 1B: Fallback to targeted DOM extraction
                    if len(collected_texts) < 5:
                        soup = bs4.BeautifulSoup(resp.text, "html.parser")
                        
                        # Use targeted selectors for review content areas
                        # Naver mobile review cards typically use specific classes
                        review_elements = soup.select('.review_content, .text_comment, [class*="review"] p, [class*="review"] span')
                        
                        found_texts = []
                        for elem in review_elements:
                            t = elem.get_text(strip=True)
                            if self._is_valid_review_text(t):
                                found_texts.append(t)
                        
                        if found_texts:
                            collected_texts.extend(found_texts)
                            collected_texts = list(set(collected_texts))  # Deduplicate
                        
                        if len(collected_texts) >= 5:
                            source_used = "naver_requests_mobile"
                            debug_code += "_t1:dom_ok"
                            notes.append(f"DOM extraction: {len(collected_texts)} clean reviews")
                        else:
                            debug_code += f"_t1:low_{len(collected_texts)}"
                else:
                    debug_code += f"_t1:http_{resp.status_code}"
            except Exception as e:
                debug_code += "_t1:error"
                print(f"[!] Tier 1 Error: {e}")


        # ---------------------------------------------------------------------
        # Tier 3: Playwright Mobile (Fallback)
        # ---------------------------------------------------------------------
        # Only if we have ID but failed requests, or have no ID at all (Playwright Search)
        
        should_run_pw = False
        if len(collected_texts) < 5 and self.playwright_available:
            should_run_pw = True
            
        if should_run_pw:
            print(f"[-] [Review] Engaging Playwright (Tier 3) Mode={ 'ID_Direct' if found_id else 'Search'}")
            try:
                pw_results = []
                # Use _collect_reviews_playwright but modified to accept ID? 
                # Or just pass the URL we constructed.
                
                # We need to modify _collect_reviews_playwright to handle direct URL
                # For now, let's pass a special query or modify the method.
                # Actually, simpler to refactor _collect_reviews_playwright to accept optional url.
                
                target_url = None
                if found_id:
                    target_url = f"https://m.place.naver.com/restaurant/{found_id}/review"
                
                # Initialize variables to prevent UnboundLocalError if Playwright fails
                pw_texts = []
                pw_keywords = []
                pw_url = None

                # Call Playwright
                # We'll pass the store_name as query fallback
                # Call Playwright
                # We'll pass the store_name as query fallback
                pw_texts, pw_url, pw_keywords = self._collect_reviews_playwright(store_name, direct_url=target_url)
                
                if pw_texts:
                    if len(pw_texts) > len(collected_texts):
                        collected_texts = pw_texts
                        source_used = "naver_playwright"
                        fallback_used = "playwright"
                        debug_code += "_pw:ok"
                        notes.append(f"Playwright collected {len(pw_texts)}")
                
                # Handle Keywords even if text is empty
                if pw_keywords:
                    # If we have keywords, we consider it a success even if texts are low
                    if not collected_texts and "pw:ok" not in debug_code:
                         debug_code += "_pw:kw_only"
                    
                    # Store keywords in notes for debugging
                    notes.append(f"PW Keywords: {len(pw_keywords)}")
                
                if not pw_texts and not pw_keywords:
                    debug_code += "_pw:empty"
                    if pw_url: 
                        notes.append("PW visited but found 0")
            except Exception as e:
                # Add error msg to debug_code for visibility
                err_msg = str(e).replace(" ", "_")[:50]
                debug_code += f"_pw:error_{err_msg}"
                notes.append(f"PW Error: {e}")
                print(f"[!] Full Playwright Error: {e}")

        # Final Count Check
        if not collected_texts and not (should_run_pw and pw_keywords):
            notes.append("No reviews found")
            if "error" not in debug_code and "http" not in debug_code:
                debug_code += "_no_reviews"
        else:
            notes.append(f"Final count: {len(collected_texts)}")

        # Clamp texts
        collected_texts = collected_texts[:100]
        
        # Analyze Phrases
        top_phrases, pain_phrases = self._analyze_reviews(collected_texts)
        
        # MERGE PLAYWRIGHT KEYWORDS (Priority)
        if should_run_pw and 'pw_keywords' in locals() and pw_keywords:
            official_phrases = [ReviewPhrase(text=k['text'], count=k['count']) for k in pw_keywords]
            
            # Combine: Official first, then text-mined
            # Remove duplicates based on text
            seen_texts = {p.text for p in official_phrases}
            for p in top_phrases:
                if p.text not in seen_texts:
                    official_phrases.append(p)
            
            top_phrases = official_phrases[:5] # Top 5
            
        # Sample Reviews (Simple)
        sample_reviews = [ReviewSample(text=t, type="neutral") for t in collected_texts[:5]]
        
        # If no samples but we have keywords, create pseudo-samples? 
        # User asked for "Keywords even if no reviews". 
        # But report expects "Sample Reviews". 
        # Leave samples empty if no text, but phrases will be populated.
        
        # Construct Stats
        stats = ReviewStats(
            source=source_used,
            review_count=len(collected_texts),
            top_phrases=top_phrases,
            pain_phrases=pain_phrases,
            sample_reviews=sample_reviews,
            fallback_used=fallback_used,
            notes=notes,
            debug_code=debug_code
        )
        
        # Save Cache (Moved BEFORE return)
        self._save_review_cache(cache_key, stats)
        
        return stats
    
    # -------------------------------------------------------------------------
    # REVIEW COLLECTION & SCRAPING (NEW)
    # -------------------------------------------------------------------------

    def _sleep_random(self):
        """Rate limiting to prevent blocking."""
        time.sleep(random.uniform(0.7, 1.8))

    def _get_review_cache_path(self, store_id: str) -> Path:
        cache_dir = Path(__file__).resolve().parent.parent / "snapshots" / "cache"
        os.makedirs(cache_dir, exist_ok=True)
        # Sanitize store_id
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', store_id)
        return cache_dir / f"reviews_{safe_id}.json"

    def _load_cached_reviews(self, store_id: str) -> ReviewStats:
        path = self._get_review_cache_path(store_id)
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check validity (24 hours)
            collected_at = datetime.fromisoformat(data.get("collected_at"))
            if datetime.now() - collected_at > timedelta(hours=24):
                return None

            # Force re-collection if debug_code is missing (Legacy Cache)
            if "debug_code" not in data:
                print(f"[-] [Review] Invalidate Legacy Cache (No Debug Code) for {store_id}")
                return None
                
            # Reconstruct objects
            return ReviewStats(
                source=data["source"],
                review_count=data["review_count"],
                top_phrases=[ReviewPhrase(**p) for p in data["top_phrases"]],
                pain_phrases=[ReviewPhrase(**p) for p in data["pain_phrases"]],
                sample_reviews=[ReviewSample(**s) for s in data["sample_reviews"]],
                fallback_used=data["fallback_used"],
                notes=data.get("notes", []),
                debug_code=data.get("debug_code")
            )
        except Exception as e:
            print(f"[CACHE] Read failed: {e}")
            return None

    def _save_review_cache(self, store_id: str, stats: ReviewStats):
        path = self._get_review_cache_path(store_id)
        try:
            data = {
                "source": stats.source,
                "review_count": stats.review_count,
                "top_phrases": [vars(p) for p in stats.top_phrases],
                "pain_phrases": [vars(p) for p in stats.pain_phrases],
                "sample_reviews": [vars(s) for s in stats.sample_reviews],
                "fallback_used": stats.fallback_used,
                "notes": stats.notes,
                "debug_code": stats.debug_code,
                "collected_at": datetime.now().isoformat()
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CACHE] Save failed: {e}")

    def _analyze_reviews(self, texts: List[str]) -> tuple[List[ReviewPhrase], List[ReviewPhrase]]:
        """
        Rule-based phrase extraction.
        1. Split by .!?
        2. Filter by length (6-30) & Blacklist & Suffix
        3. Simple normalization
        4. Count & Pain point extraction
        """
        # Constants
        BLACKLIST = ["이벤트", "협찬", "쿠폰", "블로그", "체험단", "방문", "리뷰", "사장님", "작성", "문의", "예약", "서비스", "주차", "위치", "건물", "층", "역", "출구"]
        VALID_SUFFIXES = ["요", "니다", "음", "함", "임", "다", "거", "게", "죠", "네"] # Relaxed but prioritized
        PAIN_KEYWORDS = ["별로", "아쉽", "불친절", "느리", "오래", "웨이팅", "대기", "비싸", "짜", "싱거", "좁", "시끄", "불편", "실망", "더러", "지저분", "냄새"]
        
        phrases = []
        pain_candidates = []
        
        for text in texts:
            # 1. Cleanup
            clean_text = re.sub(r'[^\w\s\.\!\?]', ' ', text) # Remove special chars except punctuation
            
            # 2. Split
            sentences = re.split(r'[\.\!\?\n]', clean_text)
            
            for s in sentences:
                s = s.strip()
                if not s: continue
                
                # Length Filter
                if len(s) < 6 or len(s) > 30: continue
                
                # Blacklist Filter
                if any(bad in s for bad in BLACKLIST): continue
                
                # Suffix Filter (Must end with 'complete' Korean verb form approx)
                if not any(s.endswith(suffix) for suffix in VALID_SUFFIXES): continue
                
                # Pain Point Check (Before Normalize)
                if any(pk in s for pk in PAIN_KEYWORDS):
                    pain_candidates.append(s)
                else:
                    phrases.append(s)

        # Count
        top_counter = Counter(phrases)
        pain_counter = Counter(pain_candidates)
        
        # Convert to objects
        top_phrases = [ReviewPhrase(text=k, count=v) for k, v in top_counter.most_common(5)]
        pain_phrases = [ReviewPhrase(text=k, count=v) for k, v in pain_counter.most_common(3)]
        
        return top_phrases, pain_phrases


    def _log_source_data(self, source_name: str, data: dict):
        raw_name = data.get("name", "")
        raw_addr = data.get("address", "")
        raw_phone = data.get("phone", "")
        
        norm_name = normalize_name(str(raw_name) if raw_name else "")
        norm_addr = normalize_address(str(raw_addr) if raw_addr else "")
        norm_phone = normalize_phone(str(raw_phone) if raw_phone else "")
        
        print(f"[COLLECT][{source_name}] raw: name={raw_name}, address={raw_addr}, phone={raw_phone}")
        print(f"[COLLECT][{source_name}] norm: name={norm_name}, address={norm_addr}, phone={norm_phone}")

    def fetch_naver_search(self, query: str) -> dict:
        # Legacy wrapper
        data, _, _ = self.fetch_naver_search_extended(query)
        return data or {}

    def fetch_naver_search_extended(self, query: str):
        """Returns (best_match_dict, all_candidates_list, error_code)"""
        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 5, "sort": "random"} 
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 401 or resp.status_code == 403:
                return None, [], ERR_AUTH_ERROR
            if resp.status_code == 429:
                return None, [], ERR_RATE_LIMIT
            
            data = resp.json()
            items = data.get("items", [])
            
            if not items:
                return None, [], ERR_SEARCH_NO_RESULT
                
            candidates = []
            for item in items:
                candidates.append({
                    "name": item.get('title', '').replace('<b>', '').replace('</b>', ''),
                    "address": item.get("roadAddress") or item.get("address"),
                    "phone": item.get("telephone") or ""
                })
            
            # Selection Logic (Same as before)
            norm_q = query.replace(" ", "")
            for cand in candidates:
                norm_n = cand['name'].replace(" ", "")
                if norm_q in norm_n or norm_n in norm_q:
                    return cand, candidates, None
                    
            # If no good match found but candidates exist
            return None, candidates, ERR_SEARCH_NO_RESULT # Or "NO_MATCHING_CANDIDATE"

        except Exception as e:
            print(f"[!] Naver search error: {e}")
            return None, [], ERR_UNKNOWN_ERROR

    def fetch_kakao_search(self, query: str) -> dict:
        # Legacy wrapper
        data, _, _ = self.fetch_kakao_search_extended(query)
        return data or {}

    def fetch_kakao_search_extended(self, query: str):
        """Returns (best_match_dict, all_candidates_list, error_code)"""
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        params = {"query": query, "size": 5}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 401 or resp.status_code == 403:
                return None, [], ERR_AUTH_ERROR
            
            data = resp.json()
            docs = data.get("documents", [])
            
            if not docs:
                return None, [], ERR_SEARCH_NO_RESULT
                
            candidates = []
            for d in docs:
                candidates.append({
                    "name": d.get('place_name'),
                    "address": d.get("road_address_name") or d.get("address_name"),
                    "phone": d.get("phone")
                })
                
            norm_q = query.replace(" ", "")
            for cand in candidates:
                norm_n = cand['name'].replace(" ", "")
                if norm_q in norm_n or norm_n in norm_q:
                    return cand, candidates, None
                    
            return None, candidates, ERR_SEARCH_NO_RESULT

            return None, candidates, ERR_SEARCH_NO_RESULT

        except Exception as e:
             print(f"[!] Kakao search error: {e}")
             return None, [], ERR_UNKNOWN_ERROR

    def search_for_picker(self, query: str):
        """
        Formatted search for Frontend Picker (Kakao only)
        """
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        params = {"query": query, "size": 15}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code != 200:
                print(f"[!] Kakao search failed: {resp.status_code} {resp.text}")
                return []
            
            data = resp.json()
            docs = data.get("documents", [])
            
            results = []
            for d in docs:
                results.append({
                    "provider": "kakao",
                    "place_id": d.get("id"),
                    "name": d.get("place_name"),
                    "address": d.get("address_name"),
                    "road_address": d.get("road_address_name"),
                    "phone": d.get("phone"),
                    "lat": float(d.get("y")) if d.get("y") else 0.0,
                    "lng": float(d.get("x")) if d.get("x") else 0.0,
                })
            return results

        except Exception as e:
            print(f"[!] Search picker error: {e}")
            return []



    def fetch_google_details(self, place_id: str, store_name_fallback: str) -> StoreInfo:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,opening_hours,types,rating,user_ratings_total",
            "key": GOOGLE_MAPS_API_KEY,
            "language": "ko"
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if "result" not in data:
            raise ValueError(f"No result found for place_id: {place_id}")
            
        result = data["result"]
        
        # Map categories (types) to simple string
        types = result.get("types", [])
        category = types[0].replace("_", " ").title() if types else "Unknown"

        return StoreInfo(
            name=result.get("name", store_name_fallback),
            address=result.get("formatted_address", "Address not available"),
            phone=result.get("formatted_phone_number", "Phone not available"),
            category=category,
            place_id=place_id
        )


    # Rename to analyze_snapshot for clarity, but keeping mock_analysis name for interface compat if needed, 
    # though logical refactor suggests renaming. Let's keep it compatible with main for now but logic changes.
    def mock_analysis(self, snapshot: SnapshotData) -> AnalysisResult:
        store_info = snapshot.standard_info
        
        # Use real consistency check using SnapshotData raw sources
        collected_sources = {
            "google": snapshot.raw_google,
            "naver": snapshot.raw_naver,
            "kakao": snapshot.raw_kakao
        }
        
        # Determine Area & Search Keyword (Global for Analysis)
        area = " ".join(store_info.address.split()[:2]) if store_info.address else "Seoul"
        
        # Determine search_keyword
        # Default "식당" as requested
        search_keyword = "식당"
        
        # If seed has category_path (from FE picker), use it
        # raw_naver contains seed data if source was naver_seed
        if snapshot.raw_naver and snapshot.raw_naver.get("category_path"):
             cat_path = snapshot.raw_naver.get("category_path")
             # Extract last part: "분식 > 김밥" -> "김밥"
             if ">" in cat_path:
                 search_keyword = cat_path.split(">")[-1].strip()
             else:
                 search_keyword = cat_path.strip()
        
        # If any source has data, run compare; else fallback
        if any(collected_sources.values()):
            consistency_results = compare_data(collected_sources)
        else:
             # Fallback mock consistency
            consistency_results = [
                ConsistencyResult("Name", "Match", {"google": store_info.name}, "Matches"),
                ConsistencyResult("Address", "Match", {"google": store_info.address}, "Matches"),
                ConsistencyResult("Phone", "Mismatch", {"google": "010-0000-0000", "naver": "02-1234-5678"}, "Mismatch found")
            ]

        # Mock Map Status (Analysis Logic - In real world, this would verify data against standards)
        map_channels = ["Naver", "Kakao", "Google"]
        map_statuses = []
        correct_count = 0
        
        # Simple heuristic for MVP: Check if source is empty or not
        # Ideally we check if data matches standard_info
        
        for channel in map_channels:
            # Check if we have data for this channel
            if channel == "Naver":
                has_data = bool(snapshot.raw_naver)
            elif channel == "Kakao":
                has_data = bool(snapshot.raw_kakao)
            else: # Google
                has_data = bool(snapshot.raw_google)
                
            is_correct = has_data # For now, presence = correct
            
            if is_correct:
                correct_count += 1
                status_text = "Information found."
                color = StatusColor.GREEN
            else:
                status_text = "Not found."
                color = StatusColor.RED
            
            map_statuses.append(MapChannelStatus(
                channel_name=channel,
                is_registered=has_data,
                is_information_correct=is_correct,
                status_text=status_text,
                color=color
            ))

        map_accuracy = (correct_count / len(map_channels)) * 100
        map_summary = "Map information is partially correct." if map_accuracy >= 70 else "Map information needs urgent update."

        # AI Status
        ai_engines = ["ChatGPT", "Gemini", "Claude", "Perplexity"]
        ai_statuses = []
        ai_responses = {}
        
        llm_provider = os.getenv("LLM_PROVIDER", "").lower()

        if llm_provider == "openai":
            # Real OpenAI Check
            try:
                # Local import
                from llm_client import LLMClient
                llm_client = LLMClient()
                
                # Use Global Area/Keyword
                
                q1_tmpl = os.getenv("AI_QUESTION_TEMPLATE_1", "{area}에서 추천할 만한 {search_keyword}이 있나요?")
                q2_tmpl = os.getenv("AI_QUESTION_TEMPLATE_2", "그중에서 {store_name}은 어떤 곳인가요?")
                q3_tmpl = os.getenv("AI_QUESTION_TEMPLATE_3", "{store_name}이 이 지역에서 자주 언급되는 이유는 무엇인가요?")
                
                questions = [
                    q1_tmpl.format(area=area, search_keyword=search_keyword, store_name=store_info.name),
                    q2_tmpl.format(area=area, search_keyword=search_keyword, store_name=store_info.name),
                    q3_tmpl.format(area=area, search_keyword=search_keyword, store_name=store_info.name)
                ]
                
                # Instruction sent separately
                system_instruction = "답변은 반드시 한국어로, 존댓말로 작성해주세요."
                
                openai_result = llm_client.check_exposure(store_info.name, questions, system_instruction=system_instruction)
                mention_rate = openai_result["mention_rate"]
                responses = openai_result["responses"]
                
                # UPDATE SNAPSHOT with LLM responses
                # Note: Modifying snapshot in-place here. In pure design, Analyzer should return new state.
                snapshot.llm_responses["ChatGPT"] = responses
                # We should save snapshot again if we want to persist LLM results
                self.snapshot_manager.save(snapshot) 
                
                if mention_rate >= 60:
                    color = StatusColor.GREEN
                    summary = "노출 안정적"
                    problem = "없음"
                    interpretation = "리뷰/정보가 잘 반영됨"
                elif mention_rate >= 20:
                    color = StatusColor.YELLOW
                    summary = "노출 불안정"
                    problem = "언급 빈도 낮음"
                    interpretation = "AI가 매장을 충분히 학습하지 못함"
                else:
                    color = StatusColor.RED
                    summary = "노출 실패"
                    problem = "AI 인지도 부족"
                    interpretation = "검색 후보군에 포함되지 않음"

                ai_statuses.append(AIEngineStatus(
                    engine_name="ChatGPT",
                    is_mentioned=mention_rate > 0,
                    mention_rate=float(mention_rate),
                    has_description=mention_rate > 0,
                    summary=summary,
                    problem=problem,
                    interpretation=interpretation,
                    color=color
                ))
                ai_responses["ChatGPT"] = responses
                
                # Fill others as unavailable
                for engine in ["Gemini", "Claude", "Perplexity"]:
                     ai_statuses.append(AIEngineStatus(
                        engine_name=engine,
                        is_mentioned=False,
                        mention_rate=0.0,
                        has_description=False,
                        summary="연동 안됨",
                        problem="서비스 미지원",
                        interpretation="-",
                        color=StatusColor.RED
                    ))
                     ai_responses[engine] = []
                     
                ai_mention_rate = float(mention_rate)
                ai_summary = "AI recognition is stable." if ai_mention_rate >= 50 else "Stable recognition failed."
                
            except Exception as e:
                print(f"[!] Analysis failed: {e}")
                ai_mention_rate = 0.0
                ai_summary = "Analysis Error"
        else:
            # MOCK RANDOM LOGIC
            mentioned_count = 0
            
            for engine in ai_engines:
                mention_rate = random.randint(0, 100)
                is_mentioned = mention_rate >= 20
                has_description = mention_rate >= 60
                
                if mention_rate >= 60:
                    color = StatusColor.GREEN
                    summary = "노출 안정적"
                    problem = "없음"
                    interpretation = "리뷰/정보가 잘 반영됨"
                elif mention_rate >= 20:
                    color = StatusColor.YELLOW
                    summary = "노출 불안정"
                    problem = "언급 빈도 낮음"
                    interpretation = "AI가 매장을 충분히 학습하지 못함"
                else:
                    color = StatusColor.RED
                    summary = "노출 실패"
                    problem = "AI 인지도 부족"
                    interpretation = "검색 후보군에 포함되지 않음"

                ai_statuses.append(AIEngineStatus(
                    engine_name=engine,
                    is_mentioned=is_mentioned,
                    mention_rate=mention_rate,
                    has_description=has_description,
                    summary=summary,
                    problem=problem,
                    interpretation=interpretation,
                    color=color
                ))
                
                # Mock Responses for Page 2
                responses = []
                # Use Global Search Keyword
                q1_tmpl = os.getenv("AI_QUESTION_TEMPLATE_1", "{area}에서 추천할 만한 {search_keyword}이 있나요?")
                
                q_tmpls = [
                    q1_tmpl,
                    os.getenv("AI_QUESTION_TEMPLATE_2", "그중에서 {store_name}은 어떤 곳인가요?"),
                    os.getenv("AI_QUESTION_TEMPLATE_3", "{store_name}이 이 지역에서 자주 언급되는 이유는 무엇인가요?")
                ]
                
                for i in range(3):
                    q_text = q_tmpls[i].format(area=area, search_keyword=search_keyword, store_name=store_info.name)
                    a_text = f"{store_info.name}을(를) 추천합니다. 맛과 분위기가 훌륭하다고 알려져 있습니다." if is_mentioned else "구체적인 정보를 찾을 수 없습니다."
                    
                    responses.append({
                        "question": q_text,
                        "answer": a_text,
                        "evaluation": "Good" if is_mentioned else "Bad"
                    })
                ai_responses[engine] = responses

            ai_mention_rate = sum(s.mention_rate for s in ai_statuses) / len(ai_statuses)
            ai_summary = "AI recognition is stable." if ai_mention_rate >= 50 else "Stable recognition failed."

        # Consistency
        # Handled above
        
        # Risks / Opportunities
        risks = ["Low AI mention rate in ChatGPT", "Incorrect phone number on Kakao Map"]
        opportunities = ["High review rating", "Detailed menu descriptions available"]

        # Improvements Page 3
        improvements = [
            {"title": "Unify Store Information", "description": "Ensure Name/Phone/Address are identical across all maps.", "importance": "High"},
            {"title": "Add AI-friendly Description", "description": "Update store introduction with structured keywords.", "importance": "Medium"},
            {"title": "Structure FAQs", "description": "Add Q&A section to map listings.", "importance": "Medium"}
        ]

        # Page 4 Sentence
        ai_intro_sentence = f"{store_info.name}은(는) {area}에서 꾸준히 언급되는 장소입니다."

        return AnalysisResult(
            map_accuracy=map_accuracy,
            ai_mention_rate=ai_mention_rate,
            map_summary=map_summary,
            ai_summary=ai_summary,
            map_statuses=map_statuses,
            ai_statuses=ai_statuses,
            consistency_results=consistency_results,
            risks=risks,
            opportunities=opportunities,
            improvements=improvements,
            ai_intro_sentence=ai_intro_sentence,
            ai_responses=ai_responses,
            field_provenance=snapshot.field_provenance
        )
