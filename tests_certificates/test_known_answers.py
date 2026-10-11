"""B15 / W04: the installed pinned tools give the known answers (behaviour, not just bytes).

Missing tools are a failure here, not a skip: this suite blocks release.
"""
from pathlib import Path
import sys
import unittest

from genesis.verification.tools import tool, toolchain_root

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'toolchain'))
from known_answers import known_answers  # noqa: E402


class KnownAnswers(unittest.TestCase):
    def test_installed_toolchain_passes_every_case(self):
        for name in ('cadical', 'drat-trim', 'eprover', 'zstd', 'lean'):
            tool(name)                       # pinned hash must match before behaviour is checked
        result = known_answers(toolchain_root())
        failed = [c['case'] for c in result['cases'] if not c['pass']]
        self.assertEqual(failed, [])
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['cases']), 10)

    def test_a_broken_checker_is_caught(self):
        # Swap drat-trim for a program that accepts everything: the negative case must fail.
        import json, shutil, tempfile
        pins = json.loads((ROOT / 'toolchain/PINS.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            fake_root = Path(d)
            for name, pin in pins.items():
                if isinstance(pin, dict) and 'binary' in pin:
                    target = fake_root / pin['binary']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if name == 'drat-trim':
                        target.write_text('#!/bin/sh\necho "s VERIFIED"\n'); target.chmod(0o755)
                    else:
                        target.symlink_to(toolchain_root() / pin['binary'])
            result = known_answers(fake_root)
        self.assertFalse(result['ok'])
        bad = [c['case'] for c in result['cases'] if not c['pass']]
        self.assertEqual(bad, ['drat-trim: rejects a bogus refutation of a SAT formula'])


if __name__ == '__main__':
    unittest.main()
