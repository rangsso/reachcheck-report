import random
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from models import (
    StoreInfo, MapChannelStatus, AIEngineStatus, ConsistencyResult, 
    ReviewAnalysis, ReportData, AnalysisResult, StatusColor
)


from pathlib import Path

# Explicitly load .env from project root
# current file is in src/, project root is 2 levels up
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

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

    def collect(self, store_name: str, place_id: str = None, naver_seed: dict = None) -> SnapshotData:
        google_data = {}
        naver_data = {}
        kakao_data = {}
        
        errors = {}
        search_candidates = {}

        # 1. Base Identity (from Naver if available)
        if naver_seed:
            # MVP: Use normalized Naver data as seed
            # naver_seed comes from frontend (ReportRequest fields)
            print(f"[-] Using Naver Seed for {store_name}")
            naver_data = {
                "name": naver_seed.get("store_name"),
                "address": naver_seed.get("address") or naver_seed.get("road_address"),
                "phone": naver_seed.get("tel"),
                "category": "General", # or pass if available
                "link": naver_seed.get("naver_link"),
                "mapx": naver_seed.get("mapx"),
                "mapy": naver_seed.get("mapy")
            }
            # Use link or synthesized ID
            if not place_id:
                place_id = f"NID-{abs(hash(store_name + str(naver_data['address'])))}"
        
        elif not place_id:
             place_id = f"PID-{random.randint(10000, 99999)}"

        # 2. Kakao Search (Find match for Naver/Input data)
        # Using name provided
        if KAKAO_REST_API_KEY:
            k_data, k_candidates, k_error = self.fetch_kakao_search_extended(store_name)
            # Refinement: check address match if strictly needed, but for MVP best match is ok
            if k_data:
                kakao_data = k_data
            if k_candidates:
                search_candidates["Kakao"] = k_candidates
            if k_error:
                errors["Kakao"] = k_error
        else:
            errors["Kakao"] = ERR_AUTH_ERROR

        # 3. Google Data (Find match or fetch by place_id if legacy flow)
        if place_id and not place_id.startswith("PID-") and not place_id.startswith("NID-") and GOOGLE_MAPS_API_KEY:
             # Legacy Flow: Place ID provided (Google ID)
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
             # Naver Flow: Search Google Text Search with name
             # MVP: Simple text search and take top result
             try:
                 # Re-use search logic (embedded here due to time constraint, or create helper)
                 url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                 params = {"query": store_name, "key": GOOGLE_MAPS_API_KEY, "language": "ko"}
                 resp = requests.get(url, params=params)
                 g_res = resp.json()
                 if g_res.get("results"):
                     top = g_res["results"][0]
                     google_data = {
                         "name": top.get("name"),
                         "address": top.get("formatted_address"),
                         "place_id": top.get("place_id")
                     }
                 else:
                     errors["Google"] = ERR_SEARCH_NO_RESULT
             except Exception as e:
                 errors["Google"] = f"SEARCH_FAIL: {str(e)}"
        else:
             # Mock
             google_data = {
                 "name": store_name, 
                 "address": "Seoul, Mock Address", 
                 "phone": "02-1234-5678",
                 "category": "General"
             }

        # 4. Naver Search (If not seeded, fetch it)
        if not naver_data and NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
            n_data, n_candidates, n_error = self.fetch_naver_search_extended(store_name)
            if n_data:
                naver_data = n_data
            if n_candidates:
                search_candidates["Naver"] = n_candidates
            if n_error:
                errors["Naver"] = n_error
        elif not naver_data:
            errors["Naver"] = ERR_AUTH_ERROR
        
        # LOGGING
        self._log_source_data("GOOGLE", google_data)
        self._log_source_data("NAVER", naver_data)
        self._log_source_data("KAKAO", kakao_data)
        
        # 5. Normalize & Snapshot
        # Use naver_data for standard info if available (Naver-First)
        if naver_data:
             # Creating StoreSchema from Naver Data manually to ensure it is the standard
             from models import StoreSchema
             standard_info = StoreSchema(
                 id=place_id,
                 name=naver_data.get("name", store_name),
                 address=naver_data.get("address", ""),
                 phone=naver_data.get("phone", ""),
                 category=naver_data.get("category", "General"),
                 lat=0.0, lng=0.0, # Mapxy conversion not in MVP scope
                 hours="",
                 description="",
                 source_url=naver_data.get("link", "") or naver_data.get("source_url", "")
             )
        else:
             standard_info = normalize_store_data(place_id, google_data, naver_data, kakao_data)
        
        # 6. Field Status Analysis (Missing vs Mismatch)
        missing_fields = []
        if not standard_info.name: missing_fields.append("name")
        if not standard_info.address: missing_fields.append("address")
        if not standard_info.phone: missing_fields.append("phone")
        if not standard_info.category or standard_info.category == "Unknown": missing_fields.append("category")
        
        mismatch_fields = []
        # Naver vs Kakao
        if naver_data and kakao_data:
            if normalize_name(naver_data.get("name","")) != normalize_name(kakao_data.get("name","")):
                mismatch_fields.append("name_naver_kakao")
            if normalize_name(naver_data.get("phone","")) != normalize_name(kakao_data.get("phone","")):
                mismatch_fields.append("phone_naver_kakao") # Fixed key name preference
        
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
                
                # Derive Area from address (Simple heuristic)
                area = " ".join(store_info.address.split()[:2]) if store_info.address else "Seoul"
                
                questions = [
                    f"Recommend a good place for {store_info.category} in {area}.",
                    f"What can you tell me about {store_info.name} in {area}?",
                    f"Is {store_info.name} a popular spot in {area}? Why?"
                ]
                
                openai_result = llm_client.check_exposure(store_info.name, questions)
                mention_rate = openai_result["mention_rate"]
                responses = openai_result["responses"]
                
                # UPDATE SNAPSHOT with LLM responses
                # Note: Modifying snapshot in-place here. In pure design, Analyzer should return new state.
                snapshot.llm_responses["ChatGPT"] = responses
                # We should save snapshot again if we want to persist LLM results
                self.snapshot_manager.save(snapshot) 
                
                if mention_rate >= 60:
                    color = StatusColor.GREEN
                    summary = "Stable recognition"
                    problem = "None"
                    interpretation = "Reflects reviews/assets well"
                elif mention_rate >= 20:
                    color = StatusColor.YELLOW
                    summary = "Unstable recognition"
                    problem = "Low frequency"
                    interpretation = "Insufficient differentiation"
                else:
                    color = StatusColor.RED
                    summary = "Failed to recognize"
                    problem = "High risk of omission"
                    interpretation = "Not recognized as a candidate"

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
                        summary="Not Connected",
                        problem="Provider not configured",
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
                    summary = "Stable recognition"
                    problem = "None"
                    interpretation = "Reflects reviews/assets well"
                elif mention_rate >= 20:
                    color = StatusColor.YELLOW
                    summary = "Unstable recognition"
                    problem = "Low frequency"
                    interpretation = "Insufficient differentiation"
                else:
                    color = StatusColor.RED
                    summary = "Failed to recognize"
                    problem = "High risk of omission"
                    interpretation = "Not recognized as a candidate"

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
                for i in range(3):
                    responses.append({
                        "question": f"Recommend a good place for {store_info.category} in this area.",
                        "answer": f"I recommend {store_info.name}. It is known for good ambiance." if is_mentioned else "I couldn't find specific details.",
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
            {"title": "Structure FAQs", "description": "Structure FAQs", "description": "Add Q&A section to map listings.", "importance": "Medium"}
        ]

        # Page 4 Sentence
        ai_intro_sentence = f"{store_info.name} is a {store_info.category} in Gangnam known for its verified taste and service."

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
            ai_responses=ai_responses
        )
