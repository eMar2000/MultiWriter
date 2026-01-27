"""Orchestration logic for multi-agent workflows"""

from .orchestrator_v2 import DocumentOrchestrator

# Old orchestrator deprecated - kept for backward compatibility with tests only
from .orchestrator import Orchestrator  # noqa: F401
from .workflow import Workflow, AgentTask, AgentStatus  # noqa: F401

__all__ = [
    "DocumentOrchestrator",
    # Deprecated - use DocumentOrchestrator instead
    "Orchestrator",
    "Workflow",
    "AgentTask",
    "AgentStatus",
]
