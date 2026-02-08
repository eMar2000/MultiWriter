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
        """Analyze registry and identify relationships - now with batched processing"""
        from src.parser.document_chunker import DocumentChunker

        registry: EntityRegistry = context.get("entity_registry")
        if not registry:
            raise ValueError("Entity registry required in context")

        # CRITICAL FIX: registry.entities is a dict, convert to list
        entity_list = list(registry.entities.values())
        self.logger.info(f"[Synthesis] Processing {len(entity_list)} entities")

        # CRITICAL FIX: Process entities in batches to avoid context overload
        chunker = DocumentChunker()
        entity_batches = chunker.chunk_entity_list(entity_list, batch_size=15)

        self.logger.info(f"[Synthesis] Split into {len(entity_batches)} batches")

        all_relationships = []
        all_conflicts = []
        all_themes = []

        # Process each batch
        for i, batch in enumerate(entity_batches):
            self.logger.info(f"[Synthesis] Processing batch {i+1}/{len(entity_batches)} ({len(batch)} entities)")

            # Create a temporary registry with just this batch
            # Note: entities are EntitySummary objects with entity_type attribute
            batch_context = "\n\n".join([
                f"**{e.name}** (ID: {e.id})\n"
                f"Type: {e.entity_type}\n"
                f"Summary: {e.summary}"
                for e in batch
            ])

            user_prompt = f"""Analyze these entities and identify relationships, conflicts, and themes:

{batch_context}

Identify all meaningful connections between these entities."""

            try:
                result = await self.generate_structured_output(
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7,
                    max_tokens=2000  # Reduced since we're processing smaller batches
                )

                # Aggregate results
                all_relationships.extend(result.get("relationships", []))
                all_conflicts.extend(result.get("conflicts", []))
                all_themes.extend(result.get("themes", []))

                self.logger.info(f"  Batch {i+1} found: {len(result.get('relationships', []))} relationships, "
                               f"{len(result.get('conflicts', []))} conflicts, {len(result.get('themes', []))} themes")

            except Exception as e:
                self.logger.error(f"  Batch {i+1} failed: {e}")
                continue

        # Deduplicate themes by name
        unique_themes = {}
        for theme in all_themes:
            if isinstance(theme, dict):
                name = theme.get("name", "").lower()
                if name and name not in unique_themes:
                    unique_themes[name] = theme

        final_themes = list(unique_themes.values())

        self.logger.info(f"[Synthesis] Total: {len(all_relationships)} relationships, "
                        f"{len(all_conflicts)} conflicts, {len(final_themes)} themes")

        return {
            "agent": self.name,
            "output": {
                "relationships": all_relationships,
                "conflicts": all_conflicts,
                "themes": final_themes,
                "notes": f"Processed {len(entity_batches)} batches of entities"
            },
            "status": "success"
        }
