"""
stt/deepgram_stt.py

Deepgram pre-recorded/segment transcription over their REST API. Used as the
hosted alternative to local Whisper - lower CPU cost on the call server at
the price of a network round trip per speech segment.
"""

from __future__ import annotations

import httpx

from config import settings
from stt.whisper_stt import pcm16_to_wav_bytes

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


class DeepgramSTT:
    def __init__(self, api_key: str | None = None, model: str = "nova-2"):
        self.api_key = api_key or settings.stt.deepgram_api_key
        if not self.api_key:
            raise RuntimeError("DEEPGRAM_API_KEY is not set")
        self.model = model
        self.language = settings.stt.language

    def transcribe_pcm16(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> str:
        if not pcm16_bytes:
            return ""

        wav_bytes = pcm16_to_wav_bytes(pcm16_bytes, sample_rate)
        params = {"model": self.model, "language": self.language, "smart_format": "true"}
        headers = {"Authorization": f"Token {self.api_key}", "Content-Type": "audio/wav"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(DEEPGRAM_URL, params=params, headers=headers, content=wav_bytes)
            resp.raise_for_status()
            data = resp.json()

        try:
            return data["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
        except (KeyError, IndexError):
            return ""
