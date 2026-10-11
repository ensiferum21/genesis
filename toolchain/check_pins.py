#!/usr/bin/env python3
"""Report whether installed tool binaries match PINS.json and whether PINS.json is the
last entry of its revision history. Exit 1 on any mismatch."""
import hashlib, json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / 'src'))
from genesis.deployment import check_pins_history  # noqa: E402
root = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'toolchain')
pins = json.loads((here / 'PINS.json').read_text())
bad = 0
for name, pin in pins.items():
    if 'binary' not in pin:
        continue
    path = root / pin['binary']
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    ok = actual == pin['binary_sha256']
    bad += not ok
    print(f"{name:10s} {'OK' if ok else 'MISMATCH'} {path} {actual}")
history = check_pins_history(pins)
print('history    ' + ('OK' if not history else 'PROBLEMS: ' + '; '.join(history)))
sys.exit(1 if bad or history else 0)
