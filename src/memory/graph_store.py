"""Abstract interface for GraphDB storage"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.models.canon import (
    CanonNode,
    CanonEdge,
    CanonQuery,
    TimelineQuery,
    NodeType,
    EdgeType
)


class GraphStore(ABC):
    """Abstract interface for graph storage"""

    @abstractmethod
    async def create_node(self, node: CanonNode) -> CanonNode:
        """Create a new node in the graph"""
        pass

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[CanonNode]:
        """Get a node by ID"""
        pass

    @abstractmethod
    async def update_node(self, node_id: str, **properties) -> Optional[CanonNode]:
        """Update node properties"""
        pass

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node (and its edges)"""
        pass

    @abstractmethod
    async def create_edge(self, edge: CanonEdge) -> CanonEdge:
        """Create a new edge in the graph"""
        pass

    @abstractmethod
    async def get_edges(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None
    ) -> List[CanonEdge]:
        """Get edges matching criteria"""
        pass

    @abstractmethod
    async def delete_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Delete an edge"""
        pass

    @abstractmethod
    async def query_nodes(self, query: CanonQuery) -> List[CanonNode]:
        """Query nodes with filters"""
        pass

    @abstractmethod
    async def query_timeline(self, query: TimelineQuery) -> List[CanonNode]:
        """Query timeline (before/after traversal)"""
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[EdgeType]] = None,
        direction: str = "both"  # "in", "out", "both"
    ) -> List[CanonNode]:
        """Get neighboring nodes"""
        pass

    @abstractmethod
    async def get_related_entities(
        self,
        node_id: str,
        max_depth: int = 2,
        edge_types: Optional[List[EdgeType]] = None
    ) -> List[CanonNode]:
        """Get related entities within max_depth hops"""
        pass

    @abstractmethod
    async def check_cycle(self, start_node_id: str, edge_types: Optional[List[EdgeType]] = None) -> bool:
        """Check if there's a cycle in the graph (for timeline validation)"""
        pass

    @abstractmethod
    async def clear(self):
        """Clear all nodes and edges (for testing)"""
        pass
