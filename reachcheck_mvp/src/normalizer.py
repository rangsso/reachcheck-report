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
