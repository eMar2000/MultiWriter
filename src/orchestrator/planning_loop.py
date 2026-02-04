"""Planning Loop - Iterative planning with quality gates"""

import logging
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

from src.llm import LLMProvider
from src.memory import StructuredState, VectorStore, GraphStore
from src.validation import ContinuityValidationService
from src.orchestrator.central_manager import CentralManager, AgentTask
from src.orchestrator.observability_manager import ObservabilityManager
from src.orchestrator.user_interaction_manager import UserInteractionManager
from src.orchestrator.version_manager import VersionManager
from src.orchestrator.canon_sync import CanonSyncManager
from src.models import NovelOutline, EntityRegistry, NovelInput

logger = logging.getLogger(__name__)


class QualityGate(str, Enum):
    """Quality gates for planning phases"""
    ENTITY_COVERAGE = "entity_coverage"
    ARC_STRUCTURE = "arc_structure"
    SCENE_QUALITY = "scene_quality"
    TIMELINE_CONSISTENCY = "timeline_consistency"
    PACING = "pacing"
    THEMATIC_COHERENCE = "thematic_coherence"


class PlanningLoop:
    """Iterative planning loop with quality gates"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        structured_state: StructuredState,
        vector_store: Optional[VectorStore] = None,
        graph_store: Optional[GraphStore] = None,
        validation_service: Optional[ContinuityValidationService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Planning Loop

        Args:
            llm_provider: LLM provider
            structured_state: Structured state storage
            vector_store: Optional vector store
            graph_store: Optional graph store
            validation_service: Optional validation service
            config: Configuration
        """
        self.llm_provider = llm_provider
        self.structured_state = structured_state
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.validation_service = validation_service
        self.config = config or {}
        self.quality_gates: Dict[QualityGate, Callable] = {}

        self.observability_manager = ObservabilityManager(
            graph_store=graph_store,
            config=config
        )
        self.user_interaction_manager = UserInteractionManager(
            config=config
        )
        self.version_manager = VersionManager(
            structured_state=structured_state,
            graph_store=graph_store,
            config=config
        )
        self.canon_sync_manager = CanonSyncManager(
            graph_store=graph_store,
            validation_service=validation_service
        ) if (graph_store and validation_service) else None

        self._register_default_quality_gates()

        self.central_manager = CentralManager(
            llm_provider=llm_provider,
            structured_state=structured_state,
            vector_store=vector_store,
            graph_store=graph_store,
            validation_service=validation_service,
            config=config
        )

    def register_quality_gate(self, gate: QualityGate, validator: Callable):
        """Register a quality gate validator"""
        self.quality_gates[gate] = validator

    def _register_default_quality_gates(self):
        """Register default quality gate validators."""
        async def entity_coverage(data: Any, registry: Optional[EntityRegistry]) -> Dict[str, Any]:
            pct = data.get("coverage_percentage", 0) if isinstance(data, dict) else 0
            threshold = self.config.get("quality_gates", {}).get("coverage_threshold", 70.0)
            return {"pass": pct >= threshold, "message": f"Coverage {pct}% (threshold {threshold}%)"}

        async def arc_structure(data: Any, registry: Optional[EntityRegistry]) -> Dict[str, Any]:
            arcs = data.get("arcs", []) if isinstance(data, dict) else []
            timeline = data.get("timeline", []) if isinstance(data, dict) else []
            ok = len(arcs) > 0 and (not timeline or len(timeline) == len(arcs))
            return {"pass": bool(ok), "message": "Arcs non-empty and timeline consistent" if ok else "Arc structure invalid"}

        async def scene_quality(data: Any, registry: Optional[EntityRegistry]) -> Dict[str, Any]:
            scenes = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "scenes" in item:
                        scenes.extend(item.get("scenes", []))
                    else:
                        scenes.append(item)
            elif isinstance(data, dict):
                expanded = data.get("expanded_arcs", [])
                for arc in expanded:
                    scenes.extend(arc.get("scenes", []) if isinstance(arc, dict) else [])
            for s in scenes:
                scene = s if isinstance(s, dict) else getattr(s, "__dict__", s)
                if not scene.get("goal") or not scene.get("conflict") or not scene.get("outcome"):
                    return {"pass": False, "message": "Some scenes missing goal/conflict/outcome"}
            return {"pass": True, "message": "Scene quality OK"}

        async def timeline_consistency(data: Any, registry: Optional[EntityRegistry]) -> Dict[str, Any]:
            val = data.get("timeline_validation", data) if isinstance(data, dict) else {}
            violations = val.get("violations", []) if isinstance(val, dict) else []
            return {"pass": len(violations) == 0, "message": f"{len(violations)} timeline violation(s)" if violations else "OK"}

        async def pacing(data: Any, registry: Optional[EntityRegistry]) -> Dict[str, Any]:
            analysis = data.get("pacing_analysis", data) if isinstance(data, dict) else {}
            critical = (analysis.get("monotony_flags") or []) + (analysis.get("rushed_sequences") or [])
            return {"pass": len(critical) == 0, "message": "Pacing OK" if not critical else f"{len(critical)} pacing issue(s)"}

        async def thematic_coherence(data: Any, registry: Optional[EntityRegistry]) -> Dict[str, Any]:
            analysis = data.get("theme_analysis", data) if isinstance(data, dict) else {}
            inconsistencies = analysis.get("thematic_inconsistencies", []) if isinstance(analysis, dict) else []
            return {"pass": len(inconsistencies) == 0, "message": "Thematic coherence OK" if not inconsistencies else f"{len(inconsistencies)} inconsistency(ies)"}

        self.register_quality_gate(QualityGate.ENTITY_COVERAGE, entity_coverage)
        self.register_quality_gate(QualityGate.ARC_STRUCTURE, arc_structure)
        self.register_quality_gate(QualityGate.SCENE_QUALITY, scene_quality)
        self.register_quality_gate(QualityGate.TIMELINE_CONSISTENCY, timeline_consistency)
        self.register_quality_gate(QualityGate.PACING, pacing)
        self.register_quality_gate(QualityGate.THEMATIC_COHERENCE, thematic_coherence)

    async def execute_planning_loop(
        self,
        registry: EntityRegistry,
        novel_input: Optional[NovelInput] = None,
        novel_id: Optional[str] = None
    ) -> NovelOutline:
        """
        Execute iterative planning loop

        Args:
            registry: Entity registry from document ingestion
            novel_input: Novel input
            novel_id: Optional novel ID

        Returns:
            Complete NovelOutline
        """
        logger.info("[Planning Loop] Starting iterative planning...")

        # Phase 1: Synthesis and Arc Planning
        logger.info("[Phase 1] Synthesis and Arc Planning...")
        arc_plan = await self._phase_synthesis_and_planning(registry, novel_input, novel_id)

        # Phase 1.5: Theme Guardian (early validation)
        logger.info("[Phase 1.5] Theme Validation...")
        theme_validation = await self._phase_theme_validation(registry, arc_plan, novel_id)

        # Quality Gate: Arc Structure
        if not await self._check_quality_gate(QualityGate.ARC_STRUCTURE, arc_plan, registry):
            logger.warning("  Arc structure quality gate failed, but continuing...")

        # Phase 2: Coverage Verification
        logger.info("[Phase 2] Coverage Verification...")
        coverage_result = await self._phase_coverage_verification(registry, arc_plan, novel_id)

        # Phase 2.5: Character Planning
        logger.info("[Phase 2.5] Character Planning...")
        character_plan = await self._phase_character_planning(registry, arc_plan, novel_id)

        # Quality Gate: Entity Coverage
        coverage_threshold = self.config.get("quality_gates", {}).get("coverage_threshold", 70.0)
        if coverage_result.get("coverage_percentage", 0) < coverage_threshold:
            logger.warning(f"  Coverage below threshold ({coverage_result.get('coverage_percentage', 0)}% < {coverage_threshold}%)")
            # Could trigger revision here

        # Phase 3: Scene Expansion
        logger.info("[Phase 3] Scene Expansion...")
        expanded_arcs = await self._phase_scene_expansion(arc_plan, registry, novel_input, novel_id)

        # Quality Gate: Scene Quality
        if not await self._check_quality_gate(QualityGate.SCENE_QUALITY, expanded_arcs, registry):
            logger.warning("  Scene quality gate failed, but continuing...")

        # Phase 4: Validation and Refinement (iterative)
        logger.info("[Phase 4] Validation and Refinement...")
        refined_outline = await self._phase_validation_and_refinement(
            registry, arc_plan, expanded_arcs, novel_input, novel_id
        )

        # Observability: health report after validation
        refinements = refined_outline.get("refinements", {})
        health_report = await self.observability_manager.report_health(
            refinements=refinements,
            novel_id=novel_id
        )
        if health_report.get("alerts"):
            logger.info(f"  Observability: {len(health_report['alerts'])} alert(s)")
        if health_report.get("escalation_required"):
            logger.warning("  Observability: escalation required")

        # Phase 4.5: Idea Generation (fill gaps)
        logger.info("[Phase 4.5] Idea Generation...")
        idea_proposals = await self._phase_idea_generation(
            registry, arc_plan, expanded_arcs, refined_outline, novel_input, novel_id
        )

        # Phase 5: Final Consolidation
        logger.info("[Phase 5] Final Consolidation...")
        outline = await self._phase_consolidation(
            registry, arc_plan, expanded_arcs, refined_outline, idea_proposals, novel_input, novel_id
        )

        # Canon sync: push outline to canon store when graph is available
        if self.canon_sync_manager:
            try:
                sync_result = await self.canon_sync_manager.sync_outline_to_canon(outline, dry_run=False)
                if sync_result.get("violations"):
                    logger.warning(f"  Canon sync had {len(sync_result['violations'])} violation(s)")
            except Exception as e:
                logger.warning(f"  Canon sync failed: {e}")

        # Version Manager: checkpoint after consolidation
        try:
            await self.version_manager.create_checkpoint(
                outline,
                label="post_planning_loop",
                novel_id=novel_id
            )
        except Exception as e:
            logger.warning(f"  Version checkpoint failed: {e}")

        # Observability: final health report
        final_refinements = refined_outline.get("refinements", {})
        await self.observability_manager.report_health(
            outline=outline.model_dump(mode='json') if hasattr(outline, 'model_dump') else {},
            refinements=final_refinements,
            novel_id=novel_id
        )

        # Queue any approval-required ideas to User Interaction Manager
        for idea in idea_proposals.get("ideas", []) or []:
            if idea.get("requires_approval"):
                await self.user_interaction_manager.add_approval_request(
                    source_agent="idea_generator",
                    request_type=idea.get("type", "idea"),
                    description=idea.get("description", ""),
                    context=idea,
                    priority="high" if idea.get("benefit") == "high" else "medium"
                )

        logger.info("[Planning Loop] Planning complete")
        return outline

    async def _phase_synthesis_and_planning(
        self,
        registry: EntityRegistry,
        novel_input: Optional[NovelInput],
        novel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 1: Synthesis and arc planning"""
        from src.agents import SynthesisAgent, OutlineArchitectAgent

        # Create tasks
        tasks = [
            AgentTask(
                agent_name="synthesis",
                agent_class=SynthesisAgent,
                context={
                    "entity_registry": registry,
                    "novel_input": novel_input.model_dump() if novel_input else {}
                },
                priority=10
            ),
            AgentTask(
                agent_name="outline_architect",
                agent_class=OutlineArchitectAgent,
                context={},  # Will be updated by synthesis result
                dependencies=["synthesis"],
                priority=9
            )
        ]

        # Execute tasks
        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)

        # Combine results
        synthesis_output = result["results"].get("synthesis", {}).get("output", {})
        architect_output = result["results"].get("outline_architect", {}).get("output", {})

        return {
            "relationships": synthesis_output.get("relationships", []),
            "conflicts": synthesis_output.get("conflicts", []),
            "themes": synthesis_output.get("themes", []),
            "arcs": architect_output.get("arcs", []),
            "timeline": architect_output.get("timeline", [])
        }

    async def _phase_theme_validation(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        novel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 1.5: Early theme validation (per plan section 8.5)"""
        from src.agents import ThemeGuardianAgent

        # Get relationships from arc_plan
        relationships = {
            "themes": arc_plan.get("themes", []),
            "relationships": arc_plan.get("relationships", [])
        }

        tasks = [
            AgentTask(
                agent_name="theme_guardian_early",
                agent_class=ThemeGuardianAgent,
                context={
                    "relationships": relationships,
                    "arc_plan": arc_plan,
                    "entity_registry": registry
                },
                dependencies=["outline_architect"],
                priority=8  # High priority, runs early
            )
        ]

        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)
        return result["results"].get("theme_guardian_early", {}).get("output", {})

    async def _phase_coverage_verification(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        novel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 2: Coverage verification"""
        from src.agents import CoverageVerifierAgent

        tasks = [
            AgentTask(
                agent_name="coverage_verifier",
                agent_class=CoverageVerifierAgent,
                context={
                    "entity_registry": registry,
                    "arc_plan": arc_plan
                },
                priority=8
            )
        ]

        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)
        return result["results"].get("coverage_verifier", {}).get("output", {})

    async def _phase_character_planning(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        novel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 2.5: Character planning (per plan section 8.6)"""
        from src.agents import CharacterPlannerAgent

        tasks = [
            AgentTask(
                agent_name="character_planner",
                agent_class=CharacterPlannerAgent,
                context={
                    "entity_registry": registry,
                    "arc_plan": arc_plan
                },
                dependencies=["outline_architect"],
                priority=7  # After arc planning, before scene expansion
            )
        ]

        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)
        return result["results"].get("character_planner", {}).get("output", {})

    async def _phase_scene_expansion(
        self,
        arc_plan: Dict[str, Any],
        registry: EntityRegistry,
        novel_input: Optional[NovelInput],
        novel_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Phase 3: Scene expansion"""
        from src.agents import SceneDynamicsAgent

        # Create tasks for each arc
        tasks = []
        for idx, arc in enumerate(arc_plan.get("arcs", [])):
            arc_id = arc.get("id", f"arc_{idx}") if isinstance(arc, dict) else getattr(arc, "id", f"arc_{idx}")
            tasks.append(
                AgentTask(
                    agent_name=f"scene_expansion_{arc_id}",
                    agent_class=SceneDynamicsAgent,
                    context={
                        "arc": arc,
                        "entity_registry": registry,
                        "novel_input": novel_input.model_dump() if novel_input else {}
                    },
                    dependencies=["outline_architect"],
                    priority=7 - idx  # Earlier arcs have higher priority
                )
            )

        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)

        # Collect expanded arcs
        expanded = []
        for task_name, task_result in result["results"].items():
            if task_name.startswith("scene_expansion_"):
                arc_id = task_name.replace("scene_expansion_", "")
                expanded.append({
                    "arc_id": arc_id,
                    "scenes": task_result.get("output", {}).get("scenes", [])
                })

        return expanded

    async def _phase_validation_and_refinement(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        expanded_arcs: List[Dict[str, Any]],
        novel_input: Optional[NovelInput],
        novel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 4: Validation and refinement (iterative)"""
        from src.agents import (
            TimelineManagerAgent,
            PacingAgent,
            ThemeGuardianAgent,
            ForeshadowingAgent
        )

        # Build temporary outline for validation agents
        from datetime import datetime
        from src.models import SceneOutline, NovelOutline

        all_scenes = []
        for arc_expansion in expanded_arcs:
            scene_dicts = arc_expansion.get("scenes", [])
            for scene_dict in scene_dicts:
                if isinstance(scene_dict, dict):
                    try:
                        scene = SceneOutline(**scene_dict)
                        all_scenes.append(scene)
                    except Exception as e:
                        logger.warning(f"  Failed to convert scene dict: {e}")
                        continue
                elif isinstance(scene_dict, SceneOutline):
                    all_scenes.append(scene_dict)

        temp_outline = NovelOutline(
            id=novel_id,
            input=novel_input,
            entity_registry=registry,
            scenes=all_scenes,
            status="in_progress",
            updated_at=datetime.utcnow()
        )

        # Get relationships from synthesis phase
        relationships = arc_plan.get("relationships", {}) if isinstance(arc_plan.get("relationships"), dict) else {}

        # Create validation tasks
        tasks = [
            # Theme Guardian - runs early to validate thematic coherence
            AgentTask(
                agent_name="theme_guardian",
                agent_class=ThemeGuardianAgent,
                context={
                    "outline": temp_outline.model_dump(mode='json'),
                    "relationships": relationships,
                    "arc_plan": arc_plan
                },
                dependencies=["outline_architect"],
                priority=6,
                validation_fn=lambda result: {
                    "valid": len(result.get("output", {}).get("thematic_inconsistencies", [])) == 0,
                    "message": "Thematic inconsistencies found" if result.get("output", {}).get("thematic_inconsistencies") else "OK"
                }
            ),
            # Timeline Manager - validates chronological consistency
            AgentTask(
                agent_name="timeline_manager",
                agent_class=TimelineManagerAgent,
                context={
                    "outline": temp_outline.model_dump(mode='json'),
                    "entity_registry": registry,
                    "graph_store": self.graph_store
                },
                dependencies=["scene_expansion_*"],  # After all scene expansions
                priority=5,
                validation_fn=lambda result: {
                    "valid": result.get("output", {}).get("is_valid", True),
                    "message": f"Timeline violations: {len(result.get('output', {}).get('violations', []))}"
                }
            ),
            # Pacing Agent - analyzes pacing and rhythm
            AgentTask(
                agent_name="pacing_agent",
                agent_class=PacingAgent,
                context={
                    "outline": temp_outline.model_dump(mode='json'),
                    "arc_plan": arc_plan,
                    "genre": novel_input.genre.value if novel_input and novel_input.genre else "other"
                },
                dependencies=["scene_expansion_*"],  # After all scene expansions
                priority=4
            ),
            # Foreshadowing Agent - tracks seeds and payoffs
            AgentTask(
                agent_name="foreshadowing_agent",
                agent_class=ForeshadowingAgent,
                context={
                    "outline": temp_outline.model_dump(mode='json'),
                    "arc_plan": arc_plan
                },
                dependencies=["scene_expansion_*"],  # After all scene expansions
                priority=3
            )
        ]

        # Execute validation tasks
        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)

        # Collect validation results
        refinements = {
            "theme_analysis": result["results"].get("theme_guardian", {}).get("output", {}),
            "timeline_validation": result["results"].get("timeline_manager", {}).get("output", {}),
            "pacing_analysis": result["results"].get("pacing_agent", {}).get("output", {}),
            "foreshadowing_analysis": result["results"].get("foreshadowing_agent", {}).get("output", {})
        }

        return {
            "arc_plan": arc_plan,
            "expanded_arcs": expanded_arcs,
            "refinements": refinements
        }

    async def _phase_idea_generation(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        expanded_arcs: List[Dict[str, Any]],
        refined_data: Dict[str, Any],
        novel_input: Optional[NovelInput],
        novel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Phase 4.5: Idea generation to fill gaps (per plan section 8.9)"""
        from src.agents import IdeaGeneratorAgent
        from datetime import datetime
        from src.models import SceneOutline, NovelOutline

        # Build temporary outline for idea generator
        all_scenes = []
        for arc_expansion in expanded_arcs:
            scene_dicts = arc_expansion.get("scenes", [])
            for scene_dict in scene_dicts:
                if isinstance(scene_dict, dict):
                    try:
                        scene = SceneOutline(**scene_dict)
                        all_scenes.append(scene)
                    except Exception as e:
                        logger.warning(f"  Failed to convert scene dict: {e}")
                        continue
                elif isinstance(scene_dict, SceneOutline):
                    all_scenes.append(scene_dict)

        temp_outline = NovelOutline(
            id=novel_id,
            input=novel_input,
            entity_registry=registry,
            scenes=all_scenes,
            status="in_progress",
            updated_at=datetime.utcnow()
        )

        # Collect validation results from Phase 4
        validation_results = refined_data.get("refinements", {})

        tasks = [
            AgentTask(
                agent_name="idea_generator",
                agent_class=IdeaGeneratorAgent,
                context={
                    "outline": temp_outline.model_dump(mode='json'),
                    "entity_registry": registry,
                    "arc_plan": arc_plan,
                    "validation_results": validation_results,
                    "user_constraints": {}  # Could be passed from config
                },
                dependencies=["timeline_manager", "pacing_agent", "foreshadowing_agent", "theme_guardian"],  # After all validation
                priority=2  # Lower priority, runs after validation
            )
        ]

        result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)
        return result["results"].get("idea_generator", {}).get("output", {})

    async def _phase_consolidation(
        self,
        registry: EntityRegistry,
        arc_plan: Dict[str, Any],
        expanded_arcs: List[Dict[str, Any]],
        refined_data: Dict[str, Any],
        idea_proposals: Dict[str, Any],
        novel_input: Optional[NovelInput],
        novel_id: Optional[str]
    ) -> NovelOutline:
        """Phase 5: Final consolidation"""
        from datetime import datetime
        from src.models import SceneOutline

        # Collect all scenes
        all_scenes = []
        for arc_expansion in expanded_arcs:
            scene_dicts = arc_expansion.get("scenes", [])
            for scene_dict in scene_dicts:
                if isinstance(scene_dict, dict):
                    try:
                        scene = SceneOutline(**scene_dict)
                        all_scenes.append(scene)
                    except Exception as e:
                        logger.warning(f"  Failed to convert scene dict: {e}")
                        continue
                elif isinstance(scene_dict, SceneOutline):
                    all_scenes.append(scene_dict)

        # Build outline
        outline = NovelOutline(
            id=novel_id,
            input=novel_input,
            entity_registry=registry,
            scenes=all_scenes,
            status="completed",
            updated_at=datetime.utcnow()
        )

        # Add relationships
        outline.relationships = {
            "arcs": arc_plan.get("arcs", []),
            "timeline": arc_plan.get("timeline", []),
            "themes": arc_plan.get("themes", [])
        }

        # Add validation and idea generation results to metadata
        outline.metadata = {
            "validation_results": refined_data.get("refinements", {}),
            "idea_proposals": idea_proposals.get("ideas", []),
            "character_plan": {}  # Would be populated from character_plan if needed
        }

        # Save to storage
        await self.central_manager.structured_state.write(
            "novel-outlines",
            outline.model_dump(mode='json')
        )

        return outline

    async def _check_quality_gate(
        self,
        gate: QualityGate,
        data: Any,
        registry: Optional[EntityRegistry] = None
    ) -> bool:
        """Check a quality gate"""
        validator = self.quality_gates.get(gate)
        if not validator:
            return True  # No validator registered, pass by default

        try:
            result = await validator(data, registry) if registry else await validator(data)
            return result.get("pass", True)
        except Exception as e:
            logger.warning(f"Quality gate {gate} check failed: {e}")
            return True  # Fail open for now
