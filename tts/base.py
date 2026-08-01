"""tts/base.py - common interface every text-to-speech provider implements."""

from __future__ import annotations

from typing import Protocol


class TextToSpeech(Protocol):
    def synthesize_pcm16(self, text: str, sample_rate: int = 16000) -> bytes:
        """Return 16-bit mono PCM audio at sample_rate for the given text."""
        ...
