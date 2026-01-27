"""Input models for novel generation"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Genre(str, Enum):
    """Novel genre"""
    FANTASY = "fantasy"
    SCIENCE_FICTION = "science_fiction"
    MYSTERY = "mystery"
    THRILLER = "thriller"
    ROMANCE = "romance"
    HORROR = "horror"
    LITERARY = "literary"
    HISTORICAL = "historical"
    YOUNG_ADULT = "young_adult"
    OTHER = "other"


class NovelInput(BaseModel):
    """User input for novel outline generation"""
    premise: str = Field(..., description="Core premise of the novel")
    genre: Genre = Field(default=Genre.OTHER)
    target_length: Optional[int] = Field(default=None, description="Target word count")
    key_elements: List[str] = Field(default_factory=list, description="Key story elements")
    character_concepts: List[str] = Field(default_factory=list, description="Character concepts")
    desired_theme: Optional[str] = Field(default=None, description="Desired thematic question")
    
    # NEW: Document references (for document-driven workflow)
    worldbuilding_doc: Optional[str] = Field(default=None, description="Path to worldbuilding document")
    characters_doc: Optional[str] = Field(default=None, description="Path to characters document")
    scenes_doc: Optional[str] = Field(default=None, description="Path to scenes document")
