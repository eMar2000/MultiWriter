"""Worldbuilding & Continuity Agent"""

from typing import Dict, Any
from pathlib import Path

from .base import BaseAgent
from src.models import WorldBuilding


class WorldbuildingAgent(BaseAgent):
    """Agent responsible for world-building and continuity"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="worldbuilding", *args, **kwargs)

        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "worldbuilding.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are a Worldbuilding & Continuity Agent, specializing in creating internally consistent, believable worlds.
Your role is to develop world rules, locations, timelines, and systems that feel real and maintain consistency throughout the story."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute world-building generation"""
        # Get context from previous agents
        theme_data = context.get("theme")
        plot_structure = context.get("plot_structure")
        characters = context.get("characters", [])
        novel_input = context.get("novel_input")

        if not novel_input:
            raise ValueError("Novel input required in context")

        # Build user prompt
        user_prompt = self._build_user_prompt(novel_input, theme_data, plot_structure, characters)

        # Generate world-building using LLM
        world_data = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_format="json",
            temperature=0.7,
            max_tokens=4000
        )

        # Ensure current_period is set
        if "current_period" not in world_data:
            world_data["current_period"] = "Present day"

        # Create WorldBuilding object
        try:
            world = WorldBuilding(**world_data)
        except Exception as e:
            # If validation fails, create with minimal required fields
            world_data.setdefault("rules", [])
            world_data.setdefault("magic_systems", [])
            world_data.setdefault("locations", [])
            world_data.setdefault("timeline", [])
            world_data.setdefault("cultures", {})
            world_data.setdefault("political_systems", {})
            world_data.setdefault("economic_systems", {})
            world_data.setdefault("consistency_constraints", [])
            world = WorldBuilding(**world_data)

        # Save to memory
        await self.write_to_memory(
            "world-rules",
            {
                "id": f"{self.novel_id}_world",
                "novel_id": self.novel_id,
                "world": world.model_dump()
            }
        )

        # Update novel outline
        await self.update_novel_outline({
            "world_rules": world.model_dump(),
            "status": "world_defined"
        })

        return {
            "agent": self.name,
            "output": {
                "world": world.model_dump(),
            },
            "status": "success"
        }

    def _build_user_prompt(
        self,
        novel_input: Dict[str, Any],
        theme_data: Dict[str, Any] = None,
        plot_structure: Dict[str, Any] = None,
        characters: List[Dict[str, Any]] = None
    ) -> str:
        """Build user prompt from context"""
        prompt_parts = [
            f"Novel Premise: {novel_input.get('premise', 'Not provided')}",
            f"Genre: {novel_input.get('genre', 'Not specified')}",
        ]

        if theme_data:
            prompt_parts.append(f"Theme Question: {theme_data.get('theme_question', 'Not provided')}")

        if plot_structure:
            prompt_parts.append(
                f"Plot Structure: {plot_structure.get('structure_type', 'Not specified')} "
                f"with {len(plot_structure.get('beats', []))} beats"
            )

        if characters:
            prompt_parts.append(f"Characters: {len(characters)} characters defined")
            # List character names/roles
            char_summary = ", ".join([
                f"{char.get('name', 'Unknown')} ({char.get('role', 'unknown')})"
                for char in characters[:5]  # Limit to first 5
            ])
            prompt_parts.append(f"Main Characters: {char_summary}")

        if novel_input.get("key_elements"):
            prompt_parts.append(f"Key World Elements: {', '.join(novel_input['key_elements'])}")

        prompt_parts.append(
            "\nPlease create comprehensive world-building with rules, locations, "
            "timeline, and systems for this novel. Ensure internal consistency "
            "and that the world supports the story and theme."
        )

        return "\n".join(prompt_parts)
