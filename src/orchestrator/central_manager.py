"""Central Manager - Iterative orchestrator for agent coordination"""

import logging
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from datetime import datetime

from src.llm import LLMProvider
from src.memory import StructuredState, VectorStore, GraphStore
from src.validation import ContinuityValidationService
from src.models import NovelOutline, EntityRegistry, NovelInput

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Status of an agent execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTask:
    """Represents a task for an agent"""

    def __init__(
        self,
        agent_name: str,
        agent_class: type,
        context: Dict[str, Any],
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
        max_iterations: int = 3,
        validation_fn: Optional[Callable] = None
    ):
        """
        Initialize agent task

        Args:
            agent_name: Name of the agent
            agent_class: Agent class to instantiate
            context: Context data for the agent
            dependencies: List of agent names that must complete first
            priority: Task priority (higher = more important)
            max_iterations: Maximum number of revision iterations
            validation_fn: Optional validation function
        """
        self.agent_name = agent_name
        self.agent_class = agent_class
        self.context = context
        self.dependencies = dependencies or []
        self.priority = priority
        self.max_iterations = max_iterations
        self.validation_fn = validation_fn
        self.status = AgentStatus.PENDING
        self.result: Optional[Dict[str, Any]] = None
        self.errors: List[str] = []
        self.iteration_count = 0


class CentralManager:
    """Central orchestrator for iterative agent coordination"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        structured_state: StructuredState,
        vector_store: Optional[VectorStore] = None,
        graph_store: Optional[GraphStore] = None,
        validation_service: Optional[ContinuityValidationService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Central Manager

        Args:
            llm_provider: LLM provider for agents
            structured_state: Structured state storage
            vector_store: Optional vector store for RAG
            graph_store: Optional graph store for canon
            validation_service: Optional validation service
            config: Configuration dictionary
        """
        self.llm_provider = llm_provider
        self.structured_state = structured_state
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.validation_service = validation_service
        self.config = config or {}
        self.novel_id: Optional[str] = None

        # Task tracking
        self.tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}
        self.failed_tasks: Dict[str, AgentTask] = {}

    async def execute_plan(
        self,
        tasks: List[AgentTask],
        novel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a plan of agent tasks iteratively

        Args:
            tasks: List of agent tasks to execute
            novel_id: Optional novel ID

        Returns:
            Results dictionary with all task outputs
        """
        self.novel_id = novel_id
        self.tasks = {task.agent_name: task for task in tasks}
        self.completed_tasks = {}
        self.failed_tasks = {}

        logger.info(f"[Central Manager] Executing plan with {len(tasks)} tasks")

        # Execute tasks in dependency order with iterations
        iteration = 0
        max_global_iterations = self.config.get("max_global_iterations", 5)

        while iteration < max_global_iterations:
            iteration += 1

            # Log task status
            pending_count = sum(1 for t in self.tasks.values() if t.status == AgentStatus.PENDING)
            running_count = sum(1 for t in self.tasks.values() if t.status == AgentStatus.RUNNING)
            completed_count = sum(1 for t in self.tasks.values() if t.status == AgentStatus.COMPLETED)
            failed_count = sum(1 for t in self.tasks.values() if t.status == AgentStatus.FAILED)

            logger.info(f"[Iteration {iteration}] Status: {completed_count} completed, {pending_count} pending, {failed_count} failed")

            # Get ready tasks (dependencies satisfied)
            ready_tasks = self._get_ready_tasks()
            logger.info(f"[Iteration {iteration}] Found {len(ready_tasks)} ready tasks: {[t.agent_name for t in ready_tasks]}")

            if not ready_tasks:
                # Check if we're done or stuck
                if all(t.status == AgentStatus.COMPLETED for t in self.tasks.values()):
                    logger.info("[Central Manager] All tasks completed")
                    break
                elif all(t.status in (AgentStatus.COMPLETED, AgentStatus.FAILED) for t in self.tasks.values()):
                    logger.warning("[Central Manager] Some tasks failed, stopping")
                    # Log which tasks failed
                    for task_name, task in self.failed_tasks.items():
                        logger.error(f"  Failed task: {task_name} - {task.errors}")
                    break
                else:
                    # Debug: show what's blocking
                    for task_name, task in self.tasks.items():
                        if task.status == AgentStatus.PENDING:
                            logger.warning(f"  Pending task: {task_name} - dependencies: {task.dependencies}")
                    logger.warning("[Central Manager] No ready tasks but not all completed - possible circular dependency")
                    break

            # Execute ready tasks
            for task in ready_tasks:
                if task.status == AgentStatus.COMPLETED:
                    continue

                await self._execute_task(task, iteration)

            # Check if all tasks are done (don't break just because no revisions needed)
            if all(t.status == AgentStatus.COMPLETED for t in self.tasks.values()):
                logger.info("[Central Manager] All tasks completed")
                break

            # Check if we need another iteration for revisions
            needs_revision = self._check_needs_revision()
            if needs_revision:
                logger.info("[Central Manager] Revisions needed, continuing...")
                # Reset failed tasks for retry
                for task_name, task in list(self.tasks.items()):
                    if task.status == AgentStatus.FAILED and task.iteration_count < task.max_iterations:
                        task.status = AgentStatus.PENDING
                        task.errors = []
                        logger.info(f"  Resetting {task_name} for retry")

        # Collect results
        results = {}
        for task_name, task in self.completed_tasks.items():
            results[task_name] = task.result

        return {
            "results": results,
            "iteration_count": iteration,
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks)
        }

    def _get_ready_tasks(self) -> List[AgentTask]:
        """Get tasks that are ready to execute (dependencies satisfied)"""
        ready = []

        for task in self.tasks.values():
            if task.status == AgentStatus.COMPLETED:
                continue

            # Check dependencies (support wildcard matching)
            dependencies_met = True
            for dep_name in task.dependencies:
                if dep_name.endswith("*"):
                    # Wildcard match - check if any task matching pattern is completed
                    pattern = dep_name[:-1]  # Remove *
                    matching_completed = any(
                        completed_name.startswith(pattern)
                        for completed_name in self.completed_tasks.keys()
                    )
                    if not matching_completed:
                        dependencies_met = False
                        break
                else:
                    # Exact match
                    if dep_name not in self.completed_tasks:
                        dependencies_met = False
                        break

            if dependencies_met:
                ready.append(task)

        # Sort by priority (higher first)
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    async def _execute_task(self, task: AgentTask, iteration: int):
        """Execute a single agent task"""
        task.status = AgentStatus.RUNNING
        task.iteration_count += 1

        logger.info(f"  Executing {task.agent_name} (iteration {task.iteration_count})")
        logger.debug(f"    Task context keys: {list(task.context.keys())}")

        try:
            # Instantiate agent
            agent = task.agent_class(
                llm_provider=self.llm_provider,
                structured_state=self.structured_state,
                vector_store=self.vector_store,
                graph_store=self.graph_store,
                novel_id=self.novel_id
            )

            # Execute agent
            logger.debug(f"    Calling {task.agent_name}.execute() with context keys: {list(task.context.keys())}")
            result = await agent.execute(task.context)
            logger.debug(f"    {task.agent_name} returned result with keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")

            # Validate entity IDs only for agents that output structured entity IDs (arcs/scenes)
            registry = task.context.get("entity_registry")
            if registry and (
                task.agent_name == "outline_architect" or task.agent_name.startswith("scene_expansion_")
            ):
                entity_validation = self._validate_entity_ids(result, registry)
                if not entity_validation.get("valid", True):
                    task.errors.append(entity_validation.get("message", "Entity ID validation failed"))
                    task.status = AgentStatus.FAILED
                    self.failed_tasks[task.agent_name] = task
                    logger.warning(f"  {task.agent_name} failed entity ID validation: {entity_validation.get('message')}")
                    return

            # Validate result if validation function provided
            if task.validation_fn:
                validation_result = task.validation_fn(result)
                if not validation_result.get("valid", True):
                    task.errors.append(validation_result.get("message", "Validation failed"))
                    task.status = AgentStatus.FAILED
                    self.failed_tasks[task.agent_name] = task
                    logger.warning(f"  {task.agent_name} failed validation: {validation_result.get('message')}")
                    return

            # Store result
            task.result = result
            task.status = AgentStatus.COMPLETED
            self.completed_tasks[task.agent_name] = task

            # Update context for dependent tasks
            self._update_dependent_contexts(task)

            logger.info(f"  {task.agent_name} completed successfully")

        except Exception as e:
            task.status = AgentStatus.FAILED
            task.errors.append(str(e))
            self.failed_tasks[task.agent_name] = task
            logger.error(f"  {task.agent_name} failed: {e}", exc_info=True)

    def _update_dependent_contexts(self, completed_task: AgentTask):
        """Update context for tasks that depend on the completed task"""
        logger.debug(f"  Updating dependent contexts for completed task: {completed_task.agent_name}")

        for task in self.tasks.values():
            # Check if this task depends on the completed task (with wildcard support)
            depends = False
            for dep_name in task.dependencies:
                if dep_name.endswith("*"):
                    # Wildcard match
                    pattern = dep_name[:-1]
                    if completed_task.agent_name.startswith(pattern):
                        depends = True
                        break
                elif dep_name == completed_task.agent_name:
                    # Exact match
                    depends = True
                    break

            if depends:
                logger.debug(f"    Updating context for dependent task: {task.agent_name}")
                # Merge completed task's output into dependent task's context
                if completed_task.result and "output" in completed_task.result:
                    output_data = completed_task.result["output"]
                    logger.debug(f"      Merging output keys: {list(output_data.keys()) if isinstance(output_data, dict) else 'not a dict'}")
                    task.context.update(output_data)
                    logger.debug(f"      Task {task.agent_name} context now has keys: {list(task.context.keys())}")

    def _validate_entity_ids(self, result: Dict[str, Any], registry: "EntityRegistry") -> Dict[str, Any]:
        """Validate that all entity IDs in result exist in registry"""
        import re

        valid_ids = registry.get_all_ids()
        referenced_ids = set()
        invalid_ids = set()

        # Extract entity IDs from result (look for common patterns)
        result_str = str(result)

        # Common ID patterns in results
        id_patterns = [
            r'character_ids?["\':\s\[]+([a-f0-9\-]{36})',
            r'location_ids?["\':\s\[]+([a-f0-9\-]{36})',
            r'scene_concept_ids?["\':\s\[]+([a-f0-9\-]{36})',
            r'pov_character["\':\s]+([a-f0-9\-]{36})',
            r'characters_present["\':\s\[]+([a-f0-9\-]{36})',
            r'entity_id["\':\s]+([a-f0-9\-]{36})',
            # Also check for placeholder patterns that should NOT be present
            r'(char_id\d+|loc_id\d+|character_id\d+|location_id\d+)',
        ]

        for pattern in id_patterns:
            matches = re.findall(pattern, result_str, re.IGNORECASE)
            for match in matches:
                # Check if it's a placeholder pattern (last pattern in list)
                if re.match(r'(char_id|loc_id|character_id|location_id)', match, re.IGNORECASE):
                    invalid_ids.add(match)
                else:
                    referenced_ids.add(match)

        # Check if referenced IDs exist in registry
        for ref_id in referenced_ids:
            if ref_id not in valid_ids:
                invalid_ids.add(ref_id)

        if invalid_ids:
            return {
                "valid": False,
                "message": f"Invalid or placeholder entity IDs found: {', '.join(list(invalid_ids)[:5])}. Must use actual entity IDs from registry.",
                "invalid_ids": list(invalid_ids)
            }

        return {"valid": True}

    def _check_needs_revision(self) -> bool:
        """Check if any tasks need revision"""
        # Check for failed tasks that can be retried
        for task in self.tasks.values():
            if task.status == AgentStatus.FAILED:
                if task.iteration_count < task.max_iterations:
                    return True

        # Check for validation issues that require revision
        # This would be expanded with actual validation logic
        return False

    def get_task_status(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self.tasks.get(task_name)
        if not task:
            return None

        return {
            "name": task.agent_name,
            "status": task.status.value,
            "iteration_count": task.iteration_count,
            "errors": task.errors,
            "has_result": task.result is not None
        }

    def get_plan_status(self) -> Dict[str, Any]:
        """Get overall plan status"""
        return {
            "total_tasks": len(self.tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "pending": len([t for t in self.tasks.values() if t.status == AgentStatus.PENDING]),
            "running": len([t for t in self.tasks.values() if t.status == AgentStatus.RUNNING])
        }
