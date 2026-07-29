"""stt/base.py - common interface every speech-to-text provider implements."""

from __future__ import annotations

from typing import Protocol


class SpeechToText(Protocol):
    """A provider that turns a chunk of 16 kHz mono PCM16 audio into text.

    Implementations are expected to be used for one speech segment at a time,
    i.e. the caller runs Silero VAD first and only forwards audio between a
    detected speech-start and speech-end boundary.
    """

    def transcribe_pcm16(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> str:
        """Return the transcript for a single speech segment. Empty string if silent/unclear."""
        ...
