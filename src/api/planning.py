"""
Single entry point for pre-writing plan generation.

Used by the CLI and intended for future web API (e.g. Next.js backend).
All dependencies (LLM, storage, graph, validation) are built from config
and passed in; no global singletons. Stateless: novel_id + storage are
the source of truth.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from src.models import NovelInput, NovelOutline, Genre
from src.llm import OllamaClient
from src.memory import (
    LocalFileState,
    LocalObjectStore,
    QdrantVectorStore,
    InMemoryGraphStore,
)
from src.validation import ContinuityValidationService
from src.orchestrator import DocumentOrchestrator

logger = logging.getLogger(__name__)


def _create_llm(config: Dict[str, Any]) -> OllamaClient:
    llm_config = config.get("llm", {})
    return OllamaClient(
        model=llm_config.get("model", "llama3.1:70b"),
        base_url=llm_config.get("base_url", "http://localhost:11434"),
        timeout=llm_config.get("timeout", 300)
    )


def _create_storage(config: Dict[str, Any]):
    """Build structured_state, object_store, vector_store, graph_store, validation_service from config."""
    storage_config = config.get("storage", {})
    provider = storage_config.get("provider", "local")

    if provider == "local":
        local_config = storage_config.get("local", {})
        structured_state = LocalFileState(
            storage_dir=local_config.get("data_dir", "./data")
        )
        object_store = LocalObjectStore(
            storage_dir=local_config.get("objects_dir", "./data/objects")
        )
    else:
        from src.memory import DynamoDBState, S3ObjectStore
        dynamodb_config = storage_config.get("dynamodb", {})
        structured_state = DynamoDBState(
            region=dynamodb_config.get("region", "us-east-1"),
            endpoint_url=dynamodb_config.get("endpoint_url"),
            table_prefix=""
        )
        s3_config = storage_config.get("s3", {})
        object_store = S3ObjectStore(
            bucket=s3_config.get("bucket", "multiwriter-outlines"),
            region=s3_config.get("region", "us-east-1"),
            endpoint_url=s3_config.get("endpoint_url")
        )

    vector_store = None
    qdrant_config = storage_config.get("qdrant", {})
    if qdrant_config.get("enabled", False):
        try:
            vector_store = QdrantVectorStore(
                host=qdrant_config.get("host", "localhost"),
                port=qdrant_config.get("port", 6333),
                collection_name=qdrant_config.get("collection_name", "multiwriter-embeddings"),
                vector_size=qdrant_config.get("vector_size", 768)
            )
        except Exception:
            pass

    graph_config = config.get("graph", {}) or {}
    graph_provider = graph_config.get("provider", "in_memory")
    if graph_provider == "neo4j":
        try:
            from src.memory import Neo4jGraphStore
            graph_store = Neo4jGraphStore(
                uri=graph_config.get("uri", "bolt://localhost:7687"),
                user=graph_config.get("user", "neo4j"),
                password=graph_config.get("password", "password"),
                database=graph_config.get("database", "neo4j")
            )
        except Exception:
            graph_store = InMemoryGraphStore()
    else:
        graph_store = InMemoryGraphStore()

    validation_service = ContinuityValidationService(graph_store=graph_store)
    return structured_state, object_store, vector_store, graph_store, validation_service


async def run_planning(
    worldbuilding_path: Optional[Path] = None,
    characters_path: Optional[Path] = None,
    scenes_path: Optional[Path] = None,
    novel_input: Optional[NovelInput] = None,
    novel_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[NovelOutline]:
    """
    Generate a pre-writing plan (outline) from document paths and config.

    This is the single async entry point for the planning pipeline.
    Used by the CLI and by a future web backend. Dependencies are
    built from config (no globals).

    Args:
        worldbuilding_path: Path to worldbuilding markdown
        characters_path: Path to characters markdown
        scenes_path: Path to scenes markdown
        novel_input: Optional premise, genre, etc.
        novel_id: Optional novel ID (generated if not provided)
        config: App config (storage, graph, llm). If None, minimal defaults.

    Returns:
        NovelOutline or None on failure
    """
    config = config or {}
    novel_input = novel_input or NovelInput(premise="Generated from documents", genre=Genre.OTHER)

    llm_provider = _create_llm(config)
    structured_state, object_store, vector_store, graph_store, validation_service = _create_storage(config)

    orchestrator = DocumentOrchestrator(
        llm_provider=llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        graph_store=graph_store,
        validation_service=validation_service,
        config=config
    )

    try:
        outline = await orchestrator.process_documents(
            worldbuilding_path=worldbuilding_path,
            characters_path=characters_path,
            scenes_path=scenes_path,
            novel_input=novel_input,
            novel_id=novel_id
        )
        return outline
    finally:
        await llm_provider.close()
