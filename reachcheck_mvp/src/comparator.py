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
                log_msg += f" {source_name}=None"
        
        print(log_msg)

        # Generate Descriptive details
        status = "Match" # Default
        details = ""
        
        # Logic: Group by value
        # value -> list of sources
        value_groups = {}
        for src in present_sources:
            val = normalized_values[src]
            if val not in value_groups:
                value_groups[val] = []
            value_groups[val].append(src)
            
        # Case 1: Everyone matches (All present, single group)
        if not missing_sources and len(value_groups) == 1:
            status = "Match"
            details = "일치"
            
        # Case 2: Missing Data
        elif missing_sources:
            # Special Logic: If Naver is missing phone but others match, treating as "Unavailable" not Mismatch
            if key == "phone" and "naver" in missing_sources and len(value_groups) == 1:
                status = "Match" # Or special status "Partial" if needed, but per req "Naver Unavailable" is descriptive enough
                details = "네이버 미제공 (Google/Kakao 일치)"
            else:
                status = "Missing"
                missing_korean = [s.replace('google','구글').replace('naver','네이버').replace('kakao','카카오') for s in missing_sources]
                missing_str = ", ".join(missing_korean)
                
                if len(value_groups) == 0:
                     details = "정보 없음"
                elif len(value_groups) == 1:
                     details = f"{missing_str} 미제공 (나머지 일치)"
                else:
                     details = f"{missing_str} 미제공 및 불일치"

        # Case 3: Mismatch
        else: 
            status = "Mismatch"
            details = "불일치 (채널간 정보 상이)"

        results.append(ConsistencyResult(
            field_name=label,
            status=status,
            evidence=evidence,
            details=details
        ))
        
    return results
