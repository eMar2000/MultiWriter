"""Neo4j implementation of GraphStore"""

import logging
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import json

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
except ImportError:
    AsyncGraphDatabase = None
    AsyncDriver = None
    AsyncSession = None

from src.memory.graph_store import GraphStore
from src.models.canon import (
    CanonNode,
    CanonEdge,
    CanonQuery,
    TimelineQuery,
    NodeType,
    EdgeType
)

logger = logging.getLogger(__name__)


class Neo4jGraphStore(GraphStore):
    """Neo4j graph store implementation"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j driver

        Args:
            uri: Neo4j connection URI (bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
        """
        if AsyncGraphDatabase is None:
            raise ImportError(
                "neo4j package not installed. Install with: pip install neo4j>=5.15.0"
            )

        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver: Optional[AsyncDriver] = AsyncGraphDatabase.driver(
            uri, auth=(user, password)
        )

    async def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            await self.driver.close()

    async def _get_session(self) -> AsyncSession:
        """Get an async session"""
        return self.driver.session(database=self.database)

    async def create_node(self, node: CanonNode) -> CanonNode:
        """Create a new node"""
        async with await self._get_session() as session:
            # Check if node already exists
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=node.id
            )
            existing = await result.single()
            if existing:
                raise ValueError(f"Node {node.id} already exists")

            # Create node with label based on type
            label = node.type.value.upper()
            query = f"""
            CREATE (n:{label} {{
                id: $id,
                type: $type,
                properties: $properties,
                created_at: $created_at,
                updated_at: $updated_at,
                version: $version
            }})
            RETURN n
            """
            result = await session.run(
                query,
                id=node.id,
                type=node.type.value,
                properties=json.dumps(node.properties),
                created_at=node.created_at.isoformat(),
                updated_at=node.updated_at.isoformat(),
                version=node.version
            )
            await session.commit()
            logger.debug(f"Created node {node.id} of type {node.type}")
            return node

    async def get_node(self, node_id: str) -> Optional[CanonNode]:
        """Get a node by ID"""
        async with await self._get_session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=node_id
            )
            record = await result.single()
            if not record:
                return None

            node_data = dict(record["n"])
            return CanonNode(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                properties=json.loads(node_data.get("properties", "{}")),
                created_at=datetime.fromisoformat(node_data["created_at"]),
                updated_at=datetime.fromisoformat(node_data["updated_at"]),
                version=node_data.get("version", 1)
            )

    async def update_node(self, node_id: str, **properties) -> Optional[CanonNode]:
        """Update node properties"""
        node = await self.get_node(node_id)
        if not node:
            return None

        # Update properties
        node.properties.update(properties)
        node.updated_at = datetime.utcnow()
        node.version += 1

        async with await self._get_session() as session:
            query = """
            MATCH (n {id: $id})
            SET n.properties = $properties,
                n.updated_at = $updated_at,
                n.version = $version
            RETURN n
            """
            await session.run(
                query,
                id=node_id,
                properties=json.dumps(node.properties),
                updated_at=node.updated_at.isoformat(),
                version=node.version
            )
            await session.commit()
            return node

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges"""
        async with await self._get_session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) DETACH DELETE n RETURN count(n) as deleted",
                id=node_id
            )
            record = await result.single()
            await session.commit()
            deleted = record["deleted"] if record else 0
            if deleted > 0:
                logger.debug(f"Deleted node {node_id}")
            return deleted > 0

    async def create_edge(self, edge: CanonEdge) -> CanonEdge:
        """Create a new edge"""
        # Validate nodes exist
        source = await self.get_node(edge.source_id)
        target = await self.get_node(edge.target_id)
        if not source:
            raise ValueError(f"Source node {edge.source_id} does not exist")
        if not target:
            raise ValueError(f"Target node {edge.target_id} does not exist")

        async with await self._get_session() as session:
            # Check if edge already exists
            result = await session.run(
                """
                MATCH (a {id: $source_id})-[r]->(b {id: $target_id})
                WHERE type(r) = $edge_type
                RETURN r
                """,
                source_id=edge.source_id,
                target_id=edge.target_id,
                edge_type=edge.type.value.upper()
            )
            existing = await result.single()
            if existing:
                # Update existing edge
                await session.run(
                    """
                    MATCH (a {id: $source_id})-[r]->(b {id: $target_id})
                    WHERE type(r) = $edge_type
                    SET r.properties = $properties
                    """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    edge_type=edge.type.value.upper(),
                    properties=json.dumps(edge.properties)
                )
                await session.commit()
                return edge

            # Create new edge
            edge_type = edge.type.value.upper()
            query = f"""
            MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
            CREATE (a)-[r:{edge_type} {{
                properties: $properties,
                created_at: $created_at
            }}]->(b)
            RETURN r
            """
            await session.run(
                query,
                source_id=edge.source_id,
                target_id=edge.target_id,
                properties=json.dumps(edge.properties),
                created_at=edge.created_at.isoformat()
            )
            await session.commit()
            logger.debug(f"Created edge {edge.type} from {edge.source_id} to {edge.target_id}")
            return edge

    async def get_edges(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None
    ) -> List[CanonEdge]:
        """Get edges matching criteria"""
        async with await self._get_session() as session:
            if source_id and target_id:
                query = """
                MATCH (a {id: $source_id})-[r]->(b {id: $target_id})
                """
                params = {"source_id": source_id, "target_id": target_id}
            elif source_id:
                query = "MATCH (a {id: $source_id})-[r]->(b)"
                params = {"source_id": source_id}
            elif target_id:
                query = "MATCH (a)-[r]->(b {id: $target_id})"
                params = {"target_id": target_id}
            else:
                query = "MATCH (a)-[r]->(b)"
                params = {}

            if edge_type:
                query += f" WHERE type(r) = '{edge_type.value.upper()}'"

            query += " RETURN a.id as source_id, b.id as target_id, type(r) as edge_type, r.properties as properties, r.created_at as created_at"

            result = await session.run(query, **params)
            edges = []
            async for record in result:
                edge_type_str = record["edge_type"].lower()
                try:
                    edge_type_enum = EdgeType(edge_type_str)
                except ValueError:
                    continue  # Skip unknown edge types

                edges.append(CanonEdge(
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    type=edge_type_enum,
                    properties=json.loads(record["properties"] or "{}"),
                    created_at=datetime.fromisoformat(record["created_at"]) if record["created_at"] else datetime.utcnow()
                ))
            return edges

    async def delete_edge(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Delete an edge"""
        async with await self._get_session() as session:
            result = await session.run(
                """
                MATCH (a {id: $source_id})-[r]->(b {id: $target_id})
                WHERE type(r) = $edge_type
                DELETE r
                RETURN count(r) as deleted
                """,
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type.value.upper()
            )
            record = await result.single()
            await session.commit()
            deleted = record["deleted"] if record else 0
            if deleted > 0:
                logger.debug(f"Deleted edge {edge_type} from {source_id} to {target_id}")
            return deleted > 0

    async def query_nodes(self, query: CanonQuery) -> List[CanonNode]:
        """Query nodes with filters"""
        async with await self._get_session() as session:
            cypher = "MATCH (n)"
            params = {}
            conditions = []

            if query.node_id:
                conditions.append("n.id = $node_id")
                params["node_id"] = query.node_id

            if query.node_type:
                label = query.node_type.value.upper()
                cypher = f"MATCH (n:{label})"

            if query.properties_filter:
                for key, value in query.properties_filter.items():
                    # Properties are stored as JSON string, so we need to parse
                    # This is a simplified approach - in production, you might want to index properties
                    conditions.append(f"n.properties CONTAINS $prop_{key}")
                    params[f"prop_{key}"] = json.dumps({key: value})

            if conditions:
                cypher += " WHERE " + " AND ".join(conditions)

            cypher += f" RETURN n LIMIT {query.limit}"

            result = await session.run(cypher, **params)
            nodes = []
            async for record in result:
                node_data = dict(record["n"])
                try:
                    node = CanonNode(
                        id=node_data["id"],
                        type=NodeType(node_data["type"]),
                        properties=json.loads(node_data.get("properties", "{}")),
                        created_at=datetime.fromisoformat(node_data["created_at"]),
                        updated_at=datetime.fromisoformat(node_data["updated_at"]),
                        version=node_data.get("version", 1)
                    )
                    nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse node: {e}")
                    continue
            return nodes

    async def query_timeline(self, query: TimelineQuery) -> List[CanonNode]:
        """Query timeline (before/after traversal)"""
        edge_types = query.edge_types or [EdgeType.BEFORE, EdgeType.AFTER]
        edge_type_names = [et.value.upper() for et in edge_types]

        async with await self._get_session() as session:
            # Build Cypher query for traversal
            if query.direction == "forward":
                # Follow AFTER edges forward
                cypher = f"""
                MATCH path = (start {{id: $start_id}})-[:{'|:'.join(edge_type_names)}*1..{query.max_depth}]->(end)
                WHERE ALL(r in relationships(path) WHERE type(r) IN {edge_type_names})
                RETURN DISTINCT end
                """
            elif query.direction == "backward":
                # Follow BEFORE edges backward
                cypher = f"""
                MATCH path = (start {{id: $start_id}})<-[:{'|:'.join(edge_type_names)}*1..{query.max_depth}]-(end)
                WHERE ALL(r in relationships(path) WHERE type(r) IN {edge_type_names})
                RETURN DISTINCT end
                """
            else:  # both
                cypher = f"""
                MATCH path = (start {{id: $start_id}})-[:{'|:'.join(edge_type_names)}*1..{query.max_depth}]-(end)
                WHERE ALL(r in relationships(path) WHERE type(r) IN {edge_type_names})
                RETURN DISTINCT end
                """

            result = await session.run(cypher, start_id=query.start_node_id)
            nodes = []
            visited = set()
            async for record in result:
                node_data = dict(record["end"])
                node_id = node_data["id"]
                if node_id in visited:
                    continue
                visited.add(node_id)

                try:
                    node = CanonNode(
                        id=node_data["id"],
                        type=NodeType(node_data["type"]),
                        properties=json.loads(node_data.get("properties", "{}")),
                        created_at=datetime.fromisoformat(node_data["created_at"]),
                        updated_at=datetime.fromisoformat(node_data["updated_at"]),
                        version=node_data.get("version", 1)
                    )
                    nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse timeline node: {e}")
                    continue
            return nodes

    async def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[EdgeType]] = None,
        direction: str = "both"
    ) -> List[CanonNode]:
        """Get neighboring nodes"""
        async with await self._get_session() as session:
            if direction == "out":
                cypher = "MATCH (n {id: $node_id})-[r]->(neighbor)"
            elif direction == "in":
                cypher = "MATCH (n {id: $node_id})<-[r]-(neighbor)"
            else:  # both
                cypher = "MATCH (n {id: $node_id})-[r]-(neighbor)"

            if edge_types:
                edge_type_names = [et.value.upper() for et in edge_types]
                cypher += f" WHERE type(r) IN {edge_type_names}"

            cypher += " RETURN DISTINCT neighbor"

            result = await session.run(cypher, node_id=node_id)
            nodes = []
            async for record in result:
                node_data = dict(record["neighbor"])
                try:
                    node = CanonNode(
                        id=node_data["id"],
                        type=NodeType(node_data["type"]),
                        properties=json.loads(node_data.get("properties", "{}")),
                        created_at=datetime.fromisoformat(node_data["created_at"]),
                        updated_at=datetime.fromisoformat(node_data["updated_at"]),
                        version=node_data.get("version", 1)
                    )
                    nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse neighbor node: {e}")
                    continue
            return nodes

    async def get_related_entities(
        self,
        node_id: str,
        max_depth: int = 2,
        edge_types: Optional[List[EdgeType]] = None
    ) -> List[CanonNode]:
        """Get related entities within max_depth hops"""
        async with await self._get_session() as session:
            if edge_types:
                edge_type_names = [et.value.upper() for et in edge_types]
                cypher = f"""
                MATCH path = (start {{id: $node_id}})-[:{'|:'.join(edge_type_names)}*1..{max_depth}]-(end)
                WHERE ALL(r in relationships(path) WHERE type(r) IN {edge_type_names})
                AND start <> end
                RETURN DISTINCT end
                """
            else:
                cypher = f"""
                MATCH path = (start {{id: $node_id}})-[*1..{max_depth}]-(end)
                WHERE start <> end
                RETURN DISTINCT end
                """

            result = await session.run(cypher, node_id=node_id)
            nodes = []
            visited = set()
            async for record in result:
                node_data = dict(record["end"])
                node_id_found = node_data["id"]
                if node_id_found in visited:
                    continue
                visited.add(node_id_found)

                try:
                    node = CanonNode(
                        id=node_data["id"],
                        type=NodeType(node_data["type"]),
                        properties=json.loads(node_data.get("properties", "{}")),
                        created_at=datetime.fromisoformat(node_data["created_at"]),
                        updated_at=datetime.fromisoformat(node_data["updated_at"]),
                        version=node_data.get("version", 1)
                    )
                    nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse related node: {e}")
                    continue
            return nodes

    async def check_cycle(self, start_node_id: str, edge_types: Optional[List[EdgeType]] = None) -> bool:
        """Check if there's a cycle in the graph"""
        async with await self._get_session() as session:
            if edge_types:
                edge_type_names = [et.value.upper() for et in edge_types]
                cypher = f"""
                MATCH path = (start {{id: $start_id}})-[:{'|:'.join(edge_type_names)}*]->(start)
                WHERE ALL(r in relationships(path) WHERE type(r) IN {edge_type_names})
                RETURN path LIMIT 1
                """
            else:
                cypher = """
                MATCH path = (start {id: $start_id})-[*]->(start)
                RETURN path LIMIT 1
                """

            result = await session.run(cypher, start_id=start_node_id)
            record = await result.single()
            return record is not None

    async def clear(self):
        """Clear all nodes and edges"""
        async with await self._get_session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
            await session.commit()
            logger.debug("Cleared Neo4j graph store")
