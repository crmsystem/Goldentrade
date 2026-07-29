"""
stt/whisper_stt.py

Local Whisper transcription via faster-whisper (CTranslate2), used for the
Silero VAD -> STT step of the call pipeline. Runs on-box, no network round
trip per segment, which keeps turn-taking latency low on a live call.
"""

from __future__ import annotations

import io

import numpy as np
from faster_whisper import WhisperModel

from config import settings


class WhisperSTT:
    def __init__(self, model_size: str | None = None, device: str = "auto", compute_type: str = "int8"):
        self.model = WhisperModel(
            model_size or settings.stt.whisper_model,
            device=device,
            compute_type=compute_type,
        )
        self.language = settings.stt.language

    def transcribe_pcm16(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> str:
        if not pcm16_bytes:
            return ""

        audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=False,  # Silero VAD already isolated this segment upstream
            beam_size=1,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()


def pcm16_to_wav_bytes(pcm16_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Helper for providers (e.g. Deepgram) that expect a WAV container instead of raw PCM."""
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16_bytes)
    return buf.getvalue()
