"""Outline ↔ Canon Sync Manager - Maintains consistency between outline and canon"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.memory.graph_store import GraphStore
from src.validation.continuity import ContinuityValidationService
from src.models.canon import CanonNode, CanonEdge, NodeType, EdgeType, ValidationResult
from src.models.outline import NovelOutline
from src.models.scene import SceneOutline

logger = logging.getLogger(__name__)


class CanonSyncManager:
    """Manages bidirectional sync between Outline and Canon Store"""

    def __init__(
        self,
        graph_store: GraphStore,
        validation_service: ContinuityValidationService
    ):
        """
        Initialize sync manager

        Args:
            graph_store: Graph store for canon
            validation_service: Validation service for mutations
        """
        self.graph_store = graph_store
        self.validation_service = validation_service

    async def sync_outline_to_canon(
        self,
        outline: NovelOutline,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync outline changes to canon store

        Args:
            outline: Novel outline to sync
            dry_run: If True, validate but don't commit

        Returns:
            Sync result with changes, violations, warnings
        """
        result = {
            "nodes_created": 0,
            "nodes_updated": 0,
            "edges_created": 0,
            "violations": [],
            "warnings": [],
            "dry_run": dry_run
        }

        # Sync scenes as events
        for scene in outline.scenes:
            scene_node_id = f"scene_{scene.scene_number or 'unknown'}"

            # Create/update scene node
            mutation = {
                "type": "node",
                "operation": "create",
                "data": {
                    "id": scene_node_id,
                    "type": NodeType.SCENE,
                    "properties": {
                        "title": scene.title,
                        "scene_number": scene.scene_number,
                        "goal": scene.goal,
                        "conflict": scene.conflict,
                        "outcome": scene.outcome,
                        "stakes": scene.stakes,
                        "scene_type": scene.scene_type.value if scene.scene_type else None,
                        "tension_start": scene.tension_start,
                        "tension_end": scene.tension_end
                    }
                }
            }

            validation = await self.validation_service.validate_mutation(mutation)
            if not validation.is_valid:
                result["violations"].extend(validation.violations)
                logger.warning(f"Scene {scene_node_id} validation failed: {validation.violations}")
                continue

            if not dry_run:
                # Create scene node
                scene_node = CanonNode(
                    id=scene_node_id,
                    type=NodeType.SCENE,
                    properties=mutation["data"]["properties"]
                )
                existing = await self.graph_store.get_node(scene_node_id)
                if existing:
                    await self.graph_store.update_node(scene_node_id, **scene_node.properties)
                    result["nodes_updated"] += 1
                else:
                    await self.graph_store.create_node(scene_node)
                    result["nodes_created"] += 1

                # Create edges for characters
                if scene.pov_character:
                    char_edge = CanonEdge(
                        source_id=scene_node_id,
                        target_id=scene.pov_character,
                        type=EdgeType.APPEARS_IN,
                        properties={"pov": True}
                    )
                    await self.graph_store.create_edge(char_edge)
                    result["edges_created"] += 1

                if scene.characters_present:
                    for char_id in scene.characters_present:
                        if char_id != scene.pov_character:
                            char_edge = CanonEdge(
                                source_id=scene_node_id,
                                target_id=char_id,
                                type=EdgeType.APPEARS_IN,
                                properties={"pov": False}
                            )
                            await self.graph_store.create_edge(char_edge)
                            result["edges_created"] += 1

                # Create edge for location
                if scene.location_id:
                    loc_edge = CanonEdge(
                        source_id=scene_node_id,
                        target_id=scene.location_id,
                        type=EdgeType.LOCATED_IN
                    )
                    await self.graph_store.create_edge(loc_edge)
                    result["edges_created"] += 1

        # Sync entity registry to canon
        if outline.entity_registry:
            for entity_id, entity in outline.entity_registry.entities.items():
                # Map entity types to canon node types
                node_type_map = {
                    "character": NodeType.CHARACTER,
                    "location": NodeType.LOCATION,
                    "organization": NodeType.ORGANIZATION,
                    "item": NodeType.OBJECT,
                    "event": NodeType.EVENT,
                    "rule": NodeType.RULE,
                }

                node_type = node_type_map.get(entity.entity_type.value)
                if not node_type:
                    continue  # Skip unmapped types

                mutation = {
                    "type": "node",
                    "operation": "create",
                    "data": {
                        "id": entity_id,
                        "type": node_type,
                        "properties": {
                            "name": entity.name,
                            "summary": entity.summary,
                            "tags": entity.tags,
                            "source_doc": entity.source_doc
                        }
                    }
                }

                validation = await self.validation_service.validate_mutation(mutation)
                if not validation.is_valid:
                    result["violations"].extend(validation.violations)
                    continue

                if not dry_run:
                    node = CanonNode(
                        id=entity_id,
                        type=node_type,
                        properties=mutation["data"]["properties"]
                    )
                    existing = await self.graph_store.get_node(entity_id)
                    if existing:
                        await self.graph_store.update_node(entity_id, **node.properties)
                        result["nodes_updated"] += 1
                    else:
                        await self.graph_store.create_node(node)
                        result["nodes_created"] += 1

        result["warnings"].extend(validation.warnings if validation else [])
        logger.info(f"Synced outline to canon: {result['nodes_created']} created, {result['nodes_updated']} updated, {result['edges_created']} edges")
        return result

    async def sync_canon_to_outline(
        self,
        outline: NovelOutline
    ) -> Dict[str, Any]:
        """
        Sync canon changes back to outline (for updates from other agents)

        Args:
            outline: Outline to update

        Returns:
            Update result
        """
        result = {
            "updated": 0,
            "warnings": []
        }

        # This would update outline based on canon changes
        # For now, simplified - would need more sophisticated diff logic
        # TODO: Implement canon-to-outline sync when canon is updated by agents

        return result

    async def create_change_log(
        self,
        operation: str,
        changes: Dict[str, Any],
        agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a change log entry"""
        return {
            "operation": operation,
            "changes": changes,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "outline_id": None  # Would be set by caller
        }
