"""Qdrant interface for vector embeddings"""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
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

        # Initialize sync client for now (can be made async later)
        self.client = QdrantClient(host=host, port=port)

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
            self.client.create_collection(
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
                self.client.upsert(
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

            results = self.client.search(
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
            self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids
            )
            return True
        except Exception as e:
            raise RuntimeError(f"Qdrant delete error: {str(e)}") from e
