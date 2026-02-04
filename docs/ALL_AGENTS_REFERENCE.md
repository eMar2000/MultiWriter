# All Agents Reference - From Project_Overview.md

This document lists all agents mentioned in the Project_Overview.md proposal document.

---

## Section 7: Initializer Agents

### 7.1 World Registry Initializer
**Status**: Not implemented (handled by document parser currently)
- Extract entities from user documents
- Create canonical IDs
- Seed GraphDB (via Continuity Validation Service)

### 7.2 RAG Parser
**Status**: Partially implemented (entity indexing exists)
- Chunk & embed user documents
- Type classification
- Link chunks to canon IDs

### 7.3 Outline Initializer
**Status**: Not implemented (handled by OutlineArchitectAgent)
- Draft beginning / middle / end
- Identify known vs unknown story areas
- Create initial arc structure

---

## Section 8: Iterative Planning Loop (High Authority)

### 8.1 Central Manager (Showrunner)
**Status**: ✅ Implemented (`src/orchestrator/central_manager.py`)
- Decide next strategic actions
- Invoke agents in appropriate order
- Manage scope and priorities
- Escalate critical issues to user

### 8.2 Central Architect
**Status**: ✅ Implemented as `OutlineArchitectAgent`
- Expand arcs → sub-arcs → chapters → scenes
- Maintain plot continuity
- Balance arc structure
- Ensure escalation curves

### 8.3 Timeline Manager
**Status**: ✅ Implemented (`src/agents/timeline_manager.py`)
- Maintain chronological consistency
- Validate event sequences against before/after edges
- Check travel time feasibility
- Flag temporal impossibilities
- Support non-linear narrative structures

### 8.4 Pacing Agent
**Status**: ✅ Implemented (`src/agents/pacing_agent.py`)
- Analyze action/reflection/dialogue ratios
- Ensure scene length variety
- Flag monotony
- Flag rushed sequences
- Validate escalation curves
- Genre-specific pacing norms

### 8.5 Theme Guardian
**Status**: ✅ Implemented (`src/agents/theme_guardian.py`)
- Track motif appearances and development
- Ensure thematic arcs parallel plot arcs
- Flag thematic inconsistencies
- Propose symbolic reinforcement opportunities
- Maintain motif density
- Validate payoff of thematic setups

### 8.6 Character Planner
**Status**: ❌ Not implemented
- Flesh out motivations, arcs, backstory
- Propose new characters when plot requires
- Track character development stages
- Ensure character consistency

### 8.7 Scene Planner
**Status**: ✅ Implemented as `SceneDynamicsAgent`
- Design scenes that turn (change the situation)
- Ensure escalation
- Balance scene types (action, dialogue, reflection)
- Link scenes to canon entities and locations

### 8.8 Foreshadowing & Payoff Agent
**Status**: ✅ Implemented (`src/agents/foreshadowing_agent.py`)
- Track seeds → reminders → payoffs
- Flag unresolved promises
- Suggest payoff opportunities
- Maintain setup-to-payoff timing ratios
- Validate that major setups have planned resolutions

### 8.9 Idea Generator
**Status**: ❌ Not implemented
- Propose new ideas to fill gaps
- Attach cost/benefit/risk analysis
- Generate alternatives when primary path is blocked
- Route to user approval when required

### 8.10 Outline ↔ Canon Sync Manager
**Status**: ✅ Implemented (`src/orchestrator/canon_sync.py`)
- Reconcile outline and canon bidirectionally
- Write validated changes to Canon Store
- Write change logs
- Prevent divergence between Outline and Canon

### 8.11 Observability Manager
**Status**: ❌ Not implemented
- Detect continuity violations
- Detect canon conflicts
- Monitor unresolved threads and payoffs
- Track tone drift
- Monitor metrics
- Escalate to user when needed

### 8.12 User Interaction Manager
**Status**: ❌ Not implemented
- Batch approval requests
- Prioritize critical decisions
- Manage approval timeouts
- Track user preference patterns
- Present decisions with context

### 8.13 Version Manager
**Status**: ❌ Not implemented
- Create snapshots at arc/chapter boundaries
- Maintain version history
- Execute rollbacks
- Validate rollback safety

---

## Section 9: Writing Loop (Lower Authority)

### 9.2 Chapter Manager
**Status**: ❌ Not implemented
- Orchestrate the writing loop
- Decide revision passes
- Manage iteration budget
- Coordinate parallel review and refinement

### 9.3 Drafter
**Status**: ❌ Not implemented
- Produce raw chapter text
- Maintain narrative voice and POV
- Hit required story beats
- Include required reveals

### 9.4 Continuity Agent
**Status**: ❌ Not implemented
- Validate chapter against Canon Store
- Check character consistency
- Detect timeline violations
- Flag unexplained knowledge
- Propose fixes

### 9.5 Dialogue Refiner
**Status**: ❌ Not implemented
- Improve subtext in dialogue
- Strengthen voice differentiation
- Add tension through conflict
- Remove on-the-nose exposition

### 9.6 Prose Refiner
**Status**: ❌ Not implemented
- Fix AI-isms
- Improve sentence rhythm
- Strengthen imagery
- Eliminate redundancy

### 9.7 Voice Bible Agent
**Status**: ❌ Not implemented
- Maintain stylistic consistency
- Enforce voice constraints
- Check for tone drift
- Validate against voice samples

### 9.8 Adversarial Reader
**Status**: ❌ Not implemented
- Identify boring passages
- Flag confusion
- Detect plot holes
- Predict reader frustration

### 9.9 Reader Simulation Agent
**Status**: ❌ Not implemented
- Predict reader expectations
- Track unanswered questions
- Flag information overload
- Validate emotional beats

### 9.10 Arbitration Agent
**Status**: ❌ Not implemented
- Synthesize feedback from reviewers
- Prioritize by severity
- Resolve conflicts
- Produce unified feedback report

---

## Section 11: Meta-Learning Layer

### 11.1 Reflection Agent
**Status**: ❌ Not implemented
- Analyze revision patterns
- Identify agent weaknesses
- Propose prompt/parameter adjustments
- Learn user preferences
- Generate improvement recommendations

---

## Summary by Status

### ✅ Implemented (9 agents)
1. **Central Manager** - Orchestration
2. **OutlineArchitectAgent** (Central Architect) - Arc planning
3. **SynthesisAgent** - Relationship analysis
4. **CoverageVerifierAgent** - Entity coverage
5. **SceneDynamicsAgent** (Scene Planner) - Scene expansion
6. **TimelineManagerAgent** - Timeline validation
7. **PacingAgent** - Pacing analysis
8. **ThemeGuardianAgent** - Thematic coherence
9. **ForeshadowingAgent** - Seeds and payoffs
10. **CanonSyncManager** - Outline ↔ Canon sync

### ❌ Not Implemented (15+ agents)

**Planning Loop:**
- Character Planner (8.6)
- Idea Generator (8.9)
- Observability Manager (8.11)
- User Interaction Manager (8.12)
- Version Manager (8.13)

**Initializers:**
- World Registry Initializer (7.1) - Handled by parser
- RAG Parser (7.2) - Partially handled
- Outline Initializer (7.3) - Handled by OutlineArchitectAgent

**Writing Loop:**
- Chapter Manager (9.2)
- Drafter (9.3)
- Continuity Agent (9.4)
- Dialogue Refiner (9.5)
- Prose Refiner (9.6)
- Voice Bible Agent (9.7)
- Adversarial Reader (9.8)
- Reader Simulation Agent (9.9)
- Arbitration Agent (9.10)

**Meta-Learning:**
- Reflection Agent (11.1)

---

## Current Focus

**Implemented**: Planning loop agents (outline generation)
**Next Priority**: Timeline Manager, Pacing Agent, Theme Guardian ✅ (Done!)
**Future**: Writing loop agents (chapter generation)

---

## Notes

- Some agents are handled by existing components (e.g., Outline Initializer → OutlineArchitectAgent)
- Writing loop agents are for actual prose generation, not outline generation
- Meta-learning agents are for system improvement over time
