"""
tests/test_orchestrator.py

Exercises CallSession's VAD-segmentation -> STT -> LLM -> TTS wiring with
fake providers, so the control flow is verified without needing real models,
API keys, or network access. Provider correctness (does Whisper transcribe
well, does Claude answer sensibly) is out of scope here - see the README's
manual/live testing section for that.
"""

from __future__ import annotations

import numpy as np
import pytest

from llm.base import ConversationState
from pipeline.orchestrator import VAD_WINDOW_SAMPLES, CallSession, PipelineComponents


class FakeVADIterator:
    """Emits a start event on the 2nd frame and an end event on the 5th, then stays quiet."""

    def __init__(self, model, sampling_rate):
        self.calls = 0

    def __call__(self, tensor, return_seconds=False):
        self.calls += 1
        if self.calls == 2:
            return {"start": 0}
        if self.calls == 5:
            return {"end": 0}
        return None

    def reset_states(self):
        pass


class FakeSTT:
    def __init__(self, transcript: str = "hello there"):
        self.transcript = transcript
        self.received: bytes | None = None

    def transcribe_pcm16(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> str:
        self.received = pcm16_bytes
        return self.transcript if pcm16_bytes else ""


class FakeLLM:
    def __init__(self, reply_text: str = "Hi, how can I help?"):
        self.reply_text = reply_text

    def reply(self, conversation: ConversationState, user_utterance: str) -> str:
        conversation.add("user", user_utterance)
        conversation.add("assistant", self.reply_text)
        return self.reply_text


class FakeTTS:
    def synthesize_pcm16(self, text: str, sample_rate: int = 16000) -> bytes:
        return b"SYNTHESIZED_AUDIO" if text else b""


@pytest.fixture
def fake_components() -> PipelineComponents:
    return PipelineComponents(
        vad_bundle={"model": None, "utils": {"VADIterator": FakeVADIterator}},
        stt=FakeSTT(),
        llm=FakeLLM(),
        tts=FakeTTS(),
        zoho=None,
    )


def _silence_frame() -> bytes:
    return np.zeros(VAD_WINDOW_SAMPLES, dtype=np.int16).tobytes()


def test_call_session_produces_reply_after_vad_end_event(fake_components):
    session = CallSession(caller_phone="+15551234567", components=fake_components)

    replies = [session.push_audio_16k(_silence_frame()) for _ in range(8)]
    reply_audio = next((r for r in replies if r), None)

    assert reply_audio == b"SYNTHESIZED_AUDIO"


def test_call_session_records_conversation_turns(fake_components):
    session = CallSession(caller_phone="+15551234567", components=fake_components)

    for _ in range(8):
        session.push_audio_16k(_silence_frame())

    assert [(t.role, t.content) for t in session.conversation.turns] == [
        ("user", "hello there"),
        ("assistant", "Hi, how can I help?"),
    ]


def test_call_session_ignores_partial_frames_until_window_is_full(fake_components):
    session = CallSession(caller_phone="+15551234567", components=fake_components)

    half_frame = np.zeros(VAD_WINDOW_SAMPLES // 2, dtype=np.int16).tobytes()
    assert session.push_audio_16k(half_frame) is None
    # VADIterator hasn't been called yet since a full window hasn't accumulated.
    assert fake_components.vad_bundle is not None  # sanity: fixture wired correctly


def test_finish_returns_none_when_no_conversation_happened(fake_components):
    session = CallSession(caller_phone="+15551234567", components=fake_components)
    assert session.finish() is None


def test_finish_logs_transcript_and_summary_to_zoho(fake_components, monkeypatch):
    logged: dict = {}

    class FakeZoho:
        def log_call(self, **kwargs):
            logged.update(kwargs)
            return "call-record-id-123"

    fake_components.zoho = FakeZoho()
    session = CallSession(caller_phone="+15551234567", components=fake_components)

    for _ in range(8):
        session.push_audio_16k(_silence_frame())

    call_id = session.finish()

    assert call_id == "call-record-id-123"
    assert logged["caller_phone"] == "+15551234567"
    assert "hello there" in logged["transcript"]
    assert "Hi, how can I help?" in logged["transcript"]
    assert logged["duration_seconds"] >= 0
