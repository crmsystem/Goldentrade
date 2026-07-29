"""llm/base.py - common interface every conversational LLM provider implements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass
class Turn:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class ConversationState:
    """Rolling transcript for one call, shared with the Zoho logging step at hang-up."""

    turns: list[Turn] = field(default_factory=list)

    def add(self, role: Literal["user", "assistant"], content: str) -> None:
        if content:
            self.turns.append(Turn(role=role, content=content))

    def as_text(self) -> str:
        return "\n".join(f"{t.role}: {t.content}" for t in self.turns)


class ChatLLM(Protocol):
    def reply(self, conversation: ConversationState, user_utterance: str) -> str:
        """Given the running conversation and the caller's latest utterance, return the
        assistant's next spoken reply (short, TTS-friendly text)."""
        ...
