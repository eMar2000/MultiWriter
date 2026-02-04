"""Pacing Agent - Analyzes and optimizes story pacing"""

import logging
from typing import Dict, Any, Optional, List
from collections import Counter

from src.agents.base import BaseAgent
from src.models import SceneType

logger = logging.getLogger(__name__)


class PacingAgent(BaseAgent):
    """Analyzes pacing and recommends improvements"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="pacing_agent", *args, **kwargs)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze pacing

        Args:
            context: Should contain:
                - outline: NovelOutline or dict
                - arc_plan: Dict with arcs
                - genre: Optional genre for pacing norms

        Returns:
            Pacing analysis with recommendations
        """
        outline = context.get("outline")
        arc_plan = context.get("arc_plan", {})
        genre = context.get("genre") or context.get("novel_input", {}).get("genre", "other")

        analysis = {
            "scene_type_distribution": {},
            "tension_curve": [],
            "monotony_flags": [],
            "rushed_sequences": [],
            "recommendations": []
        }

        if outline:
            scenes = outline.get("scenes", [])
            analysis.update(await self._analyze_scene_types(scenes))
            analysis.update(await self._analyze_tension_curve(scenes))
            analysis["monotony_flags"] = await self._detect_monotony(scenes)
            analysis["rushed_sequences"] = await self._detect_rushed_sequences(scenes)

        # Genre-specific recommendations
        analysis["recommendations"].extend(
            await self._genre_specific_recommendations(analysis, genre)
        )

        return {
            "output": analysis
        }

    async def _analyze_scene_types(self, scenes: List[Any]) -> Dict[str, Any]:
        """Analyze distribution of scene types"""
        scene_types = []

        for scene in scenes:
            if isinstance(scene, dict):
                scene_type = scene.get("scene_type")
            else:
                scene_type = getattr(scene, "scene_type", None)
                if scene_type and hasattr(scene_type, "value"):
                    scene_type = scene_type.value

            if scene_type:
                scene_types.append(scene_type)

        type_counts = Counter(scene_types)
        total = len(scene_types) if scene_types else 1

        distribution = {
            scene_type: {
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for scene_type, count in type_counts.items()
        }

        return {"scene_type_distribution": distribution}

    async def _analyze_tension_curve(self, scenes: List[Any]) -> Dict[str, Any]:
        """Analyze tension progression"""
        tension_points = []

        for idx, scene in enumerate(scenes):
            if isinstance(scene, dict):
                tension_start = scene.get("tension_start", 0)
                tension_end = scene.get("tension_end", 0)
            else:
                tension_start = getattr(scene, "tension_start", 0) or 0
                tension_end = getattr(scene, "tension_end", 0) or 0

            tension_points.append({
                "scene_index": idx,
                "tension_start": tension_start,
                "tension_end": tension_end
            })

        # Check if tension generally increases
        increasing = True
        for i in range(1, len(tension_points)):
            if tension_points[i]["tension_start"] < tension_points[i-1]["tension_end"]:
                increasing = False
                break

        return {
            "tension_curve": tension_points,
            "is_increasing": increasing
        }

    async def _detect_monotony(self, scenes: List[Any]) -> List[Dict[str, Any]]:
        """Detect sequences of similar scenes"""
        monotony_flags = []

        if len(scenes) < 3:
            return monotony_flags

        consecutive_same_type = 1
        prev_type = None

        for idx, scene in enumerate(scenes):
            if isinstance(scene, dict):
                scene_type = scene.get("scene_type")
            else:
                scene_type = getattr(scene, "scene_type", None)
                if scene_type and hasattr(scene_type, "value"):
                    scene_type = scene_type.value

            if scene_type == prev_type:
                consecutive_same_type += 1
            else:
                if consecutive_same_type >= 3:
                    monotony_flags.append({
                        "type": "consecutive_same_type",
                        "scene_type": prev_type,
                        "count": consecutive_same_type,
                        "start_index": idx - consecutive_same_type
                    })
                consecutive_same_type = 1
                prev_type = scene_type

        # Check final sequence
        if consecutive_same_type >= 3:
            monotony_flags.append({
                "type": "consecutive_same_type",
                "scene_type": prev_type,
                "count": consecutive_same_type,
                "start_index": len(scenes) - consecutive_same_type
            })

        return monotony_flags

    async def _detect_rushed_sequences(self, scenes: List[Any]) -> List[Dict[str, Any]]:
        """Detect sequences that may be rushed"""
        rushed = []

        # Check for scenes with very high tension jumps
        for idx in range(1, len(scenes)):
            prev_scene = scenes[idx - 1]
            curr_scene = scenes[idx]

            if isinstance(prev_scene, dict):
                prev_tension = prev_scene.get("tension_end", 0)
            else:
                prev_tension = getattr(prev_scene, "tension_end", 0) or 0

            if isinstance(curr_scene, dict):
                curr_tension = curr_scene.get("tension_start", 0)
            else:
                curr_tension = getattr(curr_scene, "tension_start", 0) or 0

            # Large jump in tension might indicate rushed pacing
            if curr_tension - prev_tension > 0.5:
                rushed.append({
                    "type": "large_tension_jump",
                    "jump": curr_tension - prev_tension,
                    "scene_index": idx
                })

        return rushed

    async def _genre_specific_recommendations(
        self,
        analysis: Dict[str, Any],
        genre: str
    ) -> List[Dict[str, Any]]:
        """Generate genre-specific recommendations"""
        recommendations = []

        distribution = analysis.get("scene_type_distribution", {})
        action_pct = distribution.get("action", {}).get("percentage", 0)
        dialogue_pct = distribution.get("dialogue", {}).get("percentage", 0)

        # Genre-specific norms (simplified)
        if genre in ("thriller", "action", "adventure"):
            if action_pct < 40:
                recommendations.append({
                    "type": "low_action_ratio",
                    "message": f"Action scenes are {action_pct}% - consider increasing for {genre} genre",
                    "current": action_pct,
                    "recommended": 40
                })
        elif genre in ("romance", "drama"):
            if dialogue_pct < 30:
                recommendations.append({
                    "type": "low_dialogue_ratio",
                    "message": f"Dialogue scenes are {dialogue_pct}% - consider increasing for {genre} genre",
                    "current": dialogue_pct,
                    "recommended": 30
                })

        # General recommendations
        if not analysis.get("is_increasing"):
            recommendations.append({
                "type": "tension_not_increasing",
                "message": "Tension curve is not consistently increasing - consider building tension more gradually"
            })

        return recommendations
