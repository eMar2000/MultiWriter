"""Local file-based storage implementation"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .structured_state import StructuredState


class LocalFileState(StructuredState):
    """Local file-based implementation of structured state storage"""

    def __init__(self, storage_dir: str = "./data"):
        """
        Initialize local file storage

        Args:
            storage_dir: Directory to store data files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_table_dir(self, table_name: str) -> Path:
        """Get directory for a table"""
        table_dir = self.storage_dir / table_name
        table_dir.mkdir(parents=True, exist_ok=True)
        return table_dir

    def _get_item_path(self, table_name: str, key: Dict[str, Any]) -> Path:
        """Get file path for an item"""
        # Use the first key value as filename
        key_value = list(key.values())[0]
        return self._get_table_dir(table_name) / f"{key_value}.json"

    def _serialize_datetime(self, obj: Any) -> Any:
        """Recursively convert datetime objects to ISO strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj

    async def write(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Write an item to local storage"""
        if "id" not in item:
            raise ValueError("Item must have an 'id' field")

        file_path = self._get_table_dir(table_name) / f"{item['id']}.json"

        # Serialize datetime objects
        serialized_item = self._serialize_datetime(item)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(serialized_item, f, indent=2, default=str)

        return True

    async def read(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Read an item from local storage"""
        file_path = self._get_item_path(table_name, key)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def query(
        self,
        table_name: str,
        key_condition: Dict[str, Any],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query items from local storage"""
        table_dir = self._get_table_dir(table_name)
        items = []

        for file_path in table_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                item = json.load(f)

                # Check if item matches key condition
                matches = all(
                    item.get(k) == v for k, v in key_condition.items()
                )
                if matches:
                    items.append(item)

        return items

    async def update(
        self,
        table_name: str,
        key: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> bool:
        """Update an item in local storage"""
        file_path = self._get_item_path(table_name, key)

        if not file_path.exists():
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            item = json.load(f)

        # Apply updates
        item.update(self._serialize_datetime(updates))

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=2, default=str)

        return True

    async def delete(self, table_name: str, key: Dict[str, Any]) -> bool:
        """Delete an item from local storage"""
        file_path = self._get_item_path(table_name, key)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def list_all(self, table_name: str) -> List[Dict[str, Any]]:
        """List all items in a table"""
        table_dir = self._get_table_dir(table_name)
        items = []

        for file_path in table_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                items.append(json.load(f))

        return items


class LocalObjectStore:
    """Local file-based object storage (replacement for S3)"""

    def __init__(self, storage_dir: str = "./data/objects"):
        """
        Initialize local object storage

        Args:
            storage_dir: Directory to store objects
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Upload an object to local storage"""
        file_path = self.storage_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)

        # Store metadata if provided
        if metadata:
            meta_path = self.storage_dir / f"{key}.meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

        return True

    async def download(self, key: str) -> Optional[bytes]:
        """Download an object from local storage"""
        file_path = self.storage_dir / key

        if not file_path.exists():
            return None

        with open(file_path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        """Delete an object from local storage"""
        file_path = self.storage_dir / key

        if file_path.exists():
            file_path.unlink()
            # Also delete metadata if exists
            meta_path = self.storage_dir / f"{key}.meta.json"
            if meta_path.exists():
                meta_path.unlink()
            return True
        return False

    async def list(self, prefix: Optional[str] = None) -> list:
        """List objects with optional prefix"""
        if prefix:
            search_path = self.storage_dir / prefix
            if search_path.is_dir():
                return [str(p.relative_to(self.storage_dir)) for p in search_path.rglob("*") if p.is_file() and not p.name.endswith(".meta.json")]
            else:
                return [str(p.relative_to(self.storage_dir)) for p in self.storage_dir.glob(f"{prefix}*") if p.is_file() and not p.name.endswith(".meta.json")]
        else:
            return [str(p.relative_to(self.storage_dir)) for p in self.storage_dir.rglob("*") if p.is_file() and not p.name.endswith(".meta.json")]
