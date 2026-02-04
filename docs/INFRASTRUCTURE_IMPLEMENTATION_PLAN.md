# Infrastructure Implementation Plan

## Overview

This document outlines the implementation plan for critical infrastructure components that are currently missing but required for the full multi-agent storytelling system. These components form the foundation that agents depend on.

## Current State Analysis

### ✅ What Exists
- **VectorStore**: Qdrant implementation with basic semantic search
- **Basic RAG**: Entity indexing and vector retrieval
- **StructuredState**: Local file and DynamoDB implementations
- **ObjectStore**: Local file and S3 implementations
- **Linear Orchestrator**: Document-driven pipeline (5 phases)

### ❌ What's Missing (Critical)
1. **GraphDB (Canon Store)** - No implementation
2. **Continuity Validation Service** - No validation layer
3. **Hybrid RAG Retrieval** - Vector-only, missing graph enrichment
4. **Iterative Planning Loop** - Linear pipeline only
5. **Outline ↔ Canon Sync Manager** - No sync mechanism

## Implementation Phases

### Phase 0: Foundation Infrastructure (Priority 1)

#### 1. GraphDB Interface & In-Memory Implementation
**Why First**: All other components depend on canonical truth storage

**Components**:
- Abstract `GraphStore` interface
- In-memory implementation (using NetworkX or custom graph)
- Node types: Character, Location, Event, Thread, Motif, Rule, Scene, Chapter, Arc
- Edge types: `appears_in`, `before/after`, `foreshadows`, `contradicts`, `wants/fears/believes/knows`, `located_in`, `travels_to`, `allies_with/opposes`
- Basic CRUD operations
- Timeline query support (before/after traversal)
- Relationship queries

**Files to Create**:
- `src/memory/graph_store.py` - Abstract interface
- `src/memory/in_memory_graph.py` - In-memory implementation
- `src/schemas/canon.py` - Canon node/edge schemas

**Dependencies**: None (foundation)

---

#### 2. Continuity Validation Service
**Why Second**: Required before any canon writes can happen safely

**Components**:
- `ContinuityValidationService` class
- Synchronous validation (blocking)
- Validation rules:
  - Contradiction detection (character in two places, dead character acting)
  - Timeline validation (before/after DAG, travel time feasibility)
  - Referential integrity (no dangling references)
  - Business rules (genre-specific constraints)
- Returns `ValidationResult` with violations, warnings, auto-fixes
- Caching for performance (TTL-based)

**Files to Create**:
- `src/validation/__init__.py`
- `src/validation/continuity.py` - Main validation service
- `src/validation/rules.py` - Validation rule definitions
- `src/schemas/validation.py` - Validation result schemas

**Dependencies**: GraphDB (Phase 0.1)

---

#### 3. Hybrid RAG Retrieval Layer
**Why Third**: Improves agent context quality significantly

**Components**:
- `HybridRAGRetrieval` service
- Combines:
  1. Vector Store (semantic match) ✅
  2. GraphDB queries (canon facts, relationships)
  3. Blob Storage (full content chunks)
- Enriches vector results with canonical facts
- Typed chunk classification
- Context building with canon metadata

**Files to Create**:
- `src/memory/rag_retrieval.py` - Hybrid retrieval service
- Update `src/agents/base.py` to use hybrid retrieval

**Dependencies**: GraphDB (Phase 0.1), VectorStore ✅, ObjectStore ✅

---

#### 4. Outline ↔ Canon Sync Manager
**Why Fourth**: Prevents divergence between outline and canon

**Components**:
- `CanonSyncManager` class
- Bidirectional sync:
  - Outline changes → Canon Store (via validation)
  - Canon changes → Outline updates
- Change log generation
- Transaction support
- Conflict resolution

**Files to Create**:
- `src/orchestrator/canon_sync.py` - Sync manager
- Update `src/orchestrator/orchestrator_v2.py` to use sync manager

**Dependencies**: GraphDB (Phase 0.1), Validation Service (Phase 0.2)

---

### Phase 1: Iterative Planning Loop (Priority 2)

#### 5. Central Manager (Iterative Orchestrator)
**Why Fifth**: Enables quality improvement through iteration

**Components**:
- `CentralManager` class
- Iterative planning loop:
  1. Analyze current state
  2. Decide next actions
  3. Invoke agents (Timeline, Pacing, Theme, etc.)
  4. Validate results
  5. IF issues: iterate back
  6. IF complete: proceed
- Agent coordination
- Dependency management
- Validation checkpoints
- Revision logic

**Files to Create**:
- `src/orchestrator/central_manager.py` - Central orchestrator
- `src/orchestrator/planning_loop.py` - Iterative loop logic
- Refactor `src/orchestrator/orchestrator_v2.py` to use iterative loop

**Dependencies**: All Phase 0 components

---

## Implementation Details

### GraphDB Schema

#### Node Types
```python
class CanonNode(BaseModel):
    id: str  # UUID
    type: NodeType  # Character, Location, Event, etc.
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int
```

#### Edge Types
```python
class CanonEdge(BaseModel):
    source_id: str
    target_id: str
    type: EdgeType  # appears_in, before, foreshadows, etc.
    properties: Dict[str, Any]
    created_at: datetime
```

### Validation Rules

1. **Contradiction Checks**:
   - Character cannot be in two places at same time
   - Character cannot act after death
   - Object cannot be in multiple locations
   - Event cannot violate before/after constraints

2. **Timeline Checks**:
   - before/after edges form valid DAG (no cycles)
   - Travel time between locations feasible
   - Age progression consistent
   - Event durations realistic

3. **Referential Integrity**:
   - All entity references exist in Canon Store
   - Deleted entities have no active incoming edges
   - Orphaned entities flagged

### Integration Points

All new components should:
- Follow existing patterns (async/await, logging)
- Use Pydantic schemas for type safety
- Support both local and cloud storage (via interfaces)
- Include comprehensive error handling
- Have unit tests

---

## Testing Strategy

1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: Components working together
3. **Compilation Tests**: Ensure no import/syntax errors
4. **Validation Tests**: Verify validation rules work correctly
5. **Sync Tests**: Ensure outline ↔ canon sync works bidirectionally

---

## Success Criteria

- [ ] GraphDB can store and query nodes/edges
- [ ] Validation service catches contradictions
- [ ] Hybrid RAG enriches vector results with canon facts
- [ ] Sync manager prevents outline/canon divergence
- [ ] Iterative loop enables quality improvement
- [ ] All code compiles without errors
- [ ] Existing tests still pass
- [ ] New components integrate with existing orchestrator

---

## Migration Path

1. **Phase 0**: Implement foundation (GraphDB, Validation, RAG, Sync)
2. **Integration**: Update existing orchestrator to use new components
3. **Phase 1**: Implement iterative loop
4. **Testing**: Comprehensive testing of all components
5. **Documentation**: Update docs with new architecture

---

## Notes

- Start with in-memory GraphDB (can upgrade to Neo4j/Neptune later)
- Validation service should be fast (<200ms for typical queries)
- Hybrid RAG should maintain backward compatibility with existing vector-only usage
- Sync manager should be transactional (all-or-nothing)
- Iterative loop should have max iteration limits to prevent infinite loops

---

## Timeline Estimate

- **Phase 0.1 (GraphDB)**: 2-3 hours
- **Phase 0.2 (Validation)**: 1-2 hours
- **Phase 0.3 (Hybrid RAG)**: 1-2 hours
- **Phase 0.4 (Sync Manager)**: 1-2 hours
- **Phase 1 (Iterative Loop)**: 2-3 hours
- **Testing & Integration**: 1-2 hours

**Total**: ~8-14 hours of focused implementation
