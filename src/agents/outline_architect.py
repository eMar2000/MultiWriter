"""Outline Architect Agent - Creates high-level arc structure"""

from typing import Dict, Any, List
from pathlib import Path

from .base import BaseAgent


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
        
        user_prompt = f"""Create a high-level arc plan for this novel:

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
        
        # Store arc plan
        await self.write_to_memory(
            "arc-plans",
            {
                "id": self.novel_id,
                "arcs": result.get("arcs", []),
                "timeline": result.get("timeline", []),
                "themes": result.get("themes", [])
            }
        )
        
        return {
            "agent": self.name,
            "output": result,
            "status": "success"
        }
