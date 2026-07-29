"""llm/openai_llm.py - GPT as the conversational brain of the call."""

from __future__ import annotations

from openai import OpenAI

from config import settings
from llm.base import ConversationState


class GPTLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = OpenAI(api_key=api_key or settings.llm.openai_api_key)
        self.model = model or settings.llm.openai_model
        self.system_prompt = settings.llm.system_prompt

    def reply(self, conversation: ConversationState, user_utterance: str) -> str:
        conversation.add("user", user_utterance)

        messages = [{"role": "system", "content": self.system_prompt}]
        messages += [{"role": t.role, "content": t.content} for t in conversation.turns]

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=300,
            messages=messages,
        )
        text = (response.choices[0].message.content or "").strip()

        conversation.add("assistant", text)
        return text
