"""Ollama LLM client implementation"""

import aiohttp
from typing import List, Optional, Dict, Any, AsyncGenerator
from .provider import LLMProvider, LLMMessage, LLMResponse


class OllamaClient(LLMProvider):
    """Ollama client implementation"""

    def __init__(
        self,
        model: str = "llama3.1:70b",
        base_url: str = "http://localhost:11434",
        timeout: int = 300
    ):
        """
        Initialize Ollama client

        Args:
            model: Model name (e.g., "llama3.1:70b")
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _convert_messages(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """Convert LLMMessages to Ollama format"""
        # Ollama uses a simpler format
        system_prompt = ""
        conversation = []

        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            elif msg.role == "user":
                conversation.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                conversation.append({"role": "assistant", "content": msg.content})

        return {
            "model": self.model,
            "messages": conversation,
            "stream": False,
            "options": {
                "temperature": 0.7,
            }
        }

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from Ollama"""
        session = await self._get_session()

        # Convert messages
        system_prompt_parts = [m.content for m in messages if m.role == "system"]
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]

        # Build conversation
        conversation = []
        for msg in messages:
            if msg.role != "system":
                conversation.append({"role": msg.role, "content": msg.content})

        # Combine system prompts
        system_content = "\n".join(system_prompt_parts) if system_prompt_parts else ""
        if system_content:
            # Prepend system content to first user message if no system role
            if conversation and conversation[0]["role"] == "user":
                conversation[0]["content"] = system_content + "\n\n" + conversation[0]["content"]
            else:
                # Insert as first user message
                conversation.insert(0, {"role": "user", "content": system_content})

        payload = {
            "model": self.model,
            "messages": conversation,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        # Merge additional options
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])

        try:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()

                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=self.model,
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    },
                    metadata={
                        "done": data.get("done", True),
                        "total_duration": data.get("total_duration", 0),
                    }
                )
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}") from e

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Ollama"""
        session = await self._get_session()

        # Convert messages (same logic as generate)
        system_prompt_parts = [m.content for m in messages if m.role == "system"]
        conversation = []

        for msg in messages:
            if msg.role != "system":
                conversation.append({"role": msg.role, "content": msg.content})

        system_content = "\n".join(system_prompt_parts) if system_prompt_parts else ""
        if system_content:
            if conversation and conversation[0]["role"] == "user":
                conversation[0]["content"] = system_content + "\n\n" + conversation[0]["content"]
            else:
                conversation.insert(0, {"role": "user", "content": system_content})

        payload = {
            "model": self.model,
            "messages": conversation,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if "options" in kwargs:
            payload["options"].update(kwargs["options"])

        try:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.content:
                    if not line.strip():
                        continue

                    try:
                        import json
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content

                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {str(e)}") from e

    def get_model_name(self) -> str:
        """Get the model name being used"""
        return self.model
