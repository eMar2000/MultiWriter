"""Qdrant interface for vector embeddings"""

from typing import List, Optional, Dict, Any, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from src.models import EntityRegistry
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)


class VectorStore(ABC):
    """Abstract interface for vector storage"""

    @abstractmethod
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine"
    ) -> bool:
        """Create a vector collection"""
        pass

    @abstractmethod
    async def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ) -> bool:
        """Upsert vectors into the collection"""
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        pass

    @abstractmethod
    async def delete(
        self,
        collection_name: str,
        point_ids: List[str]
    ) -> bool:
        """Delete vectors by IDs"""
        pass


class QdrantVectorStore(VectorStore):
    """Qdrant implementation of vector storage"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "multiwriter-embeddings",
        vector_size: int = 768
    ):
        """
        Initialize Qdrant client

        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Default collection name
            vector_size: Default vector dimension
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Initialize async client
        url = f"http://{host}:{port}"
        self.client = AsyncQdrantClient(url=url)

    def _get_distance(self, distance: str) -> Distance:
        """Convert distance string to Qdrant Distance enum"""
        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclidean": Distance.EUCLID,
            "Dot": Distance.DOT,
        }
        return distance_map.get(distance, Distance.COSINE)

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine"
    ) -> bool:
        """Create a vector collection in Qdrant"""
        try:
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=self._get_distance(distance)
                )
            )
            return True
        except Exception as e:
            # Collection might already exist
            if "already exists" in str(e).lower():
                return True
            raise RuntimeError(f"Qdrant create_collection error: {str(e)}") from e

    async def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ) -> bool:
        """Upsert vectors into Qdrant"""
        try:
            qdrant_points = []
            for point in points:
                point_id = point.get("id")
                vector = point.get("vector")
                payload = point.get("payload", {})

                if point_id is None or vector is None:
                    continue

                qdrant_points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                )

            if qdrant_points:
                await self.client.upsert(
                    collection_name=collection_name,
                    points=qdrant_points
                )
            return True
        except Exception as e:
            raise RuntimeError(f"Qdrant upsert error: {str(e)}") from e

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant"""
        try:
            # Build filter if provided
            qdrant_filter = None
            if filter:
                conditions = []
                for key, value in filter.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                if conditions:
                    qdrant_filter = Filter(must=conditions)

            results = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter
            )

            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                }
                for result in results
            ]
        except Exception as e:
            raise RuntimeError(f"Qdrant search error: {str(e)}") from e

    async def delete(
        self,
        collection_name: str,
        point_ids: List[str]
    ) -> bool:
        """Delete vectors by IDs from Qdrant"""
        try:
            await self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids
            )
            return True
        except Exception as e:
            raise RuntimeError(f"Qdrant delete error: {str(e)}") from e

    async def retrieve_by_ids(
        self,
        collection_name: str,
        entity_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Retrieve entities by their IDs (deterministic)"""
        try:
            results = []
            # Qdrant retrieve method
            retrieved = await self.client.retrieve(
                collection_name=collection_name,
                ids=entity_ids
            )

            for point in retrieved:
                results.append({
                    "id": str(point.id),
                    "payload": point.payload
                })

            return results
        except Exception as e:
            raise RuntimeError(f"Qdrant retrieve_by_ids error: {str(e)}") from e

    async def retrieve_related(
        self,
        collection_name: str,
        query: str,
        embedding_fn: Callable[[str], Any],
        top_k: int = 10,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve semantically related entities"""
        # Generate embedding
        query_embedding = await embedding_fn(query)

        # Build filter if entity_type specified
        filter_dict = None
        if entity_type:
            filter_dict = {"type": entity_type}

        return await self.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k,
            filter=filter_dict
        )

    async def index_entities(
        self,
        collection_name: str,
        registry: 'EntityRegistry',
        full_content_map: Dict[str, str],
        embedding_fn: Callable[[str], Any]
    ) -> bool:
        """Index all entities with their full content for retrieval"""
        points = []

        for entity_id, entity in registry.entities.items():
            full_content = full_content_map.get(entity_id, entity.summary)

            # Generate embedding
            embedding = await embedding_fn(full_content)

            # entity_type may be an enum or string (depending on use_enum_values config)
            entity_type_str = entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type)
            points.append({
                "id": entity_id,
                "vector": embedding,
                "payload": {
                    "name": entity.name,
                    "type": entity_type_str,
                    "summary": entity.summary,
                    "content": full_content,
                    "tags": entity.tags,
                    "source_doc": entity.source_doc
                }
            })

        return await self.upsert(collection_name, points)
