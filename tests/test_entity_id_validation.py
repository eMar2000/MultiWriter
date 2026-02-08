"""Tests for entity ID validation"""

import pytest
import uuid
import re

from src.orchestrator import CentralManager
from src.models import EntityRegistry, EntitySummary, EntityType
from unittest.mock import AsyncMock, MagicMock


class TestEntityIDValidation:
    """Test entity ID validation in central manager"""

    @pytest.fixture
    def sample_registry(self):
        """Create sample entity registry with known IDs"""
        registry = EntityRegistry()

        char_id = str(uuid.uuid4())
        loc_id = str(uuid.uuid4())

        char = EntitySummary(
            id=char_id,
            name="Alice",
            entity_type=EntityType.CHARACTER,
            summary="Protagonist"
        )

        loc = EntitySummary(
            id=loc_id,
            name="The Pit",
            entity_type=EntityType.LOCATION,
            summary="Arena"
        )

        registry.add(char)
        registry.add(loc)

        return registry, char_id, loc_id

    def test_validate_valid_entity_ids(self, sample_registry):
        """Test validation passes for valid entity IDs"""
        registry, char_id, loc_id = sample_registry

        central_manager = CentralManager(
            llm_provider=MagicMock(),
            structured_state=MagicMock()
        )

        # Result with valid IDs
        result = {
            "output": {
                "scenes": [
                    {
                        "pov_character": char_id,
                        "characters_present": [char_id],
                        "location_id": loc_id
                    }
                ]
            }
        }

        validation = central_manager._validate_entity_ids(result, registry)
        assert validation["valid"] is True

    def test_validate_detects_placeholder_ids(self, sample_registry):
        """Test validation detects placeholder IDs"""
        registry, _, _ = sample_registry

        central_manager = CentralManager(
            llm_provider=MagicMock(),
            structured_state=MagicMock()
        )

        # Result with placeholder IDs
        result = {
            "output": {
                "scenes": [
                    {
                        "pov_character": "char_id1",
                        "characters_present": ["char_id1", "char_id2"],
                        "location_id": "loc_id1"
                    }
                ]
            }
        }

        validation = central_manager._validate_entity_ids(result, registry)
        assert validation["valid"] is False
        assert "invalid_ids" in validation
        assert len(validation["invalid_ids"]) > 0

    def test_validate_detects_nonexistent_ids(self, sample_registry):
        """Test validation detects non-existent UUIDs"""
        registry, _, _ = sample_registry

        central_manager = CentralManager(
            llm_provider=MagicMock(),
            structured_state=MagicMock()
        )

        # Result with non-existent but valid UUID
        fake_id = str(uuid.uuid4())
        result = {
            "output": {
                "scenes": [
                    {
                        "pov_character": fake_id,
                        "location_id": fake_id
                    }
                ]
            }
        }

        validation = central_manager._validate_entity_ids(result, registry)
        assert validation["valid"] is False
        assert fake_id in validation["invalid_ids"]

    def test_validate_empty_result(self, sample_registry):
        """Test validation handles empty result"""
        registry, _, _ = sample_registry

        central_manager = CentralManager(
            llm_provider=MagicMock(),
            structured_state=MagicMock()
        )

        result = {"output": {}}

        validation = central_manager._validate_entity_ids(result, registry)
        assert validation["valid"] is True

    @pytest.mark.asyncio
    async def test_validation_in_execute_task(self, sample_registry):
        """Test that validation is called during task execution"""
        registry, char_id, _ = sample_registry

        from src.agents.base import BaseAgent
        from src.orchestrator.central_manager import AgentTask

        # Mock agent that returns invalid IDs
        class MockAgent(BaseAgent):
            async def execute(self, context):
                return {
                    "output": {
                        "scenes": [{
                            "pov_character": "char_id1",  # Invalid placeholder
                            "characters_present": ["char_id1"]
                        }]
                    }
                }

        central_manager = CentralManager(
            llm_provider=MagicMock(),
            structured_state=MagicMock()
        )

        task = AgentTask(
            agent_name="test_agent",
            agent_class=MockAgent,
            context={"entity_registry": registry}
        )

        await central_manager._execute_task(task, iteration=1)

        # Task should fail validation
        assert task.status.value == "failed"
        assert len(task.errors) > 0
        assert any("entity" in error.lower() or "id" in error.lower() for error in task.errors)


class TestEntityIDPatterns:
    """Test entity ID pattern recognition"""

    def test_uuid_pattern_recognition(self):
        """Test UUID pattern is correctly identified"""
        uuid_pattern = r'[a-f0-9\-]{36}'

        valid_uuid = str(uuid.uuid4())
        assert re.search(uuid_pattern, valid_uuid)

        invalid_ids = ["char_id1", "loc_1", "character_id_123"]
        for invalid_id in invalid_ids:
            # These should NOT match UUID pattern
            match = re.fullmatch(uuid_pattern, invalid_id)
            assert match is None

    def test_placeholder_pattern_recognition(self):
        """Test placeholder patterns are correctly identified"""
        placeholder_pattern = r'(char_id|loc_id|character_id|location_id)\d+'

        invalid_ids = [
            "char_id1",
            "loc_id2",
            "character_id123",
            "location_id456"
        ]

        for invalid_id in invalid_ids:
            assert re.match(placeholder_pattern, invalid_id, re.IGNORECASE)

        # Valid UUID should not match
        valid_uuid = str(uuid.uuid4())
        assert not re.match(placeholder_pattern, valid_uuid, re.IGNORECASE)

    def test_id_extraction_from_json(self):
        """Test extraction of entity IDs from JSON-like strings"""
        char_id = str(uuid.uuid4())
        loc_id = str(uuid.uuid4())

        json_str = f'{{"character_ids": ["{char_id}"], "location_id": "{loc_id}"}}'

        # Extract UUIDs
        uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
        found_ids = re.findall(uuid_pattern, json_str)

        assert len(found_ids) == 2
        assert char_id in found_ids
        assert loc_id in found_ids
