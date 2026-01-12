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
        missing_source_found = False
        
        for source_name in required_sources:
            data = sources.get(source_name, {})
            raw_val = data.get(key)
            
            if raw_val:
                evidence[source_name] = str(raw_val)
                norm_val = normalizer(str(raw_val))
                normalized_values[source_name] = norm_val
                log_msg += f" {source_name}={norm_val}"
            else:
                evidence[source_name] = "(Missing)"
                normalized_values[source_name] = None
                missing_source_found = True
                log_msg += f" {source_name}=None"
        
        print(log_msg)

        # Determine status
        # Rule (A): If ANY source is missing -> INSUFFICIENT_DATA
        if missing_source_found:
            status = "INSUFFICIENT_DATA"
            details = "Some data sources are unavailable."
        else:
            # All sources present. Check consistency.
            # Rule (B): Mismatch only if they differ
            valid_norms = list(normalized_values.values())
            
            if len(set(valid_norms)) == 1:
                status = "Match"
                details = "All sources match."
            else:
                status = "Mismatch"
                details = "Data differs across sources."

        results.append(ConsistencyResult(
            field_name=label,
            status=status,
            evidence=evidence,
            details=details
        ))
        
    return results
