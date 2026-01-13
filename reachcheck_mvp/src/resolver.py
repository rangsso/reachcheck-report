from typing import List, Dict, Optional
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

class StoreResolver:
    def __init__(self):
        # Explicitly load .env from project root
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        
        self.google_key = os.getenv("GOOGLE_MAPS_API_KEY")

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Searches for a store on Google Maps and returns candidates.
        Returns list of {name, address, place_id}
        """
        if not self.google_key:
            print("[!] Google Maps API Key missing.")
            return []

        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": self.google_key,
            "language": "ko"
        }
        
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            results = data.get("results", [])
            
            candidates = []
            for r in results:
                candidates.append({
                    "name": r.get("name"),
                    "address": r.get("formatted_address"),
                    "place_id": r.get("place_id")
                })
            return candidates
            
        except Exception as e:
            print(f"[!] Place search failed: {e}")
            return []

    def resolve(self, query: str) -> Optional[str]:
        """
        Resolves a query to a SINGLE place_id.
        If multiple found, asks user (via CLI) or picks first (if strict).
        For now, we'll pick the first one and log it.
        """
        candidates = self.search(query)
        
        if not candidates:
            print(f"[!] No places found for '{query}'")
            return None
            
        # If strict CLI interaction is requested, we could add input() here.
        # But for automation/API, picking top 1 is standard unless ambiguous.
        
        best = candidates[0]
        print(f"[*] Resolved '{query}' -> {best['name']} ({best['place_id']})")
        return best["place_id"]
