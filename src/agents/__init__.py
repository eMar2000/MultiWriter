"""Agent implementations for novel outline generation (planning loop)"""

from .base import BaseAgent
from .synthesis import SynthesisAgent
from .outline_architect import OutlineArchitectAgent
from .coverage_verifier import CoverageVerifierAgent
from .scene_dynamics import SceneDynamicsAgent
from .timeline_manager import TimelineManagerAgent
from .pacing_agent import PacingAgent
from .theme_guardian import ThemeGuardianAgent
from .foreshadowing_agent import ForeshadowingAgent
from .character_planner import CharacterPlannerAgent
from .idea_generator import IdeaGeneratorAgent

__all__ = [
    "BaseAgent",
    "SynthesisAgent",
    "OutlineArchitectAgent",
    "CoverageVerifierAgent",
    "SceneDynamicsAgent",
    "TimelineManagerAgent",
    "PacingAgent",
    "ThemeGuardianAgent",
    "ForeshadowingAgent",
    "CharacterPlannerAgent",
    "IdeaGeneratorAgent",
]
