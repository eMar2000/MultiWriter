"""Version Manager (8.13) - Snapshots, version history, rollback"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

from src.memory import StructuredState, GraphStore

logger = logging.getLogger(__name__)

VERSIONS_TABLE = "outline-versions"


class VersionManager:
    """
    Creates snapshots at arc/chapter boundaries, maintains version history,
    executes rollbacks, validates rollback safety.
    """

    def __init__(
        self,
        structured_state: StructuredState,
        graph_store: Optional[GraphStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.structured_state = structured_state
        self.graph_store = graph_store
        self.config = config or {}
        self.retention_versions = self.config.get("retention_versions", 50)

    async def create_checkpoint(
        self,
        outline: Any,
        label: str,
        novel_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a version snapshot of the outline (and optionally canon state).

        Args:
            outline: NovelOutline or dict
            label: Human-readable label (e.g. "post_phase_5", "arc_2_complete")
            novel_id: Optional novel ID
            metadata: Optional extra metadata

        Returns:
            Version ID
        """
        version_id = str(uuid.uuid4())
        try:
            outline_data = outline.model_dump(mode='json') if hasattr(outline, 'model_dump') else outline
        except Exception:
            outline_data = outline if isinstance(outline, dict) else {}

        record = {
            "id": version_id,
            "version_id": version_id,
            "novel_id": novel_id,
            "label": label,
            "outline_snapshot": outline_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

        await self.structured_state.write(VERSIONS_TABLE, record)
        logger.info(f"[VersionManager] Created checkpoint {version_id} ({label})")
        return version_id

    async def list_versions(
        self,
        novel_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        List version metadata (no full snapshots) for a novel or all.
        """
        key_condition = {"novel_id": novel_id} if novel_id else {}
        items = await self.structured_state.query(
            VERSIONS_TABLE,
            key_condition,
            limit=limit * 2
        )
        if novel_id:
            items = [i for i in items if i.get("novel_id") == novel_id]

        # Sort by created_at desc and return metadata only
        out = []
        for item in items:
            out.append({
                "version_id": item.get("version_id"),
                "novel_id": item.get("novel_id"),
                "label": item.get("label"),
                "created_at": item.get("created_at"),
                "metadata": item.get("metadata", {})
            })
        out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return out[:limit]

    async def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Load full snapshot by version_id."""
        return await self.structured_state.read(
            VERSIONS_TABLE,
            {"id": version_id}
        )

    async def validate_rollback_safety(self, version_id: str) -> Dict[str, Any]:
        """
        Check if rollback to this version is safe (e.g. no dependent artifacts broken).
        For now: always allow; can be extended to check dependent chapters/artifacts.
        """
        version = await self.get_version(version_id)
        if not version:
            return {"safe": False, "reason": "version_not_found"}

        return {
            "safe": True,
            "version_id": version_id,
            "label": version.get("label"),
            "created_at": version.get("created_at")
        }

    async def rollback(
        self,
        version_id: str,
        novel_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Restore outline (and optionally canon) from a snapshot.
        Writes restored outline back to structured_state (e.g. novel-outlines table).
        """
        version = await self.get_version(version_id)
        if not version:
            return {"success": False, "error": "version_not_found"}

        safety = await self.validate_rollback_safety(version_id)
        if not safety.get("safe"):
            return {"success": False, "error": safety.get("reason", "unsafe")}

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "version_id": version_id,
                "outline_preview": list(version.get("outline_snapshot", {}).keys())[:5]
            }

        outline_snapshot = version.get("outline_snapshot", {})
        nid = novel_id or version.get("novel_id") or outline_snapshot.get("id")
        if nid:
            await self.structured_state.write("novel-outlines", {**outline_snapshot, "id": nid})
            logger.info(f"[VersionManager] Rolled back novel {nid} to version {version_id}")
            return {"success": True, "version_id": version_id, "novel_id": nid}

        return {"success": False, "error": "no_novel_id"}
