"""Pydantic schemas for MultiWriter data structures"""

from .input import NovelInput, Genre
from .theme import ThemeStatement
from .plot import PlotStructure, PlotBeat, StoryStructure
from .character import CharacterProfile, CharacterArc, Archetype
from .world import WorldBuilding, WorldRule, Location, MagicSystem, TimelineEvent
from .scene import SceneOutline, SceneType, SequelType, SceneBeat
from .outline import NovelOutline
from .entity import EntitySummary, EntityRegistry, EntityType
from .canon import (
    CanonNode,
    CanonEdge,
    CanonQuery,
    TimelineQuery,
    ValidationResult,
    NodeType,
    EdgeType
)

__all__ = [
    # Input
    "NovelInput",
    "Genre",
    # Theme
    "ThemeStatement",
    # Plot
    "PlotStructure",
    "PlotBeat",
    "StoryStructure",
    # Character
    "CharacterProfile",
    "CharacterArc",
    "Archetype",
    # World
    "WorldBuilding",
    "WorldRule",
    "Location",
    "MagicSystem",
    "TimelineEvent",
    # Scene
    "SceneOutline",
    "SceneType",
    "SequelType",
    "SceneBeat",
    # Outline
    "NovelOutline",
    # Entity (new for Phase 1)
    "EntitySummary",
    "EntityRegistry",
    "EntityType",
    # Canon Store
    "CanonNode",
    "CanonEdge",
    "CanonQuery",
    "TimelineQuery",
    "ValidationResult",
    "NodeType",
    "EdgeType",
]
