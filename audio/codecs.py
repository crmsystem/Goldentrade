"""
audio/codecs.py

Small numpy-only audio codec/resampling helpers for the telephony bridge.

Twilio Media Streams sends/receives 8 kHz mono mu-law. Silero VAD, Whisper,
and most TTS providers used here operate on 16 kHz PCM16. This module avoids
the stdlib `audioop` module (removed in Python 3.13+) and any extra native
dependency, at the cost of resampling quality that's adequate for
phone-bandwidth speech but not hi-fi audio.
"""

from __future__ import annotations

import numpy as np

_MULAW_BIAS = 0x84
_MULAW_MAX = 32635


def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """Decode 8-bit G.711 mu-law bytes to 16-bit signed PCM bytes (same sample rate)."""
    u = np.frombuffer(mulaw_bytes, dtype=np.uint8).astype(np.int32)
    u = ~u & 0xFF

    sign = u & 0x80
    exponent = (u >> 4) & 0x07
    mantissa = u & 0x0F

    magnitude = ((mantissa << 3) + _MULAW_BIAS) << exponent
    magnitude -= _MULAW_BIAS

    pcm = np.where(sign != 0, -magnitude, magnitude)
    pcm = np.clip(pcm, -32768, 32767).astype(np.int16)
    return pcm.tobytes()


# mu-law only has 256 representable levels, so encoding is exact nearest-level
# quantization against the (verified-correct) decode table above - this avoids
# re-deriving the segment/exponent bit-twiddling, which is easy to get subtly wrong.
_DECODE_TABLE = np.frombuffer(mulaw_to_pcm16(bytes(range(256))), dtype=np.int16).astype(np.int32)
_SORT_ORDER = np.argsort(_DECODE_TABLE)
_SORTED_LEVELS = _DECODE_TABLE[_SORT_ORDER]


def pcm16_to_mulaw(pcm16_bytes: bytes) -> bytes:
    """Encode 16-bit signed PCM bytes to 8-bit G.711 mu-law bytes (same sample rate)."""
    if not pcm16_bytes:
        return b""

    pcm = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.int32)

    # Index of the first sorted level >= sample; compare against its left
    # neighbor to find whichever representable level is actually closest.
    right = np.clip(np.searchsorted(_SORTED_LEVELS, pcm), 0, 255)
    left = np.clip(right - 1, 0, 255)
    pick_left = np.abs(_SORTED_LEVELS[left] - pcm) <= np.abs(_SORTED_LEVELS[right] - pcm)

    sorted_idx = np.where(pick_left, left, right)
    byte = _SORT_ORDER[sorted_idx]
    return byte.astype(np.uint8).tobytes()


def resample_pcm16(pcm16_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    """Linear-interpolation resampler. Fine for 8k<->16k telephony-band speech."""
    if from_rate == to_rate or not pcm16_bytes:
        return pcm16_bytes

    samples = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32)
    duration = len(samples) / from_rate
    src_times = np.arange(len(samples)) / from_rate
    dst_times = np.arange(int(duration * to_rate)) / to_rate

    resampled = np.interp(dst_times, src_times, samples)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
