"""llm/anthropic_llm.py - Claude as the conversational brain of the call."""

from __future__ import annotations

from anthropic import Anthropic

from config import settings
from llm.base import ConversationState


class ClaudeLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = Anthropic(api_key=api_key or settings.llm.anthropic_api_key)
        self.model = model or settings.llm.anthropic_model
        self.system_prompt = settings.llm.system_prompt

    def reply(self, conversation: ConversationState, user_utterance: str) -> str:
        conversation.add("user", user_utterance)

        messages = [{"role": t.role, "content": t.content} for t in conversation.turns]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=self.system_prompt,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()

        conversation.add("assistant", text)
        return text
