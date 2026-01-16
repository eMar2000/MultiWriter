"""Tests for Pydantic models"""

import pytest
from src.models import (
    NovelInput,
    NovelOutline,
    Genre,
    ThemeStatement,
    PlotStructure,
    PlotBeat,
    CharacterProfile,
    CharacterArc,
    WorldBuilding,
    SceneOutline,
    SceneType,
)


def test_novel_input():
    """Test NovelInput model"""
    novel_input = NovelInput(
        premise="Test premise",
        genre=Genre.FANTASY
    )

    assert novel_input.premise == "Test premise"
    assert novel_input.genre == Genre.FANTASY
    assert novel_input.key_elements == []
    assert novel_input.character_concepts == []


def test_theme_statement():
    """Test ThemeStatement model"""
    theme = ThemeStatement(
        premise="Test premise",
        theme_question="What is the meaning?",
        moral_argument="Meaning comes from within"
    )

    assert theme.premise == "Test premise"
    assert theme.theme_question == "What is the meaning?"
    assert theme.moral_argument == "Meaning comes from within"
    assert theme.thematic_constraints == []


def test_plot_structure():
    """Test PlotStructure model"""
    beat = PlotBeat(
        beat_number=1,
        beat_name="Opening",
        description="Story begins",
        tension_level=0.2,
        purpose="Set up story"
    )

    plot = PlotStructure(
        structure_type="three_act",
        beats=[beat]
    )

    assert plot.structure_type == "three_act"
    assert len(plot.beats) == 1
    assert plot.beats[0].beat_name == "Opening"


def test_character_profile():
    """Test CharacterProfile model"""
    character = CharacterProfile(
        id="char1",
        name="Test Character",
        role="protagonist",
        want="External goal",
        need="Internal growth",
        lie="The lie they believe",
        fear="Greatest fear",
        belief="Core belief",
        arc_type=CharacterArc.POSITIVE,
        starting_point="Beginning",
        ending_point="End",
        personality_summary="Personality description",
        story_function="Main character",
        conflicts=[],
        skills=[],
        weaknesses=[]
    )

    assert character.name == "Test Character"
    assert character.role == "protagonist"
    assert character.arc_type == CharacterArc.POSITIVE


def test_world_building():
    """Test WorldBuilding model"""
    world = WorldBuilding(
        current_period="Present day",
        rules=[],
        magic_systems=[],
        locations=[],
        timeline=[],
        cultures={},
        political_systems={},
        economic_systems={},
        consistency_constraints=[]
    )

    assert world.current_period == "Present day"
    assert world.rules == []


def test_scene_outline():
    """Test SceneOutline model"""
    scene = SceneOutline(
        scene_id="scene1",
        scene_number=1,
        scene_type=SceneType.ACTION,
        goal="Character goal",
        conflict="Obstacle",
        outcome="Result",
        stakes="What's at risk",
        emotional_arc="Emotional journey",
        beats=[]
    )

    assert scene.scene_id == "scene1"
    assert scene.scene_type == SceneType.ACTION
    assert scene.goal == "Character goal"
