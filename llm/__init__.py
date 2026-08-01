"""llm package - pluggable conversational providers (Claude, GPT)."""

from __future__ import annotations

from config import settings
from llm.base import ChatLLM, ConversationState, Turn

__all__ = ["ChatLLM", "ConversationState", "Turn", "get_llm_provider"]


def get_llm_provider() -> ChatLLM:
    provider = settings.llm.provider.lower()
    if provider == "anthropic":
        from llm.anthropic_llm import ClaudeLLM

        return ClaudeLLM()
    if provider == "openai":
        from llm.openai_llm import GPTLLM

        return GPTLLM()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (expected 'anthropic' or 'openai')")
