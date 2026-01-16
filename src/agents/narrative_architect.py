"""Narrative Architect Agent"""

from typing import Dict, Any
from pathlib import Path

from .base import BaseAgent
from src.models import PlotStructure, StoryStructure


class NarrativeArchitectAgent(BaseAgent):
    """Agent responsible for story structure and plot beats"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="narrative_architect", *args, **kwargs)

        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "narrative_architect.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are a Narrative Architect Agent, specializing in story structure and plot development.
Your role is to design the overall narrative structure, create plot beats, and define tension escalation."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute narrative structure generation"""
        # Get context from previous agents
        theme_data = context.get("theme")
        novel_input = context.get("novel_input")

        if not novel_input:
            raise ValueError("Novel input required in context")

        # Build user prompt
        user_prompt = self._build_user_prompt(novel_input, theme_data)

        # Generate plot structure using LLM
        plot_data = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_format="json",
            temperature=0.7,
            max_tokens=4000
        )

        # Validate structure type
        structure_type_str = plot_data.get("structure_type", "three_act")
        try:
            structure_type = StoryStructure(structure_type_str)
        except ValueError:
            # Default to three_act if invalid
            structure_type = StoryStructure.THREE_ACT
            plot_data["structure_type"] = structure_type.value

        # Create PlotStructure object
        plot_structure = PlotStructure(**plot_data)

        # Save to memory
        await self.update_novel_outline({
            "plot_structure": plot_structure.model_dump(),
            "status": "structure_defined"
        })

        # Also save individual beats for easier querying
        for beat in plot_structure.beats:
            await self.write_to_memory(
                "plot-beats",
                {
                    "id": f"{self.novel_id}_beat_{beat.beat_number}",
                    "novel_id": self.novel_id,
                    "beat_number": beat.beat_number,
                    "beat": beat.model_dump()
                }
            )

        return {
            "agent": self.name,
            "output": {
                "plot_structure": plot_structure.model_dump(),
            },
            "status": "success"
        }

    def _build_user_prompt(self, novel_input: Dict[str, Any], theme_data: Dict[str, Any] = None) -> str:
        """Build user prompt from context"""
        prompt_parts = [
            f"Novel Premise: {novel_input.get('premise', 'Not provided')}",
            f"Genre: {novel_input.get('genre', 'Not specified')}",
        ]

        if theme_data:
            prompt_parts.append(f"Theme Question: {theme_data.get('theme_question', 'Not provided')}")
            prompt_parts.append(f"Moral Argument: {theme_data.get('moral_argument', 'Not provided')}")

        if novel_input.get("target_length"):
            prompt_parts.append(f"Target Length: {novel_input['target_length']} words")

        prompt_parts.append(
            "\nPlease design a complete narrative structure with plot beats, "
            "tension escalation, and key reversals for this novel. "
            "Select the most appropriate structure type for the genre and theme."
        )

        return "\n".join(prompt_parts)
