# Agent Implementation Roadmap

## Current State

### ✅ Implemented Agents (Active in DocumentOrchestrator)
1. **SynthesisAgent** - Analyzes entity registry and identifies relationships, conflicts, themes
2. **OutlineArchitectAgent** - Creates high-level narrative arc structure from relationships
3. **CoverageVerifierAgent** - Verifies all entities are referenced in arcs
4. **SceneDynamicsAgent** - Expands arcs into detailed scene outlines

### ⚠️ Deprecated Agents (Legacy - Only for Tests)
- **ThemePremiseAgent** - Old interactive workflow
- **NarrativeArchitectAgent** - Old interactive workflow
- **CharacterAgent** - Old interactive workflow
- **WorldbuildingAgent** - Old interactive workflow

---

## Priority Agents to Implement

Based on the proposal document, here are the agents that should be implemented next, prioritized by importance for the document-driven workflow:

### 🔴 High Priority (Core Functionality)

#### 1. **Timeline Manager** (Section 8.3)
**Purpose:** Maintain chronological consistency and validate temporal constraints

**Why Critical:**
- Prevents timeline violations (character in two places, impossible travel times)
- Essential for maintaining story coherence
- Currently missing - could cause plot holes

**Responsibilities:**
- Validate event sequences against before/after edges
- Check travel time feasibility between locations
- Flag temporal impossibilities
- Support non-linear narrative structures (flashbacks, parallel timelines)
- Enforce temporal constraints (e.g., pregnancy duration, travel time)

**Implementation Notes:**
- Works with EntityRegistry to track locations and events
- Can be integrated into orchestrator validation phase
- Should run before scene expansion to catch issues early

---

#### 2. **Pacing Agent** (Section 8.4)
**Purpose:** Analyze and optimize story pacing

**Why Critical:**
- Ensures proper rhythm and escalation
- Prevents monotony (too many similar scenes)
- Validates tension curves
- Genre-specific pacing norms

**Responsibilities:**
- Analyze action/reflection/dialogue ratios per chapter and arc
- Ensure scene length variety
- Flag monotony (too many similar scenes in sequence)
- Flag rushed sequences (insufficient development time)
- Recommend beat adjustments for rhythm
- Validate escalation curves (tension should build)
- Consider genre-specific pacing norms

**Implementation Notes:**
- Works with SceneOutline objects
- Can analyze after scene expansion
- Should provide recommendations to OutlineArchitectAgent

---

#### 3. **Theme Guardian** (Section 8.5)
**Purpose:** Ensure thematic coherence and motif tracking

**Why Critical:**
- Maintains thematic consistency across the story
- Tracks motif development
- Ensures thematic arcs parallel plot arcs
- Validates payoff of thematic setups

**Responsibilities:**
- Track motif appearances and development across arcs
- Ensure thematic arcs parallel plot arcs
- Flag thematic inconsistencies or abandonment
- Propose symbolic reinforcement opportunities
- Maintain motif density (not too sparse, not overwhelming)
- Validate payoff of thematic setups

**Implementation Notes:**
- Works with relationships data from SynthesisAgent
- Can track themes identified in synthesis phase
- Should validate after arc planning

---

### 🟡 Medium Priority (Quality Improvements)

#### 4. **Foreshadowing & Payoff Agent** (Section 8.8)
**Purpose:** Track seeds, reminders, and payoffs

**Why Important:**
- Ensures narrative promises are kept
- Maintains setup-to-payoff timing
- Flags unresolved promises

**Responsibilities:**
- Track seeds → reminders → payoffs
- Flag unresolved promises approaching end of story
- Suggest payoff opportunities in upcoming chapters
- Maintain setup-to-payoff timing ratios
- Validate that major setups have planned resolutions

**Implementation Notes:**
- Works with arc structure and scene outlines
- Can identify foreshadowing opportunities during scene planning
- Should run after scene expansion

---

#### 5. **Character Planner** (Section 8.6)
**Purpose:** Flesh out character development and consistency

**Why Important:**
- Ensures character arcs are properly developed
- Maintains character consistency
- Proposes new characters when needed

**Responsibilities:**
- Flesh out motivations, arcs, backstory
- Propose new characters when plot requires
- Track character development stages
- Ensure character consistency across appearances

**Implementation Notes:**
- Works with EntityRegistry (character entities)
- Can enhance character entities with development arcs
- Should run during arc planning phase

---

### 🟢 Lower Priority (Future Enhancements)

#### 6. **Idea Generator** (Section 8.9)
**Purpose:** Propose new ideas to fill gaps

**When Needed:**
- When plot holes are detected
- When story feels stale
- When coverage is low

**Responsibilities:**
- Propose new ideas to fill gaps or resolve issues
- Attach cost/benefit/risk analysis to proposals
- Generate alternatives when primary path is blocked
- Route to user approval when required

---

#### 7. **Observability Manager** (Section 8.11)
**Purpose:** Monitor system health and detect issues

**When Needed:**
- For production monitoring
- For debugging and optimization
- For quality metrics tracking

**Responsibilities:**
- Detect continuity violations
- Detect canon conflicts
- Monitor unresolved threads and payoffs
- Track tone drift
- Monitor metrics
- Escalate to user when automated resolution impossible

---

## Implementation Strategy

### Phase 1: Core Validation (Next Sprint)
1. **Timeline Manager** - Critical for preventing plot holes
2. **Pacing Agent** - Essential for story quality

### Phase 2: Thematic Coherence (Following Sprint)
3. **Theme Guardian** - Maintains story depth

### Phase 3: Advanced Features (Later)
4. **Foreshadowing & Payoff Agent**
5. **Character Planner**

### Phase 4: System Health (Production Ready)
6. **Observability Manager**
7. **Idea Generator**

---

## Integration Points

All new agents should:
- Inherit from `BaseAgent`
- Work with `EntityRegistry` and `NovelOutline` schemas
- Use `StructuredState` for persistence
- Support both document-driven and future interactive workflows
- Return structured output compatible with orchestrator

---

## Notes

- **Writing Loop Agents** (Drafter, Continuity Agent, Prose Refiner, etc.) are for actual chapter writing, not outline generation. These are lower priority for the current outline-focused workflow.
- **Canon Store** agents (Outline ↔ Canon Sync Manager, etc.) require GraphDB implementation, which is a larger architectural change.
- Focus on agents that improve **outline quality** first, then move to **writing quality** agents later.
