"""Canon Store schemas for GraphDB nodes and edges"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import uuid


class NodeType(str, Enum):
    """Types of nodes in the Canon Store"""
    CHARACTER = "character"
    LOCATION = "location"
    OBJECT = "object"
    ORGANIZATION = "organization"
    EVENT = "event"
    SCENE = "scene"
    CHAPTER = "chapter"
    ARC = "arc"
    THREAD = "thread"  # Subplot
    MOTIF = "motif"
    RULE = "rule"
    SECRET = "secret"


class EdgeType(str, Enum):
    """Types of edges in the Canon Store"""
    # Appearance & Location
    APPEARS_IN = "appears_in"
    LOCATED_IN = "located_in"
    TRAVELS_TO = "travels_to"
    
    # Timeline
    BEFORE = "before"
    AFTER = "after"
    
    # Narrative
    FORESHADOWS = "foreshadows"
    PAYS_OFF = "pays_off"
    CONTRADICTS = "contradicts"
    
    # Character relationships
    WANTS = "wants"
    FEARS = "fears"
    BELIEVES = "believes"
    KNOWS = "knows"
    ALLIES_WITH = "allies_with"
    OPPOSES = "opposes"
    BETRAYS = "betrays"
    
    # Ownership
    OWNS = "owns"
    LOSES = "loses"
    
    # Story structure
    INTRODUCED_IN = "introduced_in"
    RESOLVED_IN = "resolved_in"
    CONTAINS = "contains"  # Arc contains Chapter, Chapter contains Scene


class CanonNode(BaseModel):
    """A node in the Canon Store graph"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NodeType
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)

    model_config = ConfigDict(use_enum_values=True)

    def update(self, **kwargs):
        """Update node properties and increment version"""
        self.properties.update(kwargs)
        self.updated_at = datetime.utcnow()
        self.version += 1


class CanonEdge(BaseModel):
    """An edge in the Canon Store graph"""
    source_id: str
    target_id: str
    type: EdgeType
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=True)

    def update_properties(self, **kwargs):
        """Update edge properties"""
        self.properties.update(kwargs)


class CanonQuery(BaseModel):
    """Query structure for Canon Store"""
    node_type: Optional[NodeType] = None
    node_id: Optional[str] = None
    edge_type: Optional[EdgeType] = None
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    properties_filter: Optional[Dict[str, Any]] = None
    limit: int = 100


class TimelineQuery(BaseModel):
    """Query for timeline traversal"""
    start_node_id: str
    direction: str = Field(default="forward", pattern="^(forward|backward|both)$")
    max_depth: int = Field(default=10, ge=1, le=100)
    edge_types: Optional[List[EdgeType]] = None  # Default: [BEFORE, AFTER]


class ValidationResult(BaseModel):
    """Result of a validation check"""
    is_valid: bool
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    auto_fixes: List[Dict[str, Any]] = Field(default_factory=list)

    def add_violation(self, violation_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Add a validation violation"""
        self.is_valid = False
        self.violations.append({
            "type": violation_type,
            "message": message,
            "details": details or {}
        })

    def add_warning(self, warning_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Add a validation warning"""
        self.warnings.append({
            "type": warning_type,
            "message": message,
            "details": details or {}
        })
