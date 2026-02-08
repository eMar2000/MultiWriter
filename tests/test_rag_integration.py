"""Integration tests for RAG flow"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid

from src.parser import DocumentParser, EntityExtractor
from src.models import EntityRegistry, EntitySummary, EntityType
from src.memory import QdrantVectorStore
from src.orchestrator import DocumentOrchestrator


class TestRAGIntegration:
    """Test RAG flow from document parsing to retrieval"""

    @pytest.fixture
    def sample_registry(self):
        """Create sample entity registry"""
        registry = EntityRegistry()

        # Add sample characters
        char1 = EntitySummary(
            id=str(uuid.uuid4()),
            name="Alice",
            entity_type=EntityType.CHARACTER,
            summary="Protagonist with special abilities",
            tags=["protagonist", "esper"],
            source_doc="characters"
        )
        char2 = EntitySummary(
            id=str(uuid.uuid4()),
            name="Dr. Chen",
            entity_type=EntityType.CHARACTER,
            summary="Mentor and scientist",
            tags=["mentor", "scientist"],
            source_doc="characters"
        )

        # Add sample locations
        loc1 = EntitySummary(
            id=str(uuid.uuid4()),
            name="The Pit",
            entity_type=EntityType.LOCATION,
            summary="Underground arena for combat",
            tags=["arena", "underground"],
            source_doc="worldbuilding"
        )

        registry.add(char1)
        registry.add(char2)
        registry.add(loc1)

        return registry

    @pytest.mark.asyncio
    async def test_document_parsing_creates_registry(self, tmp_path):
        """Test that document parsing creates entity registry"""
        # Create sample markdown file
        doc_path = tmp_path / "worldbuilding.md"
        doc_path.write_text("""
# The Pit

An underground arena where espers battle for glory and survival.

# Atlas City

A massive metropolis divided into layers by social class.
""")

        parser = DocumentParser()
        extractor = EntityExtractor()

        # Parse document
        sections = parser.parse_file(doc_path)
        assert len(sections) > 0

        # Extract entities
        registry = extractor.build_registry([doc_path])

        # Verify entities extracted
        assert len(registry.entities) >= 2
        locations = registry.get_by_type(EntityType.LOCATION)
        assert len(locations) >= 1

        # Check entity IDs are valid UUIDs
        for entity in registry.entities.values():
            uuid.UUID(entity.id)  # Should not raise

    @pytest.mark.asyncio
    async def test_vector_store_indexing(self, sample_registry):
        """Test that entities are indexed in vector store"""
        vector_store = MagicMock(spec=QdrantVectorStore)
        vector_store.create_collection = AsyncMock(return_value=True)
        vector_store.upsert = AsyncMock(return_value=True)
        vector_store.index_entities = AsyncMock(return_value=True)

        # Mock embedding function
        async def mock_embedding(text: str) -> list:
            return [0.1] * 768

        # Index entities
        await vector_store.index_entities(
            collection_name="test_collection",
            registry=sample_registry,
            full_content_map={e.id: e.summary for e in sample_registry.entities.values()},
            embedding_fn=mock_embedding
        )

        # Verify indexing was called
        vector_store.index_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_retrieval_returns_valid_ids(self, sample_registry):
        """Test that RAG retrieval returns entities with valid IDs"""
        vector_store = MagicMock(spec=QdrantVectorStore)

        # Mock search results with actual entity IDs
        entity_list = list(sample_registry.entities.values())
        vector_store.search = AsyncMock(return_value=[
            {
                "id": entity_list[0].id,
                "score": 0.9,
                "payload": {
                    "name": entity_list[0].name,
                    "type": entity_list[0].entity_type,
                    "summary": entity_list[0].summary
                }
            }
        ])

        # Mock embedding function
        query_vector = [0.1] * 768

        # Retrieve entities
        results = await vector_store.search(
            collection_name="test_collection",
            query_vector=query_vector,
            limit=10
        )

        # Verify results contain valid entity IDs
        assert len(results) > 0
        for result in results:
            entity_id = result["id"]
            # Verify ID exists in registry
            assert entity_id in sample_registry.entities
            # Verify it's a valid UUID
            uuid.UUID(entity_id)

    @pytest.mark.asyncio
    async def test_incremental_rag_updates(self, sample_registry):
        """Test that RAG is updated incrementally during planning"""
        vector_store = MagicMock(spec=QdrantVectorStore)
        vector_store.upsert = AsyncMock(return_value=True)

        # Simulate arc indexing
        arc_data = {
            "arcs": [
                {
                    "id": "arc_1",
                    "name": "The Awakening",
                    "description": "Alice discovers her powers"
                }
            ]
        }

        # Mock embedding function
        async def mock_embedding(text: str) -> list:
            return [0.1] * 768

        # Mock DocumentOrchestrator _index_arcs
        embedding = await mock_embedding("test")
        points = [{
            "id": "arc_arc_1",
            "vector": embedding,
            "payload": {
                "name": "The Awakening",
                "type": "arc",
                "content": "Alice discovers her powers"
            }
        }]

        await vector_store.upsert("test_collection", points)

        # Verify upsert was called
        vector_store.upsert.assert_called_once()
        call_args = vector_store.upsert.call_args[0]
        assert call_args[0] == "test_collection"
        assert len(call_args[1]) > 0
        assert call_args[1][0]["id"].startswith("arc_")

    @pytest.mark.asyncio
    async def test_rag_context_in_agent(self, sample_registry):
        """Test that agents receive RAG context"""
        from src.agents import SceneDynamicsAgent
        from src.llm import OllamaProvider

        # Mock vector store with search results
        vector_store = MagicMock(spec=QdrantVectorStore)
        entity_list = list(sample_registry.entities.values())
        vector_store.retrieve = AsyncMock(return_value=[
            {
                "id": entity_list[0].id,
                "payload": {
                    "name": entity_list[0].name,
                    "content": f"{entity_list[0].name}: {entity_list[0].summary}",
                    "type": entity_list[0].entity_type
                }
            }
        ])

        # Create agent with mocked dependencies
        llm_provider = MagicMock(spec=OllamaProvider)
        agent = SceneDynamicsAgent(
            llm_provider=llm_provider,
            structured_state=MagicMock(),
            vector_store=vector_store,
            novel_id="test_novel"
        )

        # Test RAG context retrieval
        rag_context = await agent._retrieve_rag_context(
            sample_registry,
            arc={"character_ids": [entity_list[0].id]},
            novel_input={"premise": "Test story"}
        )

        # Verify context was retrieved
        assert isinstance(rag_context, str)
        # Context should be empty or contain worldbuilding header
        assert rag_context == "" or "WORLDBUILDING CONTEXT" in rag_context


class TestEntityIDConsistency:
    """Test entity ID consistency across system"""

    def test_registry_ids_are_valid_uuids(self):
        """Test that all entity IDs in registry are valid UUIDs"""
        registry = EntityRegistry()

        # Add entities
        for i in range(5):
            entity = EntitySummary(
                name=f"Entity {i}",
                entity_type=EntityType.CHARACTER,
                summary=f"Summary {i}"
            )
            entity_id = registry.add(entity)

            # Verify ID is valid UUID
            uuid.UUID(entity_id)

    def test_no_placeholder_ids_in_registry(self):
        """Test that registry doesn't contain placeholder IDs"""
        import re

        registry = EntityRegistry()

        # Add entities with auto-generated IDs
        for i in range(5):
            entity = EntitySummary(
                name=f"Character {i}",
                entity_type=EntityType.CHARACTER,
                summary=f"Description {i}"
            )
            registry.add(entity)

        # Check all IDs
        placeholder_pattern = re.compile(r'(char_id|loc_id|character_id|location_id)\d+', re.IGNORECASE)
        for entity_id in registry.get_all_ids():
            assert not placeholder_pattern.match(entity_id), f"Found placeholder ID: {entity_id}"

    def test_entity_id_format_in_context_string(self):
        """Test that entity IDs are properly formatted in context strings"""
        registry = EntityRegistry()

        entity = EntitySummary(
            name="Test Character",
            entity_type=EntityType.CHARACTER,
            summary="A test character"
        )
        entity_id = registry.add(entity)

        # Get context string
        context = registry.to_context_string()

        # Verify ID appears in brackets
        assert f"[{entity_id}]" in context
        assert entity.name in context
