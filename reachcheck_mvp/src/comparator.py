from typing import Dict, List, Any
from models import ConsistencyResult
from normalizer import normalize_name, normalize_phone, normalize_address

def compare_data(sources: Dict[str, Dict[str, Any]]) -> List[ConsistencyResult]:
    """
    sources structure:
    {
       'google': {'name': '...', ...},
       'naver': {'name': '...', ...},
       'kakao': {'name': '...', ...}
    }
    """
    
    results = []
    
    # Define fields to compare and their normalizers
    fields = [
        ("Name", "name", normalize_name),
        ("Address", "address", normalize_address),
        ("Phone", "phone", normalize_phone),
    ]
    
    # Required sources for full verification
    required_sources = ["google", "naver", "kakao"]
    
    # Relaxed Address Comparator (Core Token Match)
    def compare_address_relaxed(a: str, b: str) -> bool:
        if not a or not b: return False
        import re
        
        # Helper: Extract Key Tokens
        def text_token(t): return t.replace(" ", "")
        
        # 1. Gu (District) - Critical Match
        gu_pattern = re.compile(r'(\S+구)\b')
        gu_a = gu_pattern.search(a)
        gu_b = gu_pattern.search(b)
        
        if gu_a and gu_b:
            if text_token(gu_a.group(1)) != text_token(gu_b.group(1)):
                return False # Different District -> Mismatch
        
        # 2. Road Address Pattern (Name + Number) e.g. 영등포로 143
        road_pattern = re.compile(r'(\S+(?:로|길))\s*([\d-]+)')
        road_a = road_pattern.search(a)
        road_b = road_pattern.search(b)
        
        # 3. Dong/Jibun Pattern (Dong + Number) e.g. 당산동 53-4 or 당산동1가 53-4
        dong_pattern = re.compile(r'(\S+(?:동|가))(?:\s*[\d-]+가)?\s*([\d-]+)')
        dong_a = dong_pattern.search(a)
        dong_b = dong_pattern.search(b)

        # Logic
        # Case A: Both have Road Address -> Must Match
        if road_a and road_b:
            # Check Road Name AND Number
            if text_token(road_a.group(1)) == text_token(road_b.group(1)) and road_a.group(2) == road_b.group(2):
                return True
            else:
                return False # Different Road Addr
        
        # Case B: Both have Dong Address -> Must Match
        if dong_a and dong_b:
             # Check Dong Name AND Number
             if text_token(dong_a.group(1)) == text_token(dong_b.group(1)) and dong_a.group(2) == dong_b.group(2):
                 return True
             else:
                 return False # Different Dong Addr
                 
        # Case C: Mixed (Road vs Dong) OR One Missing Pattern
        # If Gu matched (or wasn't found to differ), and we can't definitively say they differ via same-type comparison:
        # We assume Match/LikelyMatch as per "Road <-> Jibun" requirement.
        # This covers: "Naver(Jibun) vs Google(Road)" -> Match
        return True

    for label, key, normalizer in fields:
        evidence = {}
        normalized_values = {}
        
        # Logging input for this field
        log_msg = f"[COMPARE][{key}]"
        
        # Collect values
        missing_sources = []
        present_sources = []
        
        for source_name in required_sources:
            data = sources.get(source_name, {})
            # Special handling for Address to use RAW for relaxed compare if needed?
            # actually we can just use the normalizer result and then custom compare.
            raw_val = data.get(key)
            
            if raw_val:
                evidence[source_name] = str(raw_val)
                norm_val = normalizer(str(raw_val))
                normalized_values[source_name] = norm_val
                present_sources.append(source_name)
                log_msg += f" {source_name}={norm_val}"
            else:
                evidence[source_name] = "(Missing)"
                normalized_values[source_name] = None
                missing_sources.append(source_name)
                
        print(log_msg)
        
        # Determine Status
        status = "Match" # Default
        details = "모든 채널 정보 일치"
        
        # Rule 1: Missing Source
        if missing_sources:
             # Basic Missing Status
             status = "Missing"
             missing_korean = [s.replace('google','구글').replace('naver','네이버').replace('kakao','카카오') for s in missing_sources]
             details = f"{', '.join(missing_korean)} 정보 미제공"
             
             # Refinement: If it's just "Naver Unavailable" for phone, we might treat differently in Analyzer, 
             # but here we just report truth: It is missing from Naver.
             # Note: Analyzer will suppress "Not Registered" if standard phone exists.
        
        # Rule 2: Check Consistency (if we have at least 2 sources)
        if len(present_sources) > 1:
            is_mismatch = False
            
            # Custom comparator for Address
            if key == "address":
                 # Compare all against first present
                 baseline = normalized_values[present_sources[0]]
                 for other in present_sources[1:]:
                     other_val = normalized_values[other]
                     if not compare_address_relaxed(baseline, other_val):
                         is_mismatch = True
                         break
            else:
                # Standard Strict Compare (Name, Phone)
                first_val = normalized_values[present_sources[0]]
                for src in present_sources[1:]:
                    if normalized_values[src] != first_val:
                        is_mismatch = True
                        break
            
            if is_mismatch:
                status = "Mismatch"
                if key == "phone":
                    details = "번호 다름 (대표번호/플랫폼번호 가능성)"
                else:
                    details = "채널 간 정보 불일치"

        results.append(ConsistencyResult(
            field_name=label,
            status=status,
            evidence=evidence,
            details=details
        ))
        
    return results
