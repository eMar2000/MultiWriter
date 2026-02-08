# Multi-Agent AI Storyteller

============================
      !!!!ATTENTION!!!!
============================

DO NOT DELETE!!!

This is the north star / central overview / roadmap document for our entire project.

AI coding Agents should NOT modify this document unless explicitly specified.

When beggining a new AI coding session, AI coding agents should review this document for context of our end goal.

Then AI agents should activly explore the codebase to get an understanding of current state, and what needs to be done.

============================

## System Architecture & Proposition Document (v3)

---

## 1. System Goal

The goal of this system is to produce **high-quality long-form fiction** by mimicking the real cognitive and collaborative process used by great novelists and story studios.

Rather than a single evolving document, the system maintains **multiple structured, evolving artifacts** governed by a **central orchestration engine**, backed by a **canonical knowledge layer** and **retrieval-augmented generation (RAG)**.

The system prioritizes:

* Narrative coherence at novel scale
* Deep character and thematic consistency
* Iterative planning and revision
* Explicit reasoning over structure, continuity, and reader experience
* User control over major creative decisions

---

## 2. Core Architectural Principles

1. **Separation of concerns**
   * Planning ≠ Writing ≠ Knowledge ≠ Storage

2. **Canonical truth is explicit**
   * "What exists" and "what is true" is never inferred from prose

3. **Revision is first-class**
   * Writing is iterative and adversarial

4. **Agents are biased specialists**
   * No agent is omniscient

5. **User remains creative authority**
   * System proposes, user disposes

6. **Validation before mutation** *(New)*
   * All canonical writes are validated before commit

---

## 3. Core Artifacts (Authoritative Objects)

### 3.1 Central Plan (Task Graph)

**Purpose:** Governs what happens next.

**Contents:**
* Ordered task graph (DAG)
* Task owner (agent)
* Inputs / outputs
* Blocking dependencies
* Acceptance criteria
* Explicit "decision required" flags

**Authority:**
* Canonical for *process*
* Not canonical for story content

---

### 3.2 Central Outline (Narrative Spine)

**Purpose:** Canonical source of truth for *what happens*.

**Structure:**
* Arcs → Sub-arcs → Chapters → Scenes
* Each scene includes:
  * Goal
  * Conflict
  * Turn
  * Stakes
  * Reveal(s)
  * Characters
  * Location
  * Time
  * Setup / payoff references
  * Canon references (Graph IDs)

**Authority:**
* Canonical for plot, pacing, and timeline
* Must remain consistent with Canon Store

---

### 3.3 Canon Store (GraphDB)

**Purpose:** Canonical source of truth for *what exists and what is true*.

**Node Types:**
* Character
* Location
* Object
* Organization / Faction
* Event
* Scene
* Chapter
* Arc
* Motif
* Rule / Constraint
* Secret
* Thread (subplot)

**Node Properties (Example - Character):**
* id (canonical UUID)
* name
* introduction_chapter_id
* status (alive, dead, missing, unknown)
* arc_stage (introduction, development, climax, resolution)
* last_appearance_chapter_id
* created_at
* updated_at
* version

**Edge Types:**
* appears_in
* introduced_in / resolved_in
* causes / foreshadows / contradicts
* wants / fears / believes / knows
* located_in / travels_to
* owns / loses
* allies_with / opposes / betrays
* before / after (timeline)

**Edge Properties (Example - appears_in):**
* chapter_id
* pov_character (boolean)
* dialogue_count
* scene_count
* first_appearance (boolean)
* timestamp

**Authority:**
* Canonical for continuity, facts, relationships, constraints

---

### 3.4 World Registry (Derived View)

**Purpose:** Human-readable inventory of all canonical elements.

**Source:**
* Auto-generated from Canon Store

**Includes:**
* All characters, locations, objects, rules, threads
* Status flags (introduced, active, unresolved, resolved)
* Usage tracking (which elements appear in which chapters)

**Structure:**
```
World Registry:
├─ Core Elements (from user input)
│  ├─ Primary Characters [links to Canon IDs]
│  ├─ Key Locations [links to Canon IDs]
│  └─ Central Conflicts [links to Canon IDs]
├─ Derived Elements (agent-generated)
│  ├─ Secondary Characters
│  ├─ Subplot Threads
│  └─ Worldbuilding Details
└─ Usage Tracking
   ├─ Elements by chapter
   ├─ Unresolved threads
   └─ Orphaned entities (never used)
```

**Authority:**
* Not authoritative
* Diagnostic and planning aid

---

### 3.5 RAG Store (Hybrid Storage)

**Purpose:** Retrieval interface over story knowledge.

**Implementation:**
* Text chunks → Blob Storage
* Embeddings → Vector Store
* Metadata → GraphDB (via canon IDs)

**Contents (typed chunks):**
* Canon facts (atomic)
* Worldbuilding prose
* Character dossier sections
* Scene cards
* Draft prose excerpts
* Notes / alternatives

**Retrieval Process:**
1. Query → Vector Store (semantic match)
2. Retrieve chunk IDs
3. Fetch text from Blob Storage
4. Enrich with GraphDB context (canon facts)

**Authority:**
* Not canonical
* Must be reconciled against Canon Store

---

### 3.6 Chapter Brief

**Purpose:** Contract between planning and writing loops.

**Contents:**
* Required beats
* Required reveals
* POV and voice constraints
* Motifs to touch
* Length target
* "Do not do" list
* Canon snapshot reference

---

### 3.7 Manuscript

**Purpose:** User-facing narrative output.

**Notes:**
* Too large for agent context
* Used via rolling summaries, state vectors, and golden excerpts

---

## 4. Core Infrastructure & Storage Layer

### 4.0 CRITICAL: Document Chunking & LLM Context Management

**Problem Identified**: Large input documents (65+ entities, 19K+ chars) overwhelm LLMs, causing:
- Empty or malformed JSON responses
- Schema mismatches (wrong keys in returned JSON)
- Context truncation and poor quality outputs

**Required Solution - Document Chunking Strategy**:

1. **Input Document Chunking** (`DocumentChunker` utility):
   - Split large markdown documents into semantic chunks BEFORE entity extraction
   - Target: 500-1000 tokens per chunk (well under 4K limit)
   - Preserve semantic boundaries (character profiles, location descriptions, event sequences)
   - Add overlap between chunks to maintain context continuity

2. **Batched Entity Processing** (Update `SynthesisAgent`, `OutlineArchitect`):
   - Process entity registry in batches of 10-15 entities per LLM call
   - Aggregate results across batches
   - Provide summarized synthesis to downstream agents, not raw entity dumps

3. **Implementation Components**:
   - `src/parser/document_chunker.py`: Semantic chunking utility
   - `src/parser/entity_extractor.py`: Update to process chunks iteratively
   - `src/agents/synthesis.py`: Add batch processing logic
   - `src/agents/outline_architect.py`: Receive condensed summaries, not full registry
   - `config.yaml`: Add chunking config (chunk_size, overlap, batch_size)

4. **Quality Gates**:
   - Log chunk sizes and verify < 1000 tokens
   - Validate LLM response schema matches expected keys
   - Log when LLM returns malformed/empty responses for debugging

**Priority**: CRITICAL - Must be implemented before agents can produce quality outputs

---

### 4.1 Storage Stack (Immutable by Default)

```
User Input
   ↓
Document Chunker (NEW)
   ↓
Immutable Blob Storage
   ↓
Canon Store (GraphDB)
   ↓
Vector Store
   ↓
RAG Retrieval Layer
   ↓
Agents
```

### 4.2 Storage Roles

#### Immutable Blob Storage
* Stores:
  * User uploads
  * Drafts
  * Chapter versions
  * Change logs
  * Agent proposals
* Append-only
* Full audit trail

#### GraphDB (Canon Store)
* Stores:
  * Canonical entities and relationships
  * Timeline assertions
  * Constraints
  * Version metadata
* Supports:
  * Structural queries
  * Inconsistency detection
  * Dependency analysis
  * ACID transactions

#### Vector Store
* Stores embeddings of:
  * Lore text
  * Character prose
  * Scene drafts
  * Prior chapters
* Optimized for semantic recall

#### RAG Retrieval Layer
* Hybrid retrieval:
  1. Graph queries (facts, relationships)
  2. Vector retrieval (descriptive context)
  3. Recency-weighted excerpts
* Enforces canon precedence

---

## 5. Core Access Patterns

| Operation                 | Source            | Validation Required |
| ------------------------- | ----------------- | ------------------- |
| "What exists?"            | GraphDB           | No (read-only)      |
| "What is true right now?" | GraphDB           | No (read-only)      |
| "What happened recently?" | Blob + summaries  | No (read-only)      |
| "Describe X"              | Vector Store      | No (read-only)      |
| "What is unresolved?"     | GraphDB           | No (read-only)      |
| "Find similar scene"      | Vector Store      | No (read-only)      |
| "Check continuity"        | GraphDB + Outline | No (read-only)      |
| "Propose canon change"    | Proposal Log      | Yes (pre-validation)|
| "Write to canon"          | GraphDB           | Yes (blocking)      |
| "Update outline"          | Outline + GraphDB | Yes (blocking)      |

---

## 6. Agent Access Control & Write Patterns

### 6.1 Read Access Levels

**Level 1 - Full Canon Access:**
* Central Manager
* Central Architect
* Character Planner
* Scene Planner
* Timeline Manager
* Outline ↔ Canon Sync Manager
* Observability Manager
* Foreshadowing & Payoff Agent
* Pacing Agent
* Theme Guardian

**Level 2 - Scoped Canon Access:**
* Chapter Manager (chapter scope + dependencies)
* Continuity Agent (chapter scope + relevant canon)
* Drafter (chapter brief + recent context)

**Level 3 - No Direct Canon Access:**
* Adversarial Reader (outline + chapters only)
* Reader Simulation Agent (outline + chapters only)
* Prose Refiner (text only)
* Dialogue Refiner (text only)

### 6.2 Write Access Patterns

#### Pattern 1: Synchronous Validation (RECOMMENDED for Canon)

**Used for:** All Canon Store writes

**Flow:**
```
1. Agent prepares mutation proposal
2. Agent invokes Continuity Validation Service (blocking call)
3. Validation Service:
   a. Checks for contradictions
   b. Validates timeline consistency
   c. Checks orphaned references
   d. Returns validation result
4. IF validation passes:
   → Mutation proceeds
   → Change log written
   ELSE:
   → Mutation rejected
   → Error returned to agent
   → Agent must revise proposal
```

**Rationale:**
* Prevents invalid state from ever entering Canon Store
* GraphDB maintains ACID guarantees
* Simpler debugging (no async reconciliation needed)
* Clear error boundaries

**Tradeoff:**
* Slightly slower writes
* BUT: Canon writes are infrequent and high-value

---

#### Pattern 2: Asynchronous Reconciliation

**Used for:** RAG updates, Registry regeneration

**Flow:**
```
1. Agent writes to Blob Storage (fast, always succeeds)
2. Agent queues reconciliation job
3. Background worker:
   a. Processes queue
   b. Updates Vector Store embeddings
   c. Regenerates World Registry
   d. Flags inconsistencies (non-blocking)
4. Observability Manager monitors queue health
```

**Rationale:**
* High throughput for non-canonical writes
* Registry is derived, can be regenerated
* Embeddings don't affect correctness

---

#### Pattern 3: Proposal-Review-Commit (for User Approval)

**Used for:** New character creation, major plot changes

**Flow:**
```
1. Agent creates proposal (immutable log)
2. Continuity Validation Service validates proposal
3. IF validation passes:
   → Proposal queued for user review
   ELSE:
   → Proposal rejected immediately
4. User Interaction Manager batches proposals
5. User approves/rejects
6. IF approved:
   → Outline ↔ Canon Sync Manager commits to Canon Store
   → Synchronous validation happens again (defensive)
   → Change log written
```

---

### 6.3 Continuity Validation Service (New Critical Component)

**Purpose:** Centralized validation for all canon mutations

**Responsibilities:**
* Detect contradictions (character alive in two places, temporal violations)
* Validate timeline ordering (before/after edges)
* Check referential integrity (no dangling references)
* Enforce business rules (e.g., dead characters can't take actions)
* Rate limiting and quota enforcement

**Interface:**
```python
class ContinuityValidationService:
    def validate_mutation(
        self,
        mutation: CanonMutation,
        context: ValidationContext
    ) -> ValidationResult:
        """
        Synchronous validation of proposed canon change.

        Returns:
            ValidationResult with:
            - is_valid: bool
            - violations: List[Violation]
            - warnings: List[Warning]
            - auto_fixes: List[AutoFix] (optional)
        """
        pass
```

**Invocation:**
* **Synchronous** - blocking call before any Canon Store write
* Called by:
  * Outline ↔ Canon Sync Manager (all canon writes)
  * Version Manager (rollback validation)
  * Manual edit API (user overrides)

**Caching:**
* Recently validated queries cached (5 min TTL)
* Invalidated on any canon write
* Reduces repeated validation overhead

---

### 6.4 Write Authority Matrix

| Agent                        | Canon Store | Outline | RAG | Blob | Registry |
| ---------------------------- | ----------- | ------- | --- | ---- | -------- |
| World Registry Initializer   | Write*      | No      | No  | Yes  | No       |
| Character Planner            | Propose**   | No      | Yes | Yes  | No       |
| Scene Planner                | Propose**   | No      | Yes | Yes  | No       |
| Outline ↔ Canon Sync Manager | Write*      | Write*  | Yes | Yes  | No       |
| Central Architect            | No          | Write*  | Yes | Yes  | No       |
| Drafter                      | No          | No      | No  | Yes  | No       |
| Version Manager              | Write*      | Write*  | No  | Yes  | No       |

\* All writes go through Continuity Validation Service (synchronous)
\** Proposals validated, then queued for approval, then committed via Sync Manager

---

## 7. Initializer Agents

### 7.1 World Registry Initializer

**Inputs:** User documents
**Outputs:** Canon nodes, registry view
**Triggers:** Story start
**Responsibilities:**
* Extract entities
* Create canonical IDs
* Seed GraphDB (via Continuity Validation Service)

---

### 7.2 RAG Parser

**Inputs:** User documents
**Outputs:** Typed RAG chunks
**Triggers:** Story start
**Responsibilities:**
* Chunk & embed
* Type classification
* Link chunks to canon IDs

---

### 7.3 Outline Initializer

**Inputs:** User docs + RAG
**Outputs:** Initial Central Outline
**Triggers:** Story start
**Responsibilities:**
* Draft beginning / middle / end
* Identify known vs unknown story areas
* Create initial arc structure

---

## 8. Iterative Planning Loop (High Authority)

### 8.1 Central Manager (Showrunner)

**Inputs:** Outline, Canon, Observability reports, Central Plan
**Outputs:** Central Plan updates
**Triggers:** Plan completion, inconsistency detection, milestone
**Responsibilities:**
* Decide next strategic actions
* Invoke agents in appropriate order
* Manage scope and priorities
* Escalate critical issues to user

---

### 8.2 Central Architect

**Inputs:** Central Plan, Outline, Canon, World Registry
**Outputs:** Expanded Outline (via Sync Manager)
**Responsibilities:**
* Expand arcs → sub-arcs → chapters → scenes
* Maintain plot continuity
* Balance arc structure
* Ensure escalation curves

---

### 8.3 Timeline Manager

**Inputs:** Canon Store (events, locations, before/after edges), Outline
**Outputs:** Timeline validation reports, temporal constraint violations
**Triggers:** Outline updates, new event creation, chapter completion
**Responsibilities:**
* Maintain chronological consistency
* Validate event sequences against before/after edges
* Check travel time feasibility (location graph + time deltas)
* Flag temporal impossibilities
* Support non-linear narrative structures (flashbacks, parallel timelines)
* Enforce temporal constraints (e.g., pregnancy duration, travel time)

---

### 8.4 Pacing Agent

**Inputs:** Outline, completed chapters, genre expectations, arc structure
**Outputs:** Pacing analysis, tempo recommendations, beat adjustments
**Triggers:** Arc planning, chapter completion, revision requests
**Responsibilities:**
* Analyze action/reflection/dialogue ratios per chapter and arc
* Ensure scene length variety
* Flag monotony (too many similar scenes in sequence)
* Flag rushed sequences (insufficient development time)
* Recommend beat adjustments for rhythm
* Validate escalation curves (tension should build)
* Consider genre-specific pacing norms

---

### 8.5 Theme Guardian

**Inputs:** Canon Store (Motif nodes, Thread nodes), Outline, completed chapters
**Outputs:** Thematic coherence reports, motif usage recommendations, symbolic opportunities
**Triggers:** Arc planning, chapter completion, motif tracking
**Responsibilities:**
* Track motif appearances and development across arcs
* Ensure thematic arcs parallel plot arcs
* Flag thematic inconsistencies or abandonment
* Propose symbolic reinforcement opportunities
* Maintain motif density (not too sparse, not overwhelming)
* Validate payoff of thematic setups

---

### 8.6 Character Planner

**Inputs:** Canon, Outline, World Registry
**Outputs:** Character updates (proposals to Sync Manager)
**Triggers:** New character needed, character development gap, arc planning
**Responsibilities:**
* Flesh out motivations, arcs, backstory
* Propose new characters when plot requires
* Track character development stages
* Ensure character consistency across appearances

---

### 8.7 Scene Planner

**Inputs:** Outline gaps, Chapter Briefs, Canon
**Outputs:** Scene cards (with goals, conflicts, turns)
**Triggers:** Chapter planning, outline expansion
**Responsibilities:**
* Design scenes that turn (change the situation)
* Ensure escalation
* Balance scene types (action, dialogue, reflection)
* Link scenes to canon entities and locations

---

### 8.8 Foreshadowing & Payoff Agent

**Inputs:** Canon Store (Thread nodes, foreshadows edges), Outline
**Outputs:** Seed/payoff tracking, unresolved promise alerts
**Triggers:** Scene planning, chapter completion, arc completion
**Responsibilities:**
* Track seeds → reminders → payoffs
* Flag unresolved promises approaching end of story
* Suggest payoff opportunities in upcoming chapters
* Maintain setup-to-payoff timing ratios
* Validate that major setups have planned resolutions

---

### 8.9 Idea Generator

**Inputs:** Canon gaps, Observability reports, user constraints
**Outputs:** New idea proposals (to User Interaction Manager)
**Triggers:** Staleness detection, plot holes, insufficient substance
**Responsibilities:**
* Propose new ideas to fill gaps or resolve issues
* Attach cost/benefit/risk analysis to proposals
* Generate alternatives when primary path is blocked
* Route to user approval when required
* Update RAG and Canon (via Sync Manager) after approval

---

### 8.10 Outline ↔ Canon Sync Manager

**Inputs:** Outline changes, Canon changes, proposals from other agents
**Outputs:** Reconciled Canon + Outline, change logs
**Triggers:** Any outline update, approved proposals, inconsistency detection
**Responsibilities:**
* Reconcile outline and canon bidirectionally
* Write validated changes to Canon Store (via Continuity Validation Service)
* Write change logs (immutable)
* Prevent divergence between Outline and Canon
* Execute approved proposals from Character/Scene Planners
* Coordinate with Version Manager for checkpoints

---

### 8.11 Observability Manager

**Inputs:** Canon Store, Outline, completed chapters, agent logs
**Outputs:** Health reports, alerts, escalations
**Triggers:** Continuous monitoring, threshold violations
**Responsibilities:**
* Detect continuity violations
* Detect canon conflicts
* Monitor unresolved threads and payoffs
* Track tone drift
* Monitor metrics (see Section 15)
* Escalate to user when automated resolution impossible
* Track system health and agent performance

---

### 8.12 User Interaction Manager

**Inputs:** User approval requests from multiple agents, user responses
**Outputs:** Batched user prompts, approval status tracking, timeout handling
**Triggers:** Agent approval requests, milestone boundaries, timeout events
**Responsibilities:**
* Batch non-urgent approvals to natural stopping points (arc end, chapter end)
* Prioritize critical decisions (canon conflicts, major plot changes) over nice-to-haves
* Manage approval timeouts and defaults (conservative defaults after 48h)
* Track user preference patterns (learn from approval history)
* Present decisions with context and implications
* Queue background work during user review

---

### 8.13 Version Manager

**Inputs:** Artifact change events, checkpoint requests, rollback requests
**Outputs:** Version snapshots, rollback operations, version metadata
**Triggers:** Arc boundaries, chapter completion, pre-major-change, manual checkpoint
**Responsibilities:**
* Create snapshots at arc/chapter boundaries
* Maintain version history for all canonical artifacts (Outline, Canon Store state)
* Execute rollbacks when Observability Manager escalates critical issues
* Prune old versions according to retention policy (keep milestones indefinitely)
* Validate rollback safety (check dependent artifacts)
* Coordinate with Sync Manager for consistent multi-artifact rollback

---

## 9. Writing Loop (Lower Authority)

### 9.1 Writing Loop Execution Order

**Per Chapter:**

```
1. Chapter Manager receives Chapter Brief from Central Architect
2. Timeline Manager validates temporal constraints for chapter
   → IF violations found: escalate to Central Architect
   → ELSE: proceed

3. Drafter produces rough draft
   → Input: Chapter Brief + last 2-3 chapters + relevant Canon (via RAG)
   → Output: Draft text (committed to Blob Storage)

4. PARALLEL REVIEW PHASE:
   ├─ Continuity Agent
   │  └─ Check canon violations, character consistency, fact errors
   ├─ Adversarial Reader
   │  └─ Check engagement, boredom, confusion, pacing within chapter
   ├─ Reader Simulation Agent
   │  └─ Check reader expectations, predict questions, flag info gaps
   └─ Voice Bible Agent
      └─ Check style consistency, tone, narrative voice

5. Arbitration Agent synthesizes feedback
   → Prioritizes by severity (canon violations > engagement > style)
   → Resolves conflicts between reviewers
   → Produces unified feedback report

6. Chapter Manager decides based on Arbitration report:
   → Major issues (canon violations, plot breaks, unreadable):
      Return to step 3 (re-draft with feedback)
   → Minor issues (style tweaks, dialogue improvements):
      Proceed to refinement

7. PARALLEL REFINEMENT PHASE (only if step 6 approves):
   ├─ Prose Refiner
   │  └─ Fix AI-isms, improve rhythm, imagery, sentence variety
   └─ Dialogue Refiner
      └─ Improve subtext, voice differentiation, tension

8. Final consistency check
   → Continuity Agent validates refined version
   → IF new issues introduced: flag for review
   → ELSE: approve

9. Version Manager creates chapter checkpoint
   → Snapshot of chapter + relevant canon state

10. Commit to Manuscript
    → Chapter appended to manuscript
    → Chapter marked complete in Central Plan
    → Async: Update RAG with chapter content
    → Async: Regenerate World Registry if needed
```

---

### 9.2 Chapter Manager

**Inputs:** Chapter Brief, Canon Snapshot
**Outputs:** Chapter versions, revision decisions
**Triggers:** Central Plan assigns chapter
**Responsibilities:**
* Orchestrate the writing loop (steps 1-10 above)
* Decide revision passes based on Arbitration Agent feedback
* Manage iteration budget (max 3 revision passes before escalation)
* Coordinate parallel review and refinement phases
* Maintain chapter-level context window

---

### 9.3 Drafter

**Inputs:** Chapter Brief, recent chapters, relevant Canon (via RAG)
**Outputs:** Raw chapter text
**Triggers:** Chapter Manager initiates drafting
**Responsibilities:**
* Produce raw chapter text following Chapter Brief strictly
* Maintain narrative voice and POV constraints
* Hit required story beats
* Include required reveals
* Respect "do not do" constraints
* Stay within length target (±20%)

---

### 9.4 Continuity Agent

**Inputs:** Draft chapter, Canon Store, Outline, previous chapters
**Outputs:** Continuity validation report, canon violation list
**Triggers:** Post-draft review, post-refinement review
**Responsibilities:**
* Validate chapter against Canon Store facts
* Check character consistency (abilities, knowledge, relationships)
* Detect timeline violations
* Flag unexplained knowledge (character knows something they shouldn't)
* Propose fixes (NO direct canon writes, only proposals)
* Cross-reference with Outline to ensure plot alignment

---

### 9.5 Dialogue Refiner

**Inputs:** Draft chapter text
**Outputs:** Refined dialogue
**Triggers:** Refinement phase (step 7)
**Responsibilities:**
* Improve subtext (show don't tell in dialogue)
* Strengthen voice differentiation between characters
* Add tension through conflict and stakes
* Remove on-the-nose exposition
* Improve rhythm and natural speech patterns
* Preserve character voice consistency

---

### 9.6 Prose Refiner

**Inputs:** Draft chapter text
**Outputs:** Refined prose
**Triggers:** Refinement phase (step 7)
**Responsibilities:**
* Fix AI-isms (e.g., "a testament to", "as if", overused metaphors)
* Improve sentence rhythm and variety
* Strengthen imagery and sensory detail
* Eliminate redundancy
* Improve paragraph flow and transitions
* Maintain narrative voice consistency

---

### 9.7 Voice Bible Agent

**Inputs:** Draft chapter, established voice samples, genre conventions
**Outputs:** Voice consistency report, style violations
**Triggers:** Review phase (step 4)
**Responsibilities:**
* Maintain stylistic consistency across chapters
* Enforce voice constraints (POV, tense, narrative distance)
* Check for tone drift
* Validate against established voice samples
* Flag genre convention violations
* Ensure consistency in narrative techniques (how description, interiority, dialogue are balanced)

---

### 9.8 Adversarial Reader

**Inputs:** Draft chapter, Outline (NO Canon Store access)
**Outputs:** Engagement report, boredom/confusion flags
**Triggers:** Review phase (step 4)
**Responsibilities:**
* Identify boring passages (lack of conflict, stakes, or change)
* Flag confusion (unclear actions, motivations, or stakes)
* Detect plot holes visible to readers (vs. continuity errors)
* Flag disbelief (character actions out of character without explanation)
* Predict reader frustration points
* Evaluate pacing within chapter (not just arc-level)

---

### 9.9 Reader Simulation Agent

**Inputs:** Draft chapter, Outline, previous chapters
**Outputs:** Reader expectation analysis, question tracking
**Triggers:** Review phase (step 4)
**Responsibilities:**
* Predict reader expectations based on setup
* Track questions raised but not answered (intentional vs. accidental)
* Flag information overload (too many new elements)
* Detect fatigue points (too much complexity without resolution)
* Validate that promises to reader are kept (e.g., if chapter opens with tension, does it deliver?)
* Assess emotional beats (are they landing as intended?)

---

### 9.10 Arbitration Agent

**Inputs:** Conflicting agent feedback, change proposals
**Outputs:** Binding decisions, unified feedback report, escalation flags
**Triggers:** Multi-agent disagreement detected (after review phase)
**Responsibilities:**
* Prioritize feedback by hierarchy:
  1. Canon violations (blocking - must fix)
  2. Outline violations (blocking - must fix)
  3. Timeline violations (blocking - must fix)
  4. Engagement issues (high priority - should fix)
  5. Voice/style issues (medium priority - nice to fix)
  6. Subjective quality (advisory - consider)
* Break deadlocks using explicit rules:
  → If Continuity Agent flags canon violation, always block
  → If Adversarial Reader + Reader Simulation both flag same issue, high priority
  → If only style agents disagree, defer to majority or Voice Bible
* Escalate unresolvable conflicts to Chapter Manager → User Interaction Manager
* Document arbitration reasoning for learning
* Produce unified feedback report for Drafter (if re-draft needed)

---

## 10. Canon Mutation Protocol

### 10.1 Authorized Canon Writers

Only these agents can write to Canon Store:
* **World Registry Initializer** (initial load only, one-time)
* **Outline ↔ Canon Sync Manager** (all reconciliation and approved proposals)
* **Version Manager** (rollback operations only)

All other agents must go through the Sync Manager via proposals.

---

### 10.2 Mutation Workflow

```
1. Agent (Character Planner, Scene Planner, etc.) proposes canon change
   → Proposal logged to Immutable Blob Storage
   → Proposal includes: change description, rationale, affected entities

2. Agent invokes Continuity Validation Service (synchronous)
   → Validation checks:
      a. No contradictions with existing canon
      b. No timeline violations
      c. No orphaned references
      d. No business rule violations (e.g., dead character acting)
   → Returns ValidationResult

3. IF validation fails:
   → Proposal rejected immediately
   → Error details returned to agent
   → Agent must revise or abandon proposal

4. IF validation passes:
   → Proposal status: "validated, pending approval"

5. IF user approval required (major changes):
   → User Interaction Manager queues decision
   → User presented with:
      * Change description
      * Impact analysis
      * Alternative options
   → User approves or rejects

6. IF approved (or auto-approved for minor changes):
   → Outline ↔ Canon Sync Manager commits to GraphDB
   → Re-validation happens (defensive, in transaction)
   → Change log created (immutable, includes before/after state)
   → Affected artifacts flagged for review
   → World Registry queued for regeneration (async)
   → Version Manager may create checkpoint (for major changes)

7. IF rejected:
   → Proposal marked as rejected with reason
   → Agent notified
   → Alternative paths considered
```

---

### 10.3 Contradiction Resolution

* Canon contradictions are **NEVER** auto-resolved
* Always escalate to User Interaction Manager
* User presented with:
  * Both conflicting states
  * When each was established
  * Impact of choosing each option
* Previous canon state preserved in version history
* After user decision, losing state archived with explanation

---

### 10.4 Validation Rules (in Continuity Validation Service)

**Contradiction Checks:**
* Character cannot be in two places at same time
* Character cannot act after death (unless resurrection explicitly canon)
* Object cannot be in multiple locations
* Event cannot violate before/after constraints

**Timeline Checks:**
* before/after edges must form valid DAG (no cycles)
* Travel time between locations must be feasible
* Age progression must be consistent
* Event durations must be realistic

**Referential Integrity:**
* All entity references must exist in Canon Store
* Deleted entities must have no active incoming edges
* Orphaned entities flagged for cleanup

**Business Rules:**
* Genre-specific constraints (e.g., magic system rules)
* User-defined rules (e.g., "no resurrection")
* Pacing constraints (e.g., minimum time between major reveals)

---

## 11. Meta-Learning Layer

### 11.1 Reflection Agent

**Inputs:** Completed arcs, revision logs, user feedback, agent performance metrics
**Outputs:** Process improvement recommendations, agent tuning suggestions, pattern reports
**Triggers:** Arc completion, milestone reviews (every 5 chapters), user-initiated review
**Responsibilities:**
* Analyze revision patterns:
  → Which agents consistently flag same issues?
  → Which chapters required most revision passes?
  → What types of feedback led to successful rewrites?
* Identify systematic agent weaknesses:
  → Drafter consistently missing required beats
  → Continuity Agent missing certain types of violations
  → Refiners over-correcting or introducing new issues
* Propose prompt/parameter adjustments:
  → Tune agent instructions based on observed failures
  → Adjust validation thresholds
  → Recommend agent invocation order changes
* Track quality metrics over time:
  → Revision rate per chapter (target: <2 passes)
  → Canon violation rate (target: declining)
  → User approval rate (target: >80%)
  → Reader engagement scores (from Adversarial Reader)
* Learn user preferences:
  → Which types of ideas user approves/rejects
  → Style preferences (verbose vs. terse)
  → Pacing preferences (fast vs. contemplative)
* Generate periodic reports for Central Manager to inform strategy

**Output Example:**
```
Arc 2 Reflection Report:
- Revision Rate: 2.3 passes/chapter (up from 1.8 in Arc 1) ⚠️
- Root Cause: Drafter missing POV constraints in Chapter Brief
- Recommendation: Add POV validation step before drafting
- User Approval: 85% (within target)
- Pacing: User prefers faster action scenes (approved 90% vs 60% for slow scenes)
- Learning: Increase action beat density in future briefs
```

---

## 12. Agent Access Patterns & Performance Model

### 12.1 Write Pattern Strategy

The system uses a **hybrid synchronous/asynchronous model** based on artifact criticality:

**SYNCHRONOUS (Blocking) - High Correctness Requirements:**
- Canon Store writes (via Continuity Validation Service)
- Outline structural updates
- Version snapshots
- Rollback operations

**ASYNCHRONOUS (Queued) - Derived/Non-Critical:**
- RAG chunk embedding updates
- World Registry regeneration
- Metrics aggregation
- Change log indexing
- Analytics processing

**Rationale:**
- Canon correctness is non-negotiable (once polluted, infects all downstream work)
- Canon writes are infrequent (~10-50 per arc vs. thousands of RAG updates)
- GraphDB validation is fast (50-200ms) vs. LLM generation (5-30s)
- Synchronous = immediate error feedback, simpler debugging
- Async = high throughput for derived data that can lag safely

---

### 12.2 Canon Write Implementation Pattern

```python
class OutlineCanonSyncManager:
    def commit_canon_change(self, proposal: CanonProposal) -> Result:
        """
        Synchronous validation + write to Canon Store.
        Returns immediately with success/failure.
        """

        # STEP 1: SYNCHRONOUS VALIDATION (blocking, ~50-200ms)
        validation = self.continuity_service.validate_mutation(
            mutation=proposal.mutation,
            context=self.get_current_canon_state(),
            cache_key=proposal.cache_key  # Optional caching
        )

        if not validation.is_valid:
            # Immediate rejection, agent can retry
            return Result.error(
                violations=validation.violations,
                suggestions=validation.auto_fixes
            )

        # STEP 2: SYNCHRONOUS WRITE (ACID transaction, ~100-300ms)
        with self.graph_db.transaction() as tx:
            # Write mutation
            tx.write(proposal.mutation)

            # Write immutable change log
            tx.write_change_log(
                proposal_id=proposal.id,
                agent=proposal.agent,
                before_state=self.snapshot(affected_entities),
                after_state=proposal.mutation,
                timestamp=now()
            )

            # Commit atomically
            tx.commit()

        # STEP 3: ASYNCHRONOUS DERIVED UPDATES (non-blocking)
        # These can lag by seconds/minutes without affecting correctness
        self.job_queue.enqueue(
            RegenerateRegistryJob(affected_entities=proposal.entities)
        )
        self.job_queue.enqueue(
            UpdateRAGEmbeddingsJob(canon_ids=proposal.entities)
        )
        self.job_queue.enqueue(
            InvalidateCacheJob(cache_keys=affected_cache_keys)
        )

        # STEP 4: IMMEDIATE SUCCESS RESPONSE
        return Result.success(
            change_log_id=change_log.id,
            warnings=validation.warnings  # Non-blocking warnings
        )
```

---

### 12.3 Validation Caching Strategy

To minimize validation latency while maintaining correctness:

```python
class ContinuityValidationService:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5min TTL
        self.cache_invalidation_patterns = {
            'character_mutation': ['character:*', 'relationship:*'],
            'location_mutation': ['location:*', 'travel:*'],
            'event_mutation': ['timeline:*', 'event:*']
        }

    def validate_mutation(
        self,
        mutation: CanonMutation,
        context: ValidationContext,
        cache_key: str = None
    ) -> ValidationResult:
        # Check cache first
        if cache_key and cache_key in self.cache:
            cached = self.cache[cache_key]
            if cached.context_hash == context.hash():
                return cached.result

        # Perform validation (50-200ms)
        result = self._validate(mutation, context)

        # Cache successful validations only
        if cache_key and result.is_valid:
            self.cache[cache_key] = CachedValidation(
                result=result,
                context_hash=context.hash(),
                timestamp=now()
            )

        return result

    def invalidate_cache_on_write(self, mutation: CanonMutation):
        """Called after successful canon write"""
        patterns = self.cache_invalidation_patterns.get(
            mutation.type,
            ['*']  # Invalidate all if unknown type
        )
        for pattern in patterns:
            self.cache.delete_pattern(pattern)
```

---

### 12.4 Parallel Validation for Independent Proposals

When multiple agents propose changes simultaneously (e.g., during planning phase):

```python
class BatchValidationService:
    def validate_batch(
        self,
        proposals: List[CanonProposal]
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple proposals in parallel if independent.
        Serialize if there are dependencies.
        """
        # Build dependency graph
        dep_graph = self._build_dependency_graph(proposals)

        # Group into batches (independent proposals)
        batches = self._topological_batches(dep_graph)

        results = {}

        for batch in batches:
            # Parallel validation within batch
            batch_results = asyncio.gather(*[
                self.validate_async(p) for p in batch
            ])
            results.update(batch_results)

            # Stop if any validation fails
            if any(not r.is_valid for r in batch_results.values()):
                # Mark remaining as skipped
                for remaining in proposals[len(results):]:
                    results[remaining.id] = ValidationResult.skipped(
                        reason="Dependent proposal failed validation"
                    )
                break

        return results
```

---

### 12.5 Read Access Patterns by Agent Type

**Planning Agents (Full Context):**
```python
# Central Architect needs broad view
canon_query = """
MATCH (arc:Arc)-[:CONTAINS]->(chapter:Chapter)-[:CONTAINS]->(scene:Scene)
WHERE arc.id = $arc_id
MATCH (scene)-[:INVOLVES]->(entity)
RETURN arc, chapter, scene, entity
"""
# Query cost: High, but infrequent (once per planning session)
```

**Writing Agents (Scoped Context):**
```python
# Drafter needs only relevant context for current chapter
rag_query = self.rag.retrieve(
    query_embedding=chapter_brief.embedding,
    filters={
        'type': ['character', 'location', 'rule'],
        'relevance_to_chapter': chapter_id,
        'max_distance': 3  # Graph hops from current chapter
    },
    top_k=20  # Limited context window
)
# Query cost: Medium, frequent (every draft)
```

**Review Agents (Minimal Context):**
```python
# Adversarial Reader intentionally doesn't see canon
# Only sees outline + chapters to simulate real reader
context = {
    'outline': self.get_outline_summary(),
    'previous_chapters': self.get_chapters(chapter_id - 3, chapter_id - 1),
    'current_chapter': chapter_text
}
# Query cost: Low, frequent (every review)
```

---

### 12.6 Performance Budgets

Target latencies for key operations:

| Operation                    | Target Latency | Max Acceptable | Frequency      |
| ---------------------------- | -------------- | -------------- | -------------- |
| Canon validation (cached)    | <10ms          | 50ms           | High           |
| Canon validation (uncached)  | 50-100ms       | 200ms          | Medium         |
| Canon write (transaction)    | 100-200ms      | 500ms          | Low            |
| RAG retrieval                | 50-150ms       | 300ms          | High           |
| GraphDB query (scoped)       | 20-50ms        | 100ms          | High           |
| GraphDB query (full)         | 100-500ms      | 2s             | Low            |
| Registry regeneration        | 1-5s           | 10s            | Low (async)    |
| LLM agent call               | 5-30s          | 60s            | High           |
| Chapter draft generation     | 30-120s        | 300s           | Medium         |

**Optimization Strategy:**
- Keep canon writes under 500ms total (validation + write)
- Use caching aggressively for repeated queries
- Async everything that doesn't affect correctness
- Parallel where safe (independent operations)
- Batch when possible (multiple proposals)

---

## 13. Error Handling & Resilience

### 13.1 Agent Failure Protocol

**Level 1: Output Validation Failure**
```python
# All agent outputs validated against schema
result = agent.execute(task)

if not schema.validate(result):
    # Retry with error context (max 3 attempts)
    for attempt in range(3):
        result = agent.execute(
            task,
            error_context=f"Previous output failed: {validation_errors}"
        )
        if schema.validate(result):
            break
    else:
        # After 3 failures, escalate
        observability_manager.escalate(
            severity="HIGH",
            agent=agent.name,
            task=task,
            error="Persistent output validation failure"
        )
```

**Level 2: Agent Execution Failure**
```python
# Network errors, timeouts, crashes
try:
    result = agent.execute(task, timeout=task.timeout)
except AgentTimeout:
    # Retry with extended timeout
    result = agent.execute(task, timeout=task.timeout * 2)
except AgentError as e:
    # Log and escalate
    observability_manager.log_agent_failure(agent, task, e)
    # Attempt fallback agent if available
    if task.fallback_agent:
        result = task.fallback_agent.execute(task)
    else:
        raise
```

**Level 3: Critical Failure (System Halt)**
```python
# Canon corruption, irrecoverable state
if observability_manager.detect_critical_failure():
    # 1. Halt all agent execution
    orchestrator.pause_all_agents()

    # 2. Create emergency snapshot
    version_manager.create_snapshot(label="emergency_pre_rollback")

    # 3. Alert user immediately
    user_interaction_manager.send_critical_alert(
        message="Critical system error detected. Story generation paused.",
        details=failure_report,
        actions=["Rollback to last checkpoint", "Manual intervention", "Contact support"]
    )

    # 4. Do NOT auto-recover (require user decision)
```

---

### 13.2 Storage Failure Protocol

**GraphDB Unavailable:**
```python
if not graph_db.is_healthy():
    # CRITICAL: Canon Store is unavailable

    # 1. Pause all canon mutations immediately
    sync_manager.pause_mutations()

    # 2. Continue with cached canon state (read-only mode)
    canon_state = cache_manager.get_last_known_canon_state()

    # 3. Alert user
    user_interaction_manager.notify(
        severity="WARNING",
        message="Canon Store temporarily unavailable. Operating in read-only mode.",
        eta=graph_db.estimated_recovery_time()
    )

    # 4. Queue mutations for later (when DB recovers)
    mutation_queue.enqueue_pending(pending_proposals)

    # 5. Continue writing loop (doesn't need canon writes)
    # But block planning loop (needs canon mutations)
```

**Vector Store Unavailable:**
```python
if not vector_store.is_healthy():
    # DEGRADED: RAG retrieval impaired but not critical

    # Fall back to graph-only retrieval
    retrieval_strategy = GraphOnlyRetrieval(graph_db)

    # Notify (non-blocking warning)
    observability_manager.log_warning(
        "Vector Store unavailable. Using graph-only retrieval. Quality may be reduced."
    )

    # Continue with degraded service
```

**Blob Storage Unavailable:**
```python
if not blob_storage.is_healthy():
    # CRITICAL: Cannot write drafts or logs

    # 1. Block new writes
    chapter_manager.pause_drafting()

    # 2. Serve from cache for reads
    cache_manager.serve_from_cache()

    # 3. Alert user
    user_interaction_manager.notify(
        severity="ERROR",
        message="Storage unavailable. Cannot save new chapters. Please retry later."
    )
```

---

### 13.3 Timeout Policy

**User Approval Timeout:**
```python
# User has 48 hours to respond to approval requests
if approval_request.age() > timedelta(hours=48):
    # Use conservative default
    decision = approval_request.get_default_decision()

    # Log timeout
    observability_manager.log(
        f"User approval timeout for {approval_request.id}. Using default: {decision}"
    )

    # Notify user
    user_interaction_manager.notify(
        f"Approval request timed out. Proceeding with conservative default: {decision}"
    )

    # Process with default
    process_approval(approval_request, decision)
```

**Agent Execution Timeout:**
```python
# Varies by agent complexity
AGENT_TIMEOUTS = {
    'drafter': 120,  # 2 minutes
    'central_architect': 60,
    'continuity_agent': 30,
    'prose_refiner': 45,
    'observability_manager': 10
}

# With exponential backoff on retry
def execute_with_timeout(agent, task):
    timeout = AGENT_TIMEOUTS.get(agent.name, 60)

    for attempt in range(3):
        try:
            return agent.execute(task, timeout=timeout * (2 ** attempt))
        except TimeoutError:
            if attempt == 2:  # Last attempt
                raise
            continue
```

**Query Timeout:**
```python
# Database queries have hard limits
QUERY_TIMEOUT = 30  # seconds

try:
    result = graph_db.query(query, timeout=QUERY_TIMEOUT)
except QueryTimeout:
    # Return partial results or retry with simplified query
    if query.can_simplify():
        result = graph_db.query(query.simplified(), timeout=QUERY_TIMEOUT)
    else:
        # Return partial cached results
        result = cache_manager.get_partial_results(query)
```

---

### 13.4 Rollback Safety Validation

**Before Rolling Back:**
```python
class VersionManager:
    def rollback(self, target_version: Version) -> RollbackResult:
        # 1. Validate rollback safety
        safety_check = self._validate_rollback_safety(target_version)

        if not safety_check.is_safe:
            return RollbackResult.unsafe(
                reason=safety_check.reason,
                conflicts=safety_check.conflicts
            )

        # 2. Create pre-rollback snapshot (can undo the undo)
        emergency_snapshot = self.create_snapshot(
            label=f"pre_rollback_{target_version.id}"
        )

        # 3. Calculate affected artifacts
        affected = self._calculate_rollback_impact(target_version)

        # 4. Confirm with user if impact is large
        if affected.chapter_count > 5 or affected.canon_entities > 20:
            confirmation = user_interaction_manager.confirm_rollback(
                target_version=target_version,
                impact=affected,
                warning="This will delete 5+ chapters and affect 20+ canon entities"
            )
            if not confirmation:
                return RollbackResult.cancelled()

        # 5. Execute rollback (atomic)
        with self.transaction() as tx:
            # Rollback Canon Store
            tx.restore_graph_state(target_version.canon_snapshot)

            # Rollback Outline
            tx.restore_outline(target_version.outline_snapshot)

            # Mark rolled-back chapters as archived (not deleted)
            tx.archive_chapters(affected.chapters)

            # Write rollback log
            tx.write_rollback_log(
                from_version=current_version,
                to_version=target_version,
                reason=rollback_reason,
                affected=affected
            )

            tx.commit()

        # 6. Async cleanup
        self.job_queue.enqueue(RegenerateRegistryJob())
        self.job_queue.enqueue(RebuildRAGIndexJob(from_version=target_version))

        return RollbackResult.success(
            restored_version=target_version,
            archived_content=affected.chapters
        )
```

---

## 14. Metrics & Observability

### 14.1 Metrics Tracked by Observability Manager

**Canon Store Health:**
```python
canon_metrics = {
    # Consistency metrics
    'unresolved_threads': count_where(Thread.status == 'unresolved'),
    'orphaned_entities': count_where(Entity.appearances == 0),
    'contradiction_count': count_where(Edge.type == 'contradicts'),
    'timeline_violations': count_timeline_cycles(),

    # Usage metrics
    'total_entities': count(Entity),
    'entities_introduced_this_arc': count_where(Entity.arc == current_arc),
    'average_entity_appearances': avg(Entity.appearances),

    # Growth metrics
    'canon_mutation_rate': mutations_per_hour(),
    'validation_failure_rate': failed_validations / total_validations,
}
```

**Outline Health:**
```python
outline_metrics = {
    # Coverage metrics
    'scenes_per_chapter': avg(Chapter.scene_count),
    'chapters_per_arc': avg(Arc.chapter_count),
    'outline_completeness': (planned_chapters / total_expected_chapters),

    # Balance metrics
    'words_per_arc': avg(Arc.word_count),
    'arc_length_variance': std_dev(Arc.word_count),

    # Escalation metrics
    'tension_curve': calculate_tension_over_time(),
    'stakes_escalation': validate_stakes_increase(),

    # Pacing metrics
    'action_scene_ratio': count(Scene.type == 'action') / count(Scene),
    'dialogue_scene_ratio': count(Scene.type == 'dialogue') / count(Scene),
    'reflection_scene_ratio': count(Scene.type == 'reflection') / count(Scene),
}
```

**Writing Quality Metrics:**
```python
writing_metrics = {
    # Revision metrics
    'avg_revision_passes_per_chapter': avg(Chapter.revision_count),
    'revision_pass_distribution': histogram(Chapter.revision_count),
    'chapters_requiring_redraft': count_where(Chapter.revision_count >= 2),

    # Quality metrics (from review agents)
    'ai_ism_detection_rate': aiisms_flagged / total_chapters,
    'continuity_violation_rate': violations / total_chapters,
    'adversarial_reader_rejection_rate': rejections / total_chapters,
    'engagement_score': avg(AdversarialReader.engagement_score),

    # Consistency metrics
    'voice_consistency_score': avg(VoiceBible.consistency_score),
    'style_drift_over_time': measure_style_variance_by_chapter(),
}
```

**Agent Performance Metrics:**
```python
agent_metrics = {
    # Execution metrics
    'agent_execution_time': {agent: avg(execution_time) for agent in agents},
    'agent_timeout_rate': {agent: timeouts / executions for agent in agents},
    'agent_failure_rate': {agent: failures / executions for agent in agents},

    # Quality metrics
    'agent_approval_rate': {agent: approvals / proposals for agent in agents},
    'agent_revision_trigger_rate': {agent: revisions_caused / executions},

    # Efficiency metrics
    'agent_retry_rate': {agent: retries / executions for agent in agents},
    'validation_cache_hit_rate': cache_hits / total_validations,
}
```

**User Interaction Metrics:**
```python
user_metrics = {
    # Approval metrics
    'user_approval_rate': approvals / total_requests,
    'user_approval_rate_by_type': {type: rate for type in request_types},
    'avg_approval_response_time': avg(response_time),
    'approval_timeout_rate': timeouts / total_requests,

    # Preference learning
    'user_preference_patterns': learn_from_approval_history(),
    'user_intervention_rate': manual_edits / total_chapters,
}
```

---

### 14.2 Alerting Thresholds

**CRITICAL (Immediate Escalation):**
```python
CRITICAL_ALERTS = {
    'canon_contradiction': lambda: contradiction_count > 0,
    'timeline_cycle_detected': lambda: has_timeline_cycles(),
    'storage_failure': lambda: not all_storage_healthy(),
    'agent_persistent_failure': lambda: agent_failure_rate > 0.5,
}
```

**HIGH (Escalate to User):**
```python
HIGH_ALERTS = {
    'unresolved_threads_high': lambda: unresolved_threads > 5,
    'revision_rate_high': lambda: avg_revision_passes > 2.5,
    'orphaned_entities': lambda: orphaned_count > 10,
    'engagement_score_low': lambda: engagement_score < 0.6,
}
```

**MEDIUM (Internal Investigation):**
```python
MEDIUM_ALERTS = {
    'validation_failure_rate_elevated': lambda: validation_failure_rate > 0.2,
    'pacing_imbalance': lambda: abs(scene_ratio - 0.33) > 0.15,
    'style_drift_detected': lambda: style_variance > threshold,
}
```

**LOW (Logging Only):**
```python
LOW_ALERTS = {
    'cache_hit_rate_low': lambda: cache_hit_rate < 0.5,
    'agent_slow': lambda: any(time > timeout * 0.8 for time in execution_times),
}
```

---

### 14.3 Observability Dashboard

**Real-time Monitoring:**
```
┌─ Story Progress ────────────────────────┐
│ Arc 2 / Chapter 7                       │
│ Progress: ████████░░ 78%                │
│ Words: 45,230 / 80,000 target           │
└─────────────────────────────────────────┘

┌─ Canon Health ──────────────────────────┐
│ ✓ No contradictions                     │
│ ✓ Timeline valid                        │
│ ⚠ 3 unresolved threads                  │
│ ✓ 127 entities, 0 orphaned              │
└─────────────────────────────────────────┘

┌─ Writing Quality ───────────────────────┐
│ Avg Revisions: 1.8 passes ✓             │
│ Engagement: 8.2/10 ✓                    │
│ Continuity Violations: 2 this arc ⚠     │
│ AI-isms detected: 12 (all fixed) ✓      │
└─────────────────────────────────────────┘

┌─ Agent Status ──────────────────────────┐
│ Drafter: ✓ Active (draft in progress)  │
│ Continuity Agent: ✓ Idle               │
│ Central Architect: ✓ Idle              │
│ Observability: ✓ Monitoring            │
└─────────────────────────────────────────┘

┌─ Recent Alerts ─────────────────────────┐
│ [10m ago] MEDIUM: Pacing imbalance Arc 2│
│ [1h ago]  LOW: Cache hit rate 45%       │
└─────────────────────────────────────────┘
```

---

## 15. User-Facing APIs

### 15.1 Start Story

```http
POST /story/init

Request:
{
  "files": {
    "worldbuilding": <file>,
    "characters": <file>,
    "scenes": <file>
  },
  "constraints": {
    "genre": "fantasy",
    "target_length": 80000,
    "pov": "third_person_limited",
    "tone": "dark_serious"
  },
  "preferences": {
    "approval_required_for": ["new_characters", "major_plot_changes"],
    "auto_approve": ["minor_worldbuilding", "scene_details"]
  }
}

Response:
{
  "story_id": "uuid",
  "status": "initializing",
  "progress": {
    "rag_parsing": "in_progress",
    "canon_init": "pending",
    "outline_init": "pending"
  },
  "eta": "2-5 minutes"
}
```

---

### 15.2 Approve / Reject Idea

```http
POST /story/idea/{idea_id}/decision

Request:
{
  "decision": "approve" | "reject" | "modify",
  "modifications": {
    "character_name": "Revised Name",
    "rationale": "User's reasoning"
  },
  "feedback": "Optional feedback for learning"
}

Response:
{
  "status": "approved",
  "applied": true,
  "change_log_id": "uuid",
  "affected_artifacts": ["canon", "outline", "registry"]
}
```

---

### 15.3 Request Revision

```http
POST /story/revise

Request:
{
  "scope": "chapter" | "arc" | "outline",
  "target_id": "chapter_7",
  "feedback": "The pacing in this chapter feels rushed. Please slow down the dialogue scene.",
  "specific_changes": {
    "expand_scene": "scene_7_3",
    "target_length": "+500 words"
  }
}

Response:
{
  "revision_id": "uuid",
  "status": "queued",
  "estimated_time": "5-10 minutes",
  "agents_involved": ["chapter_manager", "drafter", "pacing_agent"]
}
```

---

### 15.4 Generate Next Chapter

```http
POST /story/chapter/next

Request:
{
  "story_id": "uuid",
  "options": {
    "auto_approve_minor": true,
    "max_revision_passes": 3
  }
}

Response:
{
  "chapter_id": "uuid",
  "status": "drafting",
  "progress_url": "/story/chapter/{chapter_id}/progress",
  "eta": "10-15 minutes"
}

# Progress endpoint (WebSocket or polling):
GET /story/chapter/{chapter_id}/progress

{
  "status": "reviewing",
  "current_step": "parallel_review",
  "steps_completed": ["drafting"],
  "agents_active": ["continuity_agent", "adversarial_reader"],
  "issues_found": 2,
  "eta": "3 minutes"
}
```

---

### 15.5 Inspect Canon / Registry

```http
GET /story/canon?entity_type=character&status=active

Response:
{
  "entities": [
    {
      "id": "char_001",
      "type": "character",
      "name": "Alice",
      "status": "alive",
      "introduced_in": "chapter_1",
      "last_appeared": "chapter_7",
      "relationships": [
        {"type": "allies_with", "target": "char_002", "strength": 0.8}
      ],
      "unresolved_threads": ["revenge_arc", "lost_artifact"]
    }
  ],
  "total": 24,
  "page": 1
}

GET /story/registry

Response:
{
  "core_elements": {
    "primary_characters": ["char_001", "char_002", "char_003"],
    "key_locations": ["loc_001", "loc_002"],
    "central_conflicts": ["thread_001"]
  },
  "derived_elements": {
    "secondary_characters": 12,
    "subplots": 5
  },
  "usage_tracking": {
    "unresolved_threads": 3,
    "orphaned_entities": 0,
    "entities_by_chapter": {...}
  },
  "generated_at": "2026-01-25T10:30:00Z"
}
```

---

### 15.6 Download Manuscript

```http
GET /story/manuscript?format=docx&include_metadata=true

Response: Binary file download

Metadata included:
- Chapter breaks
- Scene breaks
- Word count per chapter
- Timestamps
- Version information
```

---

### 15.7 Pause/Resume Story

```http
POST /story/pause

Response:
{
  "status": "paused",
  "snapshot_created": "snapshot_uuid",
  "can_resume_from": "chapter_7"
}

POST /story/resume

Response:
{
  "status": "resumed",
  "resuming_from": "chapter_7",
  "pending_tasks": 3
}
```

---

### 15.8 Rollback to Checkpoint

```http
POST /story/rollback

Request:
{
  "version_id": "arc_2_checkpoint_3",
  "reason": "Major plot issue detected",
  "confirm_data_loss": true
}

Response:
{
  "status": "rolled_back",
  "restored_version": "arc_2_checkpoint_3",
  "archived_chapters": ["chapter_8", "chapter_9", "chapter_10"],
  "canon_entities_restored": 15,
  "pre_rollback_snapshot": "emergency_snapshot_uuid"
}
```

---

### 15.9 Query Canon

```http
POST /story/canon/query

Request:
{
  "query": "WHERE was Alice last seen?",
  "type": "graph" | "natural_language"
}

Response (graph):
{
  "results": [
    {
      "entity": "char_001",
      "name": "Alice",
      "last_location": "loc_005",
      "location_name": "The Forbidden Library",
      "chapter": "chapter_7",
      "scene": "scene_7_5"
    }
  ]
}

Response (natural_language):
{
  "answer": "Alice was last seen in The Forbidden Library during chapter 7, scene 5.",
  "confidence": 0.95,
  "supporting_facts": ["char_001.last_appearance", "scene_7_5.location"]
}
```

---

### 15.10 Export World Bible

```http
GET /story/worldbible?format=markdown

Response: Auto-generated comprehensive reference document

Structure:
# World Bible - [Story Title]

## Characters
### Primary Characters
- Alice (char_001)
  - Status: Alive
  - Role: Protagonist
  - Arc: Revenge → Redemption
  - Relationships: ...
  - Appearances: Chapter 1, 3, 5, 7

### Secondary Characters
...

## Locations
...

## Timeline
...

## Unresolved Threads
...

## Motifs & Themes
...
```

---

### 15.11 Inject Manual Edit

```http
POST /story/manual/edit

Request:
{
  "artifact": "outline" | "canon" | "chapter",
  "target_id": "chapter_7",
  "change": {
    "type": "replace_scene",
    "scene_id": "scene_7_3",
    "new_content": "..."
  },
  "rationale": "User's explanation"
}

Response:
{
  "status": "validating",
  "validation_result": {
    "is_valid": true,
    "warnings": ["This changes character location. Affected: 3 future scenes"],
    "requires_resync": true
  },
  "resync_job_id": "uuid",
  "affected_artifacts": ["outline", "canon", "rag"]
}
```

---

### 15.12 Get Metrics Dashboard

```http
GET /story/metrics

Response:
{
  "story_progress": {
    "current_arc": 2,
    "current_chapter": 7,
    "completion_percentage": 78,
    "words_written": 45230,
    "target_words": 80000
  },
  "canon_health": {
    "contradictions": 0,
    "timeline_valid": true,
    "unresolved_threads": 3,
    "orphaned_entities": 0,
    "total_entities": 127
  },
  "writing_quality": {
    "avg_revision_passes": 1.8,
    "engagement_score": 8.2,
    "continuity_violations_this_arc": 2,
    "ai_isms_detected": 12
  },
  "agent_status": {
    "drafter": "active",
    "central_architect": "idle",
    "observability_manager": "monitoring"
  },
  "recent_alerts": [
    {
      "time": "10m ago",
      "severity": "MEDIUM",
      "message": "Pacing imbalance detected in Arc 2"
    }
  ]
}
```

---

### 15.13 Batch Approval Interface

```http
GET /story/approvals/pending

Response:
{
  "pending_approvals": [
    {
      "id": "approval_001",
      "type": "new_character",
      "agent": "character_planner",
      "proposal": {
        "character_name": "Marcus",
        "role": "Mentor",
        "rationale": "Alice needs guidance for magic training"
      },
      "impact": "low",
      "priority": 3,
      "created_at": "2h ago"
    },
    {
      "id": "approval_002",
      "type": "plot_change",
      "agent": "idea_generator",
      "proposal": {
        "change": "Add betrayal subplot",
        "rationale": "Resolves staleness in Arc 2"
      },
      "impact": "high",
      "priority": 1,
      "created_at": "1h ago"
    }
  ],
  "total": 2
}

POST /story/approvals/batch

Request:
{
  "decisions": [
    {"approval_id": "approval_001", "decision": "approve"},
    {"approval_id": "approval_002", "decision": "reject", "reason": "Too dark for target audience"}
  ]
}

Response:
{
  "processed": 2,
  "approved": 1,
  "rejected": 1,
  "changes_applied": ["canon", "outline"]
}
```

---

## 16. Agent Dependency Graph

### 16.1 Initialization Phase

```
Start
  │
  ├─→ World Registry Initializer
  │     └─→ Creates initial Canon nodes
  │
  ├─→ RAG Parser (parallel)
  │     └─→ Creates RAG chunks
  │
  └─→ Outline Initializer (depends on above)
        └─→ Creates initial Central Outline
        └─→ Triggers Version Manager (initial checkpoint)
```

---

### 16.2 Planning Loop (Per Arc)

```
Central Manager (orchestrates all below)
  │
  ├─→ Timeline Manager
  │     └─→ Validates temporal consistency
  │
  ├─→ Central Architect
  │     └─→ Expands outline (arcs → chapters → scenes)
  │     └─→ Depends on: World Registry, Canon Store
  │
  ├─→ Character Planner (parallel)
  │     └─→ Proposes character developments
  │     └─→ Depends on: Canon Store, Outline
  │
  ├─→ Scene Planner (parallel)
  │     └─→ Creates scene cards
  │     └─→ Depends on: Outline gaps
  │
  ├─→ Pacing Agent (after scene planning)
  │     └─→ Analyzes tempo and rhythm
  │
  ├─→ Theme Guardian (after scene planning)
  │     └─→ Validates motif usage
  │
  ├─→ Foreshadowing & Payoff Agent (after scene planning)
  │     └─→ Tracks seeds and payoffs
  │
  └─→ Outline ↔ Canon Sync Manager (after all proposals)
        └─→ Reconciles and commits changes
        └─→ Invokes: Continuity Validation Service
        └─→ Triggers: User Interaction Manager (if needed)
        └─→ Triggers: Version Manager (checkpoint)

Observability Manager (monitors all continuously)
```

---

### 16.3 Writing Loop (Per Chapter)

```
Chapter Manager receives Chapter Brief
  │
  ├─→ Timeline Manager
  │     └─→ Pre-validates temporal constraints
  │
  ├─→ Drafter
  │     └─→ Produces rough draft
  │
  ├─→ PARALLEL REVIEW
  │     ├─→ Continuity Agent
  │     ├─→ Adversarial Reader
  │     ├─→ Reader Simulation Agent
  │     └─→ Voice Bible Agent
  │
  ├─→ Arbitration Agent
  │     └─→ Synthesizes feedback
  │     └─→ Resolves conflicts
  │
  ├─→ Chapter Manager decision point
  │     ├─→ IF major issues: loop back to Drafter
  │     └─→ IF minor issues: proceed to refinement
  │
  ├─→ PARALLEL REFINEMENT
  │     ├─→ Prose Refiner
  │     └─→ Dialogue Refiner
  │
  ├─→ Continuity Agent (final check)
  │
  ├─→ Version Manager
  │     └─→ Creates chapter checkpoint
  │
  └─→ Commit to Manuscript
        └─→ Async: Update RAG
        └─→ Async: Regenerate Registry (if needed)

Observability Manager (monitors all continuously)
```

---

### 16.4 Meta-Learning (Per Arc Completion)

```
Arc Completion Event
  │
  └─→ Reflection Agent
        └─→ Analyzes completed arc
        └─→ Generates improvement recommendations
        └─→ Feeds back to Central Manager
        └─→ Optionally updates agent prompts/parameters
```

---

## 17. Consensus & Conflict Resolution

### 17.1 Consensus Rules (for Arbitration Agent)

**Priority Hierarchy:**
```
1. Canon violations        (BLOCKING - must fix)
   └─ Character contradictions
   └─ Timeline violations
   └─ Fact errors

2. Outline violations      (BLOCKING - must fix)
   └─ Missing required beats
   └─ Skipped reveals
   └─ Plot structure breaks

3. Timeline violations     (BLOCKING - must fix)
   └─ Temporal impossibilities
   └─ Travel time errors

4. Engagement issues       (HIGH PRIORITY - should fix)
   └─ Boredom (Adversarial Reader)
   └─ Confusion (Reader Simulation)
   └─ Pacing problems

5. Voice/style issues      (MEDIUM PRIORITY - nice to fix)
   └─ Style drift
   └─ Tone inconsistency
   └─ POV violations

6. Subjective quality      (ADVISORY - consider)
   └─ Prose quality suggestions
   └─ Dialogue improvements
```

**Voting Mechanism:**
```python
class ArbitrationAgent:
    def resolve_conflicts(self, reviews: List[AgentReview]) -> Resolution:
        # Extract all issues
        issues = []
        for review in reviews:
            issues.extend(review.issues)

        # Group by priority
        blocking = [i for i in issues if i.priority == 'BLOCKING']
        high = [i for i in issues if i.priority == 'HIGH']
        medium = [i for i in issues if i.priority == 'MEDIUM']
        advisory = [i for i in issues if i.priority == 'ADVISORY']

        # Decision logic
        if blocking:
            return Resolution.require_redraft(
                reason="Blocking issues found",
                issues=blocking,
                feedback=self.synthesize_feedback(blocking)
            )

        if len(high) >= 2:  # Two high-priority issues = redraft
            return Resolution.require_redraft(
                reason="Multiple high-priority issues",
                issues=high,
                feedback=self.synthesize_feedback(high)
            )

        if high or medium:
            return Resolution.proceed_with_refinement(
                issues=high + medium,
                feedback=self.synthesize_feedback(high + medium)
            )

        if advisory:
            return Resolution.proceed_with_notes(
                notes=self.synthesize_feedback(advisory)
            )

        return Resolution.approve()
```

**Conflict Resolution Examples:**

**Scenario 1: Continuity vs. Engagement**
```
Continuity Agent: "Character uses magic they don't know yet" (BLOCKING)
Adversarial Reader: "This scene is very engaging" (ADVISORY)

Resolution: BLOCK - Canon violations always win
Rationale: Engagement doesn't matter if story is inconsistent
```

**Scenario 2: Multiple Style Disagreements**
```
Prose Refiner: "Too many short sentences" (MEDIUM)
Dialogue Refiner: "Short sentences work well for dialogue" (MEDIUM)
Voice Bible: "Style matches established voice" (ADVISORY)

Resolution: PROCEED - No blocking issues, defer to Voice Bible
Rationale: Style is subjective, established voice takes precedence
```

**Scenario 3: Escalation Required**
```
Continuity Agent: "Character death contradicts outline" (BLOCKING)
Adversarial Reader: "Death scene is powerful climax" (HIGH)

Resolution: ESCALATE to User
Rationale: Canon vs. creative quality - user must decide
Present options:
  A) Keep death, update outline and canon
  B) Revise scene, preserve canon
  C) Find middle ground (near-death instead)
```

---

## 18. GraphDB Schema Details

### 18.1 Node Types with Full Properties

**Character Node:**
```cypher
CREATE (c:Character {
  id: UUID,
  name: String,
  aliases: [String],
  status: ENUM('alive', 'dead', 'missing', 'unknown'),

  # Arc tracking
  arc_stage: ENUM('introduction', 'development', 'climax', 'resolution'),
  introduced_in_chapter: UUID,
  last_appearance_chapter: UUID,

  # Attributes
  age: Integer,
  occupation: String,
  faction: UUID,

  # Story tracking
  pov_character: Boolean,
  total_appearances: Integer,
  total_dialogue_lines: Integer,

  # Metadata
  created_at: Timestamp,
  updated_at: Timestamp,
  version: Integer,
  created_by_agent: String
})
```

**Location Node:**
```cypher
CREATE (l:Location {
  id: UUID,
  name: String,
  type: ENUM('city', 'building', 'room', 'landmark', 'region'),

  # Geography
  parent_location: UUID,  # For hierarchical locations
  coordinates: Point,     # Optional spatial data

  # Story tracking
  introduced_in_chapter: UUID,
  scenes_set_here: Integer,

  # Properties
  description_summary: String,
  notable_features: [String],

  # Metadata
  created_at: Timestamp,
  updated_at: Timestamp,
  version: Integer
})
```

**Thread Node (Subplot/Arc):**
```cypher
CREATE (t:Thread {
  id: UUID,
  name: String,
  type: ENUM('plot', 'subplot', 'character_arc', 'mystery'),

  # Status
  status: ENUM('planned', 'active', 'resolved', 'abandoned'),
  priority: ENUM('primary', 'secondary', 'tertiary'),

  # Story tracking
  introduced_in: UUID,  # Chapter/Scene
  resolved_in: UUID,    # Chapter/Scene (if resolved)
  expected_resolution: UUID,  # Planned chapter

  # Content
  description: String,
  stakes: String,

  # Metadata
  created_at: Timestamp,
  updated_at: Timestamp,
  version: Integer
})
```

**Event Node:**
```cypher
CREATE (e:Event {
  id: UUID,
  name: String,
  type: ENUM('action', 'revelation', 'decision', 'consequence'),

  # Timing
  occurs_in_chapter: UUID,
  occurs_in_scene: UUID,
  story_time: Timestamp,  # In-universe time

  # Relationships
  affects_characters: [UUID],
  affects_threads: [UUID],

  # Content
  description: String,
  significance: ENUM('major', 'moderate', 'minor'),

  # Metadata
  created_at: Timestamp,
  updated_at: Timestamp
})
```

**Motif Node:**
```cypher
CREATE (m:Motif {
  id: UUID,
  name: String,
  type: ENUM('symbol', 'theme', 'recurring_element'),

  # Content
  description: String,
  meaning: String,

  # Tracking
  appearances: [UUID],  # Scene IDs where it appears
  appearance_count: Integer,
  target_appearances: Integer,  # Desired frequency

  # Metadata
  created_at: Timestamp,
  updated_at: Timestamp
})
```

---

### 18.2 Edge Types with Full Properties

**appears_in (Character → Scene/Chapter):**
```cypher
CREATE (c:Character)-[r:APPEARS_IN]->(s:Scene)
SET r = {
  pov_character: Boolean,
  dialogue_lines: Integer,
  actions_taken: Integer,
  first_appearance: Boolean,
  character_state: String,  # emotional/physical state
  timestamp: Timestamp
}
```

**before/after (Event → Event):**
```cypher
CREATE (e1:Event)-[r:BEFORE]->(e2:Event)
SET r = {
  time_delta: Duration,  # How much time between events
  causality: ENUM('direct_cause', 'indirect', 'unrelated'),
  timestamp: Timestamp
}
```

**foreshadows (Event → Event):**
```cypher
CREATE (e1:Event)-[r:FORESHADOWS]->(e2:Event)
SET r = {
  subtlety: ENUM('obvious', 'moderate', 'subtle'),
  payoff_delivered: Boolean,
  chapters_between: Integer,
  timestamp: Timestamp
}
```

**wants/fears/believes/knows (Character → Entity):**
```cypher
CREATE (c:Character)-[r:WANTS]->(obj:Object)
SET r = {
  intensity: Float,  # 0.0 to 1.0
  since_chapter: UUID,
  reason: String,
  fulfilled: Boolean,
  timestamp: Timestamp
}
```

**contradicts (Any → Any):**
```cypher
CREATE (e1:Entity)-[r:CONTRADICTS]->(e2:Entity)
SET r = {
  contradiction_type: ENUM('fact', 'timeline', 'character', 'physics'),
  severity: ENUM('critical', 'major', 'minor'),
  detected_by: String,  # Agent name
  resolved: Boolean,
  resolution: String,
  timestamp: Timestamp
}
```

---

## 19. Additional Considerations

### 19.1 Scaling Considerations

**For Very Long Novels (200k+ words):**

```python
# Partition Canon Store by arc
canon_partitions = {
    'arc_1': GraphPartition(arcs=[1]),
    'arc_2': GraphPartition(arcs=[2]),
    'shared': GraphPartition(global_entities=True)
}

# Query strategy: Check shared first, then relevant partition
def query_canon(query, current_arc):
    results = canon_partitions['shared'].query(query)
    results.extend(canon_partitions[f'arc_{current_arc}'].query(query))
    return deduplicate(results)
```

**For Many Concurrent Users (Multi-tenant):**

```python
# Story-level isolation
story_namespaces = {
    'story_uuid_1': IsolatedCanonStore(),
    'story_uuid_2': IsolatedCanonStore()
}

# No cross-contamination possible
```

---

### 19.2 Advanced Features (Future Enhancements)

**Multi-POV Coordination:**
```python
class MultiPOVManager:
    """
    Coordinates multiple POV characters in same timeframe.
    Ensures consistency across parallel timelines.
    """
    def validate_parallel_chapters(self, chapters: List[Chapter]):
        # Check that events seen from multiple POVs match
        # Validate that information known to characters is consistent
        pass
```

**Collaborative Writing:**
```python
class CollaborativeWritingManager:
    """
    Allows multiple human authors + AI agents to co-write.
    Manages merge conflicts and approval workflows.
    """
    def merge_human_edits(self, human_edit, ai_draft):
        # Smart merge with conflict detection
        pass
```

**Genre-Specific Agents:**
```python
# Mystery: Clue placement agent, red herring generator
# Romance: Chemistry tracker, relationship arc manager
# Thriller: Tension escalation agent, twist planner
```

---

## 20. Complete System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  (APIs, Dashboard, Approval Interface, Manuscript Viewer)       │
└─────────────────────────────────────────────────────────────────┘
                              ││
                              ▼▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Central    │  │   Chapter    │  │    User      │         │
│  │   Manager    │  │   Manager    │  │ Interaction  │         │
│  └──────────────┘  └──────────────┘  │   Manager    │         │
│  ┌──────────────┐  ┌──────────────┐  └──────────────┘         │
│  │ Observability│  │   Version    │  ┌──────────────┐         │
│  │   Manager    │  │   Manager    │  │ Arbitration  │         │
│  └──────────────┘  └──────────────┘  │    Agent     │         │
│                                       └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ││
              ┌───────────────┼┼───────────────┐
              ▼▼              ▼▼               ▼▼
┌────────────────────┐  ┌────────────┐  ┌─────────────────┐
│  PLANNING AGENTS   │  │  WRITING   │  │ META-LEARNING   │
│                    │  │   AGENTS   │  │                 │
│ • Central Architect│  │ • Drafter  │  │ • Reflection    │
│ • Timeline Manager │  │ • Continuity│  │   Agent         │
│ • Pacing Agent     │  │ • Prose    │  │                 │
│ • Theme Guardian   │  │ • Dialogue │  │                 │
│ • Character Planner│  │ • Adversarial│                 │
│ • Scene Planner    │  │ • Reader Sim│                   │
│ • Foreshadowing    │  │ • Voice Bible│                  │
│ • Idea Generator   │  └────────────┘                    │
│ • Sync Manager     │                                     │
└────────────────────┘                └─────────────────┘
         ││                    ││                 ││
         ▼▼                    ▼▼                 ▼▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION & SERVICES                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │      Continuity Validation Service (Synchronous)       │    │
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         RAG Retrieval Service (Hybrid Query)           │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ││
              ┌───────────────┼┼───────────────┐
              ▼▼              ▼▼               ▼▼
┌────────────────────┐  ┌────────────┐  ┌─────────────────┐
│   CANON STORE      │  │  OUTLINE   │  │   RAG STORE     │
│   (GraphDB)        │  │  (Document)│  │  (Vector+Blob)  │
│                    │  │            │  │                 │
│ • Characters       │  │ • Arcs     │  │ • Chunks        │
│ • Locations        │  │ • Chapters │  │ • Embeddings    │
│ • Events           │  │ • Scenes   │  │ • Metadata      │
│ • Threads          │  │ • Beats    │  │                 │
│ • Motifs           │  │            │  │                 │
│ • Relationships    │  │            │  │                 │
│ (AUTHORITATIVE)    │  │(AUTHORITATIVE)│ (DERIVED)       │
└────────────────────┘  └────────────┘  └─────────────────┘
              ││              ││                 ││
              ▼▼              ▼▼                 ▼▼
┌─────────────────────────────────────────────────────────────────┐
│                  IMMUTABLE STORAGE LAYER                        │
│  • Blob Storage (Drafts, Logs, Archives)                       │
│  • Change Logs (Audit Trail)                                    │
│  • Version Snapshots (Checkpoints)                              │
└─────────────────────────────────────────────────────────────────┘
              ││
              ▼▼
┌─────────────────────────────────────────────────────────────────┐
│                      DERIVED OUTPUTS                            │
│  • Manuscript (User-facing)                                     │
│  • World Registry (Generated from Canon)                        │
│  • Metrics Dashboard (Analytics)                                │
│  • World Bible (Export)                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 21. Summary & Implementation Roadmap

### 21.1 Core Architectural Wins

✅ **Canon Store as GraphDB** - Single source of truth for entities and relationships
✅ **Synchronous Validation** - Prevents invalid state from entering canon
✅ **Immutable Audit Trail** - Full history, safe rollback
✅ **Clear Authority Separation** - No circular dependencies
✅ **Explicit Write Patterns** - Sync for correctness, async for performance
✅ **Comprehensive Agent Coverage** - All aspects of storytelling addressed
✅ **User Control** - System proposes, user disposes

---

### 21.2 Implementation Phases

**Phase 1: Core Infrastructure (Weeks 1-4)**
- GraphDB setup (Neo4j or Neptune)
- Blob storage (S3 or equivalent)
- Vector store (Pinecone, Weaviate, or Qdrant)
- Basic API framework
- Continuity Validation Service

**Phase 2: Initialization (Weeks 5-8)**
- World Registry Initializer
- RAG Parser
- Outline Initializer
- Version Manager (basic)
- Simple user approval workflow

**Phase 3: Planning Loop (Weeks 9-14)**
- Central Manager
- Central Architect
- Timeline Manager
- Character Planner
- Scene Planner
- Outline ↔ Canon Sync Manager
- Observability Manager (basic)

**Phase 4: Writing Loop (Weeks 15-20)**
- Chapter Manager
- Drafter
- Continuity Agent
- Prose & Dialogue Refiners
- Adversarial Reader
- Reader Simulation Agent
- Voice Bible Agent
- Arbitration Agent

**Phase 5: Advanced Features (Weeks 21-24)**
- Pacing Agent
- Theme Guardian
- Foreshadowing & Payoff Agent
- Idea Generator
- Reflection Agent
- Enhanced Observability
- Full metrics dashboard

**Phase 6: Polish & Scale (Weeks 25-30)**
- Performance optimization
- Error handling hardening
- User experience refinement
- Documentation
- Testing & validation
- Beta user testing

---

### 21.3 Success Metrics

**System Health:**
- Canon contradiction rate: <0.1% per chapter
- Timeline violation rate: <0.5% per arc
- System uptime: >99%

**Writing Quality:**
- Average revision passes: <2.5 per chapter
- User approval rate: >80%
- Engagement score: >7/10 (from Adversarial Reader)

**Efficiency:**
- Time to draft chapter: <15 minutes
- Time to complete arc: <4 hours
- Canon validation latency: <200ms

**User Satisfaction:**
- User intervention rate: <10% of chapters
- Manual edit rate: <5% of chapters
- Project completion rate: >70%

---

## End of Document
