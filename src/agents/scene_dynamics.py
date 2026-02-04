"""Scene Dynamics Agent"""

from typing import Dict, Any, List
from pathlib import Path
import uuid

from .base import BaseAgent
from src.models import SceneOutline, SceneType


class SceneDynamicsAgent(BaseAgent):
    """Agent responsible for converting plot beats into scene outlines"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="scene_dynamics", *args, **kwargs)

        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "scene_dynamics.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are a Scene Dynamics Agent, specializing in converting plot beats into specific scene outlines.
Your role is to break down plot beats into actionable scenes with clear goals, conflicts, and outcomes that drive the story forward."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scene outline generation"""
        # Get context from previous agents
        theme_data = context.get("theme")
        plot_structure = context.get("plot_structure")
        arc = context.get("arc")  # For document-driven workflow
        entity_registry = context.get("entity_registry")
        characters = context.get("characters", [])
        world = context.get("world")
        novel_input = context.get("novel_input")

        # Support both workflows: plot_structure (interactive) or arc (document-driven)
        if not novel_input:
            raise ValueError("Novel input required in context")

        if not plot_structure and not arc:
            raise ValueError("Either plot_structure or arc required in context")

        # Build user prompt - support both plot_structure and arc workflows
        user_prompt = self._build_user_prompt(
            novel_input, theme_data, plot_structure, characters, world, arc, entity_registry
        )

        # Generate scene outlines using LLM
        scene_data = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_format="json",
            temperature=0.7,
            max_tokens=6000  # Scenes can be large
        )

        # Process scenes
        scenes_list = scene_data.get("scenes", [])
        scene_sequences = scene_data.get("scene_sequence", [])

        # Validate and create SceneOutline objects
        validated_scenes = []
        for scene_data_item in scenes_list:
            # Ensure scene has an ID
            if "scene_id" not in scene_data_item:
                scene_data_item["scene_id"] = str(uuid.uuid4())

            # Normalize scene_type (LLM may return compound types like "action/reaction")
            scene_type_str = scene_data_item.get("scene_type", "action")
            if scene_type_str:
                # Take the first part if compound (e.g., "action/reaction" -> "action")
                scene_type_str = scene_type_str.split("/")[0].strip().lower()
                try:
                    scene_type = SceneType(scene_type_str)
                    scene_data_item["scene_type"] = scene_type.value
                except ValueError:
                    scene_data_item["scene_type"] = SceneType.ACTION.value

            # Normalize sequel_type if present
            sequel_type_str = scene_data_item.get("sequel_type")
            if sequel_type_str and sequel_type_str.strip():
                sequel_type_str = sequel_type_str.split("/")[0].strip().lower()
                from src.models import SequelType
                try:
                    scene_data_item["sequel_type"] = SequelType(sequel_type_str).value
                except ValueError:
                    scene_data_item["sequel_type"] = None
            else:
                # Remove empty string or None - Pydantic will use default
                scene_data_item.pop("sequel_type", None)

            try:
                scene = SceneOutline(**scene_data_item)
                validated_scenes.append(scene)
            except Exception as e:
                # Log error but continue with other scenes
                print(f"Warning: Failed to validate scene {scene_data_item.get('scene_number', 'unknown')}: {str(e)}")
                continue

        # Sort scenes by scene_number
        validated_scenes.sort(key=lambda s: s.scene_number)

        # Save scenes to memory
        for scene in validated_scenes:
            await self.write_to_memory(
                "scenes",
                {
                    "id": f"{self.novel_id}_scene_{scene.scene_number}",
                    "novel_id": self.novel_id,
                    "scene": scene.model_dump()
                }
            )

        # Update novel outline
        await self.update_novel_outline({
            "scenes": [scene.model_dump() for scene in validated_scenes],
            "scene_sequences": scene_sequences,
            "status": "scenes_defined"
        })

        return {
            "agent": self.name,
            "output": {
                "scenes": [scene.model_dump() for scene in validated_scenes],
                "scene_sequences": scene_sequences,
            },
            "status": "success"
        }

    def _build_user_prompt(
        self,
        novel_input: Dict[str, Any],
        theme_data: Dict[str, Any] = None,
        plot_structure: Dict[str, Any] = None,
        characters: List[Dict[str, Any]] = None,
        world: Dict[str, Any] = None,
        arc: Dict[str, Any] = None,
        entity_registry = None
    ) -> str:
        """Build user prompt from context"""
        prompt_parts = [
            f"Novel Premise: {novel_input.get('premise', 'Not provided')}",
            f"Genre: {novel_input.get('genre', 'Not specified')}",
        ]

        if theme_data:
            prompt_parts.append(f"Theme Question: {theme_data.get('theme_question', 'Not provided')}")

        # Support arc-based workflow (document-driven)
        if arc:
            prompt_parts.append(f"\n=== ARC: {arc.get('name', 'Unknown')} ===")
            prompt_parts.append(f"Type: {arc.get('type', 'unknown')}")
            prompt_parts.append(f"Description: {arc.get('description', 'No description')}")

            # Include character IDs if available
            char_ids = arc.get('character_ids', [])
            if char_ids and entity_registry:
                char_names = []
                for char_id in char_ids[:5]:  # Limit to 5
                    entity = entity_registry.get(char_id)
                    if entity:
                        char_names.append(entity.name)
                if char_names:
                    prompt_parts.append(f"Characters: {', '.join(char_names)}")

            # Include location IDs if available
            loc_ids = arc.get('location_ids', [])
            if loc_ids and entity_registry:
                loc_names = []
                for loc_id in loc_ids[:3]:  # Limit to 3
                    entity = entity_registry.get(loc_id)
                    if entity:
                        loc_names.append(entity.name)
                if loc_names:
                    prompt_parts.append(f"Locations: {', '.join(loc_names)}")

            prompt_parts.append(
                "\nPlease create detailed scene outlines for this arc. Each scene should have: "
                "goal, conflict, outcome, stakes, characters present, and location. "
                "Create 3-5 scenes that progress this arc from beginning to end."
            )

        # Support plot_structure workflow (interactive/legacy)
        elif plot_structure:
            beats = plot_structure.get("beats", [])
            prompt_parts.append(
                f"Plot Structure: {plot_structure.get('structure_type', 'Not specified')} "
                f"with {len(beats)} beats"
            )
            # Include beat summary
            if beats:
                prompt_parts.append("\nPlot Beats:")
                for beat in beats[:10]:  # Limit to first 10 beats
                    prompt_parts.append(
                        f"  Beat {beat.get('beat_number', '?')}: {beat.get('beat_name', 'Unknown')} - "
                        f"{beat.get('description', 'No description')[:100]}"
                    )
            prompt_parts.append(
                "\nPlease convert the plot beats into detailed scene outlines with goals, "
                "conflicts, outcomes, and character interactions. Each scene should advance "
                "plot, character, or theme (ideally all three)."
            )

        if characters:
            prompt_parts.append(f"\nCharacters: {len(characters)} characters")
            char_summary = ", ".join([
                f"{char.get('name', 'Unknown')} ({char.get('role', 'unknown')})"
                for char in characters[:5]
            ])
            prompt_parts.append(f"Main Characters: {char_summary}")

        if world:
            prompt_parts.append(f"\nWorld: {len(world.get('rules', []))} rules, "
                              f"{len(world.get('locations', []))} locations")

        return "\n".join(prompt_parts)
