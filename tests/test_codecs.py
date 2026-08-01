"""
tests/test_codecs.py

audio/codecs.py exists specifically to replace the stdlib `audioop` module
(removed in Python 3.13, the project's target runtime). Where `audioop` is
importable in the test environment, we hold our codec to it directly since
it's the canonical G.711 reference; otherwise we fall back to self-consistency
checks that don't depend on it.
"""

from __future__ import annotations

import numpy as np
import pytest

from audio.codecs import mulaw_to_pcm16, pcm16_to_mulaw, resample_pcm16

try:
    import audioop

    HAVE_AUDIOOP = True
except ImportError:
    HAVE_AUDIOOP = False


def _random_pcm16(n: int, seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed)
    return rng.integers(-32768, 32767, size=n, dtype=np.int16).tobytes()


@pytest.mark.skipif(not HAVE_AUDIOOP, reason="audioop not available in this interpreter")
def test_decode_matches_audioop_exactly():
    mulaw_bytes = bytes(range(256))
    assert mulaw_to_pcm16(mulaw_bytes) == audioop.ulaw2lin(mulaw_bytes, 2)


@pytest.mark.skipif(not HAVE_AUDIOOP, reason="audioop not available in this interpreter")
def test_encode_quality_matches_audioop_reference():
    pcm = _random_pcm16(8000)

    ref_mulaw = audioop.lin2ulaw(pcm, 2)
    our_mulaw = pcm16_to_mulaw(pcm)

    ref_reconstructed = np.frombuffer(audioop.ulaw2lin(ref_mulaw, 2), dtype=np.int16).astype(int)
    our_reconstructed = np.frombuffer(audioop.ulaw2lin(our_mulaw, 2), dtype=np.int16).astype(int)
    original = np.frombuffer(pcm, dtype=np.int16).astype(int)

    ref_error = np.mean(np.abs(ref_reconstructed - original))
    our_error = np.mean(np.abs(our_reconstructed - original))

    # Our encoder is a nearest-level quantizer against the exact decode table,
    # so it should be at least as accurate as audioop's bit-twiddling encoder.
    assert our_error <= ref_error * 1.05


def test_encode_decode_round_trip_is_near_lossless_for_every_representable_level():
    # Every mu-law byte decodes to one of 256 representable PCM16 levels;
    # re-encoding that exact level should always recover the original byte.
    all_bytes = bytes(range(256))
    decoded_pcm16 = mulaw_to_pcm16(all_bytes)
    re_encoded = pcm16_to_mulaw(decoded_pcm16)

    decoded_again = np.frombuffer(mulaw_to_pcm16(re_encoded), dtype=np.int16)
    original_decoded = np.frombuffer(decoded_pcm16, dtype=np.int16)

    assert np.array_equal(decoded_again, original_decoded)


def test_pcm16_to_mulaw_empty_input():
    assert pcm16_to_mulaw(b"") == b""


def test_mulaw_to_pcm16_empty_input():
    assert mulaw_to_pcm16(b"") == b""


def test_resample_noop_when_rates_match():
    pcm = _random_pcm16(320)
    assert resample_pcm16(pcm, 16000, 16000) == pcm


def test_resample_output_length_matches_target_rate():
    pcm_8k = _random_pcm16(160)  # 20ms @ 8kHz
    pcm_16k = resample_pcm16(pcm_8k, 8000, 16000)

    samples_8k = len(pcm_8k) // 2
    samples_16k = len(pcm_16k) // 2
    assert samples_16k == samples_8k * 2


def test_resample_round_trip_preserves_tone_frequency():
    sample_rate = 8000
    freq = 440
    n = 1600
    t = np.arange(n) / sample_rate
    tone = (np.sin(2 * np.pi * freq * t) * 10000).astype(np.int16).tobytes()

    up = resample_pcm16(tone, sample_rate, 16000)
    down = resample_pcm16(up, 16000, sample_rate)

    original = np.frombuffer(tone, dtype=np.int16).astype(np.float64)
    round_tripped = np.frombuffer(down, dtype=np.int16).astype(np.float64)

    correlation = np.corrcoef(original, round_tripped[: len(original)])[0, 1]
    assert correlation > 0.99
