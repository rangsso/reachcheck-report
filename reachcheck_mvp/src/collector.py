import random
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from models import (
    StoreInfo, MapChannelStatus, AIEngineStatus, ConsistencyResult, 
    ReviewAnalysis, ReportData, AnalysisResult, StatusColor
)
import bs4
import re
import json
import time
import shutil
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
        
        # Save immediately
        self.snapshot_manager.save(snapshot)
        
        return snapshot
    
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
