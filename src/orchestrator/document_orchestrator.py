"""Document-driven orchestrator with iterative planning loop"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

from src.llm import LLMProvider
from src.llm.provider import LLMMessage
from src.memory import StructuredState, VectorStore, GraphStore
from src.validation import ContinuityValidationService
from src.models import NovelInput, NovelOutline, EntityRegistry, Genre
from src.parser import build_registry
from src.orchestrator.planning_loop import PlanningLoop
from src.orchestrator.canon_sync import CanonSyncManager

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

        # Derive premise from documents when not provided or placeholder
        if novel_input is None or not novel_input.premise.strip() or novel_input.premise == "Generated from documents":
            try:
                derived_premise = await self._derive_premise_from_documents(
                    registry, worldbuilding_path, characters_path, scenes_path
                )
                genre = novel_input.genre if novel_input else Genre.OTHER
                novel_input = NovelInput(premise=derived_premise, genre=genre)
                logger.info("  Premise derived from documents")
            except Exception as e:
                logger.warning(f"  Premise derivation failed: {e}, using placeholder")
                if novel_input is None:
                    novel_input = NovelInput(premise="Generated from documents", genre=Genre.OTHER)

        # Seed GraphDB from registry so scene->character/location edges reference existing nodes
        if self.graph_store and self.validation_service:
            try:
                sync_manager = CanonSyncManager(
                    graph_store=self.graph_store,
                    validation_service=self.validation_service,
                )
                seed_result = await sync_manager.seed_registry_to_canon(registry)
                logger.info(f"  Graph seeded: {seed_result.get('nodes_created', 0)} nodes created")
            except Exception as e:
                logger.warning(f"  Failed to seed graph from registry: {e}")

        # Index entities in vector store
        if self.vector_store:
            try:
                await self._index_entities(registry, worldbuilding_path, characters_path, scenes_path)
                logger.info("  Entities indexed in vector store")
            except Exception as e:
                logger.warning(f"  Failed to index entities in vector store: {e}")

        # Execute iterative planning loop (with incremental RAG re-index after consolidation/canon sync)
        async def reindex_after_planning(reg: EntityRegistry, _outline: NovelOutline) -> None:
            if self.vector_store and reg:
                await self._index_entities(reg, worldbuilding_path, characters_path, scenes_path)

        # Pass document orchestrator to planning loop for incremental RAG updates
        self.planning_loop.document_orchestrator = self

        outline = await self.planning_loop.execute_planning_loop(
            registry=registry,
            novel_input=novel_input,
            novel_id=self.novel_id,
            on_planning_updated=reindex_after_planning if self.vector_store else None,
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

    async def _derive_premise_from_documents(
        self,
        registry: EntityRegistry,
        worldbuilding_path: Optional[Path],
        characters_path: Optional[Path],
        scenes_path: Optional[Path],
    ) -> str:
        """Produce a 1-2 sentence premise from registry and optional doc snippets."""
        summary = registry.to_context_string(max_tokens=1500)
        doc_snippets: List[str] = []
        for path, label in [
            (worldbuilding_path, "Worldbuilding"),
            (characters_path, "Characters"),
            (scenes_path, "Scenes"),
        ]:
            if path and path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        snippet = f.read(500).strip()
                    if snippet:
                        doc_snippets.append(f"--- {label} ---\n{snippet}")
                except Exception:
                    pass
        if doc_snippets:
            summary = summary + "\n\n" + "\n\n".join(doc_snippets)

        messages = [
            LLMMessage(role="system", content="You are a story analyst. Given story world and character information, output only a single 1-2 sentence premise that captures the core story. No preamble or explanation."),
            LLMMessage(role="user", content=summary[:8000]),
        ]
        response = await self.llm_provider.generate(messages, temperature=0.4, max_tokens=200)
        premise = (response.content or "").strip()
        return premise if premise else "Generated from documents"

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

    async def _index_arcs(self, arc_plan: Dict[str, Any]):
        """Index arc plans in vector store for retrieval during later phases"""
        if not self.vector_store or not hasattr(self.llm_provider, 'get_embedding'):
            return

        arcs = arc_plan.get("arcs", [])
        if not arcs:
            return

        collection_name = self.vector_store.collection_name
        embedding_model = self.config.get('rag', {}).get('embedding_model', 'nomic-embed-text')

        points = []
        for arc in arcs:
            if not isinstance(arc, dict):
                continue

            arc_id = arc.get("id", "")
            arc_name = arc.get("name", "")
            arc_desc = arc.get("description", "")

            # Create content for embedding
            content = f"{arc_name}\n\n{arc_desc}"

            # Generate embedding
            embedding = await self.llm_provider.get_embedding(content, model=embedding_model)

            points.append({
                "id": f"arc_{arc_id}",
                "vector": embedding,
                "payload": {
                    "name": arc_name,
                    "type": "arc",
                    "summary": arc_desc,
                    "content": content,
                    "arc_id": arc_id,
                    "source_doc": "generated_arc_plan"
                }
            })

        if points:
            await self.vector_store.upsert(collection_name, points)

    async def _index_scenes(self, expanded_arcs: List[Dict[str, Any]]):
        """Index generated scenes in vector store for retrieval during validation"""
        if not self.vector_store or not hasattr(self.llm_provider, 'get_embedding'):
            return

        collection_name = self.vector_store.collection_name
        embedding_model = self.config.get('rag', {}).get('embedding_model', 'nomic-embed-text')

        points = []
        for arc_data in expanded_arcs:
            arc_id = arc_data.get("arc_id", "")
            scenes = arc_data.get("scenes", [])

            for scene in scenes:
                if not isinstance(scene, dict):
                    continue

                scene_id = scene.get("scene_id", "")
                if not scene_id:
                    continue

                # Build content from scene data
                scene_name = scene.get("name", f"Scene {scene.get('scene_number', '')}")
                goal = scene.get("goal", "")
                conflict = scene.get("conflict", "")
                outcome = scene.get("outcome", "")

                content = f"{scene_name}\n\nGoal: {goal}\n\nConflict: {conflict}\n\nOutcome: {outcome}"

                # Generate embedding
                embedding = await self.llm_provider.get_embedding(content, model=embedding_model)

                points.append({
                    "id": f"scene_{scene_id}",
                    "vector": embedding,
                    "payload": {
                        "name": scene_name,
                        "type": "scene",
                        "summary": f"{goal[:100]}...",
                        "content": content,
                        "scene_id": scene_id,
                        "arc_id": arc_id,
                        "source_doc": "generated_scene"
                    }
                })

        if points:
            await self.vector_store.upsert(collection_name, points)
