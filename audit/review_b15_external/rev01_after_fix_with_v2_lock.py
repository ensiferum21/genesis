"""B15-REV-01, after the repair: the reviewer's scenario with a lock written by the
repaired code (per-file manifest of installed bytes). Expected: before ok, after not ok."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests_genesis.test_external_review_b15 import ProbeDistribution  # noqa: E402

with tempfile.TemporaryDirectory() as td:
    with ProbeDistribution(Path(td)) as probe:
        before = probe.check()
        (probe.site / 'reviewprobe' / '__init__.py').write_bytes(b'VALUE = 999\n')
        after = probe.check()
        import reviewprobe
        print(json.dumps({'before': before, 'after_file_change': after, 'imported_value': reviewprobe.VALUE},
                         indent=2))
        assert before['ok'] and not after['ok'] and reviewprobe.VALUE == 999
        print('REPAIRED: a module changed without touching RECORD fails the dependency check')
