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

    def _build_entity_id_block(self, entity_registry, arc) -> str:
        """Build explicit entity ID block for scene generation"""
        from src.models import EntityType

        lines = ["## AVAILABLE ENTITY IDs (MUST USE THESE - DO NOT INVENT NEW IDs)\n"]

        # Get arc-specific entity IDs if available
        arc_char_ids = set(arc.get("character_ids", [])) if arc else set()
        arc_loc_ids = set(arc.get("location_ids", [])) if arc else set()

        # Characters - prioritize arc-specific ones
        chars = entity_registry.get_by_type(EntityType.CHARACTER)
        if chars:
            lines.append("### Characters (use these exact IDs in pov_character and characters_present):")
            arc_chars = [c for c in chars if c.id in arc_char_ids]
            other_chars = [c for c in chars if c.id not in arc_char_ids]

            for char in (arc_chars + other_chars)[:20]:
                marker = " [PRIMARY]" if char.id in arc_char_ids else ""
                lines.append(f"- {char.id}: \"{char.name}\"{marker}")

        # Locations - prioritize arc-specific ones
        locs = entity_registry.get_by_type(EntityType.LOCATION)
        if locs:
            lines.append("\n### Locations (use these exact IDs in location_id):")
            arc_locs = [l for l in locs if l.id in arc_loc_ids]
            other_locs = [l for l in locs if l.id not in arc_loc_ids]

            for loc in (arc_locs + other_locs)[:15]:
                marker = " [PRIMARY]" if loc.id in arc_loc_ids else ""
                lines.append(f"- {loc.id}: \"{loc.name}\"{marker}")

        lines.append("\n**CRITICAL**: Only use IDs from the lists above. Never use placeholder IDs like 'char_1', 'loc_1', 'character_id1', etc.\n")

        return "\n".join(lines)

    async def _retrieve_rag_context(self, entity_registry, arc, novel_input) -> str:
        """Retrieve worldbuilding and character context from RAG"""
        if not self.vector_store or not entity_registry:
            return ""

        try:
            # Get entity IDs relevant to this arc
            entity_ids = []
            if arc:
                entity_ids.extend(arc.get("character_ids", []))
                entity_ids.extend(arc.get("location_ids", []))
                entity_ids.extend(arc.get("scene_concept_ids", []))

            # If no arc-specific entities, get all entities
            if not entity_ids:
                from src.models import EntityType
                chars = entity_registry.get_by_type(EntityType.CHARACTER)
                locs = entity_registry.get_by_type(EntityType.LOCATION)
                entity_ids = [e.id for e in chars[:10]] + [e.id for e in locs[:5]]

            if not entity_ids:
                return ""

            # Retrieve related content from RAG
            rag_results = await self.retrieve_related_entities(
                entity_ids=entity_ids[:15],  # Limit to avoid token overflow
                relationship_types=['located_in', 'belongs_to', 'rules', 'has_ability'],
                max_depth=2
            )

            if not rag_results:
                return ""

            # Build context string
            context_parts = ["## WORLDBUILDING CONTEXT FROM SOURCE DOCUMENTS\n"]
            for result in rag_results[:20]:  # Limit results
                name = result.get("name", "Unknown")
                content = result.get("content", result.get("summary", ""))
                if content:
                    context_parts.append(f"**{name}**: {content[:300]}...")

            return "\n".join(context_parts) + "\n"

        except Exception as e:
            self.logger.warning(f"Failed to retrieve RAG context: {e}")
            return ""

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

        # Retrieve worldbuilding context from RAG
        rag_context = await self._retrieve_rag_context(entity_registry, arc, novel_input)

        # Build user prompt - support both plot_structure and arc workflows
        user_prompt = self._build_user_prompt(
            novel_input, theme_data, plot_structure, characters, world, arc, entity_registry, rag_context
        )

        # Generate scene outlines using LLM
        scene_data = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_format="json",
            temperature=0.7,
            max_tokens=10000  # Increased for 10-15 detailed scenes per arc
        )

        # Process scenes
        scenes_list = scene_data.get("scenes", [])
        scene_sequences = scene_data.get("scene_sequence", [])

        # Resolve character/location IDs to valid registry IDs (arc has character_ids, location_ids)
        arc = context.get("arc") or {}
        entity_registry = context.get("entity_registry")
        valid_char_ids = list(arc.get("character_ids", [])) if arc else []
        valid_loc_ids = list(arc.get("location_ids", [])) if arc else []
        if entity_registry:
            if not valid_char_ids:
                from src.models import EntityType
                valid_char_ids = [e.id for e in entity_registry.get_by_type(EntityType.CHARACTER)[:20]]
            if not valid_loc_ids:
                from src.models import EntityType
                valid_loc_ids = [e.id for e in entity_registry.get_by_type(EntityType.LOCATION)[:15]]

        for scene_data_item in scenes_list:
            # Fix pov_character and characters_present to use valid registry IDs
            if valid_char_ids:
                pov = scene_data_item.get("pov_character")
                if pov and entity_registry and not entity_registry.get(pov):
                    scene_data_item["pov_character"] = valid_char_ids[0]
                chars = scene_data_item.get("characters_present") or []
                if isinstance(chars, list):
                    fixed_chars = [c if (not entity_registry or entity_registry.get(c)) else valid_char_ids[0] for c in chars]
                    scene_data_item["characters_present"] = fixed_chars[:10]
            if valid_loc_ids and entity_registry:
                loc = scene_data_item.get("location_id")
                if loc and not entity_registry.get(loc):
                    scene_data_item["location_id"] = valid_loc_ids[0]

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
        entity_registry = None,
        rag_context: str = ""
    ) -> str:
        """Build user prompt from context"""
        prompt_parts = []

        # Add RAG context first if available
        if rag_context:
            prompt_parts.append(rag_context)

        # Add entity ID block if registry available
        if entity_registry:
            entity_id_block = self._build_entity_id_block(entity_registry, arc)
            prompt_parts.append(entity_id_block)

        prompt_parts.extend([
            f"Novel Premise: {novel_input.get('premise', 'Not provided')}",
            f"Genre: {novel_input.get('genre', 'Not specified')}",
        ])

        if theme_data:
            prompt_parts.append(f"Theme Question: {theme_data.get('theme_question', 'Not provided')}")

        # Support arc-based workflow (document-driven)
        if arc:
            prompt_parts.append(f"\n=== ARC: {arc.get('name', 'Unknown')} ===")
            prompt_parts.append(f"Type: {arc.get('type', 'unknown')}")
            prompt_parts.append(f"Description: {arc.get('description', 'No description')}")

            # Include character IDs and names so the LLM uses exact registry IDs
            char_ids = arc.get('character_ids', [])
            if char_ids and entity_registry:
                char_names = []
                for char_id in char_ids[:10]:
                    entity = entity_registry.get(char_id)
                    if entity:
                        char_names.append(entity.name)
                    else:
                        char_names.append(char_id)
                if char_names:
                    prompt_parts.append(f"Characters (name): {', '.join(char_names)}")
                prompt_parts.append(f"Valid character IDs for this arc (use these exact IDs for pov_character and characters_present): {char_ids}")

            # Include location IDs and names
            loc_ids = arc.get('location_ids', [])
            if loc_ids and entity_registry:
                loc_names = []
                for loc_id in loc_ids[:5]:
                    entity = entity_registry.get(loc_id)
                    if entity:
                        loc_names.append(entity.name)
                    else:
                        loc_names.append(loc_id)
                if loc_names:
                    prompt_parts.append(f"Locations (name): {', '.join(loc_names)}")
                prompt_parts.append(f"Valid location IDs for this arc (use these exact IDs for location_id): {loc_ids}")
            elif entity_registry:
                # If arc has no locations, list all location IDs from registry so LLM can pick
                from src.models import EntityType
                loc_entities = entity_registry.get_by_type(EntityType.LOCATION)
                if loc_entities:
                    loc_ids_all = [e.id for e in loc_entities[:15]]
                    prompt_parts.append(f"Valid location IDs (use one for location_id): {loc_ids_all}")

            prompt_parts.append(
                "\nPlease create 10-15 detailed scene outlines/beats for this arc.\n"
                "Each scene should have:\n"
                "- Clear goal, conflict, and outcome\n"
                "- Stakes and reveals\n"
                "- Specific characters present (use entity IDs) and POV character\n"
                "- Exact location (use entity ID from list above)\n"
                "- How it advances plot/character/theme\n\n"
                "Make the arc COMPREHENSIVE with all key moments from beginning to end."
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
