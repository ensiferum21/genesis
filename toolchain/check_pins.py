#!/usr/bin/env python3
"""Report whether installed tool binaries match PINS.json. Exit 1 on any mismatch."""
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'toolchain')
pins = json.loads((Path(__file__).parent / 'PINS.json').read_text())
bad = 0
for name, pin in pins.items():
    if 'binary' not in pin:
        continue
    path = root / pin['binary']
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    ok = actual == pin['binary_sha256']
    bad += not ok
    print(f"{name:10s} {'OK' if ok else 'MISMATCH'} {path} {actual}")
sys.exit(1 if bad else 0)
