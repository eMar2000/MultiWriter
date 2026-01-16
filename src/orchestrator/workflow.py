"""Workflow dependency management"""

from typing import Dict, List, Set, Any, Optional
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTask:
    """Represents an agent task in the workflow"""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        dependencies: Optional[List[str]] = None,
        required: bool = True
    ):
        """
        Initialize agent task

        Args:
            agent_id: Unique identifier for this agent task
            agent_name: Name of the agent class
            dependencies: List of agent_ids this task depends on
            required: Whether this task is required (vs optional)
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.dependencies = dependencies or []
        self.required = required
        self.status = AgentStatus.PENDING
        self.output: Optional[Dict[str, Any]] = None
        self.error: Optional[Exception] = None

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are completed"""
        if self.status != AgentStatus.PENDING:
            return False
        return all(dep in completed_tasks for dep in self.dependencies)

    def mark_completed(self, output: Dict[str, Any]):
        """Mark task as completed with output"""
        self.status = AgentStatus.COMPLETED
        self.output = output

    def mark_failed(self, error: Exception):
        """Mark task as failed with error"""
        self.status = AgentStatus.FAILED
        self.error = error


class Workflow:
    """Manages workflow dependencies and execution order"""

    def __init__(self):
        """Initialize workflow"""
        self.tasks: Dict[str, AgentTask] = {}

    def add_task(
        self,
        agent_id: str,
        agent_name: str,
        dependencies: Optional[List[str]] = None,
        required: bool = True
    ):
        """Add a task to the workflow"""
        self.tasks[agent_id] = AgentTask(
            agent_id=agent_id,
            agent_name=agent_name,
            dependencies=dependencies or [],
            required=required
        )

    def get_ready_tasks(self) -> List[AgentTask]:
        """Get all tasks that are ready to execute"""
        completed_ids = {
            task.agent_id
            for task in self.tasks.values()
            if task.status == AgentStatus.COMPLETED
        }

        ready = [
            task
            for task in self.tasks.values()
            if task.is_ready(completed_ids) and task.status == AgentStatus.PENDING
        ]

        return ready

    def get_execution_order(self) -> List[str]:
        """Get the execution order of tasks (topological sort)"""
        # Simple topological sort
        completed = set()
        order = []

        while len(completed) < len(self.tasks):
            ready = [
                task.agent_id
                for task in self.tasks.values()
                if task.agent_id not in completed
                and all(dep in completed for dep in task.dependencies)
            ]

            if not ready:
                # Circular dependency or incomplete dependencies
                remaining = [
                    task.agent_id
                    for task in self.tasks.values()
                    if task.agent_id not in completed
                ]
                raise ValueError(f"Cannot resolve dependencies for tasks: {remaining}")

            # Add ready tasks (in order if multiple)
            order.extend(sorted(ready))
            completed.update(ready)

        return order

    def get_task(self, agent_id: str) -> Optional[AgentTask]:
        """Get a task by ID"""
        return self.tasks.get(agent_id)

    def get_all_outputs(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed task outputs"""
        return {
            task.agent_id: task.output
            for task in self.tasks.values()
            if task.status == AgentStatus.COMPLETED and task.output is not None
        }

    def is_complete(self) -> bool:
        """Check if all required tasks are completed"""
        return all(
            task.status in (AgentStatus.COMPLETED, AgentStatus.SKIPPED)
            or (task.status == AgentStatus.FAILED and not task.required)
            for task in self.tasks.values()
        )

    def has_failures(self) -> bool:
        """Check if any required tasks failed"""
        return any(
            task.status == AgentStatus.FAILED and task.required
            for task in self.tasks.values()
        )
