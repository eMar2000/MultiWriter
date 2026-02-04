"""Integration tests for document-driven outline generation and planning agents"""

import pytest
import asyncio
from pathlib import Path
import uuid
from datetime import datetime, timezone

from src.models import NovelInput, Genre, EntityRegistry, EntitySummary, EntityType
from src.models import NovelOutline, SceneOutline, SceneType
from src.llm import OllamaClient
from src.memory import LocalFileState, LocalObjectStore, InMemoryGraphStore
from src.validation import ContinuityValidationService
from src.orchestrator import IterativeDocumentOrchestrator
from src.export import MarkdownExporter


@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        "llm": {
            "model": "llama3.1:70b",
            "base_url": "http://localhost:11434",
            "timeout": 300
        },
        "storage": {
            "provider": "local",
            "local": {
                "data_dir": "./data_test",
                "objects_dir": "./data_test/objects"
            }
        },
        "graph": {
            "provider": "in_memory"
        }
    }


@pytest.fixture
def test_llm_provider(test_config):
    """Create test LLM provider"""
    llm_config = test_config["llm"]
    return OllamaClient(
        model=llm_config["model"],
        base_url=llm_config["base_url"],
        timeout=llm_config["timeout"]
    )


@pytest.fixture
def test_storage(test_config):
    """Create test storage instances (local + in-memory graph for planning loop)"""
    storage_config = test_config["storage"].get("local", {})
    structured_state = LocalFileState(
        storage_dir=storage_config.get("data_dir", "./data_test")
    )
    object_store = LocalObjectStore(
        storage_dir=storage_config.get("objects_dir", "./data_test/objects")
    )
    vector_store = None  # Optional for tests
    graph_store = InMemoryGraphStore()
    validation_service = ContinuityValidationService(graph_store=graph_store)
    return structured_state, object_store, vector_store, graph_store, validation_service


@pytest.fixture
def test_storage_simple(test_config):
    """Minimal storage for agent-only tests (no graph)."""
    storage_config = test_config["storage"].get("local", {})
    structured_state = LocalFileState(
        storage_dir=storage_config.get("data_dir", "./data_test")
    )
    return structured_state, None  # vector_store optional


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama - run manually")
async def test_synthesis_agent(test_llm_provider, test_storage_simple):
    """Test Synthesis agent with minimal registry"""
    structured_state, vector_store = test_storage_simple

    from src.agents import SynthesisAgent

    novel_id = str(uuid.uuid4())
    agent = SynthesisAgent(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        novel_id=novel_id
    )

    registry = EntityRegistry(entities={
        "char1": EntitySummary(
            id="char1",
            name="Hero",
            entity_type=EntityType.CHARACTER,
            summary="The protagonist",
            source_doc="characters"
        ),
        "loc1": EntitySummary(
            id="loc1",
            name="Castle",
            entity_type=EntityType.LOCATION,
            summary="Ancient castle",
            source_doc="worldbuilding"
        )
    })

    context = {
        "entity_registry": registry,
        "novel_input": {"premise": "A hero saves the kingdom.", "genre": "fantasy"}
    }

    result = await agent.execute(context)

    assert "output" in result
    assert "relationships" in result["output"] or "themes" in result["output"] or "conflicts" in result["output"]
    await test_llm_provider.close()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama - run manually")
async def test_scene_dynamics_agent(test_llm_provider, test_storage_simple):
    """Test Scene Dynamics agent with document-driven context (arc + entity_registry)"""
    structured_state, vector_store = test_storage_simple

    from src.agents import SceneDynamicsAgent

    novel_id = str(uuid.uuid4())
    agent = SceneDynamicsAgent(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        novel_id=novel_id
    )

    novel_input = NovelInput(
        premise="Two rival chefs compete in a high-stakes cooking competition.",
        genre=Genre.OTHER
    )

    arc = {
        "id": "arc_1",
        "name": "Competition Arc",
        "description": "Chefs compete for the title",
        "type": "main",
        "character_ids": ["char1"],
        "location_ids": ["loc1"],
        "scene_concept_ids": [],
        "estimated_chapters": 3
    }

    registry = EntityRegistry(entities={
        "char1": EntitySummary(
            id="char1",
            name="Chef A",
            entity_type=EntityType.CHARACTER,
            summary="The protagonist chef",
            source_doc="characters"
        ),
        "loc1": EntitySummary(
            id="loc1",
            name="Kitchen Arena",
            entity_type=EntityType.LOCATION,
            summary="High-tech cooking arena",
            source_doc="worldbuilding"
        )
    })

    context = {
        "novel_input": novel_input.model_dump(),
        "arc": arc,
        "entity_registry": registry
    }

    result = await agent.execute(context)

    assert "output" in result
    assert "scenes" in result["output"]
    assert isinstance(result["output"]["scenes"], list)
    await test_llm_provider.close()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama and full setup - run manually")
async def test_full_outline_generation(test_llm_provider, test_storage, test_config):
    """Test full end-to-end outline generation with IterativeDocumentOrchestrator"""
    (structured_state, object_store, vector_store,
     graph_store, validation_service) = test_storage

    novel_input = NovelInput(
        premise="A time traveler must prevent a catastrophic event.",
        genre=Genre.SCIFI,
        key_elements=["time travel", "paradoxes"],
        character_concepts=["scientist", "observer"]
    )

    # Use real input paths if available; otherwise test will need to be run with fixtures
    base = Path(__file__).parent.parent
    worldbuilding_path = base / "input" / "worldbuilding.md"
    characters_path = base / "input" / "characters.md"
    scenes_path = base / "input" / "scenes.md"
    if not worldbuilding_path.exists() or not characters_path.exists() or not scenes_path.exists():
        pytest.skip("Input documents not found (input/worldbuilding.md, characters.md, scenes.md)")

    orchestrator = IterativeDocumentOrchestrator(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        graph_store=graph_store,
        validation_service=validation_service,
        config=test_config
    )

    outline = await orchestrator.process_documents(
        worldbuilding_path=worldbuilding_path,
        characters_path=characters_path,
        scenes_path=scenes_path,
        novel_input=novel_input
    )

    assert outline is not None
    assert outline.scenes is not None
    assert outline.input is not None

    exporter = MarkdownExporter()
    markdown = exporter.export(outline)
    assert len(markdown) > 0
    assert "Premise" in markdown or outline.input.premise[:30] in markdown

    await test_llm_provider.close()


def test_markdown_export_document_driven():
    """Test Markdown export with document-driven outline (relationships, scenes)"""
    from src.models import NovelInput, NovelOutline

    novel_input = NovelInput(
        premise="Test premise for export",
        genre=Genre.FANTASY
    )

    outline = NovelOutline(
        id="test_id",
        input=novel_input,
        scenes=[],
        relationships={
            "arcs": [
                {"id": "arc_1", "name": "Arc One", "description": "First arc", "type": "main"}
            ],
            "timeline": ["arc_1"],
            "themes": []
        },
        entity_registry=None,
        status="completed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    exporter = MarkdownExporter()
    markdown = exporter.export(outline)

    assert "Test premise for export" in markdown
    assert "Story Arcs" in markdown or "Arc One" in markdown
    assert "Arc One" in markdown


def test_markdown_export_with_theme():
    """Test Markdown export when theme is present (backward-compatible shape)"""
    from src.models import NovelInput, NovelOutline, ThemeStatement, PlotStructure

    novel_input = NovelInput(
        premise="Test premise for export",
        genre=Genre.FANTASY
    )

    outline = NovelOutline(
        id="test_id",
        input=novel_input,
        theme=ThemeStatement(
            premise="Test premise",
            theme_question="What is the meaning of life?",
            moral_argument="Life has meaning through connections"
        ),
        plot_structure=PlotStructure(
            structure_type="three_act",
            beats=[]
        ),
        scenes=[],
        relationships={},
        status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    exporter = MarkdownExporter()
    markdown = exporter.export(outline)

    assert "Test premise for export" in markdown
    assert "Theme & Premise" in markdown
    assert "What is the meaning of life?" in markdown
