import random
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from models import (
    StoreInfo, MapChannelStatus, AIEngineStatus, ConsistencyResult, 
    ReviewAnalysis, ReportData, AnalysisResult, StatusColor
)


load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

from comparator import compare_data
from normalizer import normalize_name, normalize_address, normalize_phone

class DataCollector:
    def collect(self, store_name: str, place_id: str = None) -> StoreInfo:
        google_data = {}
        naver_data = {}
        kakao_data = {}

        # 1. Google Data
        if place_id and not place_id.startswith("PID-") and GOOGLE_MAPS_API_KEY:
             try:
                 print(f"[-] Fetching details for Place ID: {place_id}")
                 store_info = self.fetch_google_details(place_id, store_name)
                 google_data = {
                     "name": store_info.name,
                     "address": store_info.address,
                     "phone": store_info.phone
                 }
             except Exception as e:
                 print(f"[!] Google API failed: {e}. Fallback to mock.")
                 # Fallback mock obj
                 store_info = StoreInfo(
                    name=store_name,
                    address=f"Seoul, Gangnam-gu, Yeoksam-dong 123-45",
                    phone="02-1234-5678",
                    category="Cafe/Restaurant",
                    place_id=place_id
                )
        else:
             # Mock
             store_info = StoreInfo(
                name=store_name,
                address=f"Seoul, Gangnam-gu, Yeoksam-dong 123-45",
                phone="02-1234-5678",
                category="Cafe/Restaurant",
                place_id=place_id if place_id else f"PID-{random.randint(10000, 99999)}"
            )
             google_data = {"name": store_info.name, "address": store_info.address, "phone": store_info.phone}

        # 2. Naver Search
        if NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
            try:
                naver_data = self.fetch_naver_search(store_name)
            except Exception as e:
                print(f"[!] Naver API failed: {e}")

        # 3. Kakao Search
        if KAKAO_REST_API_KEY:
            try:
                kakao_data = self.fetch_kakao_search(store_name)
            except Exception as e:
                print(f"[!] Kakao API failed: {e}")
        
        
        # LOGGING (New Requirement: 1-A)
        self._log_source_data("GOOGLE", google_data)
        self._log_source_data("NAVER", naver_data)
        self._log_source_data("KAKAO", kakao_data)
        
        self.collected_sources = {
            "google": google_data,
            "naver": naver_data,
            "kakao": kakao_data
        }

        return store_info
    
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
        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 5, "sort": "random"} # Fetch 5 to filter
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            data = resp.json()
            items = data.get("items", [])
            
            # Simple validation: query should be part of name or vice-versa
            # Logic: verify coverage
            norm_q = query.replace(" ", "")
            
            for item in items:
                name = item.get('title').replace('<b>', '').replace('</b>', '')
                norm_n = name.replace(" ", "")
                
                # Loose check
                print(f"[DEBUG] Check: '{norm_q}' in '{norm_n}'?")
                if norm_q in norm_n or norm_n in norm_q:
                     return {
                        "name": name,
                        "address": item.get("roadAddress") or item.get("address"),
                        "phone": item.get("telephone") or "" 
                    }
        except Exception as e:
            print(f"[!] Naver search error: {e}")
            
        return {}

    def fetch_kakao_search(self, query: str) -> dict:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        params = {"query": query, "size": 5}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            data = resp.json()
            docs = data.get("documents", [])
            
            norm_q = query.replace(" ", "")
            
            for d in docs:
                name = d.get('place_name')
                norm_n = name.replace(" ", "")
                
                if norm_q in norm_n or norm_n in norm_q:
                    return {
                        "name": name,
                        "address": d.get("road_address_name") or d.get("address_name"),
                        "phone": d.get("phone")
                    }
        except Exception as e:
             print(f"[!] Kakao search error: {e}")
             
        return {}


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


    def mock_analysis(self, store_info: StoreInfo) -> AnalysisResult:
        # Use real consistency check if available
        if hasattr(self, 'collected_sources') and any(self.collected_sources.values()):
            consistency_results = compare_data(self.collected_sources)
        else:
             # Fallback mock consistency
            consistency_results = [
                ConsistencyResult("Name", "Match", {"google": store_info.name}, "Matches"),
                ConsistencyResult("Address", "Match", {"google": store_info.address}, "Matches"),
                ConsistencyResult("Phone", "Mismatch", {"google": "010-0000-0000", "naver": "02-1234-5678"}, "Mismatch found")
            ]

        # Mock Map Status
        map_channels = ["Naver", "Kakao", "Google"]
        map_statuses = []
        correct_count = 0
        
        for channel in map_channels:
            is_correct = random.random() > 0.3  # 70% chance of being correct
            if is_correct:
                correct_count += 1
                status_text = "All information matches."
                color = StatusColor.GREEN
            else:
                status_text = "Phone number or hours mismatch."
                color = StatusColor.YELLOW if random.random() > 0.5 else StatusColor.RED
            
            map_statuses.append(MapChannelStatus(
                channel_name=channel,
                is_registered=True,
                is_information_correct=is_correct,
                status_text=status_text,
                color=color
            ))

        map_accuracy = (correct_count / len(map_channels)) * 100
        map_summary = "Map information is partially correct." if map_accuracy >= 70 else "Map information needs urgent update."

        # Mock AI Status
        ai_engines = ["ChatGPT", "Gemini", "Claude", "Perplexity"]
        ai_statuses = []
        mentioned_count = 0
        total_questions = 10 
        
        ai_responses = {}

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
            {"title": "Structure FAQs", "description": "Add Q&A section to map listings.", "importance": "Medium"}
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
