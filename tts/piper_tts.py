"""
tts/piper_tts.py

Local, offline TTS via Piper (https://github.com/rhasspy/piper). Useful when
audio must never leave the box, or as a free fallback when no ElevenLabs key
is configured. Piper writes raw PCM16 mono to stdout at the voice model's
native sample rate (commonly 22050 Hz) - resample downstream if the
telephony leg needs a different rate.
"""

from __future__ import annotations

import subprocess

from config import settings


class PiperTTS:
    def __init__(self, model_path: str | None = None, piper_binary: str | None = None):
        self.model_path = model_path or settings.tts.piper_model_path
        self.piper_binary = piper_binary or settings.tts.piper_binary
        if not self.model_path:
            raise RuntimeError("PIPER_MODEL_PATH must be set to a Piper .onnx voice model")

    def synthesize_pcm16(self, text: str, sample_rate: int = 16000) -> bytes:
        if not text:
            return b""

        proc = subprocess.run(
            [self.piper_binary, "--model", self.model_path, "--output-raw"],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return proc.stdout
