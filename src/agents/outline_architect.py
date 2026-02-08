"""Outline Architect Agent - Creates high-level arc structure"""

from typing import Dict, Any, List
from pathlib import Path

from .base import BaseAgent
from src.models import EntityType


class OutlineArchitectAgent(BaseAgent):
    """Agent that creates the high-level narrative arc structure"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="outline_architect", *args, **kwargs)

        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "outline_architect.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _build_entity_id_block(self, registry) -> str:
        """Build explicit entity ID block for agents"""
        from src.models import EntityType

        lines = ["## AVAILABLE ENTITY IDs (MUST USE THESE - DO NOT INVENT NEW IDs)\n"]

        # Characters
        chars = registry.get_by_type(EntityType.CHARACTER)
        if chars:
            lines.append("### Characters:")
            for char in chars[:30]:  # Limit to avoid token overflow
                lines.append(f"- {char.id}: \"{char.name}\" ({char.summary[:60]}...)")

        # Locations
        locs = registry.get_by_type(EntityType.LOCATION)
        if locs:
            lines.append("\n### Locations:")
            for loc in locs[:20]:
                lines.append(f"- {loc.id}: \"{loc.name}\" ({loc.summary[:60]}...)")

        # Scene Concepts
        scenes = registry.get_by_type(EntityType.SCENE_CONCEPT)
        if scenes:
            lines.append("\n### Scene Concepts:")
            for scene in scenes[:15]:
                lines.append(f"- {scene.id}: \"{scene.name}\" ({scene.summary[:60]}...)")

        # Organizations
        orgs = registry.get_by_type(EntityType.ORGANIZATION)
        if orgs:
            lines.append("\n### Organizations:")
            for org in orgs[:10]:
                lines.append(f"- {org.id}: \"{org.name}\" ({org.summary[:60]}...)")

        lines.append("\n**IMPORTANT**: Only use IDs from the lists above. Never use placeholder IDs like 'char_1', 'loc_1', etc.\n")

        return "\n".join(lines)

    def _default_system_prompt(self) -> str:
        return """You are an Outline Architect specializing in narrative structure.
Given an entity registry with relationships, create a high-level arc plan.

CRITICAL: character_ids, location_ids, and scene_concept_ids MUST be exact entity IDs from the ENTITIES list (the IDs appear in brackets [id]). Do NOT invent new IDs like "id1" or "loc1". Use only the IDs shown in brackets from ENTITIES.

1. Identify main story arcs from available scene concepts
2. Assign characters to arcs (primary vs secondary roles) using only entity IDs from ENTITIES
3. Assign locations to arcs using only entity IDs from ENTITIES
4. Define arc dependencies and ordering
5. Estimate scope (chapters per arc)

Output a JSON object:
{
    "arcs": [
        {
            "id": "arc_1",
            "name": "Arc Name",
            "description": "Brief arc description",
            "type": "main|subplot|character",
            "character_ids": ["<use actual character entity IDs from ENTITIES>"],
            "location_ids": ["<use actual location entity IDs from ENTITIES>"],
            "scene_concept_ids": ["<use actual scene_concept entity IDs from ENTITIES>"],
            "estimated_chapters": 5,
            "dependencies": []
        }
    ],
    "timeline": ["arc_1", "arc_2"],
    "themes": ["theme1", "theme2"],
    "notes": "..."
}"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create arc structure from enriched registry"""
        self.logger.info("[Outline Architect] Starting execution")
        self.logger.debug(f"  Context keys: {list(context.keys())}")

        registry = context.get("entity_registry")
        relationships = context.get("relationships", [])
        conflicts = context.get("conflicts", [])
        themes = context.get("themes", [])
        novel_input = context.get("novel_input", {})

        if not registry:
            self.logger.error("  Entity registry missing from context!")
            raise ValueError("Entity registry required in context")

        self.logger.info(f"  Entity registry has {len(registry.entities)} entities")
        self.logger.info(f"  Synthesis provided: {len(relationships)} relationships, "
                        f"{len(conflicts)} conflicts, {len(themes)} themes")
        self.logger.info(f"  Novel premise: {novel_input.get('premise', 'N/A')[:100]}...")

        rag_block = ""
        if self.vector_store and hasattr(self.llm_provider, "get_embedding"):
            try:
                query = f"arc plot structure {novel_input.get('premise', '')[:200]}"
                related = await self.retrieve_related_entities(query, top_k=5)
                if related:
                    entity_ids = [r.get("id") for r in related if r.get("id")]
                    if entity_ids:
                        retrieved = await self.retrieve_entities(entity_ids)
                        rag_block = self.build_rag_context(registry, entity_ids, retrieved) + "\n\n"
            except Exception:
                pass

        # Build explicit entity ID mappings
        entity_id_block = self._build_entity_id_block(registry)

        # CRITICAL FIX: Don't dump entire registry - create summary instead
        char_count = len(registry.get_by_type(EntityType.CHARACTER))
        loc_count = len(registry.get_by_type(EntityType.LOCATION))
        scene_count = len(registry.get_by_type(EntityType.SCENE_CONCEPT))

        # Summarize synthesis results
        rel_summary = f"{len(relationships)} relationships identified" if relationships else "No relationships provided"
        conf_summary = f"{len(conflicts)} conflicts identified" if conflicts else "No conflicts provided"
        theme_list = ", ".join([t.get('name', 'Unknown') for t in themes[:5]]) if themes else "No themes provided"

        user_prompt = f"""{rag_block}Create a high-level arc plan for this novel:

PREMISE: {novel_input.get('premise', 'Not specified')}
GENRE: {novel_input.get('genre', 'Not specified')}

ENTITY SUMMARY:
- Characters: {char_count}
- Locations: {loc_count}
- Scene Concepts: {scene_count}

SYNTHESIS SUMMARY:
- {rel_summary}
- {conf_summary}
- Themes: {theme_list}

{entity_id_block}

TASK: Create 10-15 narrative arcs that comprehensively cover the story from beginning to end. Each arc should:
1. Use actual entity IDs from the "AVAILABLE ENTITY IDs" section above
2. Include 5-8 major events/beats in the description
3. Specify which characters, locations, and scene concepts are involved
4. Cover different aspects: main plot, subplots, character development, worldbuilding

ARC TYPES TO INCLUDE:
- Main story arcs (3-4): Core narrative progression
- Character arcs (4-6): Individual character journeys and development
- Subplot arcs (3-4): Secondary storylines that intersect with main plot
- Worldbuilding arcs (2-3): Exploration of setting, factions, systems

CRITICAL:
- Respond with EXACTLY this JSON structure: {{"arcs": [...], "timeline": [...], "themes": [...], "notes": "..."}}
- The "arcs" key MUST be present and MUST be a list of 10-15 arcs
- Each arc must have: id, name, description (detailed, 2-3 sentences), type, character_ids, location_ids, scene_concept_ids, estimated_chapters, dependencies
- Use ONLY entity IDs from the lists above
- DO NOT invent placeholder IDs like "char_1" or "loc_1" """

        self.logger.info("  Calling LLM to generate arc plan...")
        self.logger.debug(f"  User prompt length: {len(user_prompt)} chars")

        result = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=6000  # Increased for more detailed arcs
        )

        self.logger.info(f"  LLM returned result with keys: {list(result.keys())}")

        # CRITICAL FIX: Handle JSON schema variations from LLM
        # LLM might return "arcs", "arc_structure", or nested structures
        arcs = result.get("arcs", [])

        if not arcs:
            # Try alternative key names
            if "arc_structure" in result:
                arc_struct = result["arc_structure"]
                if isinstance(arc_struct, dict):
                    arcs = arc_struct.get("arcs", [])
                elif isinstance(arc_struct, list):
                    arcs = arc_struct
                self.logger.warning(f"  LLM used 'arc_structure' key, extracted {len(arcs)} arcs")
            elif "story_arcs" in result:
                arcs = result["story_arcs"]
                self.logger.warning(f"  LLM used 'story_arcs' key, extracted {len(arcs)} arcs")

        # Ensure we have arcs - if empty, create at least one default arc
        if not arcs:
            self.logger.warning("  LLM returned no arcs, will create default")
        self.logger.info(f"  Parsed {len(arcs)} arcs from LLM response")
        valid_ids = registry.get_all_ids() if registry else set()
        # Post-process: replace unrecognized IDs with first valid ID of same type (or drop)
        for arc in arcs:
            if not isinstance(arc, dict):
                continue
            for key in ("character_ids", "location_ids", "scene_concept_ids"):
                ids = arc.get(key)
                if not isinstance(ids, list):
                    continue
                fixed = []
                for eid in ids:
                    if eid in valid_ids:
                        fixed.append(eid)
                    else:
                        # Replace with first valid ID of appropriate type if available
                        if key == "character_ids":
                            chars = registry.get_by_type(EntityType.CHARACTER)
                            if chars:
                                fixed.append(chars[0].id)
                        elif key == "location_ids":
                            locs = registry.get_by_type(EntityType.LOCATION)
                            if locs:
                                fixed.append(locs[0].id)
                        elif key == "scene_concept_ids":
                            scenes = registry.get_by_type(EntityType.SCENE_CONCEPT)
                            if scenes:
                                fixed.append(scenes[0].id)
                arc[key] = fixed
        if not arcs:
            # Create a default arc from scene concepts if available
            scene_concepts = registry.get_by_type(EntityType.SCENE_CONCEPT)
            if scene_concepts:
                # Create a single main arc using first few scene concepts
                default_arc = {
                    "id": "arc_1",
                    "name": "Main Story Arc",
                    "description": f"Primary narrative arc involving {len(scene_concepts)} key scenes",
                    "type": "main",
                    "character_ids": [],
                    "location_ids": [],
                    "scene_concept_ids": [sc.id for sc in scene_concepts[:5]],
                    "estimated_chapters": 5,
                    "dependencies": []
                }
                arcs = [default_arc]
                result["arcs"] = arcs
                result["timeline"] = ["arc_1"]

        # Store arc plan
        await self.write_to_memory(
            "arc-plans",
            {
                "id": self.novel_id,
                "arcs": arcs,
                "timeline": result.get("timeline", [a.get("id") for a in arcs]),
                "themes": result.get("themes", [])
            }
        )

        self.logger.info(f"[Outline Architect] Execution complete - returning {len(arcs)} arcs")
        for i, arc in enumerate(arcs):
            self.logger.info(f"  Arc {i+1}: {arc.get('name', 'Untitled')} - "
                           f"{len(arc.get('character_ids', []))} chars, "
                           f"{len(arc.get('location_ids', []))} locs, "
                           f"{len(arc.get('scene_concept_ids', []))} scenes")

        return {
            "agent": self.name,
            "output": result,
            "status": "success"
        }
