"""User Interaction Manager (8.12) - Batch approvals, prioritization, timeouts"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """Single approval request from an agent"""
    id: str
    source_agent: str
    request_type: str  # e.g. "new_character", "major_plot_change"
    description: str
    context: Dict[str, Any]
    priority: str  # "critical", "high", "medium", "low"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_hours: float = 48.0
    response: Optional[Dict[str, Any]] = None


class UserInteractionManager:
    """
    Batches approval requests, prioritizes critical decisions,
    applies timeouts/defaults. Tracks patterns for future use.
    """

    def __init__(
        self,
        default_timeout_hours: float = 48.0,
        config: Optional[Dict[str, Any]] = None
    ):
        self.default_timeout_hours = default_timeout_hours
        self.config = config or {}
        self._pending: Dict[str, ApprovalRequest] = {}
        self._history: List[Dict[str, Any]] = []

    async def add_approval_request(
        self,
        source_agent: str,
        request_type: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
        request_id: Optional[str] = None
    ) -> str:
        """
        Add an approval request to the pending batch.

        Returns:
            Unique request ID
        """
        import uuid
        rid = request_id or str(uuid.uuid4())
        timeout = self.config.get("approval_timeout_hours", self.default_timeout_hours)
        self._pending[rid] = ApprovalRequest(
            id=rid,
            source_agent=source_agent,
            request_type=request_type,
            description=description,
            context=context or {},
            priority=priority,
            timeout_hours=timeout
        )
        logger.info(f"[UIM] Added approval request {rid} from {source_agent} (priority={priority})")
        return rid

    async def get_pending_batch(
        self,
        include_timed_out: bool = True,
        sort_by_priority: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests, optionally including timed-out ones.
        Critical/high first if sort_by_priority.
        """
        now = datetime.now(timezone.utc)
        order = ("critical", "high", "medium", "low")

        def key(r: ApprovalRequest):
            if not include_timed_out and r.response is None:
                deadline = r.created_at + timedelta(hours=r.timeout_hours)
                if now > deadline:
                    return (1, 0, r.created_at)  # exclude by putting last and filter
            prio = order.index(r.priority) if r.priority in order else 2
            return (0, prio, r.created_at)

        items = [r for r in self._pending.values() if r.response is None]
        if include_timed_out:
            items = [r for r in items if (now <= r.created_at + timedelta(hours=r.timeout_hours))]
        if sort_by_priority:
            items.sort(key=lambda r: (order.index(r.priority) if r.priority in order else 2, r.created_at))

        return [
            {
                "id": r.id,
                "source_agent": r.source_agent,
                "request_type": r.request_type,
                "description": r.description,
                "context": r.context,
                "priority": r.priority,
                "created_at": r.created_at.isoformat()
            }
            for r in items
        ]

    async def record_response(
        self,
        decision_id: str,
        approved: bool,
        comment: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record user response for an approval request.

        Returns:
            True if the request was found and updated
        """
        if decision_id not in self._pending:
            return False

        r = self._pending[decision_id]
        r.response = {
            "approved": approved,
            "comment": comment,
            "overrides": overrides or {},
            "responded_at": datetime.now(timezone.utc).isoformat()
        }
        self._history.append({
            "id": r.id,
            "source_agent": r.source_agent,
            "request_type": r.request_type,
            "approved": approved
        })
        return True

    def get_preference_patterns(self) -> Dict[str, Any]:
        """Simple aggregate of approval history for future learning."""
        if not self._history:
            return {}
        approved = sum(1 for h in self._history if h.get("approved"))
        by_type = {}
        for h in self._history:
            t = h.get("request_type", "unknown")
            by_type[t] = by_type.get(t, {"approved": 0, "total": 0})
            by_type[t]["total"] += 1
            if h.get("approved"):
                by_type[t]["approved"] += 1
        return {
            "total_requests": len(self._history),
            "approval_rate": approved / len(self._history) if self._history else 0,
            "by_type": by_type
        }
