"""Hybrid RAG Retrieval - Combines vector search with graph enrichment"""

import logging
from typing import List, Dict, Any, Optional, Callable
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.object_store import ObjectStore
from src.models.canon import CanonNode, EdgeType

logger = logging.getLogger(__name__)


class HybridRAGRetrieval:
    """Hybrid retrieval combining vector search, graph queries, and blob storage"""

    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: Optional[GraphStore] = None,
        object_store: Optional[ObjectStore] = None,
        collection_name: str = "multiwriter-embeddings"
    ):
        """
        Initialize hybrid RAG retrieval

        Args:
            vector_store: Vector store for semantic search
            graph_store: Optional graph store for canon enrichment
            object_store: Optional object store for full content chunks
            collection_name: Vector collection name
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.object_store = object_store
        self.collection_name = collection_name

    async def retrieve(
        self,
        query: str,
        embedding_fn: Callable[[str], List[float]],
        top_k: int = 10,
        entity_type: Optional[str] = None,
        enrich_with_canon: bool = True,
        include_full_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: vector search + graph enrichment + blob content

        Args:
            query: Query string
            embedding_fn: Function to generate embeddings
            top_k: Number of results
            entity_type: Optional entity type filter
            enrich_with_canon: Whether to enrich with canon facts
            include_full_content: Whether to fetch full content from blob storage

        Returns:
            List of enriched results with metadata
        """
        # Step 1: Vector search (semantic match)
        query_embedding = await embedding_fn(query)

        filter_dict = None
        if entity_type:
            filter_dict = {"type": entity_type}

        vector_results = await self.vector_store.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            filter=filter_dict
        )

        logger.debug(f"Vector search returned {len(vector_results)} results")

        # Step 2: Enrich with canon facts from graph
        enriched_results = []
        for result in vector_results:
            enriched = {
                "id": result["id"],
                "score": result["score"],
                "payload": result["payload"].copy(),
                "canon_facts": [],
                "relationships": [],
                "full_content": None
            }

            entity_id = result["id"]

            # Enrich with graph facts if available
            if enrich_with_canon and self.graph_store:
                try:
                    node = await self.graph_store.get_node(entity_id)
                    if node:
                        # Add canon metadata
                        enriched["canon_node"] = {
                            "id": node.id,
                            "type": node.type,
                            "properties": node.properties,
                            "version": node.version
                        }

                        # Get relationships
                        neighbors = await self.graph_store.get_neighbors(
                            entity_id,
                            direction="both"
                        )
                        enriched["relationships"] = [
                            {
                                "id": n.id,
                                "type": n.type,
                                "name": n.properties.get("name", n.id)
                            }
                            for n in neighbors[:5]  # Limit to 5 relationships
                        ]

                        # Get timeline context (if event)
                        if node.type.value in ("event", "scene", "chapter"):
                            timeline_edges = await self.graph_store.get_edges(
                                source_id=entity_id,
                                edge_type=EdgeType.BEFORE
                            )
                            enriched["canon_facts"].append({
                                "type": "timeline",
                                "before_events": len(timeline_edges)
                            })
                except Exception as e:
                    logger.warning(f"Failed to enrich {entity_id} with canon: {e}")

            # Step 3: Fetch full content from blob storage if requested
            if include_full_content and self.object_store:
                try:
                    # Try to fetch full content chunk
                    content_key = f"entities/{entity_id}/content.txt"
                    content = await self.object_store.download(content_key)
                    if content:
                        enriched["full_content"] = content.decode("utf-8") if isinstance(content, bytes) else content
                except Exception as e:
                    logger.debug(f"Could not fetch full content for {entity_id}: {e}")
                    # Fallback to payload content
                    enriched["full_content"] = result["payload"].get("content", result["payload"].get("summary", ""))

            enriched_results.append(enriched)

        return enriched_results

    async def retrieve_by_ids(
        self,
        entity_ids: List[str],
        enrich_with_canon: bool = True,
        include_full_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve entities by IDs (deterministic, not semantic)

        Args:
            entity_ids: List of entity IDs
            enrich_with_canon: Whether to enrich with canon facts
            include_full_content: Whether to fetch full content

        Returns:
            List of enriched entity data
        """
        results = []

        # Get from vector store (by ID)
        vector_data = await self.vector_store.retrieve_by_ids(
            collection_name=self.collection_name,
            entity_ids=entity_ids
        )

        # Enrich each result
        for data in vector_data:
            entity_id = data["id"]
            enriched = {
                "id": entity_id,
                "payload": data["payload"].copy(),
                "canon_facts": [],
                "relationships": [],
                "full_content": None
            }

            # Enrich with graph
            if enrich_with_canon and self.graph_store:
                try:
                    node = await self.graph_store.get_node(entity_id)
                    if node:
                        enriched["canon_node"] = {
                            "id": node.id,
                            "type": node.type,
                            "properties": node.properties,
                            "version": node.version
                        }

                        # Get relationships
                        neighbors = await self.graph_store.get_neighbors(
                            entity_id,
                            direction="both"
                        )
                        enriched["relationships"] = [
                            {
                                "id": n.id,
                                "type": n.type,
                                "name": n.properties.get("name", n.id)
                            }
                            for n in neighbors
                        ]
                except Exception as e:
                    logger.warning(f"Failed to enrich {entity_id} with canon: {e}")

            # Fetch full content if requested
            if include_full_content and self.object_store:
                try:
                    content_key = f"entities/{entity_id}/content.txt"
                    content = await self.object_store.download(content_key)
                    if content:
                        enriched["full_content"] = content.decode("utf-8") if isinstance(content, bytes) else content
                except Exception as e:
                    logger.debug(f"Could not fetch full content for {entity_id}: {e}")
                    enriched["full_content"] = data["payload"].get("content", data["payload"].get("summary", ""))

            results.append(enriched)

        return results

    async def build_context(
        self,
        query: str,
        embedding_fn: Callable[[str], List[float]],
        max_tokens: int = 2000,
        top_k: int = 10
    ) -> str:
        """
        Build context string from hybrid retrieval

        Args:
            query: Query string
            embedding_fn: Embedding function
            max_tokens: Maximum tokens in context
            top_k: Number of results to retrieve

        Returns:
            Formatted context string
        """
        results = await self.retrieve(
            query=query,
            embedding_fn=embedding_fn,
            top_k=top_k,
            enrich_with_canon=True,
            include_full_content=False  # Use summaries for context
        )

        context_parts = []
        token_count = 0

        for result in results:
            payload = result["payload"]
            name = payload.get("name", result["id"])
            summary = payload.get("summary", payload.get("content", ""))
            entity_type = payload.get("type", "unknown")

            # Add entity summary
            entity_text = f"[{entity_type}] {name}: {summary}"
            entity_tokens = len(entity_text.split())  # Rough estimate

            if token_count + entity_tokens > max_tokens:
                break

            context_parts.append(entity_text)
            token_count += entity_tokens

            # Add canon facts if available
            if result.get("canon_node"):
                canon = result["canon_node"]
                canon_text = f"  Canon: {canon['type']} (v{canon['version']})"
                canon_tokens = len(canon_text.split())
                if token_count + canon_tokens <= max_tokens:
                    context_parts.append(canon_text)
                    token_count += canon_tokens

            # Add relationships if available
            if result.get("relationships"):
                rels = result["relationships"][:3]  # Limit to 3
                rel_names = [r["name"] for r in rels]
                rel_text = f"  Related: {', '.join(rel_names)}"
                rel_tokens = len(rel_text.split())
                if token_count + rel_tokens <= max_tokens:
                    context_parts.append(rel_text)
                    token_count += rel_tokens

        return "\n".join(context_parts)
