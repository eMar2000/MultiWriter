"""Character Psychodynamics Agent"""

from typing import Dict, Any, List
from pathlib import Path
import uuid

from .base import BaseAgent
from src.models import CharacterProfile


class CharacterAgent(BaseAgent):
    """Agent responsible for character profiles and arcs"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="character", *args, **kwargs)

        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "character.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are a Character Psychodynamics Agent, specializing in creating deep, authentic characters with clear arcs.
Your role is to develop character profiles that reflect real human psychology, with clear wants, needs, flaws, and growth trajectories."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute character profile generation"""
        # Get context from previous agents
        theme_data = context.get("theme")
        plot_structure = context.get("plot_structure")
        novel_input = context.get("novel_input")

        if not novel_input:
            raise ValueError("Novel input required in context")

        # Build user prompt
        user_prompt = self._build_user_prompt(novel_input, theme_data, plot_structure)

        # Generate character profiles using LLM
        character_data = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_format="json",
            temperature=0.7,
            max_tokens=4000
        )

        # Process characters
        characters_list = character_data.get("characters", [])
        relationships = character_data.get("relationships", {})

        # Validate and create CharacterProfile objects
        validated_characters = []
        for char_data in characters_list:
            # Ensure character has an ID
            if "id" not in char_data:
                char_data["id"] = str(uuid.uuid4())

            try:
                character = CharacterProfile(**char_data)
                validated_characters.append(character)
            except Exception as e:
                # Log error but continue with other characters
                print(f"Warning: Failed to validate character {char_data.get('name', 'unknown')}: {str(e)}")
                continue

        # Save characters to memory
        for character in validated_characters:
            await self.write_to_memory(
                "characters",
                {
                    "id": f"{self.novel_id}_{character.id}",
                    "novel_id": self.novel_id,
                    "character": character.model_dump()
                }
            )

        # Update novel outline
        await self.update_novel_outline({
            "characters": [char.model_dump() for char in validated_characters],
            "relationships": relationships,
            "status": "characters_defined"
        })

        return {
            "agent": self.name,
            "output": {
                "characters": [char.model_dump() for char in validated_characters],
                "relationships": relationships,
            },
            "status": "success"
        }

    def _build_user_prompt(
        self,
        novel_input: Dict[str, Any],
        theme_data: Dict[str, Any] = None,
        plot_structure: Dict[str, Any] = None
    ) -> str:
        """Build user prompt from context"""
        prompt_parts = [
            f"Novel Premise: {novel_input.get('premise', 'Not provided')}",
            f"Genre: {novel_input.get('genre', 'Not specified')}",
        ]

        if theme_data:
            prompt_parts.append(f"Theme Question: {theme_data.get('theme_question', 'Not provided')}")
            prompt_parts.append(f"Moral Argument: {theme_data.get('moral_argument', 'Not provided')}")

        if novel_input.get("character_concepts"):
            prompt_parts.append(
                f"Character Concepts: {', '.join(novel_input['character_concepts'])}"
            )

        if plot_structure:
            prompt_parts.append(
                f"Plot Structure: {plot_structure.get('structure_type', 'Not specified')} "
                f"with {len(plot_structure.get('beats', []))} beats"
            )

        prompt_parts.append(
            "\nPlease create complete character profiles with arcs, motivations, "
            "fears, beliefs, and relationships for this novel. "
            "Ensure characters serve the story and theme."
        )

        return "\n".join(prompt_parts)
