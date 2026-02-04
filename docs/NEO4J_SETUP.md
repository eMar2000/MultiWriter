# Neo4j GraphDB Setup

## Overview

Neo4j has been added as an optional GraphDB implementation. The system can use either:
- **InMemoryGraphStore** (default, no installation needed)
- **Neo4jGraphStore** (requires Neo4j server)

## Installation

### 1. Install Neo4j Python Driver

```bash
pip install neo4j>=5.15.0
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Install Neo4j Server

#### Option A: Docker (Recommended)
```bash
docker run \
    --name neo4j-multiwriter \
    -p7474:7474 -p7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -d neo4j:latest
```

#### Option B: Local Installation
Download from: https://neo4j.com/download/

Default connection:
- URI: `bolt://localhost:7687`
- Username: `neo4j`
- Password: `password` (change on first login)

## Usage

### In Code

```python
from src.memory import Neo4jGraphStore
from src.models.canon import CanonNode, NodeType

# Initialize Neo4j graph store
graph = Neo4jGraphStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    database="neo4j"
)

# Use like any GraphStore
node = CanonNode(type=NodeType.CHARACTER, properties={"name": "Alice"})
await graph.create_node(node)

# Don't forget to close when done
await graph.close()
```

### In Configuration

Update your `config/config.yaml`:

```yaml
storage:
  graph:
    provider: "neo4j"  # or "in_memory"
    neo4j:
      uri: "bolt://localhost:7687"
      user: "neo4j"
      password: "password"
      database: "neo4j"
```

## Features

The Neo4j implementation supports all GraphStore operations:
- ✅ Node CRUD (create, read, update, delete)
- ✅ Edge CRUD
- ✅ Timeline queries (before/after traversal)
- ✅ Relationship queries (neighbors, related entities)
- ✅ Cycle detection
- ✅ Complex Cypher queries

## Performance Notes

- **In-Memory**: Fast for small graphs, but data is lost on restart
- **Neo4j**: Persistent storage, better for large graphs, supports transactions

## Migration

To migrate from in-memory to Neo4j:
1. Install Neo4j server
2. Update configuration
3. Restart application
4. Data will be synced from outline to Neo4j on next run

## Troubleshooting

### Import Error
If you see `ImportError: neo4j package not installed`:
```bash
pip install neo4j>=5.15.0
```

### Connection Error
If Neo4j connection fails:
1. Check Neo4j server is running: `docker ps` or check service status
2. Verify URI, username, password
3. Check firewall/network settings
4. Try connecting with Neo4j Browser: http://localhost:7474

### Fallback
If Neo4j is not available, the system automatically falls back to InMemoryGraphStore.
