"""Outline ↔ Canon Sync Manager - Maintains consistency between outline and canon"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.memory.graph_store import GraphStore
from src.validation.continuity import ContinuityValidationService
from src.models.canon import CanonNode, CanonEdge, NodeType, EdgeType, ValidationResult
from src.models.outline import NovelOutline
from src.models.scene import SceneOutline
from src.models.entity import EntityRegistry

logger = logging.getLogger(__name__)

# Map EntityRegistry entity_type to canon NodeType (for seed and sync)
ENTITY_TYPE_TO_NODE_TYPE = {
    "character": NodeType.CHARACTER,
    "location": NodeType.LOCATION,
    "organization": NodeType.ORGANIZATION,
    "item": NodeType.OBJECT,
    "event": NodeType.EVENT,
    "rule": NodeType.RULE,
}


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

    async def seed_registry_to_canon(self, registry: EntityRegistry) -> Dict[str, Any]:
        """
        Seed canon store with all entities from the registry (World Registry Initializer).
        Call once at story start before the planning loop so scene->character/location edges
        reference existing nodes.

        Args:
            registry: Entity registry from document ingestion

        Returns:
            Result with nodes_created, nodes_updated, violations, warnings
        """
        result = {
            "nodes_created": 0,
            "nodes_updated": 0,
            "violations": [],
            "warnings": [],
        }
        for entity_id, entity in registry.entities.items():
            entity_type_val = (
                entity.entity_type.value
                if hasattr(entity.entity_type, "value")
                else str(entity.entity_type)
            )
            node_type = ENTITY_TYPE_TO_NODE_TYPE.get(entity_type_val)
            if not node_type:
                continue
            mutation = {
                "type": "node",
                "operation": "create",
                "data": {
                    "id": entity_id,
                    "type": node_type,
                    "properties": {
                        "name": entity.name,
                        "summary": entity.summary,
                        "tags": entity.tags or [],
                        "source_doc": entity.source_doc,
                    },
                },
            }
            validation = await self.validation_service.validate_mutation(mutation)
            if not validation.is_valid:
                result["violations"].extend(validation.violations)
                continue
            node = CanonNode(
                id=entity_id,
                type=node_type,
                properties=mutation["data"]["properties"],
            )
            existing = await self.graph_store.get_node(entity_id)
            if existing:
                await self.graph_store.update_node(entity_id, **node.properties)
                result["nodes_updated"] += 1
            else:
                await self.graph_store.create_node(node)
                result["nodes_created"] += 1
        if result["violations"]:
            logger.warning(f"Seed registry: {len(result['violations'])} validation violations")
        logger.info(f"Seed registry to canon: {result['nodes_created']} created, {result['nodes_updated']} updated")
        return result

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
                entity_type_val = (
                    entity.entity_type.value
                    if hasattr(entity.entity_type, "value")
                    else str(entity.entity_type)
                )
                node_type = ENTITY_TYPE_TO_NODE_TYPE.get(entity_type_val)
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
            "warnings": [],
            "synced_entities": []
        }

        if not self.graph_store:
            result["warnings"].append("No graph store available for canon sync")
            return result

        try:
            # Get all character nodes from canon
            from src.models.canon import CanonQuery, NodeType
            character_query = CanonQuery(node_type=NodeType.CHARACTER)
            canon_characters = await self.graph_store.query_nodes(character_query)

            # Get all location nodes from canon
            location_query = CanonQuery(node_type=NodeType.LOCATION)
            canon_locations = await self.graph_store.query_nodes(location_query)

            # Update outline with canonical states
            updated_scenes = []
            for scene in outline.get("scenes", []):
                if not isinstance(scene, dict):
                    continue

                scene_updated = False

                # Update character states in scene
                for char in canon_characters:
                    char_id = char.id
                    if char_id in scene.get("characters_present", []):
                        # Check if character state has changed
                        char_props = char.properties
                        if char_props.get("status") == "dead":
                            result["warnings"].append(
                                f"Scene {scene.get('scene_number')} includes dead character {char_id}"
                            )

                        # Update character locations if available
                        if "current_location" in char_props:
                            scene["canon_character_states"] = scene.get("canon_character_states", {})
                            scene["canon_character_states"][char_id] = {
                                "status": char_props.get("status", "alive"),
                                "location": char_props.get("current_location")
                            }
                            scene_updated = True

                # Update location details from canon
                location_id = scene.get("location_id")
                if location_id:
                    for loc in canon_locations:
                        if loc.id == location_id:
                            loc_props = loc.properties
                            if "description" in loc_props:
                                scene["canon_location_details"] = loc_props.get("description")
                                scene_updated = True

                if scene_updated:
                    updated_scenes.append(scene)
                    result["updated"] += 1
                    result["synced_entities"].append(scene.get("scene_id", "unknown"))

            # Update outline metadata
            if result["updated"] > 0:
                outline["last_canon_sync"] = datetime.utcnow().isoformat()
                outline["canon_sync_version"] = outline.get("canon_sync_version", 0) + 1

            logger.info(f"Canon-to-outline sync: Updated {result['updated']} scenes")

        except Exception as e:
            logger.error(f"Canon-to-outline sync failed: {e}", exc_info=True)
            result["warnings"].append(f"Sync error: {str(e)}")

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
