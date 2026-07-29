"""
tests/conftest.py

Unit tests exercise pipeline wiring and pure logic, not real ML inference or
live provider APIs. `audio/vad.py` imports `torch`/`soundfile` at module
level purely to load the real Silero model via torch.hub - something we
never want a unit test run to do (multi-GB download, network access, GPU).

If those packages aren't installed (e.g. a lightweight dev/CI box that
hasn't pulled the full requirements-py314.txt), install minimal stand-ins so
`pipeline.orchestrator` still imports. Where the real packages *are*
installed, this is a no-op and tests run against them normally.
"""

from __future__ import annotations

import sys
import types


def _ensure_stub(name: str, **attrs: object) -> None:
    try:
        __import__(name)
    except ImportError:
        module = types.ModuleType(name)
        for attr, value in attrs.items():
            setattr(module, attr, value)
        sys.modules[name] = module


_ensure_stub("torch", from_numpy=lambda x: x, Tensor=object)
_ensure_stub("soundfile")
