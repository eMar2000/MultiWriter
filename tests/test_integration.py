"""Integration tests for end-to-end outline generation"""

import pytest
import asyncio
from pathlib import Path
import uuid
from typing import Dict, Any

from src.models import NovelInput, Genre
from src.llm import OllamaClient
from src.memory import DynamoDBState, QdrantVectorStore
from src.orchestrator import Orchestrator
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
            "dynamodb": {
                "region": "us-east-1",
                "endpoint_url": None,
                "table_prefix": "test_"
            },
            "qdrant": {
                "host": "localhost",
                "port": 6333,
                "collection_name": "test-multiwriter-embeddings",
                "vector_size": 768
            }
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
    """Create test storage instances"""
    storage_config = test_config["storage"]

    # DynamoDB (using endpoint_url=None for testing - would need localstack for actual tests)
    dynamodb_config = storage_config["dynamodb"]
    structured_state = DynamoDBState(
        region=dynamodb_config["region"],
        endpoint_url=dynamodb_config["endpoint_url"],
        table_prefix=dynamodb_config["table_prefix"]
    )

    # Qdrant
    qdrant_config = storage_config["qdrant"]
    vector_store = QdrantVectorStore(
        host=qdrant_config["host"],
        port=qdrant_config["port"],
        collection_name=qdrant_config["collection_name"],
        vector_size=qdrant_config["vector_size"]
    )

    return structured_state, vector_store


@pytest.mark.asyncio
async def test_theme_premise_agent(test_llm_provider, test_storage):
    """Test Theme & Premise agent"""
    structured_state, vector_store = test_storage

    from src.agents import ThemePremiseAgent

    novel_id = str(uuid.uuid4())
    agent = ThemePremiseAgent(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        novel_id=novel_id
    )

    novel_input = NovelInput(
        premise="A detective must solve a murder while their own memories are being erased.",
        genre=Genre.MYSTERY
    )

    context = {
        "novel_input": novel_input.model_dump()
    }

    result = await agent.execute(context)

    assert result["status"] == "success"
    assert "theme" in result["output"]
    assert result["output"]["theme"].get("premise")
    assert result["output"]["theme"].get("theme_question")

    # Cleanup
    await test_llm_provider.close()


@pytest.mark.asyncio
async def test_narrative_architect_agent(test_llm_provider, test_storage):
    """Test Narrative Architect agent"""
    structured_state, vector_store = test_storage

    from src.agents import NarrativeArchitectAgent

    novel_id = str(uuid.uuid4())
    agent = NarrativeArchitectAgent(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        novel_id=novel_id
    )

    novel_input = NovelInput(
        premise="A young wizard discovers they have the power to travel between parallel worlds.",
        genre=Genre.FANTASY
    )

    theme_data = {
        "premise": novel_input.premise,
        "theme_question": "What does it mean to belong in a world where you could be anywhere?",
        "moral_argument": "Belonging is a choice, not a birthright",
        "thematic_constraints": []
    }

    context = {
        "novel_input": novel_input.model_dump(),
        "theme": theme_data
    }

    result = await agent.execute(context)

    assert result["status"] == "success"
    assert "plot_structure" in result["output"]
    assert result["output"]["plot_structure"].get("structure_type")
    assert result["output"]["plot_structure"].get("beats")

    # Cleanup
    await test_llm_provider.close()


@pytest.mark.asyncio
async def test_character_agent(test_llm_provider, test_storage):
    """Test Character agent"""
    structured_state, vector_store = test_storage

    from src.agents import CharacterAgent

    novel_id = str(uuid.uuid4())
    agent = CharacterAgent(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        novel_id=novel_id
    )

    novel_input = NovelInput(
        premise="A retired assassin must protect their family from their past.",
        genre=Genre.THRILLER
    )

    theme_data = {
        "theme_question": "Can we escape our past?",
        "moral_argument": "Redemption requires facing, not running from, the past"
    }

    plot_structure = {
        "structure_type": "three_act",
        "beats": [
            {
                "beat_number": 1,
                "beat_name": "Inciting Incident",
                "description": "Assassin's past catches up",
                "tension_level": 0.3,
                "purpose": "Begin the story",
                "required_elements": []
            }
        ]
    }

    context = {
        "novel_input": novel_input.model_dump(),
        "theme": theme_data,
        "plot_structure": plot_structure
    }

    result = await agent.execute(context)

    assert result["status"] == "success"
    assert "characters" in result["output"]
    assert isinstance(result["output"]["characters"], list)

    # Cleanup
    await test_llm_provider.close()


@pytest.mark.asyncio
async def test_worldbuilding_agent(test_llm_provider, test_storage):
    """Test Worldbuilding agent"""
    structured_state, vector_store = test_storage

    from src.agents import WorldbuildingAgent

    novel_id = str(uuid.uuid4())
    agent = WorldbuildingAgent(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store,
        novel_id=novel_id
    )

    novel_input = NovelInput(
        premise="In a world where magic is controlled by corporations, a rogue mage fights for freedom.",
        genre=Genre.FANTASY
    )

    theme_data = {
        "theme_question": "What is the cost of freedom?",
        "moral_argument": "Freedom requires sacrifice"
    }

    plot_structure = {
        "structure_type": "three_act",
        "beats": []
    }

    context = {
        "novel_input": novel_input.model_dump(),
        "theme": theme_data,
        "plot_structure": plot_structure
    }

    result = await agent.execute(context)

    assert result["status"] == "success"
    assert "world" in result["output"]
    assert result["output"]["world"].get("current_period")

    # Cleanup
    await test_llm_provider.close()


@pytest.mark.asyncio
async def test_scene_dynamics_agent(test_llm_provider, test_storage):
    """Test Scene Dynamics agent"""
    structured_state, vector_store = test_storage

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
        genre=Genre.CONTEMPORARY
    )

    theme_data = {
        "theme_question": "What defines success?",
        "moral_argument": "Success is personal growth, not victory"
    }

    plot_structure = {
        "structure_type": "three_act",
        "beats": [
            {
                "beat_number": 1,
                "beat_name": "Opening",
                "description": "Competition announced",
                "tension_level": 0.2,
                "purpose": "Set up story",
                "required_elements": []
            }
        ]
    }

    characters = [
        {
            "id": "char1",
            "name": "Chef A",
            "role": "protagonist",
            "want": "Win competition",
            "need": "Self-worth",
            "lie": "I'm only valuable if I win",
            "fear": "Failure",
            "belief": "Success is everything",
            "arc_type": "positive",
            "starting_point": "Defined by competition",
            "ending_point": "Defined by growth",
            "personality_summary": "Intense, driven",
            "story_function": "Main character",
            "conflicts": [],
            "skills": [],
            "weaknesses": []
        }
    ]

    world = {
        "current_period": "Present day",
        "rules": [],
        "locations": [
            {
                "location_id": "loc1",
                "name": "Kitchen Arena",
                "type": "competition venue",
                "description": "High-tech cooking arena"
            }
        ],
        "timeline": []
    }

    context = {
        "novel_input": novel_input.model_dump(),
        "theme": theme_data,
        "plot_structure": plot_structure,
        "characters": characters,
        "world": world
    }

    result = await agent.execute(context)

    assert result["status"] == "success"
    assert "scenes" in result["output"]
    assert isinstance(result["output"]["scenes"], list)

    # Cleanup
    await test_llm_provider.close()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Ollama and full setup - run manually")
async def test_full_outline_generation(test_llm_provider, test_storage):
    """Test full end-to-end outline generation"""
    structured_state, vector_store = test_storage

    novel_input = NovelInput(
        premise="A time traveler must prevent a catastrophic event while avoiding creating paradoxes.",
        genre=Genre.SCIFI,
        key_elements=["time travel", "paradoxes", "catastrophe"],
        character_concepts=["brilliant scientist", "skeptical observer"]
    )

    orchestrator = Orchestrator(
        llm_provider=test_llm_provider,
        structured_state=structured_state,
        vector_store=vector_store
    )

    outline = await orchestrator.generate_outline(novel_input)

    assert outline is not None
    assert outline.theme is not None
    assert outline.plot_structure is not None
    assert outline.characters is not None
    assert outline.world_rules is not None
    assert outline.scenes is not None

    # Test export
    exporter = MarkdownExporter()
    markdown = exporter.export(outline)
    assert len(markdown) > 0
    assert "Premise" in markdown

    # Cleanup
    await test_llm_provider.close()


def test_markdown_export():
    """Test Markdown export functionality"""
    from src.models import NovelOutline, NovelInput, Genre, ThemeStatement, PlotStructure

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
        )
    )

    exporter = MarkdownExporter()
    markdown = exporter.export(outline)

    assert "Test premise for export" in markdown
    assert "Theme & Premise" in markdown
    assert "What is the meaning of life?" in markdown
