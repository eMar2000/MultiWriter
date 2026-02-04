"""Synthesis Agent - Enriches registry with relationships"""

from typing import Dict, Any, List
from pathlib import Path

from .base import BaseAgent
from src.models import EntityRegistry, EntityType


class SynthesisAgent(BaseAgent):
    """Agent that analyzes entities and identifies relationships"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="synthesis", *args, **kwargs)

        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "synthesis.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return """You are a Synthesis Agent specializing in narrative analysis.
Your task is to analyze an entity registry and identify:
1. Character-to-character relationships (allies, enemies, family, mentors)
2. Character-to-organization memberships
3. Character-to-location connections
4. Potential conflicts between entities
5. Thematic connections and patterns

Output a JSON object with:
{
    "relationships": [
        {"from_id": "...", "to_id": "...", "type": "...", "description": "..."}
    ],
    "conflicts": [
        {"entities": ["id1", "id2"], "type": "...", "description": "..."}
    ],
    "themes": [
        {"name": "...", "related_entities": ["id1", "id2"]}
    ],
    "notes": "..."
}"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze registry and identify relationships"""
        registry: EntityRegistry = context.get("entity_registry")
        if not registry:
            raise ValueError("Entity registry required in context")

        # Optional RAG: retrieve related entity details for richer context
        rag_block = ""
        if self.vector_store and hasattr(self.llm_provider, "get_embedding"):
            try:
                query = registry.to_context_string(max_tokens=500) or "characters locations relationships"
                related = await self.retrieve_related_entities(query, top_k=5)
                if related:
                    entity_ids = [r.get("id") for r in related if r.get("id")]
                    if entity_ids:
                        retrieved = await self.retrieve_entities(entity_ids)
                        rag_block = self.build_rag_context(registry, entity_ids, retrieved) + "\n\n"
            except Exception:
                pass

        # Build prompt with registry (and RAG block if available)
        user_prompt = f"""{rag_block}Analyze these entities and identify relationships, conflicts, and themes:

{registry.to_context_string()}

Identify all meaningful connections between entities."""

        result = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=4000
        )

        return {
            "agent": self.name,
            "output": {
                "relationships": result.get("relationships", []),
                "conflicts": result.get("conflicts", []),
                "themes": result.get("themes", []),
                "notes": result.get("notes", "")
            },
            "status": "success"
        }
