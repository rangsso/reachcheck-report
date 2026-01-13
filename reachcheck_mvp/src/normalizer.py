import re

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    # Remove all non-digits
    digits = re.sub(r"\D", "", phone)
    # Handle +82 format (e.g. 821012345678 -> 01012345678, 82212345678 -> 0212345678)
    if digits.startswith("82"):
        digits = "0" + digits[2:]
    return digits

def normalize_name(name: str) -> str:
    if not name:
        return ""
    # Remove spaces
    s = name.replace(" ", "")
    # Remove branch info commonly found in parenthesis e.g. (Gangnam Branch)
    s = re.sub(r"\(.*?\)", "", s)
    # Remove common suffixes if they are at the end
    s = re.sub(r"(지점|점)$", "", s)
    return s.strip()

def normalize_address(addr: str) -> str:
    if not addr:
        return ""
    
    s = addr
    # Remove Country
    s = s.replace("Republic of Korea", "").replace("South Korea", "").replace("대한민국", "")
    
    # Remove common Province/City prefixes to focus on District/Street
    # (Handling inconsistencies like "Seoul" vs "Seoul Special City" vs "서울특별시" vs "서울")
    # This is a heuristic for MVP.
    prefixes = [
        "서울특별시", "서울시", "서울", "Seoul", 
        "경기도", "경기", "Gyeonggi-do", "Gyeonggi",
        "인천광역시", "인천", "Incheon",
        "부산광역시", "부산", "Busan",
        "대구광역시", "대구", "Daegu",
        "대전광역시", "대전", "Daejeon",
        "광주광역시", "광주", "Gwangju",
        "울산광역시", "울산", "Ulsan",
        "세종특별자치시", "세종", "Sejong",
        "제주특별자치도", "제주", "Jeju"
    ]
    
    for p in prefixes:
        s = s.replace(p, "")
        
    # Remove floor/suite info (e.g. 1층, 101호, B1, 2F)
    s = re.sub(r"\s\d+(층|호|F)\b", "", s) # 1층, 101호
    s = re.sub(r"\sB\d+\b", "", s)       # B1
    
    # Remove spaces/punctuation
    s = re.sub(r"[\s,.]", "", s)
    return s

from models import StoreSchema, PhotoData
from typing import Dict, Any, List

def normalize_store_data(
    store_id: str, 
    raw_google: Dict[str, Any], 
    raw_naver: Dict[str, Any], 
    raw_kakao: Dict[str, Any]
) -> StoreSchema:
    """
    Consolidates raw data from multiple sources into a single standardized StoreSchema.
    Priority: Google > Naver > Kakao (for MVP)
    """
    
    # 1. Name
    name = raw_google.get("name") or raw_naver.get("name") or raw_kakao.get("name") or "Unknown Store"
    
    # 2. Address
    address = raw_google.get("address") or raw_naver.get("address") or raw_kakao.get("address") or ""
    
    # 3. Phone
    phone = raw_google.get("phone") or raw_naver.get("phone") or raw_kakao.get("phone") or ""
    
    # 4. Category
    # Google uses types list, Naver/Kakao might differ. Simplified for MVP.
    category = "Unknown"
    # Google (already processed in collector, but let's re-verify if possible or trust collector passed refined dict)
    # The current collector flattens google struct slightly. Let's assume raw_google has 'category' or we extract from 'types' if preserved.
    # We will assume collector passed 'category' in the dictionary for convenience or we stick to what we have.
    # In collector currently: google_data = {"name": ..., "address": ..., "phone": ...} 
    # We need to ensure collector passes 'category' too.
    
    category = raw_google.get("category") or raw_naver.get("category") or "General"

    # 5. Geolocation (Lat/Lng) - Only Google Details provides this readily in this MVP setup
    # If missing, default to 0.0
    lat = raw_google.get("lat", 0.0)
    lng = raw_google.get("lng", 0.0)
    
    # 6. Photos
    photos = []
    # Implementation detail: Photo parsing would happen here if we had raw photo data.
    
    return StoreSchema(
        id=store_id,
        name=name,
        address=address,
        phone=phone,
        category=category,
        lat=lat,
        lng=lng,
        hours="", # To be implemented
        description="", # To be implemented
        photos=photos,
        source_url=""
    )

