"""Worldbuilding models"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WorldRule(BaseModel):
    """A world rule or constraint"""
    rule: str = Field(..., description="The rule itself")
    category: str = Field(default="general", description="Category of rule")
    explanation: Optional[str] = Field(default=None, description="Explanation of the rule")
    importance: str = Field(default="medium", description="Importance: critical, high, medium, low")


class MagicSystem(BaseModel):
    """Magic or technology system"""
    system_name: str = Field(..., description="Name of the system")
    hardness: str = Field(default="medium", description="Hardness: hard, medium, soft")
    description: str = Field(..., description="Description of how it works")
    limitations: List[str] = Field(default_factory=list, description="Limitations/constraints")
    rules: List[str] = Field(default_factory=list, description="Specific rules")


class Location(BaseModel):
    """A location in the world"""
    name: str = Field(..., description="Location name")
    type: str = Field(default="general", description="Type: city, building, region, etc.")
    description: str = Field(..., description="Description of the location")
    notable_features: List[str] = Field(default_factory=list, description="Notable features")
    significance: Optional[str] = Field(default=None, description="Significance to the story")


class TimelineEvent(BaseModel):
    """A historical event"""
    name: str = Field(..., description="Event name")
    time_period: str = Field(..., description="When it occurred")
    description: str = Field(..., description="What happened")
    significance: Optional[str] = Field(default=None, description="Significance to current story")


class WorldBuilding(BaseModel):
    """Complete worldbuilding information"""
    current_period: str = Field(default="Present day", description="Current time period")
    rules: List[WorldRule] = Field(default_factory=list, description="World rules")
    magic_systems: List[MagicSystem] = Field(default_factory=list, description="Magic/tech systems")
    locations: List[Location] = Field(default_factory=list, description="Locations")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Historical timeline")
    cultures: Dict[str, Any] = Field(default_factory=dict, description="Cultural information")
    political_systems: Dict[str, Any] = Field(default_factory=dict, description="Political systems")
    economic_systems: Dict[str, Any] = Field(default_factory=dict, description="Economic systems")
    consistency_constraints: List[str] = Field(default_factory=list, description="Constraints for consistency")
