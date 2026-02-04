"""Timeline Manager Agent - Validates chronological consistency"""

import logging
from typing import Dict, Any, Optional, List

from src.agents.base import BaseAgent
from src.memory import GraphStore
from src.models.canon import EdgeType, NodeType

logger = logging.getLogger(__name__)


class TimelineManagerAgent(BaseAgent):
    """Validates timeline consistency and temporal constraints"""

    def __init__(self, *args, graph_store: Optional[GraphStore] = None, **kwargs):
        """
        Initialize Timeline Manager

        Args:
            graph_store: Optional graph store for timeline queries
        """
        super().__init__(name="timeline_manager", *args, **kwargs)
        self.graph_store = graph_store

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate timeline consistency

        Args:
            context: Should contain:
                - outline: NovelOutline or dict
                - entity_registry: EntityRegistry
                - graph_store: Optional GraphStore

        Returns:
            Validation report with violations and recommendations
        """
        outline = context.get("outline")
        entity_registry = context.get("entity_registry")
        graph_store = context.get("graph_store") or self.graph_store

        violations = []
        warnings = []
        recommendations = []

        # If we have a graph store, use it for timeline validation
        if graph_store:
            violations.extend(await self._validate_with_graph(outline, graph_store))
        else:
            # Basic validation without graph store
            violations.extend(await self._validate_basic(outline, entity_registry))

        # Check for temporal impossibilities
        warnings.extend(await self._check_temporal_constraints(outline, entity_registry))

        return {
            "output": {
                "violations": violations,
                "warnings": warnings,
                "recommendations": recommendations,
                "is_valid": len(violations) == 0
            }
        }

    async def _validate_with_graph(
        self,
        outline: Optional[Dict[str, Any]],
        graph_store: GraphStore
    ) -> List[Dict[str, Any]]:
        """Validate timeline using graph store"""
        violations = []

        if not outline:
            return violations

        # Check for cycles in before/after edges
        try:
            # Get all event nodes
            from src.models.canon import CanonQuery
            query = CanonQuery(node_type=NodeType.EVENT, limit=100)
            events = await graph_store.query_nodes(query)

            for event in events:
                has_cycle = await graph_store.check_cycle(
                    event.id,
                    edge_types=[EdgeType.BEFORE, EdgeType.AFTER]
                )
                if has_cycle:
                    violations.append({
                        "type": "timeline_cycle",
                        "message": f"Timeline cycle detected involving event {event.id}",
                        "event_id": event.id
                    })
        except Exception as e:
            logger.warning(f"Graph-based timeline validation failed: {e}")

        return violations

    async def _validate_basic(
        self,
        outline: Optional[Dict[str, Any]],
        entity_registry: Optional[Any]
    ) -> List[Dict[str, Any]]:
        """Basic timeline validation without graph store"""
        violations = []

        if not outline:
            return violations

        # Check scene order if scenes have sequence numbers
        scenes = outline.get("scenes", [])
        scene_numbers = []
        for scene in scenes:
            if isinstance(scene, dict):
                scene_num = scene.get("scene_number")
            else:
                scene_num = getattr(scene, "scene_number", None)
            if scene_num:
                scene_numbers.append(scene_num)

        # Check for duplicate scene numbers
        if len(scene_numbers) != len(set(scene_numbers)):
            violations.append({
                "type": "duplicate_scene_numbers",
                "message": "Duplicate scene numbers detected"
            })

        return violations

    async def _check_temporal_constraints(
        self,
        outline: Optional[Dict[str, Any]],
        entity_registry: Optional[Any]
    ) -> List[Dict[str, Any]]:
        """Check temporal constraints (travel time, etc.)"""
        warnings = []

        if not outline:
            return warnings

        # Check for rapid location changes that might be impossible
        scenes = outline.get("scenes", [])
        prev_location = None
        prev_time = None

        for scene in scenes:
            if isinstance(scene, dict):
                location = scene.get("location_id")
                time_period = scene.get("time_period")
            else:
                location = getattr(scene, "location_id", None)
                time_period = getattr(scene, "time_period", None)

            if prev_location and location and prev_location != location:
                # Location changed - check if time allows for travel
                if prev_time == time_period:
                    warnings.append({
                        "type": "impossible_travel",
                        "message": f"Character may have traveled from {prev_location} to {location} instantly",
                        "scene": scene.get("title", "Unknown") if isinstance(scene, dict) else getattr(scene, "title", "Unknown")
                    })

            prev_location = location
            prev_time = time_period

        return warnings
