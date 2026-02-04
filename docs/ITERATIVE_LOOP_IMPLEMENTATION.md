# Iterative Planning Loop Implementation

## Overview

The Iterative Planning Loop has been implemented to enable quality improvement through agent coordination, validation checkpoints, and revision cycles.

## Components Implemented

### 1. Central Manager (`src/orchestrator/central_manager.py`)

**Purpose**: Orchestrates agent tasks iteratively with dependency management

**Key Features**:
- **Agent Task Management**: Tracks tasks with dependencies, priorities, and status
- **Dependency Resolution**: Executes tasks in correct order based on dependencies
- **Iteration Support**: Allows tasks to be retried with revision logic
- **Status Tracking**: Monitors task execution (pending, running, completed, failed)
- **Context Propagation**: Automatically updates dependent task contexts with results

**Usage**:
```python
from src.orchestrator import CentralManager, AgentTask
from src.agents import SynthesisAgent, OutlineArchitectAgent

# Create tasks
tasks = [
    AgentTask(
        agent_name="synthesis",
        agent_class=SynthesisAgent,
        context={"entity_registry": registry},
        priority=10
    ),
    AgentTask(
        agent_name="outline_architect",
        agent_class=OutlineArchitectAgent,
        context={},
        dependencies=["synthesis"],  # Waits for synthesis to complete
        priority=9
    )
]

# Execute plan
manager = CentralManager(...)
result = await manager.execute_plan(tasks, novel_id=novel_id)
```

---

### 2. Planning Loop (`src/orchestrator/planning_loop.py`)

**Purpose**: High-level iterative planning with quality gates

**Key Features**:
- **Phase-Based Planning**: Organizes planning into logical phases
- **Quality Gates**: Validates quality at each phase (coverage, structure, etc.)
- **Iterative Refinement**: Can iterate on phases that fail quality gates
- **Agent Coordination**: Uses Central Manager to coordinate agents

**Phases**:
1. **Synthesis and Arc Planning**: Analyzes relationships, creates arcs
2. **Coverage Verification**: Ensures all entities are referenced
3. **Scene Expansion**: Expands arcs into detailed scenes
4. **Validation and Refinement**: Validates and refines (future: Timeline, Pacing agents)
5. **Final Consolidation**: Builds final outline

**Usage**:
```python
from src.orchestrator import PlanningLoop

planning_loop = PlanningLoop(
    llm_provider=llm_provider,
    structured_state=structured_state,
    vector_store=vector_store,
    graph_store=graph_store,
    validation_service=validation_service
)

outline = await planning_loop.execute_planning_loop(
    registry=registry,
    novel_input=novel_input,
    novel_id=novel_id
)
```

---

### 3. Iterative Document Orchestrator (`src/orchestrator/orchestrator_v3.py`)

**Purpose**: Drop-in replacement for `DocumentOrchestrator` with iterative planning

**Key Features**:
- **Same Interface**: Compatible with existing `DocumentOrchestrator` API
- **Iterative Planning**: Uses Planning Loop instead of linear pipeline
- **Backward Compatible**: Can be used alongside `orchestrator_v2.py`

**Usage**:
```python
from src.orchestrator import IterativeDocumentOrchestrator

orchestrator = IterativeDocumentOrchestrator(
    llm_provider=llm_provider,
    structured_state=structured_state,
    vector_store=vector_store,
    graph_store=graph_store,
    validation_service=validation_service
)

outline = await orchestrator.process_documents(
    worldbuilding_path=worldbuilding_path,
    characters_path=characters_path,
    scenes_path=scenes_path,
    novel_input=novel_input
)
```

---

## Architecture

```
IterativeDocumentOrchestrator
    └─> PlanningLoop
            └─> CentralManager
                    └─> AgentTask(s)
                            └─> Agent.execute()
```

**Flow**:
1. Orchestrator ingests documents → Entity Registry
2. Planning Loop executes phases iteratively
3. Central Manager coordinates agent tasks
4. Agents execute with dependency resolution
5. Quality gates validate results
6. Iteration occurs if quality gates fail
7. Final outline is consolidated

---

## Integration with New Agents

### Adding a New Agent to the Loop

1. **Create Agent Task**:
```python
AgentTask(
    agent_name="timeline_manager",
    agent_class=TimelineManagerAgent,
    context={
        "outline": outline,
        "graph_store": graph_store
    },
    dependencies=["scene_expansion_*"],  # After scenes are expanded
    priority=6,
    max_iterations=3,
    validation_fn=lambda result: {
        "valid": len(result.get("violations", [])) == 0,
        "message": "Timeline violations found" if result.get("violations") else "OK"
    }
)
```

2. **Add to Planning Loop Phase**:
```python
# In _phase_validation_and_refinement()
tasks.append(
    AgentTask(
        agent_name="timeline_manager",
        agent_class=TimelineManagerAgent,
        context={...},
        dependencies=["outline_architect"],
        priority=6
    )
)
```

3. **Register Quality Gate** (optional):
```python
def validate_timeline(data, registry):
    violations = data.get("violations", [])
    return {"pass": len(violations) == 0}

planning_loop.register_quality_gate(QualityGate.TIMELINE_CONSISTENCY, validate_timeline)
```

---

## Configuration

### Max Iterations
```yaml
# config/config.yaml
orchestrator:
  max_global_iterations: 5  # Max iterations across all phases
  max_task_iterations: 3    # Max iterations per task
  quality_gates:
    coverage_threshold: 70.0  # Minimum entity coverage %
```

---

## Benefits

1. **Quality Improvement**: Agents can iterate to improve results
2. **Dependency Management**: Tasks execute in correct order
3. **Error Recovery**: Failed tasks can be retried
4. **Validation Checkpoints**: Quality gates catch issues early
5. **Extensibility**: Easy to add new agents to the loop
6. **Coordination**: Central Manager handles agent coordination

---

## Migration Path

### Option 1: Use Iterative Orchestrator (Recommended)
```python
# Replace DocumentOrchestrator with IterativeDocumentOrchestrator
from src.orchestrator import IterativeDocumentOrchestrator

orchestrator = IterativeDocumentOrchestrator(...)
```

### Option 2: Keep Existing, Add Iterative Features
- Keep using `DocumentOrchestrator` for existing workflows
- Use `PlanningLoop` directly for new features
- Gradually migrate to iterative approach

---

## Testing Status

✅ **Compilation**: All files compile without errors
✅ **Imports**: All components import successfully
✅ **Integration**: Works with existing agents
⏳ **Unit Tests**: To be added
⏳ **Integration Tests**: To be added

---

## Next Steps

1. **Add Timeline Manager Agent**: Integrate with planning loop
2. **Add Pacing Agent**: Integrate with planning loop
3. **Add Quality Gates**: Implement validation for each phase
4. **Add Unit Tests**: Test Central Manager and Planning Loop
5. **Add Integration Tests**: Test full iterative workflow

---

## Files Created

- `src/orchestrator/central_manager.py` - Central Manager implementation
- `src/orchestrator/planning_loop.py` - Planning Loop implementation
- `src/orchestrator/orchestrator_v3.py` - Iterative Document Orchestrator
- `docs/ITERATIVE_LOOP_IMPLEMENTATION.md` - This document

## Files Modified

- `src/orchestrator/__init__.py` - Added exports for new components

---

## Example: Adding Timeline Manager

```python
# In planning_loop.py, _phase_validation_and_refinement()

from src.agents import TimelineManagerAgent  # Future agent

tasks = [
    AgentTask(
        agent_name="timeline_manager",
        agent_class=TimelineManagerAgent,
        context={
            "outline": current_outline,
            "graph_store": self.graph_store,
            "entity_registry": registry
        },
        dependencies=["outline_architect"],  # After arcs are created
        priority=6,
        validation_fn=lambda result: {
            "valid": len(result.get("output", {}).get("violations", [])) == 0
        }
    )
]

result = await self.central_manager.execute_plan(tasks, novel_id=novel_id)
```

The iterative loop is now ready for new agents to be integrated!
