"""Idea Generator Agent - Proposes new ideas to fill gaps"""

import logging
from typing import Dict, Any, Optional, List

from src.agents.base import BaseAgent
from src.models import EntityType

logger = logging.getLogger(__name__)


class IdeaGeneratorAgent(BaseAgent):
    """Generates ideas to fill gaps or resolve issues"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="idea_generator", *args, **kwargs)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ideas to fill gaps

        Args:
            context: Should contain:
                - outline: NovelOutline or dict
                - entity_registry: EntityRegistry
                - arc_plan: Dict with arcs
                - validation_results: Results from other agents
                - user_constraints: Optional user constraints

        Returns:
            Idea proposals with cost/benefit/risk analysis
        """
        outline = context.get("outline")
        entity_registry = context.get("entity_registry")
        arc_plan = context.get("arc_plan", {})
        validation_results = context.get("validation_results", {})
        user_constraints = context.get("user_constraints", {})

        proposals = {
            "ideas": [],
            "gap_analysis": {},
            "recommendations": []
        }

        # Analyze gaps
        proposals["gap_analysis"] = await self._analyze_gaps(
            outline, entity_registry, arc_plan, validation_results
        )

        # Generate ideas to fill gaps
        proposals["ideas"] = await self._generate_ideas(
            proposals["gap_analysis"], user_constraints
        )

        # Generate recommendations
        proposals["recommendations"] = await self._prioritize_proposals(proposals["ideas"])

        return {
            "output": proposals
        }

    async def _analyze_gaps(
        self,
        outline: Optional[Dict[str, Any]],
        entity_registry: Optional[Any],
        arc_plan: Dict[str, Any],
        validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze gaps in the story"""
        gaps = {
            "plot_holes": [],
            "underdeveloped_areas": [],
            "missing_elements": [],
            "stale_areas": []
        }

        # Check validation results for issues
        timeline_validation = validation_results.get("timeline_validation", {})
        if timeline_validation.get("violations"):
            gaps["plot_holes"].extend([
                {
                    "type": "timeline_violation",
                    "issue": v.get("message", "Timeline violation"),
                    "severity": "high"
                }
                for v in timeline_validation.get("violations", [])
            ])

        pacing_analysis = validation_results.get("pacing_analysis", {})
        if pacing_analysis.get("monotony_flags"):
            gaps["stale_areas"].extend([
                {
                    "type": "monotony",
                    "issue": f"Monotony detected: {m.get('scene_type')} scenes repeated {m.get('count')} times",
                    "severity": "medium"
                }
                for m in pacing_analysis.get("monotony_flags", [])
            ])

        # Check for underdeveloped arcs
        arcs = arc_plan.get("arcs", [])
        scenes = outline.get("scenes", []) if outline else []

        if arcs and scenes:
            scenes_per_arc = len(scenes) / len(arcs) if arcs else 0
            if scenes_per_arc < 3:
                gaps["underdeveloped_areas"].append({
                    "type": "thin_arcs",
                    "issue": f"Average {scenes_per_arc:.1f} scenes per arc - consider expanding",
                    "severity": "medium"
                })

        # Check for missing elements
        if entity_registry:
            characters = entity_registry.get_by_type(EntityType.CHARACTER) if hasattr(entity_registry, "get_by_type") else []
            if len(characters) < 2:
                gaps["missing_elements"].append({
                    "type": "few_characters",
                    "issue": f"Only {len(characters)} character(s) - consider adding more",
                    "severity": "low"
                })

        return gaps

    async def _generate_ideas(
        self,
        gap_analysis: Dict[str, Any],
        user_constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate ideas to fill gaps (heuristic + optional LLM for creative alternatives)"""
        ideas = []

        for plot_hole in gap_analysis.get("plot_holes", []):
            ideas.append({
                "type": "fix_plot_hole",
                "description": f"Resolve: {plot_hole.get('issue', '')}",
                "cost": "low",
                "benefit": "high",
                "risk": "low",
                "requires_approval": False
            })

        for stale in gap_analysis.get("stale_areas", []):
            ideas.append({
                "type": "add_variety",
                "description": f"Add scene variety to address: {stale.get('issue', '')}",
                "cost": "medium",
                "benefit": "medium",
                "risk": "low",
                "requires_approval": False
            })

        for underdev in gap_analysis.get("underdeveloped_areas", []):
            ideas.append({
                "type": "expand_arc",
                "description": f"Expand arcs: {underdev.get('issue', '')}",
                "cost": "medium",
                "benefit": "high",
                "risk": "low",
                "requires_approval": True
            })

        for missing in gap_analysis.get("missing_elements", []):
            ideas.append({
                "type": "add_element",
                "description": f"Add elements: {missing.get('issue', '')}",
                "cost": "medium",
                "benefit": "medium",
                "risk": "medium",
                "requires_approval": True
            })

        # Optional LLM: creative alternatives for top gaps
        gap_count = (
            len(gap_analysis.get("plot_holes", []))
            + len(gap_analysis.get("underdeveloped_areas", []))
            + len(gap_analysis.get("missing_elements", []))
        )
        if gap_count > 0:
            try:
                user_prompt = f"""Story gaps detected: plot_holes, underdeveloped_areas, missing_elements. Suggest 1-3 creative story ideas to address them (with cost/benefit/risk).

Gap summary: {list(gap_analysis.keys())}

Respond with JSON only: {{ "ideas": [ {{ "type": "...", "description": "...", "cost": "low|medium|high", "benefit": "low|medium|high", "risk": "low|medium|high", "requires_approval": true|false }} ] }}."""
                result = await self.generate_structured_output(
                    system_prompt="You are a story development expert. Output valid JSON only.",
                    user_prompt=user_prompt,
                    temperature=0.6,
                    max_tokens=600
                )
                for idea in result.get("ideas", [])[:3]:
                    ideas.append({
                        "type": idea.get("type", "creative"),
                        "description": idea.get("description", ""),
                        "cost": idea.get("cost", "medium"),
                        "benefit": idea.get("benefit", "medium"),
                        "risk": idea.get("risk", "low"),
                        "requires_approval": idea.get("requires_approval", True)
                    })
            except Exception:
                pass

        return ideas

    async def _prioritize_proposals(
        self,
        ideas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prioritize proposals by cost/benefit/risk"""
        # Sort by benefit (high first), then by cost (low first)
        prioritized = sorted(
            ideas,
            key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}.get(x.get("benefit", "low"), 1),
                -{"high": 3, "medium": 2, "low": 1}.get(x.get("cost", "high"), 3)
            ),
            reverse=True
        )

        return [
            {
                "idea": idea,
                "priority": "high" if idea.get("benefit") == "high" and idea.get("cost") == "low" else "medium"
            }
            for idea in prioritized
        ]
