# Planning Agents Integration Summary

## Overview

All planning agents from the Project_Overview.md document have been created and integrated into the iterative planning loop.

## Agents Created

### 1. Timeline Manager Agent (`src/agents/timeline_manager.py`)
**Section 8.3** - Maintain chronological consistency

**Features**:
- Validates event sequences against before/after edges
- Checks travel time feasibility between locations
- Flags temporal impossibilities
- Supports timeline cycle detection (with GraphDB)
- Basic validation without GraphDB

**Integration**: Phase 4 (Validation and Refinement)
- Runs after all scene expansions
- Priority: 5
- Dependencies: `scene_expansion_*` (wildcard)

---

### 2. Pacing Agent (`src/agents/pacing_agent.py`)
**Section 8.4** - Analyze and optimize story pacing

**Features**:
- Analyzes action/reflection/dialogue ratios per arc
- Ensures scene length variety
- Flags monotony (consecutive similar scenes)
- Flags rushed sequences (large tension jumps)
- Validates escalation curves (tension should build)
- Genre-specific pacing recommendations

**Integration**: Phase 4 (Validation and Refinement)
- Runs after all scene expansions
- Priority: 4
- Dependencies: `scene_expansion_*` (wildcard)

---

### 3. Theme Guardian Agent (`src/agents/theme_guardian.py`)
**Section 8.5** - Ensure thematic coherence

**Features**:
- Tracks motif appearances and development across arcs
- Ensures thematic arcs parallel plot arcs
- Flags thematic inconsistencies or abandonment
- Maintains motif density tracking
- Validates payoff of thematic setups

**Integration**: 
- **Phase 1.5**: Early theme validation (after arc planning)
- **Phase 4**: Full theme analysis (after scene expansion)
- Priority: 6 (Phase 4), 8 (Phase 1.5)
- Dependencies: `outline_architect`

---

### 4. Foreshadowing & Payoff Agent (`src/agents/foreshadowing_agent.py`)
**Section 8.8** - Track seeds, reminders, and payoffs

**Features**:
- Tracks seeds → reminders → payoffs
- Flags unresolved promises approaching end of story
- Suggests payoff opportunities
- Maintains setup-to-payoff timing ratios
- Validates that major setups have planned resolutions

**Integration**: Phase 4 (Validation and Refinement)
- Runs after all scene expansions
- Priority: 3
- Dependencies: `scene_expansion_*` (wildcard)

---

## Integration Flow

### Phase 1: Synthesis and Arc Planning
1. **SynthesisAgent** - Analyzes relationships, conflicts, themes
2. **OutlineArchitectAgent** - Creates narrative arcs

### Phase 1.5: Early Theme Validation
3. **ThemeGuardianAgent** (early) - Validates themes are reflected in arcs

### Phase 2: Coverage Verification
4. **CoverageVerifierAgent** - Verifies all entities are referenced

### Phase 3: Scene Expansion
5. **SceneDynamicsAgent** (per arc) - Expands arcs into detailed scenes

### Phase 4: Validation and Refinement
6. **ThemeGuardianAgent** (full) - Complete thematic analysis
7. **TimelineManagerAgent** - Validates chronological consistency
8. **PacingAgent** - Analyzes pacing and rhythm
9. **ForeshadowingAgent** - Tracks seeds and payoffs

### Phase 5: Final Consolidation
10. Builds final outline with all validation results

---

## Dependency Management

The Central Manager now supports:
- **Exact dependencies**: `["synthesis"]` - waits for exact task name
- **Wildcard dependencies**: `["scene_expansion_*"]` - waits for any task matching pattern

This allows validation agents to wait for all scene expansion tasks to complete.

---

## Validation Functions

Agents can have validation functions that check their output:
- **TimelineManagerAgent**: Validates no timeline violations
- **ThemeGuardianAgent**: Validates no thematic inconsistencies

If validation fails, the task is marked as failed and can be retried.

---

## Output Structure

Each agent returns analysis in `output`:
- **TimelineManagerAgent**: `{violations, warnings, recommendations, is_valid}`
- **PacingAgent**: `{scene_type_distribution, tension_curve, monotony_flags, rushed_sequences, recommendations}`
- **ThemeGuardianAgent**: `{themes_identified, motif_tracking, thematic_inconsistencies, abandoned_themes, recommendations}`
- **ForeshadowingAgent**: `{seeds, reminders, payoffs, unresolved_promises, recommendations}`

All results are collected in `refinements` and can be used for:
- Quality gates
- Iteration decisions
- Final outline enhancement

---

## Files Created

- `src/agents/timeline_manager.py` - Timeline Manager Agent
- `src/agents/pacing_agent.py` - Pacing Agent
- `src/agents/theme_guardian.py` - Theme Guardian Agent
- `src/agents/foreshadowing_agent.py` - Foreshadowing & Payoff Agent
- `docs/PLANNING_AGENTS_INTEGRATION.md` - This document

## Files Modified

- `src/agents/__init__.py` - Added exports for new agents
- `src/orchestrator/planning_loop.py` - Integrated all agents into phases
- `src/orchestrator/central_manager.py` - Added wildcard dependency support

---

## Testing Status

✅ **Compilation**: All files compile without errors
✅ **Imports**: All agents import successfully
✅ **Integration**: All agents integrate with planning loop
✅ **Dependencies**: Wildcard dependencies work correctly

---

## Usage

The agents are automatically executed when using `IterativeDocumentOrchestrator`:

```python
from src.orchestrator import IterativeDocumentOrchestrator

orchestrator = IterativeDocumentOrchestrator(
    llm_provider=llm_provider,
    structured_state=structured_state,
    vector_store=vector_store,
    graph_store=graph_store,  # Optional, for Timeline Manager
    validation_service=validation_service
)

outline = await orchestrator.process_documents(...)
# All planning agents run automatically in the iterative loop
```

---

## Next Steps

1. **Enhance Agent Logic**: Improve analysis algorithms (currently basic heuristics)
2. **Add LLM Integration**: Use LLM for more sophisticated analysis
3. **Quality Gates**: Implement quality gates that trigger revisions
4. **Iteration Logic**: Add logic to revise based on agent recommendations
5. **Unit Tests**: Add tests for each agent
6. **Integration Tests**: Test full workflow with all agents

---

## Notes

- Agents currently use basic heuristics for analysis
- Timeline Manager works better with GraphDB (optional)
- All agents can be enhanced with LLM-based analysis
- Validation results are collected but not yet used for automatic revision
- Future: Add iteration logic based on validation results

All planning agents are now integrated and ready to use!
