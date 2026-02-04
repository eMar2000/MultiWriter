"""Continuity Validation Service - Validates canon mutations before commit"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.memory.graph_store import GraphStore
from src.models.canon import (
    CanonNode,
    CanonEdge,
    ValidationResult,
    NodeType,
    EdgeType
)

logger = logging.getLogger(__name__)


class ContinuityValidationService:
    """Validates canon mutations for contradictions and violations"""

    def __init__(self, graph_store: GraphStore, cache_ttl_seconds: int = 300):
        """
        Initialize validation service

        Args:
            graph_store: Graph store to validate against
            cache_ttl_seconds: TTL for validation cache (default 5 minutes)
        """
        self.graph_store = graph_store
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.cache: Dict[str, tuple[ValidationResult, datetime]] = {}

    async def validate_mutation(
        self,
        mutation: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a proposed canon mutation

        Args:
            mutation: Mutation to validate (contains 'type', 'operation', 'data')
            context: Optional context (current canon state, etc.)

        Returns:
            ValidationResult with is_valid, violations, warnings, auto_fixes
        """
        result = ValidationResult(is_valid=True)

        mutation_type = mutation.get("type")  # "node", "edge"
        operation = mutation.get("operation")  # "create", "update", "delete"
        data = mutation.get("data", {})

        # Check cache
        cache_key = self._get_cache_key(mutation)
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                logger.debug(f"Using cached validation result for {cache_key}")
                return cached_result

        # Run validation checks
        if mutation_type == "node":
            await self._validate_node_mutation(result, operation, data)
        elif mutation_type == "edge":
            await self._validate_edge_mutation(result, operation, data)
        else:
            result.add_violation("invalid_mutation", f"Unknown mutation type: {mutation_type}")

        # Check for contradictions
        if result.is_valid:
            await self._check_contradictions(result, mutation)

        # Check timeline consistency
        if result.is_valid:
            await self._check_timeline(result, mutation)

        # Check referential integrity
        if result.is_valid:
            await self._check_referential_integrity(result, mutation)

        # Cache result if valid
        if result.is_valid:
            self.cache[cache_key] = (result, datetime.utcnow())

        return result

    async def _validate_node_mutation(
        self,
        result: ValidationResult,
        operation: str,
        data: Dict[str, Any]
    ):
        """Validate node mutation"""
        if operation == "create":
            # Check required fields
            if "type" not in data:
                result.add_violation("missing_field", "Node type is required")
            if "id" in data and await self.graph_store.get_node(data["id"]):
                result.add_violation("duplicate_id", f"Node {data['id']} already exists")

        elif operation == "update":
            node_id = data.get("id")
            if not node_id:
                result.add_violation("missing_field", "Node ID is required for update")
            elif not await self.graph_store.get_node(node_id):
                result.add_violation("not_found", f"Node {node_id} does not exist")

        elif operation == "delete":
            node_id = data.get("id")
            if not node_id:
                result.add_violation("missing_field", "Node ID is required for delete")
            elif not await self.graph_store.get_node(node_id):
                result.add_warning("not_found", f"Node {node_id} does not exist (already deleted?)")

    async def _validate_edge_mutation(
        self,
        result: ValidationResult,
        operation: str,
        data: Dict[str, Any]
    ):
        """Validate edge mutation"""
        source_id = data.get("source_id")
        target_id = data.get("target_id")
        edge_type = data.get("type")

        if not source_id or not target_id:
            result.add_violation("missing_field", "Source and target IDs are required")
            return

        if not edge_type:
            result.add_violation("missing_field", "Edge type is required")
            return

        # Check nodes exist
        source_node = await self.graph_store.get_node(source_id)
        target_node = await self.graph_store.get_node(target_id)

        if not source_node:
            result.add_violation("invalid_reference", f"Source node {source_id} does not exist")
        if not target_node:
            result.add_violation("invalid_reference", f"Target node {target_id} does not exist")

        if operation == "create":
            # Check for duplicate edge
            existing_edges = await self.graph_store.get_edges(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type
            )
            if existing_edges:
                result.add_warning("duplicate_edge", f"Edge {edge_type} from {source_id} to {target_id} already exists")

    async def _check_contradictions(
        self,
        result: ValidationResult,
        mutation: Dict[str, Any]
    ):
        """Check for contradictions with existing canon"""
        mutation_type = mutation.get("type")
        operation = mutation.get("operation")
        data = mutation.get("data", {})

        if mutation_type == "node" and operation == "create":
            node_type = data.get("type")
            node_id = data.get("id")

            # Check for character in two places at same time
            if node_type == NodeType.CHARACTER:
                # This would require checking timeline - simplified for now
                pass

            # Check for dead character acting
            if node_type == NodeType.CHARACTER:
                properties = data.get("properties", {})
                status = properties.get("status")
                if status == "dead":
                    # Check if character has any future events
                    # This would require timeline query - simplified for now
                    pass

        elif mutation_type == "edge" and operation == "create":
            edge_type = data.get("type")
            source_id = data.get("source_id")
            target_id = data.get("target_id")

            # Check for contradictory edges
            if edge_type == EdgeType.CONTRADICTS:
                # Check if contradiction already exists
                existing = await self.graph_store.get_edges(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=EdgeType.CONTRADICTS
                )
                if existing:
                    result.add_warning("duplicate_contradiction", "Contradiction edge already exists")

    async def _check_timeline(
        self,
        result: ValidationResult,
        mutation: Dict[str, Any]
    ):
        """Check timeline consistency"""
        mutation_type = mutation.get("type")
        operation = mutation.get("operation")
        data = mutation.get("data", {})

        if mutation_type == "edge" and operation == "create":
            edge_type = data.get("type")
            source_id = data.get("source_id")
            target_id = data.get("target_id")

            # Check for cycles in before/after edges
            if edge_type in (EdgeType.BEFORE, EdgeType.AFTER):
                # Create temporary edge to check for cycle
                # Note: This is a simplified check - full implementation would need transaction support
                try:
                    # Check if adding this edge would create a cycle
                    # We check if target can reach source through before/after edges
                    from src.models.canon import TimelineQuery
                    timeline_query = TimelineQuery(
                        start_node_id=target_id,
                        direction="forward",
                        max_depth=10,
                        edge_types=[EdgeType.BEFORE, EdgeType.AFTER]
                    )
                    reachable = await self.graph_store.query_timeline(timeline_query)
                    reachable_ids = {n.id for n in reachable}

                    # If source is reachable from target, adding edge would create cycle
                    if source_id in reachable_ids:
                        result.add_violation(
                            "timeline_cycle",
                            f"Adding {edge_type} edge from {source_id} to {target_id} would create a timeline cycle"
                        )
                except Exception as e:
                    logger.warning(f"Timeline cycle check failed: {e}")
                    result.add_warning("timeline_check_failed", f"Could not verify timeline consistency: {e}")

    async def _check_referential_integrity(
        self,
        result: ValidationResult,
        mutation: Dict[str, Any]
    ):
        """Check referential integrity"""
        mutation_type = mutation.get("type")
        operation = mutation.get("operation")
        data = mutation.get("data", {})

        if mutation_type == "node" and operation == "delete":
            node_id = data.get("id")
            if node_id:
                # Check for incoming edges
                incoming = await self.graph_store.get_edges(target_id=node_id)
                if incoming:
                    result.add_violation(
                        "referential_integrity",
                        f"Cannot delete node {node_id}: {len(incoming)} incoming edges exist"
                    )

        elif mutation_type == "edge" and operation == "create":
            source_id = data.get("source_id")
            target_id = data.get("target_id")

            # Nodes are already checked in _validate_edge_mutation
            pass

    def _get_cache_key(self, mutation: Dict[str, Any]) -> str:
        """Generate cache key for mutation"""
        return f"{mutation.get('type')}:{mutation.get('operation')}:{str(sorted(mutation.get('data', {}).items()))}"

    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate validation cache"""
        if pattern:
            # Invalidate matching keys
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Clear all cache
            self.cache.clear()
        logger.debug(f"Invalidated validation cache (pattern: {pattern or 'all'})")
