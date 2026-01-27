"""Plot structure models"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class StoryStructure(str, Enum):
    """Types of story structures"""
    THREE_ACT = "three_act"
    FIVE_ACT = "five_act"
    HERO_JOURNEY = "hero_journey"
    SAVE_THE_CAT = "save_the_cat"
    FIVE_POINT = "five_point"
    SEVEN_POINT = "seven_point"
    FREYTAG = "freytag"
    OTHER = "other"


class PlotBeat(BaseModel):
    """A single plot beat"""
    beat_number: int = Field(..., description="Beat number in sequence")
    beat_name: str = Field(..., description="Name of the beat")
    description: str = Field(..., description="What happens in this beat")
    tension_level: float = Field(default=0.5, ge=0.0, le=1.0, description="Tension level 0-1")
    purpose: str = Field(..., description="Purpose of this beat in the story")
    required_elements: List[str] = Field(default_factory=list, description="Required story elements")
    character_focus: Optional[str] = Field(default=None, description="Primary character for this beat")
    location: Optional[str] = Field(default=None, description="Location where beat occurs")


class PlotStructure(BaseModel):
    """Overall plot structure"""
    structure_type: StoryStructure = Field(default=StoryStructure.THREE_ACT)
    beats: List[PlotBeat] = Field(default_factory=list, description="Plot beats in order")
    acts: Optional[List[Dict[str, Any]]] = Field(default=None, description="Act structure if applicable")
    midpoint: Optional[str] = Field(default=None, description="Midpoint description")
    reversals: Optional[List[str]] = Field(default=None, description="Key plot reversals")
