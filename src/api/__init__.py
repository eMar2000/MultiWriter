"""API layer - single entry point for planning (CLI and future web)"""

from .planning import run_planning

__all__ = ["run_planning"]
