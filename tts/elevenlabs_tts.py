"""
tts/elevenlabs_tts.py

Hosted TTS via the ElevenLabs API. Requests raw PCM directly (output_format=
pcm_16000) so no MP3 decoding step is needed before the audio goes back out
to the caller.
"""

from __future__ import annotations

import httpx

from config import settings

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsTTS:
    def __init__(self, api_key: str | None = None, voice_id: str | None = None):
        self.api_key = api_key or settings.tts.elevenlabs_api_key
        self.voice_id = voice_id or settings.tts.elevenlabs_voice_id
        if not self.api_key or not self.voice_id:
            raise RuntimeError("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID must be set")

    def synthesize_pcm16(self, text: str, sample_rate: int = 16000) -> bytes:
        if not text:
            return b""

        url = ELEVENLABS_URL.format(voice_id=self.voice_id)
        params = {"output_format": f"pcm_{sample_rate}"}
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, params=params, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content
