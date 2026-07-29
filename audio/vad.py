"""
audio/vad.py

Silero VAD helper module for crmsystem/Goldentrade
Target Python: 3.14+

Dependencies:
- torch (install matching your CUDA if GPU is used)
- soundfile

Optional:
- scipy (if you need resampling utilities)

This module provides simple file-based utilities to load the Silero VAD model via torch.hub,
detect speech intervals, and extract speech chunks to WAV files.

Usage example:
    from audio.vad import load_silero_model, detect_speech_intervals, extract_speech_chunks

    bundle = load_silero_model()
    intervals = detect_speech_intervals("input.wav", bundle)
    extract_speech_chunks("input.wav", "out_chunks", bundle)

Note: Silero expects 16 kHz mono audio. If your recordings use a different sample rate,
resample before calling detect_speech_intervals/extract_speech_chunks.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import torch
import soundfile as sf
import numpy as np

# Type aliases
ModelBundle = Dict[str, Any]


def load_silero_model(device: torch.device | None = None, force_reload: bool = False) -> ModelBundle:
    """Load Silero VAD model via torch.hub and return a model bundle.

    The bundle contains:
      - 'model': the PyTorch model
      - 'utils': dict with helper callables from the silero-vad repo
      - 'device': the torch.device used

    device: if None, auto-selects CUDA when available.
    force_reload: pass True to force-reload the hub repo (useful during development).
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # The repo 'snakers4/silero-vad' exposes model and utils via torch.hub
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=force_reload,
    )

    get_speech_timestamps = utils[0] if isinstance(utils, (list, tuple)) else utils.get_speech_timestamps  # defensive

    # The upstream utils are returned as a tuple: (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks)
    # Normalize into a dict for clarity
    if isinstance(utils, (list, tuple)) and len(utils) >= 5:
        get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks = utils[:5]
        utils_dict = {
            "get_speech_timestamps": get_speech_timestamps,
            "save_audio": save_audio,
            "read_audio": read_audio,
            "VADIterator": VADIterator,
            "collect_chunks": collect_chunks,
        }
    elif isinstance(utils, dict):
        utils_dict = utils
    else:
        # Fallback: try attribute access
        utils_dict = {
            "get_speech_timestamps": getattr(utils, "get_speech_timestamps", None),
            "save_audio": getattr(utils, "save_audio", None),
            "read_audio": getattr(utils, "read_audio", None),
            "VADIterator": getattr(utils, "VADIterator", None),
            "collect_chunks": getattr(utils, "collect_chunks", None),
        }

    model.to(device)
    model.eval()

    return {"model": model, "utils": utils_dict, "device": device}


def detect_speech_intervals(
    wav_path: str,
    model_bundle: ModelBundle,
    sampling_rate: int = 16000,
    min_speech_duration_ms: int = 200,
) -> List[Tuple[int, int]]:
    """Return list of (start_ms, end_ms) speech intervals for the given wav file.

    wav_path: path to a WAV file (recommended 16 kHz, mono). If not 16 kHz, resample beforehand.
    model_bundle: bundle returned by load_silero_model().
    min_speech_duration_ms: filter out segments shorter than this threshold.
    """
    read_audio = model_bundle["utils"]["read_audio"]
    get_speech_timestamps = model_bundle["utils"]["get_speech_timestamps"]

    if read_audio is None or get_speech_timestamps is None:
        raise RuntimeError("Silero VAD utils not available in model bundle")

    # read_audio returns a numpy array or torch tensor in the range [-1, 1]
    audio = read_audio(wav_path, sampling_rate=sampling_rate)

    # Make sure we have a 1D numpy array
    if isinstance(audio, torch.Tensor):
        audio_np = audio.detach().cpu().numpy()
    else:
        audio_np = np.asarray(audio)

    # Ensure 1D
    if audio_np.ndim > 1:
        audio_np = np.mean(audio_np, axis=0)

    speech_timestamps = get_speech_timestamps(audio_np, model_bundle["model"], sampling_rate=sampling_rate)

    intervals: List[Tuple[int, int]] = []
    for seg in speech_timestamps:
        start_ms = int(1000 * seg["start"] / sampling_rate)
        end_ms = int(1000 * seg["end"] / sampling_rate)
        if (end_ms - start_ms) >= min_speech_duration_ms:
            intervals.append((start_ms, end_ms))
    return intervals


def extract_speech_chunks(
    wav_path: str, out_dir: str, model_bundle: ModelBundle, sampling_rate: int = 16000
) -> List[str]:
    """Extract detected speech segments into separate WAV files saved under out_dir.

    Returns list of output file paths.
    """
    os.makedirs(out_dir, exist_ok=True)

    read_audio = model_bundle["utils"]["read_audio"]
    collect_chunks = model_bundle["utils"]["collect_chunks"]
    get_speech_timestamps = model_bundle["utils"]["get_speech_timestamps"]

    if read_audio is None or collect_chunks is None or get_speech_timestamps is None:
        raise RuntimeError("Silero VAD utils missing from model bundle")

    audio = read_audio(wav_path, sampling_rate=sampling_rate)

    if isinstance(audio, torch.Tensor):
        audio_np = audio.detach().cpu().numpy()
    else:
        audio_np = np.asarray(audio)

    if audio_np.ndim > 1:
        audio_np = np.mean(audio_np, axis=0)

    speech_timestamps = get_speech_timestamps(audio_np, model_bundle["model"], sampling_rate=sampling_rate)
    chunks = collect_chunks(speech_timestamps, audio_np, sampling_rate=sampling_rate)

    out_paths: List[str] = []
    for i, chunk in enumerate(chunks):
        out_path = os.path.join(out_dir, f"chunk_{i:03d}.wav")
        # chunk is float32 in [-1,1]
        sf.write(out_path, chunk, samplerate=sampling_rate)
        out_paths.append(out_path)

    return out_paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Silero VAD file-based demo for Goldentrade")
    parser.add_argument("wav", help="input wav file (16 kHz recommended)")
    parser.add_argument("--out-dir", default="speech_chunks", help="dir to save detected speech segments")
    args = parser.parse_args()

    bundle = load_silero_model()
    intervals = detect_speech_intervals(args.wav, bundle)
    print("Detected speech intervals (ms):", intervals)
    out_files = extract_speech_chunks(args.wav, args.out_dir, bundle)
    print("Saved chunks:", out_files)
