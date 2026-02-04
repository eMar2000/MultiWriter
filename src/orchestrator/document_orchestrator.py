"""Document-driven orchestrator with iterative planning loop"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

from src.llm import LLMProvider
from src.memory import StructuredState, VectorStore, GraphStore
from src.validation import ContinuityValidationService
from src.models import NovelInput, NovelOutline, EntityRegistry
from src.parser import build_registry
from src.orchestrator.planning_loop import PlanningLoop

logger = logging.getLogger(__name__)


class IterativeDocumentOrchestrator:
    """Orchestrates document-to-outline pipeline with iterative planning loop"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        structured_state: StructuredState,
        vector_store: Optional[VectorStore] = None,
        graph_store: Optional[GraphStore] = None,
        validation_service: Optional[ContinuityValidationService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Iterative Document Orchestrator

        Args:
            llm_provider: LLM provider
            structured_state: Structured state storage
            vector_store: Optional vector store for RAG
            graph_store: Optional graph store for canon
            validation_service: Optional validation service
            config: Configuration dictionary
        """
        self.llm_provider = llm_provider
        self.structured_state = structured_state
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.validation_service = validation_service
        self.config = config or {}
        self.novel_id: Optional[str] = None

        # Initialize planning loop
        self.planning_loop = PlanningLoop(
            llm_provider=llm_provider,
            structured_state=structured_state,
            vector_store=vector_store,
            graph_store=graph_store,
            validation_service=validation_service,
            config=config
        )

    async def process_documents(
        self,
        worldbuilding_path: Optional[Path] = None,
        characters_path: Optional[Path] = None,
        scenes_path: Optional[Path] = None,
        novel_input: Optional[NovelInput] = None,
        novel_id: Optional[str] = None
    ) -> NovelOutline:
        """
        Main entry point: Process documents into novel outline using iterative planning

        Args:
            worldbuilding_path: Path to worldbuilding markdown
            characters_path: Path to characters markdown
            scenes_path: Path to scenes markdown
            novel_input: Optional additional input (premise, genre, etc.)
            novel_id: Optional novel ID

        Returns:
            Complete NovelOutline
        """
        self.novel_id = novel_id or str(uuid.uuid4())

        # Validate input files
        self._validate_input_files(worldbuilding_path, characters_path, scenes_path)

        # Phase 0: Ingest documents into entity registry
        logger.info("[Phase 0] Ingesting documents...")
        registry = await self._ingest_documents(
            worldbuilding_path, characters_path, scenes_path
        )
        logger.info(f"  Extracted {len(registry.entities)} entities")

        # Index entities in vector store
        if self.vector_store:
            try:
                await self._index_entities(registry, worldbuilding_path, characters_path, scenes_path)
                logger.info("  Entities indexed in vector store")
            except Exception as e:
                logger.warning(f"  Failed to index entities in vector store: {e}")

        # Execute iterative planning loop
        outline = await self.planning_loop.execute_planning_loop(
            registry=registry,
            novel_input=novel_input,
            novel_id=self.novel_id
        )

        # RAG update: re-index so next run or downstream sees current state
        if self.vector_store and registry:
            try:
                await self._index_entities(registry, worldbuilding_path, characters_path, scenes_path)
                logger.info("  RAG index updated after planning")
            except Exception as e:
                logger.warning(f"  RAG update failed: {e}")

        return outline

    def _validate_input_files(
        self,
        worldbuilding_path: Optional[Path],
        characters_path: Optional[Path],
        scenes_path: Optional[Path]
    ):
        """Validate input files before processing"""
        max_size_mb = 10
        max_size_bytes = max_size_mb * 1024 * 1024

        for path, name in [
            (worldbuilding_path, "worldbuilding"),
            (characters_path, "characters"),
            (scenes_path, "scenes")
        ]:
            if path is None:
                continue

            if not path.exists():
                raise FileNotFoundError(f"{name} file not found: {path}")

            if path.stat().st_size == 0:
                raise ValueError(f"{name} file is empty: {path}")

            if path.stat().st_size > max_size_bytes:
                logger.warning(f"{name} file is large ({path.stat().st_size / 1024 / 1024:.1f}MB), processing may be slow")

            # Try to read and validate encoding
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    f.read(1)
            except UnicodeDecodeError:
                raise ValueError(f"{name} file is not valid UTF-8: {path}")

    async def _ingest_documents(
        self,
        worldbuilding_path: Optional[Path],
        characters_path: Optional[Path],
        scenes_path: Optional[Path]
    ) -> EntityRegistry:
        """Phase 0: Parse documents and extract entities"""
        registry = build_registry(
            worldbuilding_path=worldbuilding_path,
            characters_path=characters_path,
            scenes_path=scenes_path
        )
        return registry

    async def _index_entities(
        self,
        registry: EntityRegistry,
        worldbuilding_path: Optional[Path],
        characters_path: Optional[Path],
        scenes_path: Optional[Path]
    ):
        """Index entities in vector store for RAG retrieval"""
        if not self.vector_store or not hasattr(self.llm_provider, 'get_embedding'):
            return

        from src.parser import EntityExtractor

        extractor = EntityExtractor()
        full_content_map = {}
        parsed_files: Dict[Path, list] = {}

        for entity_id, entity in registry.entities.items():
            source_doc = entity.source_doc
            file_path = None

            if source_doc == "worldbuilding" and worldbuilding_path:
                file_path = worldbuilding_path
            elif source_doc == "characters" and characters_path:
                file_path = characters_path
            elif source_doc == "scenes" and scenes_path:
                file_path = scenes_path

            if file_path and file_path.exists():
                if file_path not in parsed_files:
                    sections = extractor.parser.parse_file(file_path)
                    parsed_files[file_path] = extractor.parser.flatten_sections(sections)

                flat_sections = parsed_files[file_path]
                for section in flat_sections:
                    if section.title == entity.name:
                        full_content_map[entity_id] = section.content
                        break

        for entity_id, entity in registry.entities.items():
            if entity_id not in full_content_map:
                full_content_map[entity_id] = entity.summary

        vector_size = self.config.get('rag', {}).get('vector_size', 768)
        embedding_model = self.config.get('rag', {}).get('embedding_model', 'nomic-embed-text')

        collection_name = self.vector_store.collection_name
        await self.vector_store.create_collection(
            collection_name=collection_name,
            vector_size=vector_size,
            distance="Cosine"
        )

        async def get_embedding(text: str) -> list[float]:
            return await self.llm_provider.get_embedding(text, model=embedding_model)

        await self.vector_store.index_entities(
            collection_name=collection_name,
            registry=registry,
            full_content_map=full_content_map,
            embedding_fn=get_embedding
        )
