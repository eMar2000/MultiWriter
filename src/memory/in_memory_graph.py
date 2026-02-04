"""In-memory implementation of GraphStore using NetworkX-like structure"""

import logging
from typing import List, Optional, Dict, Any, Set
from collections import defaultdict, deque

from src.memory.graph_store import GraphStore
from src.models.canon import (
    CanonNode,
    CanonEdge,
    CanonQuery,
    TimelineQuery,
    NodeType,
    EdgeType
)

logger = logging.getLogger(__name__)


class InMemoryGraphStore(GraphStore):
    """In-memory graph store implementation"""

    def __init__(self):
        """Initialize empty graph"""
        self.nodes: Dict[str, CanonNode] = {}
        self.edges: Dict[str, List[CanonEdge]] = defaultdict(list)  # source_id -> [edges]
        self.reverse_edges: Dict[str, List[CanonEdge]] = defaultdict(list)  # target_id -> [edges]
        self.edge_index: Dict[tuple, CanonEdge] = {}  # (source_id, target_id, edge_type) -> edge

    async def create_node(self, node: CanonNode) -> CanonNode:
        """Create a new node"""
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists")
        self.nodes[node.id] = node
        logger.debug(f"Created node {node.id} of type {node.type}")
        return node

    async def get_node(self, node_id: str) -> Optional[CanonNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)

    async def update_node(self, node_id: str, **properties) -> Optional[CanonNode]:
        """Update node properties"""
        node = self.nodes.get(node_id)
        if not node:
            return None
        node.update(**properties)
        return node

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges"""
        if node_id not in self.nodes:
            return False

        # Delete all outgoing edges
        if node_id in self.edges:
            for edge in self.edges[node_id]:
                # Remove from reverse index
                if edge.target_id in self.reverse_edges:
                    self.reverse_edges[edge.target_id] = [
                        e for e in self.reverse_edges[edge.target_id]
                        if not (e.source_id == edge.source_id and e.type == edge.type)
                    ]
                # Remove from edge index
                key = (edge.source_id, edge.target_id, edge.type)
                if key in self.edge_index:
                    del self.edge_index[key]
            del self.edges[node_id]

        # Delete all incoming edges
        if node_id in self.reverse_edges:
            for edge in self.reverse_edges[node_id]:
                # Remove from forward index
                if edge.source_id in self.edges:
                    self.edges[edge.source_id] = [
                        e for e in self.edges[edge.source_id]
                        if not (e.target_id == edge.target_id and e.type == edge.type)
                    ]
                # Remove from edge index
                key = (edge.source_id, edge.target_id, edge.type)
                if key in self.edge_index:
                    del self.edge_index[key]
            del self.reverse_edges[node_id]

        del self.nodes[node_id]
        logger.debug(f"Deleted node {node_id}")
        return True

    async def create_edge(self, edge: CanonEdge) -> CanonEdge:
        """Create a new edge"""
        # Validate nodes exist
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} does not exist")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} does not exist")

        # Check if edge already exists
        key = (edge.source_id, edge.target_id, edge.type)
        if key in self.edge_index:
            # Update existing edge
            existing = self.edge_index[key]
            existing.update_properties(**edge.properties)
            return existing

        # Add to indexes
        self.edges[edge.source_id].append(edge)
        self.reverse_edges[edge.target_id].append(edge)
        self.edge_index[key] = edge
        logger.debug(f"Created edge {edge.type} from {edge.source_id} to {edge.target_id}")
        return edge

    async def get_edges(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None
    ) -> List[CanonEdge]:
        """Get edges matching criteria"""
        results = []

        if source_id:
            # Search from source
            edges = self.edges.get(source_id, [])
            for edge in edges:
                if (target_id is None or edge.target_id == target_id) and \
                   (edge_type is None or edge.type == edge_type):
                    results.append(edge)
        elif target_id:
            # Search from target (reverse)
            edges = self.reverse_edges.get(target_id, [])
            for edge in edges:
                if (edge_type is None or edge.type == edge_type):
                    results.append(edge)
        else:
            # Search all edges
            for edges_list in self.edges.values():
                for edge in edges_list:
                    if (edge_type is None or edge.type == edge_type):
                        results.append(edge)

        return results

    async def delete_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Delete an edge"""
        key = (source_id, target_id, edge_type)
        if key not in self.edge_index:
            return False

        edge = self.edge_index[key]

        # Remove from forward index
        if source_id in self.edges:
            self.edges[source_id] = [
                e for e in self.edges[source_id]
                if not (e.target_id == target_id and e.type == edge_type)
            ]

        # Remove from reverse index
        if target_id in self.reverse_edges:
            self.reverse_edges[target_id] = [
                e for e in self.reverse_edges[target_id]
                if not (e.source_id == source_id and e.type == edge_type)
            ]

        del self.edge_index[key]
        logger.debug(f"Deleted edge {edge_type} from {source_id} to {target_id}")
        return True

    async def query_nodes(self, query: CanonQuery) -> List[CanonNode]:
        """Query nodes with filters"""
        results = []

        for node in self.nodes.values():
            # Filter by type
            if query.node_type and node.type != query.node_type:
                continue

            # Filter by ID
            if query.node_id and node.id != query.node_id:
                continue

            # Filter by properties
            if query.properties_filter:
                match = True
                for key, value in query.properties_filter.items():
                    if node.properties.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(node)

            # Apply limit
            if len(results) >= query.limit:
                break

        return results

    async def query_timeline(self, query: TimelineQuery) -> List[CanonNode]:
        """Query timeline (before/after traversal)"""
        edge_types = query.edge_types or [EdgeType.BEFORE, EdgeType.AFTER]
        visited: Set[str] = set()
        results: List[CanonNode] = []
        queue = deque([(query.start_node_id, 0)])

        while queue:
            node_id, depth = queue.popleft()

            if depth > query.max_depth or node_id in visited:
                continue

            visited.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                results.append(node)

            # Get neighbors based on direction
            if query.direction in ("forward", "both"):
                # Follow AFTER edges (forward in time)
                edges = await self.get_edges(source_id=node_id, edge_type=EdgeType.AFTER)
                for edge in edges:
                    if edge.type in edge_types:
                        queue.append((edge.target_id, depth + 1))

            if query.direction in ("backward", "both"):
                # Follow BEFORE edges (backward in time)
                edges = await self.get_edges(target_id=node_id, edge_type=EdgeType.BEFORE)
                for edge in edges:
                    if edge.type in edge_types:
                        queue.append((edge.source_id, depth + 1))

        return results

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[EdgeType]] = None,
        direction: str = "both"
    ) -> List[CanonNode]:
        """Get neighboring nodes"""
        neighbors: Set[str] = set()

        if direction in ("out", "both"):
            edges = self.edges.get(node_id, [])
            for edge in edges:
                if edge_types is None or edge.type in edge_types:
                    neighbors.add(edge.target_id)

        if direction in ("in", "both"):
            edges = self.reverse_edges.get(node_id, [])
            for edge in edges:
                if edge_types is None or edge.type in edge_types:
                    neighbors.add(edge.source_id)

        return [self.nodes[nid] for nid in neighbors if nid in self.nodes]

    async def get_related_entities(
        self,
        node_id: str,
        max_depth: int = 2,
        edge_types: Optional[List[EdgeType]] = None
    ) -> List[CanonNode]:
        """Get related entities within max_depth hops"""
        visited: Set[str] = {node_id}
        results: List[CanonNode] = []
        queue = deque([(node_id, 0)])

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            neighbors = await self.get_neighbors(current_id, edge_types=edge_types, direction="both")
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    results.append(neighbor)
                    queue.append((neighbor.id, depth + 1))

        return results

    async def check_cycle(self, start_node_id: str, edge_types: Optional[List[EdgeType]] = None) -> bool:
        """Check if there's a cycle in the graph (DFS)"""
        if start_node_id not in self.nodes:
            return False

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            # Check outgoing edges
            edges = self.edges.get(node_id, [])
            for edge in edges:
                if edge_types and edge.type not in edge_types:
                    continue

                target_id = edge.target_id
                if target_id not in visited:
                    if has_cycle(target_id):
                        return True
                elif target_id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        return has_cycle(start_node_id)

    async def clear(self):
        """Clear all nodes and edges"""
        self.nodes.clear()
        self.edges.clear()
        self.reverse_edges.clear()
        self.edge_index.clear()
        logger.debug("Cleared graph store")
