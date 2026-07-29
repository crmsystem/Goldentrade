"""
pipeline/orchestrator.py

Ties one phone call's audio stream through:

  raw audio in (16 kHz PCM16) -> Silero VAD (streaming) -> STT -> LLM -> TTS
  -> raw audio out (16 kHz PCM16) -> ... -> Zoho CRM call log at hang-up

The telephony transport (telephony/twilio_stream.py, or a LiveKit agent) is
responsible for getting audio to/from the wire format (mu-law, sample rate,
websocket framing) - this module only ever sees/produces 16 kHz PCM16, so it
is transport-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import torch

from audio.vad import load_silero_model
from crm.zoho_client import ZohoCRMClient
from llm import ConversationState, get_llm_provider
from stt import get_stt_provider
from tts import get_tts_provider

SAMPLE_RATE = 16000
VAD_WINDOW_SAMPLES = 512  # required window size for the 16 kHz Silero VAD model
SPEECH_END_SILENCE_MS = 500  # how much trailing silence marks end-of-utterance


@dataclass
class PipelineComponents:
    """Heavyweight, stateless-per-call providers shared across every CallSession."""

    vad_bundle: dict
    stt: object
    llm: object
    tts: object
    zoho: ZohoCRMClient


_components: PipelineComponents | None = None


def get_components() -> PipelineComponents:
    """Lazily build and cache the shared providers (models, API clients) once per process."""
    global _components
    if _components is None:
        _components = PipelineComponents(
            vad_bundle=load_silero_model(),
            stt=get_stt_provider(),
            llm=get_llm_provider(),
            tts=get_tts_provider(),
            zoho=ZohoCRMClient(),
        )
    return _components


@dataclass
class CallSession:
    """Per-call state: one instance per active phone call."""

    caller_phone: str
    components: PipelineComponents = field(default_factory=get_components)
    conversation: ConversationState = field(default_factory=ConversationState)

    _vad_iterator: object = field(init=False, repr=False)
    _pending_frame: bytes = field(default=b"", init=False, repr=False)
    _speech_buffer: bytearray = field(default_factory=bytearray, init=False, repr=False)
    _in_speech: bool = field(default=False, init=False, repr=False)
    _started_at: float = field(default_factory=time.time, init=False, repr=False)

    def __post_init__(self) -> None:
        vad_iterator_cls = self.components.vad_bundle["utils"]["VADIterator"]
        self._vad_iterator = vad_iterator_cls(
            self.components.vad_bundle["model"], sampling_rate=SAMPLE_RATE
        )

    def push_audio_16k(self, pcm16_bytes: bytes) -> bytes | None:
        """Feed a chunk of caller audio in. Returns the agent's spoken reply (16 kHz PCM16)
        once a full utterance has been detected and answered, else None."""
        self._pending_frame += pcm16_bytes

        frame_bytes = VAD_WINDOW_SAMPLES * 2  # int16 -> 2 bytes/sample
        reply_audio: bytes | None = None

        while len(self._pending_frame) >= frame_bytes:
            frame, self._pending_frame = self._pending_frame[:frame_bytes], self._pending_frame[frame_bytes:]
            reply_audio = self._process_vad_frame(frame) or reply_audio

        return reply_audio

    def _process_vad_frame(self, frame: bytes) -> bytes | None:
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        tensor = torch.from_numpy(samples)

        event = self._vad_iterator(tensor, return_seconds=False)

        if self._in_speech:
            self._speech_buffer.extend(frame)

        if event is None:
            return None

        if "start" in event:
            self._in_speech = True
            self._speech_buffer = bytearray(frame)
            return None

        if "end" in event and self._in_speech:
            self._in_speech = False
            utterance_pcm16 = bytes(self._speech_buffer)
            self._speech_buffer = bytearray()
            self._vad_iterator.reset_states()
            return self._handle_utterance(utterance_pcm16)

        return None

    def _handle_utterance(self, utterance_pcm16: bytes) -> bytes | None:
        transcript = self.components.stt.transcribe_pcm16(utterance_pcm16, sample_rate=SAMPLE_RATE)
        if not transcript:
            return None

        reply_text = self.components.llm.reply(self.conversation, transcript)
        if not reply_text:
            return None

        return self.components.tts.synthesize_pcm16(reply_text, sample_rate=SAMPLE_RATE)

    def finish(self) -> str | None:
        """Call has ended: log the full transcript + a short summary to Zoho CRM.

        Returns the new Zoho Call record id, or None if the call had no matchable
        content (e.g. it dropped before any utterance was captured).
        """
        if not self.conversation.turns:
            return None

        duration_seconds = int(time.time() - self._started_at)
        summary = self._build_summary()

        return self.components.zoho.log_call(
            caller_phone=self.caller_phone,
            call_start_iso=_iso_from_epoch(self._started_at),
            duration_seconds=duration_seconds,
            transcript=self.conversation.as_text(),
            summary=summary,
        )

    def _build_summary(self) -> str:
        """One-line summary via the same LLM, kept separate from the live conversation turns."""
        summary_prompt = (
            "Summarize the phone call above in one or two sentences for a CRM activity log, "
            "focusing on the caller's request and the outcome."
        )
        scratch_conversation = ConversationState(turns=list(self.conversation.turns))
        return self.components.llm.reply(scratch_conversation, summary_prompt)


def _iso_from_epoch(epoch_seconds: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(epoch_seconds))
