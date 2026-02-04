"""Orchestration logic for multi-agent workflows"""

from .document_orchestrator import IterativeDocumentOrchestrator
from .central_manager import CentralManager, AgentTask, AgentStatus
from .planning_loop import PlanningLoop, QualityGate
from .observability_manager import ObservabilityManager, Alert
from .user_interaction_manager import UserInteractionManager, ApprovalRequest
from .version_manager import VersionManager

# Alias for compatibility
DocumentOrchestrator = IterativeDocumentOrchestrator

__all__ = [
    "DocumentOrchestrator",
    "IterativeDocumentOrchestrator",
    "CentralManager",
    "AgentTask",
    "AgentStatus",
    "PlanningLoop",
    "QualityGate",
    "ObservabilityManager",
    "Alert",
    "UserInteractionManager",
    "ApprovalRequest",
    "VersionManager",
]
