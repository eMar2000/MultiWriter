"""Base agent class with shared memory and LLM interaction"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Awaitable, TYPE_CHECKING
import json
import uuid
from datetime import datetime

if TYPE_CHECKING:
    from src.models import EntityRegistry

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

    def _fix_json(self, text: str) -> str:
        """
        Attempt to fix common JSON issues from LLM output.

        Args:
            text: JSON string that may have issues

        Returns:
            Fixed JSON string
        """
        import re

        # Remove trailing commas before } or ]
        text = re.sub(r',(\s*[}\]])', r'\1', text)

        # Try to close unclosed brackets if JSON is truncated
        # Count open brackets
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')

        # If we have unclosed brackets, try to close them
        if open_braces > 0 or open_brackets > 0:
            # Find the last complete value and truncate there
            # Then add closing brackets

            # Remove any trailing incomplete content after last complete value
            # Look for patterns like: "key": ... or "key": "incomplete
            text = re.sub(r',\s*"[^"]*":\s*[^,}\]]*$', '', text)
            text = re.sub(r',\s*$', '', text)

            # Add missing closing brackets
            text = text.rstrip()
            for _ in range(open_brackets):
                text += ']'
            for _ in range(open_braces):
                text += '}'

        return text

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text that may contain extra content before/after.

        Args:
            text: Raw text that may contain JSON

        Returns:
            Extracted JSON string
        """
        text = text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Find the start of JSON (first { or [)
        json_start = -1
        for i, char in enumerate(text):
            if char in '{[':
                json_start = i
                break

        if json_start == -1:
            return text  # No JSON found, return as-is

        # Find the matching closing bracket
        start_char = text[json_start]
        end_char = '}' if start_char == '{' else ']'

        depth = 0
        in_string = False
        escape_next = False
        json_end = -1

        for i in range(json_start, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == start_char:
                depth += 1
            elif char == end_char:
                depth -= 1
                if depth == 0:
                    json_end = i + 1
                    break

        if json_end > json_start:
            return text[json_start:json_end]

        # If we couldn't find a matching bracket, the JSON might be truncated
        # Extract what we have and try to fix it
        extracted = text[json_start:] if json_start >= 0 else text
        return self._fix_json(extracted)

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
            format_prompt = "\n\nIMPORTANT: Respond with valid JSON only. Do not include any text before or after the JSON. Do not include any markdown formatting or code blocks. Return pure JSON."

        full_prompt = user_prompt + format_prompt

        # Try up to 2 times in case of JSON parsing errors
        last_error = None
        for attempt in range(2):
            response = await self.generate_with_llm(
                system_prompt=system_prompt,
                user_prompt=full_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract and parse JSON response
            cleaned_response = self._extract_json(response)

            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                last_error = e
                if attempt == 0:
                    # First attempt failed, try again with a more explicit prompt
                    full_prompt = user_prompt + "\n\nCRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown, no truncation. Complete the entire JSON structure."
                    continue
                else:
                    raise ValueError(f"Failed to parse JSON response: {str(last_error)}\nResponse: {cleaned_response[:500]}...")

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

    async def retrieve_entities(
        self,
        entity_ids: List[str],
        collection_name: str = None
    ) -> Dict[str, Dict[str, Any]]:
        """Retrieve full entity content from vector store by IDs"""
        if not self.vector_store:
            return {}

        collection = collection_name or self.vector_store.collection_name
        results = await self.vector_store.retrieve_by_ids(collection, entity_ids)
        return {r["id"]: r["payload"] for r in results}

    async def retrieve_related_entities(
        self,
        query: str,
        top_k: int = 5,
        entity_type: Optional[str] = None,
        collection_name: str = None,
        embedding_fn: Optional[Callable[[str], Awaitable[List[float]]]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve semantically related entities"""
        if not self.vector_store:
            return []

        # Use provided embedding function or try to get from LLM provider
        if embedding_fn is None:
            if hasattr(self.llm_provider, 'get_embedding'):
                async def get_embedding(text: str) -> List[float]:
                    return await self.llm_provider.get_embedding(text)
                embedding_fn = get_embedding
            else:
                raise ValueError("No embedding function available. Provide embedding_fn or use LLM provider with get_embedding method.")

        collection = collection_name or self.vector_store.collection_name
        return await self.vector_store.retrieve_related(
            collection_name=collection,
            query=query,
            embedding_fn=embedding_fn,
            top_k=top_k,
            entity_type=entity_type
        )

    def build_rag_context(
        self,
        registry: 'EntityRegistry',
        entity_ids: List[str],
        retrieved_content: Dict[str, Dict[str, Any]]
    ) -> str:
        """Build context string combining registry summaries and retrieved full content"""
        context_parts = []

        # Add registry overview
        context_parts.append("=== ENTITY REGISTRY (Summary) ===")
        context_parts.append(registry.to_context_string(max_tokens=2000))

        # Add full content for requested entities
        context_parts.append("\n=== RELEVANT ENTITY DETAILS ===")
        for entity_id in entity_ids:
            if entity_id in retrieved_content:
                content = retrieved_content[entity_id]
                context_parts.append(f"\n[{entity_id}] {content.get('name', 'Unknown')}:")
                context_parts.append(content.get('content', content.get('summary', '')))

        return "\n".join(context_parts)
