"""Main orchestrator for multi-agent workflows"""

import asyncio
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from .workflow import Workflow, AgentTask, AgentStatus
from src.agents import (
    ThemePremiseAgent,
    NarrativeArchitectAgent,
    CharacterAgent,
    WorldbuildingAgent,
    SceneDynamicsAgent,
)
from src.llm import LLMProvider
from src.memory import StructuredState, VectorStore
from src.models import NovelInput, NovelOutline


class Orchestrator:
    """Orchestrates multi-agent novel outline generation"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        structured_state: StructuredState,
        vector_store: Optional[VectorStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize orchestrator

        Args:
            llm_provider: LLM provider instance
            structured_state: Structured state storage
            vector_store: Vector store for embeddings
            config: Configuration dictionary
        """
        self.llm_provider = llm_provider
        self.structured_state = structured_state
        self.vector_store = vector_store
        self.config = config or {}
        self.novel_id: Optional[str] = None

    def _create_workflow(self) -> Workflow:
        """Create the agent workflow with dependencies"""
        workflow = Workflow()

        # Define workflow: Theme → Structure → (World, Character) → Scenes
        workflow.add_task(
            agent_id="theme_premise",
            agent_name="ThemePremiseAgent",
            dependencies=[],
            required=True
        )

        workflow.add_task(
            agent_id="narrative_architect",
            agent_name="NarrativeArchitectAgent",
            dependencies=["theme_premise"],
            required=True
        )

        # World and Character can run in parallel
        workflow.add_task(
            agent_id="worldbuilding",
            agent_name="WorldbuildingAgent",
            dependencies=["theme_premise", "narrative_architect"],
            required=True
        )

        workflow.add_task(
            agent_id="character",
            agent_name="CharacterAgent",
            dependencies=["theme_premise", "narrative_architect"],
            required=True
        )

        workflow.add_task(
            agent_id="scene_dynamics",
            agent_name="SceneDynamicsAgent",
            dependencies=["theme_premise", "narrative_architect", "worldbuilding", "character"],
            required=True
        )

        return workflow

    def _create_agent(self, agent_name: str) -> Any:
        """Create an agent instance"""
        agent_classes = {
            "ThemePremiseAgent": ThemePremiseAgent,
            "NarrativeArchitectAgent": NarrativeArchitectAgent,
            "CharacterAgent": CharacterAgent,
            "WorldbuildingAgent": WorldbuildingAgent,
            "SceneDynamicsAgent": SceneDynamicsAgent,
        }

        agent_class = agent_classes.get(agent_name)
        if not agent_class:
            raise ValueError(f"Unknown agent: {agent_name}")

        return agent_class(
            llm_provider=self.llm_provider,
            structured_state=self.structured_state,
            vector_store=self.vector_store,
            novel_id=self.novel_id
        )

    async def generate_outline(
        self,
        novel_input: NovelInput,
        novel_id: Optional[str] = None
    ) -> NovelOutline:
        """
        Generate a complete novel outline

        Args:
            novel_input: User input for the novel
            novel_id: Optional novel ID (generated if not provided)

        Returns:
            Complete novel outline
        """
        # Set novel ID
        self.novel_id = novel_id or str(uuid.uuid4())

        # Create initial novel outline
        outline = NovelOutline(
            id=self.novel_id,
            input=novel_input,
            status="in_progress"
        )

        # Save initial outline to memory
        await self.structured_state.write(
            "novel-outlines",
            {
                "id": self.novel_id,
                **outline.model_dump()
            }
        )

        # Create workflow
        workflow = self._create_workflow()

        # Execution context (shared between agents)
        context: Dict[str, Any] = {
            "novel_input": novel_input.model_dump(),
            "novel_id": self.novel_id,
        }

        # Execute workflow
        try:
            await self._execute_workflow(workflow, context)
        except Exception as e:
            # Update outline with error
            outline.status = "failed"
            await self.structured_state.update(
                "novel-outlines",
                {"id": self.novel_id},
                {"status": "failed", "error": str(e)}
            )
            raise

        # Retrieve final outline from memory
        outline_data = await self.structured_state.read(
            "novel-outlines",
            {"id": self.novel_id}
        )

        if not outline_data:
            raise RuntimeError("Failed to retrieve outline from memory")

        # Update outline
        outline = NovelOutline(**outline_data)
        outline.status = "completed"
        outline.updated_at = datetime.utcnow()

        # Save final outline
        await self.structured_state.write(
            "novel-outlines",
            outline.model_dump()
        )

        return outline

    async def _execute_workflow(
        self,
        workflow: Workflow,
        context: Dict[str, Any]
    ):
        """Execute the workflow"""
        # Get execution order
        execution_order = workflow.get_execution_order()

        # Execute tasks in order (some can run in parallel)
        completed_tasks = set()

        for agent_id in execution_order:
            task = workflow.get_task(agent_id)
            if not task:
                continue

            # Wait for dependencies if not already completed
            if not task.is_ready(completed_tasks):
                # This shouldn't happen if execution_order is correct
                raise RuntimeError(f"Task {agent_id} is not ready")

            # Mark as running
            task.status = AgentStatus.RUNNING

            try:
                # Create agent
                agent = self._create_agent(task.agent_name)

                # Execute agent
                result = await agent.execute(context)

                # Mark as completed
                task.mark_completed(result)
                completed_tasks.add(agent_id)

                # Update context with agent output
                if "output" in result:
                    # Add output to context with appropriate key
                    output_key = agent_id  # Use agent_id as key
                    context[output_key] = result["output"]

                    # Also add with specific keys for convenience
                    if agent_id == "theme_premise":
                        context["theme"] = result["output"].get("theme", {})
                    elif agent_id == "narrative_architect":
                        context["plot_structure"] = result["output"].get("plot_structure", {})
                    elif agent_id == "character":
                        context["characters"] = result["output"].get("characters", [])
                        context["relationships"] = result["output"].get("relationships", {})
                    elif agent_id == "worldbuilding":
                        context["world"] = result["output"].get("world", {})
                    elif agent_id == "scene_dynamics":
                        context["scenes"] = result["output"].get("scenes", [])
                        context["scene_sequences"] = result["output"].get("scene_sequences", [])

            except Exception as e:
                # Mark as failed
                task.mark_failed(e)

                # If required, re-raise
                if task.required:
                    raise RuntimeError(f"Required task {agent_id} failed: {str(e)}") from e

                # Otherwise, continue
                completed_tasks.add(agent_id)

    async def validate_outline(self, outline: NovelOutline) -> Dict[str, Any]:
        """Validate a generated outline"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # Check required fields
        if not outline.theme:
            validation_results["valid"] = False
            validation_results["errors"].append("Theme is missing")

        if not outline.plot_structure:
            validation_results["valid"] = False
            validation_results["errors"].append("Plot structure is missing")

        if not outline.characters or len(outline.characters) == 0:
            validation_results["warnings"].append("No characters defined")

        if not outline.world_rules:
            validation_results["warnings"].append("No world rules defined")

        if not outline.scenes or len(outline.scenes) == 0:
            validation_results["valid"] = False
            validation_results["errors"].append("No scenes defined")

        # Check plot structure has beats
        if outline.plot_structure and not outline.plot_structure.beats:
            validation_results["errors"].append("Plot structure has no beats")

        return validation_results
