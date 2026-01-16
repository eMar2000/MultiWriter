"""Base agent class with shared memory and LLM interaction"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime

from src.llm import LLMProvider, LLMMessage
from src.memory import StructuredState, VectorStore


class BaseAgent(ABC):
    """Base class for all agents with shared memory access and LLM interaction"""

    def __init__(
        self,
        name: str,
        llm_provider: LLMProvider,
        structured_state: StructuredState,
        vector_store: Optional[VectorStore] = None,
        novel_id: Optional[str] = None
    ):
        """
        Initialize base agent

        Args:
            name: Agent name
            llm_provider: LLM provider instance
            structured_state: Structured state storage (DynamoDB)
            vector_store: Vector store for embeddings (Qdrant)
            novel_id: ID of the novel being processed
        """
        self.name = name
        self.llm_provider = llm_provider
        self.structured_state = structured_state
        self.vector_store = vector_store
        self.novel_id = novel_id or str(uuid.uuid4())

    async def read_from_memory(
        self,
        table_name: str,
        key: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Read data from structured memory"""
        return await self.structured_state.read(table_name, key)

    async def write_to_memory(
        self,
        table_name: str,
        data: Dict[str, Any]
    ) -> bool:
        """Write data to structured memory"""
        # Ensure novel_id is included
        if "novel_id" not in data:
            data["novel_id"] = self.novel_id

        # Add timestamps if not present
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()

        return await self.structured_state.write(table_name, data)

    async def update_memory(
        self,
        table_name: str,
        key: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> bool:
        """Update data in structured memory"""
        updates["updated_at"] = datetime.utcnow().isoformat()
        return await self.structured_state.update(table_name, key, updates)

    async def query_memory(
        self,
        table_name: str,
        key_condition: Dict[str, Any],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query data from structured memory"""
        return await self.structured_state.query(table_name, key_condition, **kwargs)

    async def get_novel_outline(self) -> Optional[Dict[str, Any]]:
        """Get the current novel outline from memory"""
        return await self.read_from_memory(
            "novel-outlines",
            {"id": self.novel_id}
        )

    async def update_novel_outline(self, updates: Dict[str, Any]) -> bool:
        """Update the novel outline in memory"""
        return await self.update_memory(
            "novel-outlines",
            {"id": self.novel_id},
            updates
        )

    async def generate_with_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate response using LLM

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query/request
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            context: Additional context messages

        Returns:
            Generated text response
        """
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        # Add context messages if provided
        if context:
            for ctx in context:
                messages.append(LLMMessage(**ctx))

        response = await self.llm_provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.content

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        output_format: str = "json",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate structured output (JSON) from LLM

        Args:
            system_prompt: System instruction prompt
            user_prompt: User query/request
            output_format: Expected output format (currently only "json")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed structured output
        """
        # Add instruction to output JSON
        format_prompt = ""
        if output_format == "json":
            format_prompt = "\n\nIMPORTANT: Respond with valid JSON only. Do not include any markdown formatting or code blocks. Return pure JSON."

        full_prompt = user_prompt + format_prompt

        response = await self.generate_with_llm(
            system_prompt=system_prompt,
            user_prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Parse JSON response
        # Remove markdown code blocks if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            # Extract JSON from code block
            lines = cleaned_response.split("\n")
            cleaned_response = "\n".join(lines[1:-1])
        if cleaned_response.startswith("```json"):
            lines = cleaned_response.split("\n")
            cleaned_response = "\n".join(lines[1:-1])

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}\nResponse: {cleaned_response}")

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main task

        Args:
            context: Context from previous agents or orchestrator

        Returns:
            Agent output results
        """
        pass

    def get_context_summary(self, context: Dict[str, Any]) -> str:
        """Get a human-readable summary of context for prompts"""
        summary_parts = []

        if "novel_input" in context:
            input_data = context["novel_input"]
            summary_parts.append(f"Novel Premise: {input_data.get('premise', 'N/A')}")
            summary_parts.append(f"Genre: {input_data.get('genre', 'N/A')}")

        if "theme" in context:
            theme_data = context["theme"]
            summary_parts.append(f"Theme: {theme_data.get('theme_question', 'N/A')}")

        if "plot_structure" in context:
            plot_data = context["plot_structure"]
            summary_parts.append(f"Plot Structure: {plot_data.get('structure_type', 'N/A')}")

        if "world" in context:
            world_data = context["world"]
            summary_parts.append(f"World: {len(world_data.get('rules', []))} rules defined")

        if "characters" in context:
            characters_data = context["characters"]
            summary_parts.append(f"Characters: {len(characters_data)} characters defined")

        return "\n".join(summary_parts)
