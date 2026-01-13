import json
import os
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Optional, Dict, Any
from models import SnapshotData, StoreSchema, PhotoData

class SnapshotManager:
    def __init__(self, output_dir: str = "snapshots"):
        self.output_dir = Path(__file__).resolve().parent.parent / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: SnapshotData) -> str:
        """Saves snapshot to JSON file. Returns file path."""
        filename = f"{snapshot.store_id}_{snapshot.timestamp}.json"
        
        # Sanitize filename
        filename = filename.replace("/", "_").replace(" ", "_")
        filepath = self.output_dir / filename
        
        data = asdict(snapshot)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"[+] Snapshot saved: {filepath}")
        return str(filepath)

    def load(self, filepath: str) -> Optional[SnapshotData]:
        """Loads snapshot from JSON file."""
        path = Path(filepath)
        if not path.exists():
            print(f"[!] Snapshot not found: {filepath}")
            return None
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Reconstruct objects
        # 1. Standard Info
        std_info_data = data.get("standard_info", {})
        photos_data = std_info_data.pop("photos", [])
        photos = [PhotoData(**p) for p in photos_data]
        
        std_info = StoreSchema(photos=photos, **std_info_data)
        
        # 2. Snapshot
        return SnapshotData(
            store_id=data.get("store_id"),
            timestamp=data.get("timestamp"),
            standard_info=std_info,
            raw_google=data.get("raw_google", {}),
            raw_naver=data.get("raw_naver", {}),
            raw_kakao=data.get("raw_kakao", {}),
            llm_responses=data.get("llm_responses", {})
        )

    def find_latest(self, store_id: str) -> Optional[str]:
        """Finds the latest snapshot file for a store_id."""
        files = sorted(self.output_dir.glob(f"{store_id}_*.json"), reverse=True)
        if files:
            return str(files[0])
        return None
