"""Trusted verifier anchors: the pinned external tool binaries (toolchain/PINS.json).

A verifier whose implementation hash is pinned here is ANCHORED (spec §15.1).
Consumers that re-derive claims (release export, bundle verification, the
relational index) use the verifier's own pins, never anchors stored by the
producer.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def pinned_tool_anchors(pins_path=None):
    path = Path(pins_path) if pins_path else REPO / 'toolchain' / 'PINS.json'
    if not path.is_file():
        return {}
    pins = json.loads(path.read_text())
    return {v['binary_sha256']: f'pinned {k}' for k, v in pins.items()
            if isinstance(v, dict) and isinstance(v.get('binary_sha256'), str)}
