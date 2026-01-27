"""Entity models for document-driven workflow"""

from enum import Enum
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field
import uuid


class EntityType(str, Enum):
    """Types of entities"""
    CHARACTER = "character"
    LOCATION = "location"
    ORGANIZATION = "organization"
    ITEM = "item"
    EVENT = "event"
    RULE = "rule"
    SCENE_CONCEPT = "scene_concept"
    RELATIONSHIP = "relationship"


class EntitySummary(BaseModel):
    """Compact entity reference for registry (~50 tokens max)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Entity name")
    entity_type: EntityType = Field(..., description="Type of entity")
    summary: str = Field(..., max_length=200, description="1-2 sentence summary")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    source_doc: Optional[str] = Field(default=None, description="Source document")

    class Config:
        use_enum_values = True


class EntityRegistry(BaseModel):
    """Compact registry of all entities (~8K tokens max)"""
    entities: Dict[str, EntitySummary] = Field(default_factory=dict, description="All entities by ID")

    def add(self, entity: EntitySummary) -> str:
        """Add entity and return its ID"""
        self.entities[entity.id] = entity
        return entity.id

    def get(self, entity_id: str) -> Optional[EntitySummary]:
        """Get entity by ID"""
        return self.entities.get(entity_id)

    def get_by_type(self, entity_type: EntityType) -> List[EntitySummary]:
        """Get all entities of a specific type"""
        # Handle both enum and string comparisons (due to use_enum_values=True)
        type_value = entity_type.value if isinstance(entity_type, EntityType) else str(entity_type)
        return [e for e in self.entities.values() if (e.entity_type == entity_type or str(e.entity_type) == type_value)]

    def get_all_ids(self) -> Set[str]:
        """Get all entity IDs"""
        return set(self.entities.keys())

    def to_context_string(self, max_tokens: int = 8000) -> str:
        """Generate context string for LLM prompts"""
        # Token estimation: ~4 characters per token is a reasonable approximation
        TOKENS_PER_CHAR = 4
        max_chars = max_tokens * TOKENS_PER_CHAR

        lines = []
        current_length = 0
        for entity in self.entities.values():
            # entity_type may be an enum or string (depending on use_enum_values config)
            entity_type_str = entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type)
            line = f"[{entity.id}] {entity_type_str}: {entity.name} - {entity.summary}"
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > max_chars:
                lines.append("... (truncated)")
                break

            lines.append(line)
            current_length += line_length

        return "\n".join(lines)
