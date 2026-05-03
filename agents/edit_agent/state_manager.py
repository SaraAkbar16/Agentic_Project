import json
import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class StateManager:
    """Manages project versioning, snapshots, and undo functionality."""
    
    def __init__(self, data_dir: str = "data/outputs"):
        self.data_dir = Path(data_dir)
        # Versions are now stored INSIDE the project directory
        self.versions_dir = self.data_dir / "versions"
        self.history_file = self.versions_dir / "history.json"
        
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history([])

    def snapshot(self, change_summary: str) -> str:
        """Create a versioned snapshot of the current data/outputs directory."""
        history = self._load_history()
        version_num = len(history) + 1
        version_id = f"v{version_num}"
        
        version_path = self.versions_dir / version_id
        version_path.mkdir(parents=True, exist_ok=True)
        
        # Copy all contents from data/outputs to the version folder
        # We ignore the 'versions' folder itself to prevent recursive nesting
        shutil.copytree(
            self.data_dir, 
            version_path, 
            dirs_exist_ok=True, 
            ignore=shutil.ignore_patterns("versions")
        )
        
        # Update history
        entry = {
            "version": version_id,
            "timestamp": datetime.now().isoformat(),
            "change_summary": change_summary,
            "path": str(version_path)
        }
        history.append(entry)
        self._save_history(history)
        
        return version_id

    def revert(self, version_id: str) -> bool:
        """Revert the current data/outputs to a previous version."""
        history = self._load_history()
        target = next((v for v in history if v["version"] == version_id), None)
        
        if not target:
            return False
            
        version_path = Path(target["path"])
        if not version_path.exists():
            return False
            
        # Clear current outputs and restore from snapshot
        for item in self.data_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
                
        shutil.copytree(version_path, self.data_dir, dirs_exist_ok=True)
        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the list of all snapshots."""
        return self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except:
            return []

    def _save_history(self, history: List[Dict[str, Any]]):
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)
