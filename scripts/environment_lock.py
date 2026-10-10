#!/usr/bin/env python3
"""Record the observed interpreter and installed distributions (with RECORD hashes)."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.release_bundle import observed_environment  # noqa: E402
env = observed_environment()
out = ROOT / 'environment' / f"observed_python{sys.version_info.major}{sys.version_info.minor}.json"
out.write_text(json.dumps(env, indent=1, sort_keys=True) + '\n')
print(out)
