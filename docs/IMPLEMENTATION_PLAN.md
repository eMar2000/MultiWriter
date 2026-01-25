# MultiWriter v2 Implementation Plan
## RAG-Enhanced Agent Workflow for Large Document Input

---

## Overview

Transform MultiWriter from an interactive CLI tool into a document-driven outline generator capable of processing 100+ page input documents with parallel arc expansion.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: INGESTION                                │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │Worldbuild.md│  │Characters.md│  │  Scenes.md  │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         └────────────────┼────────────────┘                                 │
│                          ▼                                                  │
│              ┌───────────────────────┐                                      │
│              │   DocumentParser      │  Parse markdown by structure         │
│              └───────────┬───────────┘                                      │
│                          ▼                                                  │
│              ┌───────────────────────┐                                      │
│              │   EntityExtractor     │  Extract ALL entities deterministically│
│              └───────────┬───────────┘                                      │
│                          ▼                                                  │
│         ┌────────────────┴────────────────┐                                 │
│         ▼                                 ▼                                 │
│  ┌─────────────────┐            ┌─────────────────┐                         │
│  │ Entity Registry │            │  Vector Store   │                         │
│  │ (ID + Summary)  │            │ (Full Content)  │                         │
│  │ ~6K tokens      │            │  Qdrant         │                         │
│  └─────────────────┘            └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 2: PLANNING                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      SynthesisAgent                                    │ │
│  │  Input: Full Entity Registry                                          │ │
│  │  Task: Identify relationships, conflicts, themes                      │ │
│  │  Output: Enriched Registry with cross-references                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                          │                                                  │
│                          ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     OutlineArchitect                                   │ │
│  │  Input: Enriched Registry                                             │ │
│  │  Task: Create high-level arc structure                                │ │
│  │  Output: Arc Plan with entity assignments                             │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                          │                                                  │
│                          ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     CoverageVerifier                                   │ │
│  │  Input: Arc Plan + Full Registry                                      │ │
│  │  Task: Ensure ALL entities are referenced                             │ │
│  │  Output: Complete Plan (iterate until 100% coverage)                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 3: PARALLEL EXPANSION                             │
│                                                                             │
│  Plan distributes to parallel ArcExpander agents:                           │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Arc1Expander│  │ Arc2Expander│  │ Arc3Expander│  │ ArcNExpander│        │
│  │             │  │             │  │             │  │             │        │
│  │ Retrieves:  │  │ Retrieves:  │  │ Retrieves:  │  │ Retrieves:  │        │
│  │ - char_1    │  │ - char_2    │  │ - char_7    │  │ - char_N    │        │
│  │ - char_5    │  │ - char_3    │  │ - char_8    │  │ - ...       │        │
│  │ - loc_2     │  │ - loc_5     │  │ - loc_9     │  │             │        │
│  │ via RAG     │  │ via RAG     │  │ via RAG     │  │ via RAG     │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         ▼                ▼                ▼                ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Iterative Expansion Loop                         │   │
│  │  Each arc expands through iterations:                                │   │
│  │  Iter 1: Subarc breakdown                                            │   │
│  │  Iter 2: Scene placement                                             │   │
│  │  Iter 3: Beat-level detail                                           │   │
│  │  Iter N: Until target depth reached                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 4: CONSOLIDATION                               │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      Consolidator                                      │ │
│  │  Input: All expanded arcs                                             │ │
│  │  Task: Merge, resolve conflicts, ensure continuity                    │ │
│  │  Output: Complete Novel Outline                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Document Ingestion System
**Priority: HIGH | Estimated Complexity: MEDIUM**

#### 1.1 Document Parser Module
**File:** `src/parser/document_parser.py`

```python
# Capabilities:
# - Parse markdown files by header structure
# - Extract entities based on header patterns (##, ###)
# - Preserve hierarchy and relationships
# - Handle various markdown formats
```

**Entity Types to Extract:**
| Source File | Entity Types |
|-------------|--------------|
| Worldbuilding.md | Organizations, Locations, Rules, History, Magic Systems, Technology |
| Characters.md | Characters, Relationships, Abilities, Backstories |
| Scenes.md | Scene Concepts, Plot Points, Key Moments, Conflicts |

#### 1.2 Entity Extractor
**File:** `src/parser/entity_extractor.py`

```python
# Responsibilities:
# - Create unique IDs for each entity
# - Generate 1-2 sentence summaries (for registry)
# - Preserve full content (for vector store)
# - Detect cross-references between entities
```

#### 1.3 Entity Registry
**File:** `src/parser/entity_registry.py`

```python
# Data Structure:
class EntityRegistry:
    characters: List[EntitySummary]      # ID + name + 1-line summary
    locations: List[EntitySummary]
    organizations: List[EntitySummary]
    scenes: List[EntitySummary]
    rules: List[EntitySummary]
    
    def to_context_string(self) -> str:  # ~6K tokens max
    def get_ids_by_type(self, type: str) -> List[str]
    def get_all_ids(self) -> Set[str]
```

#### 1.4 Vector Store Integration
**File:** `src/memory/qdrant_store.py` (enhance existing)

```python
# Collections:
# - entities: Full entity content with embeddings
# - relationships: Cross-references between entities

# Operations:
# - index_entity(id, content, metadata)
# - retrieve_by_ids(ids: List[str]) -> List[Entity]
# - retrieve_similar(query: str, top_k: int) -> List[Entity]
```

---

### Phase 2: Enhanced Agent System
**Priority: HIGH | Estimated Complexity: HIGH**

#### 2.1 New Agent Base Class
**File:** `src/agents/base.py` (enhance)

```python
class RAGEnabledAgent(BaseAgent):
    """Base agent with RAG retrieval capabilities"""
    
    async def retrieve_entities(self, entity_ids: List[str]) -> Dict[str, Entity]:
        """Retrieve full entity content from vector store"""
        
    async def retrieve_related(self, query: str, top_k: int = 5) -> List[Entity]:
        """Retrieve semantically similar entities"""
        
    def build_context(self, registry: EntityRegistry, entity_ids: List[str]) -> str:
        """Build context string from registry + retrieved entities"""
```

#### 2.2 New Agents

| Agent | File | Input | Output |
|-------|------|-------|--------|
| **SynthesisAgent** | `src/agents/synthesis.py` | Entity Registry | Enriched Registry with relationships |
| **OutlineArchitect** | `src/agents/outline_architect.py` | Enriched Registry | Arc structure with entity assignments |
| **CoverageVerifier** | `src/agents/coverage_verifier.py` | Arc Plan + Registry | Verified complete plan |
| **ArcExpander** | `src/agents/arc_expander.py` | Arc + Entity IDs | Expanded arc with subarcs/scenes |
| **Consolidator** | `src/agents/consolidator.py` | All expanded arcs | Unified outline |

#### 2.3 Agent Specifications

**SynthesisAgent:**
```python
# Input: Full entity registry
# Process:
#   1. Identify character-to-character relationships
#   2. Map characters to organizations
#   3. Connect characters to locations
#   4. Identify potential conflicts
#   5. Detect thematic elements
# Output: Registry + relationship graph + conflict map
```

**OutlineArchitect:**
```python
# Input: Enriched registry
# Process:
#   1. Identify main story arcs from scene concepts
#   2. Assign characters to arcs (primary/secondary)
#   3. Assign locations to arcs
#   4. Define arc dependencies/order
#   5. Estimate arc scope (chapters/scenes)
# Output: ArcPlan with entity assignments per arc
```

**CoverageVerifier:**
```python
# Input: Arc Plan + Full Registry
# Process:
#   1. Check which entities are referenced
#   2. Identify unreferenced entities
#   3. For each unreferenced:
#      - Suggest arc assignment, OR
#      - Mark as "background" element
#   4. Iterate until 100% coverage
# Output: Complete verified plan
```

**ArcExpander:**
```python
# Input: Single arc definition + entity IDs
# Process (iterative):
#   Iteration 1: Break into subarcs
#   Iteration 2: Define scenes per subarc
#   Iteration 3: Add scene beats
#   Iteration 4: Add tension curves, hooks
# Uses RAG to retrieve full entity details
# Output: Fully expanded arc
```

**Consolidator:**
```python
# Input: All expanded arcs
# Process:
#   1. Merge arcs into timeline
#   2. Resolve conflicts/inconsistencies
#   3. Ensure character continuity
#   4. Add inter-arc connections
#   5. Generate final outline structure
# Output: Complete NovelOutline
```

---

### Phase 3: Enhanced Orchestrator
**Priority: HIGH | Estimated Complexity: MEDIUM**

#### 3.1 New Orchestrator
**File:** `src/orchestrator/orchestrator_v2.py`

```python
class OutlineOrchestrator:
    """Orchestrates document-to-outline pipeline"""
    
    async def process_documents(
        self,
        worldbuilding_path: Path,
        characters_path: Path,
        scenes_path: Path
    ) -> NovelOutline:
        # Phase 1: Ingest
        registry = await self.ingest_documents(paths)
        
        # Phase 2: Plan
        plan = await self.create_plan(registry)
        
        # Phase 3: Expand (parallel)
        expanded_arcs = await self.expand_arcs_parallel(plan)
        
        # Phase 4: Consolidate
        outline = await self.consolidate(expanded_arcs)
        
        return outline
```

#### 3.2 Parallel Execution
```python
async def expand_arcs_parallel(self, plan: ArcPlan) -> List[ExpandedArc]:
    """Run arc expanders in parallel"""
    tasks = []
    for arc in plan.arcs:
        expander = ArcExpander(
            llm_provider=self.llm_provider,
            vector_store=self.vector_store,
            arc=arc
        )
        tasks.append(expander.expand())
    
    return await asyncio.gather(*tasks)
```

---

### Phase 4: Updated CLI
**Priority: MEDIUM | Estimated Complexity: LOW**

#### 4.1 New CLI Commands
**File:** `src/cli/main.py` (enhance)

```python
@click.command()
@click.option('--worldbuilding', type=click.Path(exists=True), required=True)
@click.option('--characters', type=click.Path(exists=True), required=True)
@click.option('--scenes', type=click.Path(exists=True), required=True)
@click.option('--output', type=click.Path(), default='output/')
@click.option('--depth', type=int, default=3, help='Expansion depth (1-5)')
def generate(worldbuilding, characters, scenes, output, depth):
    """Generate outline from document inputs"""
```

---

### Phase 5: Updated Models
**Priority: MEDIUM | Estimated Complexity: LOW**

#### 5.1 New Pydantic Models
**File:** `src/models/planning.py`

```python
class EntitySummary(BaseModel):
    id: str
    name: str
    type: EntityType  # character, location, organization, scene, rule
    summary: str  # 1-2 sentences
    tags: List[str]
    
class EntityRegistry(BaseModel):
    entities: Dict[str, EntitySummary]
    relationships: List[Relationship]
    
class Arc(BaseModel):
    id: str
    name: str
    description: str
    character_ids: List[str]
    location_ids: List[str]
    organization_ids: List[str]
    scene_ids: List[str]
    dependencies: List[str]  # Arc IDs this depends on
    
class ArcPlan(BaseModel):
    arcs: List[Arc]
    timeline: List[str]  # Ordered arc IDs
    themes: List[str]
    
class ExpandedArc(BaseModel):
    arc_id: str
    subarcs: List[SubArc]
    scenes: List[SceneOutline]
    tension_curve: List[float]
```

---

## File Structure (New/Modified)

```
src/
├── parser/                      # NEW
│   ├── __init__.py
│   ├── document_parser.py       # Markdown parsing
│   ├── entity_extractor.py      # Entity identification
│   └── entity_registry.py       # Registry data structure
│
├── agents/
│   ├── base.py                  # MODIFIED - add RAG capabilities
│   ├── synthesis.py             # NEW - relationship synthesis
│   ├── outline_architect.py     # NEW - arc planning
│   ├── coverage_verifier.py     # NEW - coverage verification
│   ├── arc_expander.py          # NEW - parallel arc expansion
│   ├── consolidator.py          # NEW - merge expanded arcs
│   ├── theme_premise.py         # DEPRECATED (functionality in synthesis)
│   ├── narrative_architect.py   # DEPRECATED (functionality in outline_architect)
│   ├── character.py             # DEPRECATED (input via documents)
│   ├── worldbuilding.py         # DEPRECATED (input via documents)
│   └── scene_dynamics.py        # MODIFIED - used within arc_expander
│
├── orchestrator/
│   ├── orchestrator.py          # KEEP for backward compat
│   └── orchestrator_v2.py       # NEW - document-based orchestration
│
├── memory/
│   ├── vector_store.py          # MODIFIED - enhanced Qdrant integration
│   ├── local_storage.py         # KEEP
│   └── entity_store.py          # NEW - entity-specific storage
│
├── models/
│   ├── planning.py              # NEW - planning models
│   └── ...                      # KEEP existing
│
└── cli/
    └── main.py                  # MODIFIED - new document input mode
```

---

## Implementation Order

### Sprint 1: Foundation (Document Ingestion)
1. [ ] Create `src/parser/` module
2. [ ] Implement `DocumentParser` for markdown
3. [ ] Implement `EntityExtractor`
4. [ ] Implement `EntityRegistry`
5. [ ] Add unit tests for parser

### Sprint 2: RAG Integration
1. [ ] Enhance Qdrant vector store
2. [ ] Implement entity indexing
3. [ ] Implement entity retrieval by ID
4. [ ] Implement similarity search
5. [ ] Add RAG capabilities to base agent

### Sprint 3: Planning Agents
1. [ ] Implement `SynthesisAgent`
2. [ ] Implement `OutlineArchitect`
3. [ ] Implement `CoverageVerifier`
4. [ ] Add planning models
5. [ ] Test planning pipeline

### Sprint 4: Expansion System
1. [ ] Implement `ArcExpander` with iteration
2. [ ] Implement parallel execution
3. [ ] Implement `Consolidator`
4. [ ] Add expansion models
5. [ ] Test expansion pipeline

### Sprint 5: Integration
1. [ ] Create `orchestrator_v2.py`
2. [ ] Update CLI for document input
3. [ ] End-to-end testing
4. [ ] Update documentation
5. [ ] Performance optimization

---

## Configuration Updates

**config/config.yaml additions:**
```yaml
# Document Input
input:
  max_document_size_mb: 10
  supported_formats: [md, markdown]
  
# Entity Processing
entities:
  summary_max_tokens: 50
  registry_max_tokens: 8000
  
# RAG Settings
rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  embedding_model: "nomic-embed-text"  # or OpenAI
  retrieval_top_k: 10
  
# Parallel Processing
parallel:
  max_concurrent_arcs: 4
  expansion_depth: 3
  
# Vector Store
storage:
  qdrant:
    enabled: true
    host: localhost
    port: 6333
    collections:
      entities: multiwriter-entities
      relationships: multiwriter-relationships
```

---

## Success Criteria

1. **Document Parsing:** Successfully parse 100+ page markdown documents
2. **Entity Extraction:** Extract all entities with no omissions
3. **RAG Retrieval:** <500ms retrieval latency per query
4. **Coverage:** 100% of input entities referenced in output
5. **Parallelism:** Arc expansion runs concurrently
6. **Output Quality:** Coherent outline with proper continuity

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM context overflow | Entity registry capped at 8K tokens, RAG for details |
| Missing entities | CoverageVerifier ensures 100% inclusion |
| Inconsistent expansion | Consolidator resolves conflicts |
| RAG retrieval misses | Deterministic ID-based retrieval, not just similarity |
| Parallel conflicts | Each arc expander works on isolated subset |

---

## Next Steps

To begin implementation, switch to Agent mode and I will:
1. Create the parser module structure
2. Implement DocumentParser
3. Implement EntityExtractor
4. Set up Qdrant collections
5. Progress through the sprint plan

Ready to proceed?
