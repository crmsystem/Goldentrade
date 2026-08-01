"""tts package - pluggable text-to-speech providers (ElevenLabs, Piper)."""

from __future__ import annotations

from config import settings
from tts.base import TextToSpeech


def get_tts_provider() -> TextToSpeech:
    provider = settings.tts.provider.lower()
    if provider == "elevenlabs":
        from tts.elevenlabs_tts import ElevenLabsTTS

        return ElevenLabsTTS()
    if provider == "piper":
        from tts.piper_tts import PiperTTS

        return PiperTTS()
    raise ValueError(f"Unknown TTS_PROVIDER: {provider!r} (expected 'elevenlabs' or 'piper')")
