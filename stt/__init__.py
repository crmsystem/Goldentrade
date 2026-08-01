"""stt package - pluggable speech-to-text providers (Whisper, Deepgram)."""

from __future__ import annotations

from config import settings
from stt.base import SpeechToText


def get_stt_provider() -> SpeechToText:
    provider = settings.stt.provider.lower()
    if provider == "whisper":
        from stt.whisper_stt import WhisperSTT

        return WhisperSTT()
    if provider == "deepgram":
        from stt.deepgram_stt import DeepgramSTT

        return DeepgramSTT()
    raise ValueError(f"Unknown STT_PROVIDER: {provider!r} (expected 'whisper' or 'deepgram')")
