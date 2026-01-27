"""Novel outline schema models"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class Genre(str, Enum):
    """Supported novel genres"""
    ROMANCE = "romance"
    THRILLER = "thriller"
    FANTASY = "fantasy"
    SCIFI = "sci-fi"
    MYSTERY = "mystery"
    HORROR = "horror"
    LITRPG = "litrpg"
    CONTEMPORARY = "contemporary"
    HISTORICAL = "historical"
    OTHER = "other"


class StoryStructure(str, Enum):
    """Story structure types"""
    THREE_ACT = "three_act"
    HERO_JOURNEY = "hero_journey"
    SAVE_THE_CAT = "save_the_cat"
    FOUR_PART = "four_part"
    FIVE_ACT = "five_act"
    HARMON_CIRCLE = "harmon_circle"
    SEVEN_POINT = "seven_point"
    KISHOTENKETSU = "kishotenketsu"


class NovelInput(BaseModel):
    """User input for novel generation"""
    premise: str = Field(..., description="The core premise of the novel")
    genre: Genre = Field(..., description="Genre of the novel")
    target_length: Optional[int] = Field(None, description="Target word count")
    key_elements: Optional[List[str]] = Field(default_factory=list, description="Key story elements")
    character_concepts: Optional[List[str]] = Field(default_factory=list, description="Initial character concepts")
    desired_theme: Optional[str] = Field(None, description="Desired theme or message")
    style_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Style preferences")


class ThemeStatement(BaseModel):
    """Theme and premise statement"""
    premise: str = Field(..., description="Refined premise statement")
    theme_question: str = Field(..., description="The thematic question the novel explores")
    moral_argument: str = Field(..., description="The moral argument or perspective")
    thematic_constraints: List[str] = Field(default_factory=list, description="Constraints for thematic coherence")


class PlotBeat(BaseModel):
    """Individual plot beat in the story structure"""
    beat_number: int = Field(..., description="Sequential beat number")
    beat_name: str = Field(..., description="Name of the beat (e.g., 'Inciting Incident')")
    act: Optional[int] = Field(None, description="Act number if applicable")
    description: str = Field(..., description="Description of what happens in this beat")
    tension_level: float = Field(..., ge=0.0, le=1.0, description="Tension level 0-1")
    purpose: str = Field(..., description="Narrative purpose of this beat")
    required_elements: List[str] = Field(default_factory=list, description="Required story elements")


class PlotStructure(BaseModel):
    """Complete plot structure"""
    structure_type: StoryStructure = Field(..., description="Type of story structure used")
    acts: Optional[List[Dict[str, Any]]] = Field(None, description="Act boundaries and descriptions")
    beats: List[PlotBeat] = Field(default_factory=list, description="All plot beats")
    tension_curve: List[float] = Field(default_factory=list, description="Tension escalation over time")
    midpoint: Optional[str] = Field(None, description="Midpoint reversal/event")
    reversals: List[str] = Field(default_factory=list, description="Key story reversals")


class NovelOutline(BaseModel):
    """Complete novel outline"""
    id: Optional[str] = Field(None, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    # Input
    input: NovelInput = Field(..., description="Original user input")

    # Core elements
    theme: Optional[ThemeStatement] = Field(None, description="Theme and premise statement")
    plot_structure: Optional[PlotStructure] = Field(None, description="Plot structure and beats")
    world_rules: Optional[Dict[str, Any]] = Field(None, description="World-building rules")
    characters: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Character profiles")
    scenes: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Scene outlines")

    # Metadata
    version: int = Field(default=1, description="Outline version number")
    status: str = Field(default="draft", description="Outline status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
