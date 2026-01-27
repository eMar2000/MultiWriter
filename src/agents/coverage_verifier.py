"""Coverage Verifier Agent - Ensures all entities are referenced"""

from typing import Dict, Any, List, Set
from pathlib import Path

from .base import BaseAgent
from src.models import EntityRegistry


class CoverageVerifierAgent(BaseAgent):
    """Agent that verifies all entities are included in the arc plan"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="coverage_verifier", *args, **kwargs)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Verify coverage and suggest additions for missing entities"""
        registry: EntityRegistry = context.get("entity_registry")
        arc_plan = context.get("arc_plan", {})

        if not registry:
            raise ValueError("Entity registry required in context")

        # Collect all referenced entity IDs from arcs
        referenced_ids: Set[str] = set()
        for arc in arc_plan.get("arcs", []):
            referenced_ids.update(arc.get("character_ids", []))
            referenced_ids.update(arc.get("location_ids", []))
            referenced_ids.update(arc.get("scene_concept_ids", []))

        # Find unreferenced entities
        all_ids = registry.get_all_ids()
        unreferenced = all_ids - referenced_ids

        coverage_percentage = (len(referenced_ids) / len(all_ids) * 100) if all_ids else 100

        result = {
            "total_entities": len(all_ids),
            "referenced_entities": len(referenced_ids),
            "unreferenced_entities": len(unreferenced),
            "coverage_percentage": round(coverage_percentage, 1),
            "unreferenced_ids": list(unreferenced),
            "is_complete": len(unreferenced) == 0
        }

        # If incomplete, suggest assignments
        if unreferenced:
            suggestions = await self._suggest_assignments(
                registry, unreferenced, arc_plan
            )
            result["suggestions"] = suggestions

        return {
            "agent": self.name,
            "output": result,
            "status": "success"
        }

    async def _suggest_assignments(
        self,
        registry: EntityRegistry,
        unreferenced: Set[str],
        arc_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest arc assignments for unreferenced entities"""
        suggestions = []

        for entity_id in unreferenced:
            entity = registry.get(entity_id)
            if not entity:
                continue

            # Use LLM to suggest best arc fit
            prompt = f"""Given this entity:
Name: {entity.name}
Type: {entity.entity_type.value if hasattr(entity.entity_type, 'value') else entity.entity_type}
Summary: {entity.summary}

And these arcs:
{arc_plan.get('arcs', [])}

Which arc would this entity best fit in? Or should it be marked as background?
Reply with JSON: {{"arc_id": "...", "role": "primary|secondary|background", "rationale": "..."}}"""

            try:
                suggestion = await self.generate_structured_output(
                    system_prompt="You are a story structure expert. Suggest where entities belong in arcs.",
                    user_prompt=prompt,
                    temperature=0.5
                )
                suggestion["entity_id"] = entity_id
                suggestion["entity_name"] = entity.name
                suggestions.append(suggestion)
            except Exception:
                suggestions.append({
                    "entity_id": entity_id,
                    "entity_name": entity.name,
                    "arc_id": None,
                    "role": "background",
                    "rationale": "Could not determine assignment"
                })

        return suggestions
