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
            details = f"{label} information matches across all maps (Google, Naver, Kakao)."
            
        # Case 2: Missing Data
        elif missing_sources:
            status = "Missing"
            missing_str = ", ".join([s.title() for s in missing_sources])
            
            if len(value_groups) == 0:
                 details = f"{label} information matches nowhere (All missing)."
            elif len(value_groups) == 1:
                # Rest match
                 details = f"{label} is missing on {missing_str}, but matches on the others."
            else:
                # Rest mismatch
                 details = f"{label} is missing on {missing_str}, and differs among the others."

        # Case 3: Mismatch (No missing, but multiple groups)
        else: # len(value_groups) > 1 and not missing_sources
            status = "Mismatch"
            # Build description of groups
            # e.g. "Google/Naver match, but Kakao differs."
            
            # Find the majority group if any
            sorted_groups = sorted(value_groups.items(), key=lambda item: len(item[1]), reverse=True)
            
            descriptions = []
            for val, srcs in sorted_groups:
                src_names = "/".join([s.title() for s in srcs])
                descriptions.append(f"{src_names}")
            
            details = f"{label} differs: {descriptions[0]} vs {descriptions[1]}."

        results.append(ConsistencyResult(
            field_name=label,
            status=status,
            evidence=evidence,
            details=details
        ))
        
    return results
