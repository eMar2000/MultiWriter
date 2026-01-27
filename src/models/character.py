"""Character models"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CharacterArc(str, Enum):
    """Types of character arcs"""
    POSITIVE = "positive"  # Character grows/improves
    NEGATIVE = "negative"  # Character degrades/falls
    FLAT = "flat"  # Character doesn't change (e.g., James Bond)
    STATIC = "static"  # Character remains the same


class Archetype(str, Enum):
    """Character archetypes"""
    HERO = "hero"
    MENTOR = "mentor"
    ALLY = "ally"
    HERALD = "herald"
    THRESHOLD_GUARDIAN = "threshold_guardian"
    SHADOW = "shadow"
    TRICKSTER = "trickster"
    SHAPESHIFTER = "shapeshifter"
    OTHER = "other"


class CharacterProfile(BaseModel):
    """Character profile"""
    id: str = Field(..., description="Unique character ID")
    name: str = Field(..., description="Character name")
    role: str = Field(..., description="Role in story (protagonist, antagonist, etc.)")
    archetype: Optional[Archetype] = Field(default=None, description="Character archetype")
    
    # Core psychology
    want: str = Field(..., description="External goal/want")
    need: str = Field(..., description="Internal need/growth")
    lie: str = Field(..., description="The lie the character believes")
    fear: str = Field(..., description="Greatest fear")
    belief: str = Field(..., description="Core belief system")
    
    # Arc
    arc_type: CharacterArc = Field(default=CharacterArc.POSITIVE)
    starting_point: str = Field(..., description="Where character starts")
    ending_point: str = Field(..., description="Where character ends")
    
    # Personality
    personality_summary: str = Field(..., description="Personality description")
    story_function: str = Field(..., description="Function in the story")
    
    # Attributes
    conflicts: List[str] = Field(default_factory=list, description="Internal/external conflicts")
    skills: List[str] = Field(default_factory=list, description="Skills/abilities")
    weaknesses: List[str] = Field(default_factory=list, description="Weaknesses/flaws")
    
    # Relationships
    relationships: Optional[Dict[str, str]] = Field(default=None, description="Relationships with other characters")
    
    # Metadata
    backstory: Optional[str] = Field(default=None, description="Backstory summary")
    notes: Optional[str] = Field(default=None, description="Additional notes")
