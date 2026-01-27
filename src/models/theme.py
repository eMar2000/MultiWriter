"""Theme and premise models"""

from typing import List
from pydantic import BaseModel, Field


class ThemeStatement(BaseModel):
    """Theme statement for the novel"""
    premise: str = Field(..., description="Refined premise")
    theme_question: str = Field(..., description="The thematic question the novel explores")
    moral_argument: str = Field(..., description="The moral argument/answer to the theme question")
    thematic_constraints: List[str] = Field(default_factory=list, description="Constraints to maintain thematic coherence")
