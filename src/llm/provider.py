"""Provider-agnostic LLM interface"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """LLM message"""
    role: str  # system, user, assistant
    content: str


class LLMResponse(BaseModel):
    """LLM response"""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used"""
        pass
