"""Character Planner Agent - Fleshes out character development"""

import logging
from typing import Dict, Any, Optional, List

from src.agents.base import BaseAgent
from src.models import EntityRegistry, EntityType

logger = logging.getLogger(__name__)


class CharacterPlannerAgent(BaseAgent):
    """Plans character development and consistency"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="character_planner", *args, **kwargs)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan character development

        Args:
            context: Should contain:
                - outline: NovelOutline or dict
                - entity_registry: EntityRegistry
                - arc_plan: Dict with arcs

        Returns:
            Character planning analysis with proposals
        """
        outline = context.get("outline")
        entity_registry = context.get("entity_registry")
        arc_plan = context.get("arc_plan", {})

        analysis = {
            "character_analysis": {},
            "development_gaps": [],
            "new_character_proposals": [],
            "consistency_issues": [],
            "recommendations": []
        }

        if entity_registry:
            # Analyze characters
            characters = entity_registry.get_by_type(EntityType.CHARACTER)
            analysis["character_analysis"] = await self._analyze_characters(
                characters, outline, arc_plan
            )

            # Check for development gaps
            analysis["development_gaps"] = await self._identify_development_gaps(
                characters, outline, arc_plan
            )

            # Check for missing characters
            analysis["new_character_proposals"] = await self._propose_new_characters(
                outline, arc_plan, characters
            )

            # Check consistency
            analysis["consistency_issues"] = await self._check_consistency(
                characters, outline
            )

        # Generate recommendations
        analysis["recommendations"] = await self._generate_recommendations(analysis)

        return {
            "output": analysis
        }

    async def _analyze_characters(
        self,
        characters: List[Any],
        outline: Optional[Dict[str, Any]],
        arc_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze character usage and development"""
        character_analysis = {}

        scenes = outline.get("scenes", []) if outline else []

        for char in characters:
            char_id = char.id if hasattr(char, "id") else str(char)
            char_name = char.name if hasattr(char, "name") else str(char)

            # Count appearances
            appearances = 0
            pov_count = 0
            for scene in scenes:
                if isinstance(scene, dict):
                    scene_chars = scene.get("characters_present", [])
                    scene_pov = scene.get("pov_character")
                else:
                    scene_chars = getattr(scene, "characters_present", []) or []
                    scene_pov = getattr(scene, "pov_character", None)

                if char_id in scene_chars:
                    appearances += 1
                if scene_pov == char_id:
                    pov_count += 1

            character_analysis[char_id] = {
                "name": char_name,
                "appearances": appearances,
                "pov_count": pov_count,
                "development_stage": "introduced" if appearances == 0 else "developing" if appearances < 3 else "active"
            }

        return character_analysis

    async def _identify_development_gaps(
        self,
        characters: List[Any],
        outline: Optional[Dict[str, Any]],
        arc_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify characters that need more development"""
        gaps = []

        scenes = outline.get("scenes", []) if outline else []
        total_scenes = len(scenes)

        for char in characters:
            char_id = char.id if hasattr(char, "id") else str(char)
            char_name = char.name if hasattr(char, "name") else str(char)

            # Count appearances
            appearances = sum(
                1 for scene in scenes
                if char_id in (scene.get("characters_present", []) if isinstance(scene, dict) else getattr(scene, "characters_present", []) or [])
            )

            # Check if character is underutilized
            if appearances == 0 and total_scenes > 0:
                gaps.append({
                    "type": "unused_character",
                    "character_id": char_id,
                    "character_name": char_name,
                    "message": f"Character '{char_name}' is defined but never appears in scenes"
                })
            elif appearances > 0 and appearances < total_scenes * 0.1:
                gaps.append({
                    "type": "underutilized_character",
                    "character_id": char_id,
                    "character_name": char_name,
                    "appearances": appearances,
                    "message": f"Character '{char_name}' appears only {appearances} time(s) - consider more development"
                })

        return gaps

    async def _propose_new_characters(
        self,
        outline: Optional[Dict[str, Any]],
        arc_plan: Dict[str, Any],
        existing_characters: List[Any]
    ) -> List[Dict[str, Any]]:
        """Propose new characters if plot requires them (heuristic + optional LLM)"""
        proposals = []

        scenes = outline.get("scenes", []) if outline else []
        arcs = arc_plan.get("arcs", [])
        if len(scenes) > 5 and len(existing_characters) < 3:
            proposals.append({
                "type": "supporting_character",
                "rationale": "Story has many scenes but few characters - consider adding supporting characters",
                "suggested_role": "supporting",
                "priority": "medium"
            })

        # Optional LLM: plot-driven character proposals
        if arcs and len(arcs) >= 1:
            try:
                arc_summary = "\n".join(
                    f"- {a.get('name', '')}: {a.get('description', '')[:150]}"
                    for a in (arcs if isinstance(arcs[0], dict) else [getattr(a, "__dict__", {}) for a in arcs])
                )
                existing_names = [getattr(c, "name", str(c)) for c in existing_characters[:20]]
                user_prompt = f"""Given these story arcs and existing characters, suggest any NEW characters the plot might need (mentor, antagonist, ally, etc.).

ARCS:
{arc_summary}

EXISTING CHARACTERS: {', '.join(existing_names) or 'None'}

Respond with JSON only: {{ "proposals": [ {{ "type": "...", "rationale": "...", "suggested_role": "...", "priority": "low|medium|high" }} ] }}. If no new characters needed, return {{ "proposals": [] }}."""
                result = await self.generate_structured_output(
                    system_prompt="You are a character planning expert. Output valid JSON only.",
                    user_prompt=user_prompt,
                    temperature=0.5,
                    max_tokens=800
                )
                proposals.extend(result.get("proposals", []))
            except Exception:
                pass

        return proposals

    async def _check_consistency(
        self,
        characters: List[Any],
        outline: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check character consistency across appearances"""
        issues = []

        scenes = outline.get("scenes", []) if outline else []

        # Check for characters appearing in multiple places at once
        for char in characters:
            char_id = char.id if hasattr(char, "id") else str(char)
            char_name = char.name if hasattr(char, "name") else str(char)

            # Get all scenes where character appears
            char_scenes = []
            for idx, scene in enumerate(scenes):
                if isinstance(scene, dict):
                    scene_chars = scene.get("characters_present", [])
                    scene_location = scene.get("location_id")
                    scene_time = scene.get("time_period")
                else:
                    scene_chars = getattr(scene, "characters_present", []) or []
                    scene_location = getattr(scene, "location_id", None)
                    scene_time = getattr(scene, "time_period", None)

                if char_id in scene_chars:
                    char_scenes.append({
                        "index": idx,
                        "location": scene_location,
                        "time": scene_time
                    })

            # Check for rapid location changes (potential inconsistency)
            if len(char_scenes) >= 2:
                for i in range(1, len(char_scenes)):
                    prev = char_scenes[i-1]
                    curr = char_scenes[i]
                    if prev["location"] and curr["location"] and prev["location"] != curr["location"]:
                        if prev["time"] == curr["time"]:
                            issues.append({
                                "type": "impossible_location_change",
                                "character_id": char_id,
                                "character_name": char_name,
                                "message": f"Character '{char_name}' appears in different locations at same time period",
                                "scenes": [prev["index"], curr["index"]]
                            })

        return issues

    async def _generate_recommendations(
        self,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for character development (heuristic + optional LLM)"""
        recommendations = []

        for gap in analysis.get("development_gaps", []):
            if gap.get("type") == "unused_character":
                recommendations.append({
                    "type": "add_scenes",
                    "character_id": gap.get("character_id"),
                    "message": f"Add scenes featuring {gap.get('character_name', 'character')} to utilize this character"
                })

        for issue in analysis.get("consistency_issues", []):
            recommendations.append({
                "type": "fix_consistency",
                "message": issue.get("message", ""),
                "character_id": issue.get("character_id")
            })

        for proposal in analysis.get("new_character_proposals", []):
            recommendations.append({
                "type": "consider_new_character",
                "message": proposal.get("rationale", ""),
                "priority": proposal.get("priority", "low")
            })

        # Optional LLM: enrich with narrative recommendations
        if recommendations and len(recommendations) <= 10:
            try:
                user_prompt = f"""Based on this character analysis, suggest 1-3 high-level narrative recommendations (e.g. strengthen arc, add beat).

ANALYSIS SUMMARY:
- Development gaps: {len(analysis.get('development_gaps', []))}
- Consistency issues: {len(analysis.get('consistency_issues', []))}
- New character proposals: {len(analysis.get('new_character_proposals', []))}

Respond with JSON only: {{ "recommendations": [ {{ "type": "narrative", "message": "..." }} ] }}."""
                result = await self.generate_structured_output(
                    system_prompt="You are a story editor. Output valid JSON only.",
                    user_prompt=user_prompt,
                    temperature=0.5,
                    max_tokens=400
                )
                for r in result.get("recommendations", [])[:3]:
                    recommendations.append({"type": r.get("type", "narrative"), "message": r.get("message", "")})
            except Exception:
                pass

        return recommendations
