"""Observability Manager (8.11) - Health reports, alerts, escalations"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from src.memory import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Single alert for escalation"""
    severity: str  # "low", "medium", "high", "critical"
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ObservabilityManager:
    """
    Monitors canon/outline health: continuity violations, conflicts,
    unresolved threads, tone drift. Aggregates and escalates when needed.
    """

    def __init__(
        self,
        graph_store: Optional[GraphStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.graph_store = graph_store
        self.config = config or {}

    async def report_health(
        self,
        outline: Optional[Dict[str, Any]] = None,
        refinements: Optional[Dict[str, Any]] = None,
        novel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Produce a health report from current outline and validation refinements.

        Args:
            outline: Outline dict (scenes, relationships)
            refinements: Output from Phase 4 (theme_analysis, timeline_validation, etc.)
            novel_id: Optional novel ID

        Returns:
            Dict with health summary, violations, alerts, escalation flags
        """
        report = {
            "novel_id": novel_id,
            "healthy": True,
            "continuity_violations": [],
            "canon_conflicts": [],
            "unresolved_threads": [],
            "timeline_violations": [],
            "thematic_issues": [],
            "pacing_issues": [],
            "alerts": [],
            "escalation_required": False
        }

        if refinements:
            # Timeline
            timeline = refinements.get("timeline_validation", {})
            violations = timeline.get("violations", [])
            if violations:
                report["timeline_violations"] = violations
                report["healthy"] = False
                report["alerts"].append({
                    "severity": "high" if len(violations) > 2 else "medium",
                    "code": "timeline_violations",
                    "message": f"{len(violations)} timeline violation(s)"
                })

            # Theme
            theme = refinements.get("theme_analysis", {})
            inconsistencies = theme.get("thematic_inconsistencies", [])
            if inconsistencies:
                report["thematic_issues"] = inconsistencies
                report["healthy"] = False
                report["alerts"].append({
                    "severity": "medium",
                    "code": "thematic_inconsistencies",
                    "message": f"{len(inconsistencies)} thematic inconsistency(ies)"
                })

            # Foreshadowing
            foreshadowing = refinements.get("foreshadowing_analysis", {})
            unresolved = foreshadowing.get("unresolved_promises", [])
            if unresolved:
                report["unresolved_threads"] = unresolved
                report["alerts"].append({
                    "severity": "low",
                    "code": "unresolved_promises",
                    "message": f"{len(unresolved)} unresolved promise(s)"
                })

            # Pacing
            pacing = refinements.get("pacing_analysis", {})
            if pacing.get("monotony_flags") or pacing.get("rushed_sequences"):
                report["pacing_issues"] = {
                    "monotony": pacing.get("monotony_flags", []),
                    "rushed": pacing.get("rushed_sequences", [])
                }
                report["alerts"].append({
                    "severity": "low",
                    "code": "pacing_issues",
                    "message": "Pacing issues detected"
                })

        # Escalation if any high/critical
        for a in report["alerts"]:
            if a.get("severity") in ("high", "critical"):
                report["escalation_required"] = True
                break

        return report

    async def check_escalation(
        self,
        report: Dict[str, Any]
    ) -> List[Alert]:
        """
        Convert health report into list of Alert objects for escalation path.

        Args:
            report: Output from report_health

        Returns:
            List of Alert instances that warrant escalation
        """
        alerts = []
        for a in report.get("alerts", []):
            severity = a.get("severity", "low")
            if severity in ("high", "critical"):
                alerts.append(Alert(
                    severity=severity,
                    code=a.get("code", "unknown"),
                    message=a.get("message", ""),
                    details=a
                ))
        return alerts
