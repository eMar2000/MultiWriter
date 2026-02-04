"""Memory and storage interfaces"""

from .structured_state import StructuredState, DynamoDBState
from .object_store import ObjectStore, S3ObjectStore
from .vector_store import VectorStore, QdrantVectorStore
from .local_storage import LocalFileState, LocalObjectStore
from .graph_store import GraphStore
from .in_memory_graph import InMemoryGraphStore
from .rag_retrieval import HybridRAGRetrieval

# Neo4j is optional - only import if available
try:
    from .neo4j_graph import Neo4jGraphStore
    _NEO4J_AVAILABLE = True
except ImportError:
    Neo4jGraphStore = None
    _NEO4J_AVAILABLE = False

__all__ = [
    "StructuredState",
    "DynamoDBState",
    "LocalFileState",
    "ObjectStore",
    "S3ObjectStore",
    "LocalObjectStore",
    "VectorStore",
    "QdrantVectorStore",
    "GraphStore",
    "InMemoryGraphStore",
    "HybridRAGRetrieval",
]

if _NEO4J_AVAILABLE:
    __all__.append("Neo4jGraphStore")
