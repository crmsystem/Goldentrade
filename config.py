"""
config.py

Central environment-based configuration for the Goldentrade voice call pipeline:

  Twilio/LiveKit -> Silero VAD -> STT (Whisper/Deepgram) -> LLM (GPT/Claude)
  -> TTS (ElevenLabs/Piper) -> Zoho CRM

All values are read from the environment (see .env.example). Nothing here
talks to a network - it just centralizes provider selection and credentials
so every module has one place to read settings from.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


@dataclass
class TwilioSettings:
    account_sid: str | None = field(default_factory=lambda: _env("TWILIO_ACCOUNT_SID"))
    auth_token: str | None = field(default_factory=lambda: _env("TWILIO_AUTH_TOKEN"))
    phone_number: str | None = field(default_factory=lambda: _env("TWILIO_PHONE_NUMBER"))
    # Public URL Twilio's <Stream> should connect back to, e.g. wss://your-host/media
    media_stream_url: str | None = field(default_factory=lambda: _env("TWILIO_MEDIA_STREAM_URL"))


@dataclass
class LiveKitSettings:
    url: str | None = field(default_factory=lambda: _env("LIVEKIT_URL"))
    api_key: str | None = field(default_factory=lambda: _env("LIVEKIT_API_KEY"))
    api_secret: str | None = field(default_factory=lambda: _env("LIVEKIT_API_SECRET"))


@dataclass
class STTSettings:
    provider: str = field(default_factory=lambda: _env("STT_PROVIDER", "whisper"))  # whisper | deepgram
    deepgram_api_key: str | None = field(default_factory=lambda: _env("DEEPGRAM_API_KEY"))
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "small"))
    language: str = field(default_factory=lambda: _env("STT_LANGUAGE", "en"))


@dataclass
class LLMSettings:
    provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "anthropic"))  # anthropic | openai
    anthropic_api_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-sonnet-5"))
    openai_api_key: str | None = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o"))
    system_prompt: str = field(
        default_factory=lambda: _env(
            "LLM_SYSTEM_PROMPT",
            "You are a helpful phone agent for Golden Trade. Keep replies short, "
            "spoken-language friendly, and confirm details before ending the call.",
        )
    )


@dataclass
class TTSSettings:
    provider: str = field(default_factory=lambda: _env("TTS_PROVIDER", "elevenlabs"))  # elevenlabs | piper
    elevenlabs_api_key: str | None = field(default_factory=lambda: _env("ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str | None = field(default_factory=lambda: _env("ELEVENLABS_VOICE_ID"))
    piper_model_path: str | None = field(default_factory=lambda: _env("PIPER_MODEL_PATH"))
    piper_binary: str = field(default_factory=lambda: _env("PIPER_BINARY", "piper"))


@dataclass
class ZohoSettings:
    # Standard Zoho CRM OAuth (self-client / server-to-server) credentials.
    client_id: str | None = field(default_factory=lambda: _env("ZOHO_CLIENT_ID"))
    client_secret: str | None = field(default_factory=lambda: _env("ZOHO_CLIENT_SECRET"))
    refresh_token: str | None = field(default_factory=lambda: _env("ZOHO_REFRESH_TOKEN"))
    accounts_url: str = field(default_factory=lambda: _env("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com"))
    api_domain: str = field(default_factory=lambda: _env("ZOHO_API_DOMAIN", "https://www.zohoapis.com"))


@dataclass
class Settings:
    twilio: TwilioSettings = field(default_factory=TwilioSettings)
    livekit: LiveKitSettings = field(default_factory=LiveKitSettings)
    stt: STTSettings = field(default_factory=STTSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    tts: TTSSettings = field(default_factory=TTSSettings)
    zoho: ZohoSettings = field(default_factory=ZohoSettings)

    # Telephony transport in front of the pipeline: "twilio" or "livekit"
    telephony_provider: str = field(default_factory=lambda: _env("TELEPHONY_PROVIDER", "twilio"))


settings = Settings()
