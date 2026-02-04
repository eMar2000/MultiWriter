"""Theme Guardian Agent - Ensures thematic coherence"""

import logging
from typing import Dict, Any, Optional, List

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ThemeGuardianAgent(BaseAgent):
    """Tracks motifs and ensures thematic coherence"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="theme_guardian", *args, **kwargs)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate thematic coherence

        Args:
            context: Should contain:
                - outline: NovelOutline or dict
                - relationships: From synthesis agent (themes, motifs)
                - arc_plan: Dict with arcs

        Returns:
            Thematic analysis with recommendations
        """
        outline = context.get("outline")
        relationships = context.get("relationships", {})
        arc_plan = context.get("arc_plan", {})
        themes = relationships.get("themes", []) if isinstance(relationships, dict) else []

        analysis = {
            "themes_identified": themes,
            "motif_tracking": {},
            "thematic_inconsistencies": [],
            "abandoned_themes": [],
            "recommendations": []
        }

        # Track motif appearances
        if outline:
            scenes = outline.get("scenes", [])
            analysis["motif_tracking"] = await self._track_motifs(scenes, themes)

        # Check for thematic inconsistencies
        analysis["thematic_inconsistencies"] = await self._check_inconsistencies(
            outline, themes, arc_plan
        )

        # Check for abandoned themes
        analysis["abandoned_themes"] = await self._check_abandoned_themes(
            outline, themes
        )

        # Generate recommendations
        analysis["recommendations"] = await self._generate_recommendations(analysis)

        return {
            "output": analysis
        }

    async def _track_motifs(
        self,
        scenes: List[Any],
        themes: List[Any]
    ) -> Dict[str, Any]:
        """Track motif appearances across scenes"""
        motif_tracking = {}

        # Initialize tracking for each theme
        for theme in themes:
            if isinstance(theme, dict):
                theme_name = theme.get("name", str(theme))
            else:
                theme_name = str(theme)
            motif_tracking[theme_name] = {
                "appearances": 0,
                "scenes": []
            }

        # Count appearances in scenes
        for idx, scene in enumerate(scenes):
            scene_text = ""
            if isinstance(scene, dict):
                scene_text = f"{scene.get('goal', '')} {scene.get('conflict', '')} {scene.get('outcome', '')}"
            else:
                scene_text = f"{getattr(scene, 'goal', '')} {getattr(scene, 'conflict', '')} {getattr(scene, 'outcome', '')}"

            # Simple keyword matching (in production, would use more sophisticated analysis)
            for theme_name in motif_tracking:
                if theme_name.lower() in scene_text.lower():
                    motif_tracking[theme_name]["appearances"] += 1
                    motif_tracking[theme_name]["scenes"].append(idx)

        return motif_tracking

    async def _check_inconsistencies(
        self,
        outline: Optional[Dict[str, Any]],
        themes: List[Any],
        arc_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check for thematic inconsistencies"""
        inconsistencies = []

        # Check if themes are mentioned in arcs
        arcs = arc_plan.get("arcs", [])
        for theme in themes:
            theme_name = theme.get("name", str(theme)) if isinstance(theme, dict) else str(theme)
            found_in_arcs = False

            for arc in arcs:
                arc_text = str(arc)
                if theme_name.lower() in arc_text.lower():
                    found_in_arcs = True
                    break

            if not found_in_arcs and themes:
                inconsistencies.append({
                    "type": "theme_not_in_arcs",
                    "theme": theme_name,
                    "message": f"Theme '{theme_name}' identified but not reflected in arc structure"
                })

        return inconsistencies

    async def _check_abandoned_themes(
        self,
        outline: Optional[Dict[str, Any]],
        themes: List[Any]
    ) -> List[Dict[str, Any]]:
        """Check for themes that are introduced but never developed"""
        abandoned = []

        if not outline:
            return abandoned

        scenes = outline.get("scenes", [])
        if len(scenes) < 3:
            return abandoned  # Too early to tell

        # Check if themes appear in early scenes but not later
        early_scenes = scenes[:len(scenes)//3]
        late_scenes = scenes[2*len(scenes)//3:]

        for theme in themes:
            theme_name = theme.get("name", str(theme)) if isinstance(theme, dict) else str(theme)
            
            # Check early scenes
            in_early = any(
                theme_name.lower() in str(scene).lower()
                for scene in early_scenes
            )

            # Check late scenes
            in_late = any(
                theme_name.lower() in str(scene).lower()
                for scene in late_scenes
            )

            if in_early and not in_late:
                abandoned.append({
                    "type": "abandoned_theme",
                    "theme": theme_name,
                    "message": f"Theme '{theme_name}' introduced early but not developed later"
                })

        return abandoned

    async def _generate_recommendations(
        self,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for thematic improvement"""
        recommendations = []

        motif_tracking = analysis.get("motif_tracking", {})
        for theme_name, tracking in motif_tracking.items():
            appearances = tracking.get("appearances", 0)
            
            if appearances == 0:
                recommendations.append({
                    "type": "missing_motif",
                    "theme": theme_name,
                    "message": f"Theme '{theme_name}' identified but not appearing in scenes"
                })
            elif appearances < 2:
                recommendations.append({
                    "type": "sparse_motif",
                    "theme": theme_name,
                    "message": f"Theme '{theme_name}' appears only {appearances} time(s) - consider reinforcing"
                })

        # Add recommendations for inconsistencies
        for inconsistency in analysis.get("thematic_inconsistencies", []):
            recommendations.append({
                "type": "thematic_inconsistency",
                "message": inconsistency.get("message", "")
            })

        return recommendations
