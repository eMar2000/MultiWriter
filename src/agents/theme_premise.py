"""Theme & Premise Agent"""

import os
from typing import Dict, Any
from pathlib import Path

from .base import BaseAgent
from src.models import NovelInput, ThemeStatement


class ThemePremiseAgent(BaseAgent):
    """Agent responsible for validating premise and ensuring thematic coherence"""

    def __init__(self, *args, **kwargs):
        super().__init__(name="theme_premise", *args, **kwargs)

        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "theme_premise.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        else:
            self.system_prompt = self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if file not found"""
        return """You are a Theme & Premise Agent, specializing in ensuring narrative meaning and thematic coherence.
Your role is to validate and refine the novel's premise, ensuring it explores a meaningful thematic question.
Theme is a question, not a message. Premise → Conflict → Resolution must form a logical chain."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute theme and premise validation"""
        # Get novel input from context
        novel_input = context.get("novel_input")
        if not novel_input:
            raise ValueError("Novel input required in context")

        # Build user prompt
        user_prompt = self._build_user_prompt(novel_input)

        # Generate theme statement using LLM
        theme_data = await self.generate_structured_output(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_format="json",
            temperature=0.7
        )

        # Validate and parse theme statement
        theme = ThemeStatement(**theme_data)

        # Save to memory
        await self.write_to_memory(
            "novel-outlines",
            {
                "id": self.novel_id,
                "theme": theme.model_dump(),
                "premise": theme.premise,
                "status": "theme_defined"
            }
        )

        return {
            "agent": self.name,
            "output": {
                "theme": theme.model_dump(),
            },
            "status": "success"
        }

    def _build_user_prompt(self, novel_input: Dict[str, Any]) -> str:
        """Build user prompt from novel input"""
        prompt_parts = [
            f"Novel Premise: {novel_input.get('premise', 'Not provided')}",
            f"Genre: {novel_input.get('genre', 'Not specified')}",
        ]

        if novel_input.get("desired_theme"):
            prompt_parts.append(f"Desired Theme: {novel_input['desired_theme']}")

        if novel_input.get("key_elements"):
            prompt_parts.append(f"Key Elements: {', '.join(novel_input['key_elements'])}")

        prompt_parts.append(
            "\nPlease validate and refine the premise, develop the thematic question, "
            "and establish thematic constraints for this novel."
        )

        return "\n".join(prompt_parts)
