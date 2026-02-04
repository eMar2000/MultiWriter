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

    def _default_system_prompt(self) -> str:
        return """You are an Outline Architect specializing in narrative structure.
Given an entity registry with relationships, create a high-level arc plan:

1. Identify main story arcs from available scene concepts
2. Assign characters to arcs (primary vs secondary roles)
3. Assign locations to arcs
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
            "character_ids": ["id1", "id2"],
            "location_ids": ["loc1"],
            "scene_concept_ids": ["scene1"],
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
        registry = context.get("entity_registry")
        relationships = context.get("relationships", [])
        conflicts = context.get("conflicts", [])
        themes = context.get("themes", [])
        novel_input = context.get("novel_input", {})

        if not registry:
            raise ValueError("Entity registry required in context")

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

        user_prompt = f"""{rag_block}Create a high-level arc plan for this novel:

PREMISE: {novel_input.get('premise', 'Not specified')}
GENRE: {novel_input.get('genre', 'Not specified')}

ENTITIES:
{registry.to_context_string()}

IDENTIFIED RELATIONSHIPS:
{relationships}

IDENTIFIED CONFLICTS:
{conflicts}

IDENTIFIED THEMES:
{themes}

Create a comprehensive arc structure that uses ALL major entities."""

        result = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=4000
        )

        # Ensure we have arcs - if empty, create at least one default arc
        arcs = result.get("arcs", [])
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

        return {
            "agent": self.name,
            "output": result,
            "status": "success"
        }
