"""Document-driven orchestrator for novel outline generation"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from src.agents import (
    SceneDynamicsAgent,
    SynthesisAgent,
    OutlineArchitectAgent,
    CoverageVerifierAgent,
)
from src.llm import LLMProvider
from src.memory import StructuredState, VectorStore
from src.models import NovelInput, NovelOutline, EntityRegistry
from src.parser import build_registry, EntityExtractor

logger = logging.getLogger(__name__)


class DocumentOrchestrator:
    """Orchestrates document-to-outline pipeline"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        structured_state: StructuredState,
        vector_store: Optional[VectorStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.llm_provider = llm_provider
        self.structured_state = structured_state
        self.vector_store = vector_store
        self.config = config or {}
        self.novel_id: Optional[str] = None

    async def process_documents(
        self,
        worldbuilding_path: Optional[Path] = None,
        characters_path: Optional[Path] = None,
        scenes_path: Optional[Path] = None,
        novel_input: Optional[NovelInput] = None,
        novel_id: Optional[str] = None
    ) -> NovelOutline:
        """
        Main entry point: Process documents into novel outline

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

        # Phase 1: Ingest documents into entity registry
        logger.info("[Phase 1] Ingesting documents...")
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

        # Phase 2: Synthesize relationships and plan arcs
        logger.info("[Phase 2] Analyzing relationships and planning...")
        arc_plan = await self._plan_arcs(registry, novel_input)
        logger.info(f"  Created {len(arc_plan.get('arcs', []))} arcs")

        # Phase 3: Verify coverage
        logger.info("[Phase 3] Verifying entity coverage...")
        coverage = await self._verify_coverage(registry, arc_plan)
        logger.info(f"  Coverage: {coverage.get('coverage_percentage', 0)}%")

        # Phase 4: Expand arcs (can be parallel in future)
        logger.info("[Phase 4] Expanding arcs into scenes...")
        expanded_arcs = await self._expand_arcs(arc_plan, registry, novel_input)

        # Phase 5: Consolidate into final outline
        logger.info("[Phase 5] Consolidating outline...")
        outline = await self._consolidate(
            registry, arc_plan, expanded_arcs, novel_input
        )

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

            # Check if it's a markdown file
            if path.suffix.lower() not in ['.md', '.markdown']:
                logger.warning(f"{name} file doesn't have .md extension: {path}")

            # Try to read and validate encoding
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    f.read(1)  # Try to read at least one character
            except UnicodeDecodeError:
                raise ValueError(f"{name} file is not valid UTF-8: {path}")

    async def _ingest_documents(
        self,
        worldbuilding_path: Optional[Path],
        characters_path: Optional[Path],
        scenes_path: Optional[Path]
    ) -> EntityRegistry:
        """Phase 1: Parse documents and extract entities"""
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

        # Build full content map from source files
        extractor = EntityExtractor()
        full_content_map = {}

        # Cache parsed files to avoid re-parsing (optimization)
        parsed_files: Dict[Path, List] = {}

        # Read full content for each entity
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
                # Parse file once and cache
                if file_path not in parsed_files:
                    sections = extractor.parser.parse_file(file_path)
                    parsed_files[file_path] = extractor.parser.flatten_sections(sections)

                flat_sections = parsed_files[file_path]
                for section in flat_sections:
                    if section.title == entity.name:
                        full_content_map[entity_id] = section.content
                        break

        # Use entity summary as fallback
        for entity_id, entity in registry.entities.items():
            if entity_id not in full_content_map:
                full_content_map[entity_id] = entity.summary

        # Get vector size from config or use default
        vector_size = self.config.get('rag', {}).get('vector_size', 768)
        embedding_model = self.config.get('rag', {}).get('embedding_model', 'nomic-embed-text')

        # Create collection if needed
        collection_name = self.vector_store.collection_name
        await self.vector_store.create_collection(
            collection_name=collection_name,
            vector_size=vector_size,
            distance="Cosine"
        )

        # Index entities
        async def get_embedding(text: str) -> List[float]:
            return await self.llm_provider.get_embedding(text, model=embedding_model)

        await self.vector_store.index_entities(
            collection_name=collection_name,
            registry=registry,
            full_content_map=full_content_map,
            embedding_fn=get_embedding
        )

    async def _plan_arcs(
        self,
        registry: EntityRegistry,
        novel_input: Optional[NovelInput]
    ) -> Dict[str, Any]:
        """Phase 2: Synthesize relationships and create arc plan"""
        context = {
            "entity_registry": registry,
            "novel_input": novel_input.model_dump() if novel_input else {}
        }

        # Run synthesis agent
        synthesis_agent = SynthesisAgent(
            llm_provider=self.llm_provider,
            structured_state=self.structured_state,
            vector_store=self.vector_store,
            novel_id=self.novel_id
        )
        synthesis_result = await synthesis_agent.execute(context)

        # Update context with relationships
        context.update({
            "relationships": synthesis_result["output"].get("relationships", []),
            "conflicts": synthesis_result["output"].get("conflicts", []),
            "themes": synthesis_result["output"].get("themes", [])
        })

        # Run outline architect
        architect_agent = OutlineArchitectAgent(
            llm_provider=self.llm_provider,
            structured_state=self.structured_state,
            vector_store=self.vector_store,
            novel_id=self.novel_id
        )
        architect_result = await architect_agent.execute(context)

        return architect_result["output"]

    async def _verify_coverage(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 3: Verify all entities are referenced"""
        context = {
            "entity_registry": registry,
            "arc_plan": arc_plan
        }

        verifier = CoverageVerifierAgent(
            llm_provider=self.llm_provider,
            structured_state=self.structured_state,
            novel_id=self.novel_id
        )
        result = await verifier.execute(context)

        # If coverage is low, could iterate here
        return result["output"]

    async def _expand_arcs(
        self,
        arc_plan: Dict[str, Any],
        registry: EntityRegistry,
        novel_input: Optional[NovelInput]
    ) -> List[Dict[str, Any]]:
        """Phase 4: Expand each arc into detailed scenes"""
        expanded = []

        # Use existing scene_dynamics agent for now
        scene_agent = SceneDynamicsAgent(
            llm_provider=self.llm_provider,
            structured_state=self.structured_state,
            vector_store=self.vector_store,
            novel_id=self.novel_id
        )

        for arc in arc_plan.get("arcs", []):
            arc_id = arc.get("id", "unknown") if isinstance(arc, dict) else getattr(arc, "id", "unknown")
            context = {
                "arc": arc,
                "entity_registry": registry,
                "novel_input": novel_input.model_dump() if novel_input else {}
            }

            # For now, use scene agent per arc
            # Future: Create dedicated ArcExpanderAgent
            try:
                result = await scene_agent.execute(context)
                expanded.append({
                    "arc_id": arc_id,
                    "scenes": result["output"].get("scenes", [])
                })
            except Exception as e:
                logger.warning(f"  Failed to expand arc {arc_id}: {e}", exc_info=True)
                expanded.append({"arc_id": arc_id, "scenes": []})

        return expanded

    async def _consolidate(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        expanded_arcs: List[Dict[str, Any]],
        novel_input: Optional[NovelInput]
    ) -> NovelOutline:
        """Phase 5: Build final outline from all components"""

        # Collect all scenes
        all_scenes = []
        for arc_expansion in expanded_arcs:
            all_scenes.extend(arc_expansion.get("scenes", []))

        # Build outline
        outline = NovelOutline(
            id=self.novel_id,
            input=novel_input,
            entity_registry=registry,
            scenes=all_scenes,
            status="completed",
            updated_at=datetime.utcnow()
        )

        # Add arc structure to relationships
        outline.relationships = {
            "arcs": arc_plan.get("arcs", []),
            "timeline": arc_plan.get("timeline", []),
            "themes": arc_plan.get("themes", [])
        }

        # Save to storage
        await self.structured_state.write(
            "novel-outlines",
            outline.model_dump(mode='json')
        )

        return outline
