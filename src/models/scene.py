"""Scene models"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SceneType(str, Enum):
    """Types of scenes"""
    ACTION = "action"
    REACTION = "reaction"
    DIALOGUE = "dialogue"
    REFLECTION = "reflection"
    TRANSITION = "transition"
    MONTAGE = "montage"
    OTHER = "other"


class SequelType(str, Enum):
    """Types of sequels (reaction scenes)"""
    EMOTIONAL = "emotional"
    RATIONAL = "rational"
    DECISION = "decision"
    ACTION = "action"
    OTHER = "other"


class SceneBeat(BaseModel):
    """A beat within a scene"""
    beat_number: int = Field(..., description="Beat number in scene")
    description: str = Field(..., description="What happens in this beat")
    purpose: Optional[str] = Field(default=None, description="Purpose of this beat")


class SceneOutline(BaseModel):
    """Scene outline"""
    scene_id: str = Field(..., description="Unique scene ID")
    scene_number: int = Field(..., description="Scene number in sequence")
    title: Optional[str] = Field(default=None, description="Scene title")
    scene_type: SceneType = Field(default=SceneType.ACTION)
    sequel_type: Optional[SequelType] = Field(default=None, description="Type if this is a sequel")
    
    # Core elements
    goal: str = Field(..., description="Character goal in scene")
    conflict: str = Field(..., description="Obstacle/conflict")
    outcome: str = Field(..., description="What happens/result")
    stakes: str = Field(..., description="What's at risk")
    
    # Characters
    pov_character: Optional[str] = Field(default=None, description="POV character")
    characters_present: List[str] = Field(default_factory=list, description="Characters in scene")
    
    # Setting
    location_id: Optional[str] = Field(default=None, description="Location ID")
    time_period: Optional[str] = Field(default=None, description="When this occurs")
    
    # Emotional arc
    emotional_arc: Optional[str] = Field(default=None, description="Emotional journey")
    tension_start: float = Field(default=0.5, ge=0.0, le=1.0, description="Starting tension")
    tension_end: float = Field(default=0.5, ge=0.0, le=1.0, description="Ending tension")
    
    # Beats
    beats: List[SceneBeat] = Field(default_factory=list, description="Scene beats")
    
    # Metadata
    notes: Optional[str] = Field(default=None, description="Additional notes")
