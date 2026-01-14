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
    s = re.sub(r'^(대한민국|Republic of Korea|South Korea)\s*', '', s, flags=re.IGNORECASE)
    
    # Remove content in parentheses (e.g. building info, extra dong)
    s = re.sub(r'\(.*?\)', '', s)
    
    # Remove detailed location info (Floor, Suite, Basement)
    # Examples: 1층, 101호, B1, 지하1층, 304호
    s = re.sub(r'\s+(지하|B)?\d+(층|호)\b', '', s)
    s = re.sub(r'\s+\d+(F|f)\b', '', s) # 1F
    s = re.sub(r'\s+(B|지하)\d+\b', '', s, flags=re.IGNORECASE) # B1, 지하1 (Standalone)
    
    # Remove common Province/City prefixes (Optional but helps core match)
    # User requirement 1-2 says "Core Tokens: Gu...". 
    # Providing clean string "Seoul Yongsan-gu..." is fine, comparator can parse.
    # We will just normalize whitespace.
    
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def format_display_address(addr: str) -> str:
    """
    Format address for display only (Reports).
    Removes country prefixes like 'Republic of Korea', '대한민국'.
    """
    if not addr: return ""
    s = addr
    # Remove Country Prefixes (case insensitive)
    # Note: Regex includes optional trailing space/comma
    s = re.sub(r'^(대한민국|Republic of Korea|South Korea|Korea, Republic of)\s*,?\s*', '', s, flags=re.IGNORECASE)
    return s.strip()

def is_valid_category_for_display(cat: str) -> bool:
    """
    Check if category is meaningful for report display.
    Hidden: Establishment, Unknown, Place, 업종 정보 없음, empty.
    """
    if not cat: return False
    hidden_keywords = ["establishment", "unknown", "place", "point of interest", "업종 정보 없음", "일반 매장"]
    norm = cat.lower().strip()
    if norm in hidden_keywords: return False
    return True

def normalize_category_for_ai(raw_cat: str) -> str:
    if not raw_cat:
        return None
    
    rc = raw_cat.strip()
    
    # Ignore list (lowercase)
    ignore_list = ["establishment", "point of interest", "store", "unknown", "-", ""]
    if rc.lower() in ignore_list:
        return None
        
    # Mappings
    mapping = {
        "restaurant": "식당",
        "food": "식당",
        "meal_takeaway": "식당",
        "meal_delivery": "식당",
        "cafe": "카페",
        "bakery": "베이커리",
        "bar": "술집",
        "pub": "술집"
    }
    
    rc_lower = rc.lower()
    for k, v in mapping.items():
        if k in rc_lower:
            return v
            
    return rc

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

