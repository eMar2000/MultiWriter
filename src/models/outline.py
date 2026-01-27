"""Novel outline model"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from .input import NovelInput
from .theme import ThemeStatement
from .plot import PlotStructure
from .character import CharacterProfile
from .world import WorldBuilding
from .scene import SceneOutline
from .entity import EntityRegistry


class NovelOutline(BaseModel):
    """Complete novel outline container"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    input: Optional[NovelInput] = None
    
    # Core components
    theme: Optional[ThemeStatement] = None
    plot_structure: Optional[PlotStructure] = None
    characters: List[CharacterProfile] = Field(default_factory=list)
    world_rules: Optional[WorldBuilding] = None
    scenes: List[SceneOutline] = Field(default_factory=list)
    
    # NEW: Entity registry for document-driven workflow
    entity_registry: Optional[EntityRegistry] = None
    
    # Metadata
    status: str = Field(default="draft", description="Status: draft, in_progress, completed, failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships (NEW - bridging to future Canon Store)
    relationships: Dict[str, Any] = Field(default_factory=dict, description="Entity relationships and arc structure")
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
