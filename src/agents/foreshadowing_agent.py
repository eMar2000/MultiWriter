"""Foreshadowing & Payoff Agent - Tracks seeds, reminders, and payoffs"""

import logging
from typing import Dict, Any, Optional, List

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ForeshadowingAgent(BaseAgent):
    """Tracks narrative promises and their payoffs"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="foreshadowing_agent", *args, **kwargs)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track foreshadowing and payoffs

        Args:
            context: Should contain:
                - outline: NovelOutline or dict
                - arc_plan: Dict with arcs

        Returns:
            Foreshadowing analysis with unresolved promises
        """
        outline = context.get("outline")
        arc_plan = context.get("arc_plan", {})

        analysis = {
            "seeds": [],
            "reminders": [],
            "payoffs": [],
            "unresolved_promises": [],
            "recommendations": []
        }

        if outline:
            scenes = outline.get("scenes", [])
            analysis.update(await self._identify_seeds_and_payoffs(scenes))
            analysis["unresolved_promises"] = await self._find_unresolved_promises(
                scenes, arc_plan
            )

        # Generate recommendations
        analysis["recommendations"] = await self._generate_payoff_recommendations(analysis)

        return {
            "output": analysis
        }

    async def _identify_seeds_and_payoffs(
        self,
        scenes: List[Any]
    ) -> Dict[str, Any]:
        """Identify seeds (setup) and payoffs (resolution)"""
        seeds = []
        payoffs = []

        # Simple heuristic: look for questions/mysteries (seeds) and answers (payoffs)
        for idx, scene in enumerate(scenes):
            scene_text = ""
            if isinstance(scene, dict):
                scene_text = f"{scene.get('goal', '')} {scene.get('conflict', '')} {scene.get('outcome', '')}"
                scene_title = scene.get("title", f"Scene {idx}")
            else:
                scene_text = f"{getattr(scene, 'goal', '')} {getattr(scene, 'conflict', '')} {getattr(scene, 'outcome', '')}"
                scene_title = getattr(scene, "title", f"Scene {idx}")

            # Look for question words (seed indicators)
            question_words = ["why", "what", "who", "how", "mystery", "secret", "unknown"]
            if any(word in scene_text.lower() for word in question_words):
                seeds.append({
                    "scene_index": idx,
                    "scene_title": scene_title,
                    "type": "question_mystery",
                    "text": scene_text[:100]  # First 100 chars
                })

            # Look for resolution words (payoff indicators)
            resolution_words = ["revealed", "discovered", "understood", "answered", "resolved"]
            if any(word in scene_text.lower() for word in resolution_words):
                payoffs.append({
                    "scene_index": idx,
                    "scene_title": scene_title,
                    "type": "resolution",
                    "text": scene_text[:100]
                })

        return {
            "seeds": seeds,
            "payoffs": payoffs
        }

    async def _find_unresolved_promises(
        self,
        scenes: List[Any],
        arc_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find promises that haven't been paid off"""
        unresolved = []

        # Get total scene count
        total_scenes = len(scenes)
        if total_scenes == 0:
            return unresolved

        # Check if seeds near the end haven't been paid off
        # Seeds in last 20% of story should have payoffs
        seed_threshold = int(total_scenes * 0.8)

        # This is simplified - in production would track seed->payoff pairs
        # For now, just flag if there are many seeds but few payoffs
        seeds = await self._identify_seeds_and_payoffs(scenes)
        seed_count = len(seeds.get("seeds", []))
        payoff_count = len(seeds.get("payoffs", []))

        if seed_count > payoff_count * 2:
            unresolved.append({
                "type": "imbalanced_setup_payoff",
                "message": f"Found {seed_count} seeds but only {payoff_count} payoffs - some promises may be unresolved",
                "seed_count": seed_count,
                "payoff_count": payoff_count
            })

        return unresolved

    async def _generate_payoff_recommendations(
        self,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for payoff opportunities"""
        recommendations = []

        unresolved = analysis.get("unresolved_promises", [])
        if unresolved:
            recommendations.append({
                "type": "add_payoffs",
                "message": "Consider adding payoff scenes for unresolved promises",
                "unresolved_count": len(unresolved)
            })

        seeds = analysis.get("seeds", [])
        payoffs = analysis.get("payoffs", [])

        # Check setup-to-payoff ratio
        if seeds and payoffs:
            ratio = len(payoffs) / len(seeds) if seeds else 0
            if ratio < 0.5:
                recommendations.append({
                    "type": "low_payoff_ratio",
                    "message": f"Payoff ratio is {ratio:.1%} - consider adding more payoffs (target: 50-70%)",
                    "current_ratio": ratio
                })

        return recommendations
