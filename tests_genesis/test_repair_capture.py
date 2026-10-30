"""The obstacle loop's first steps (`docs/OMEGA_SELF_REPAIR.md`, SR-a and SR-b): failed runs' tracebacks parsed into
failures, their signatures, the boundary of what Genesis may repair, escalation, and retrieval from the repair vault,
on the real crashes of 30 Oct 2026 (their slice logs are committed evidence) and on synthetic ones."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repair import capture as C  # noqa: E402
from genesis.repair import vault as V  # noqa: E402

LOGS = {'B20R177-LIBRARY': 'evidence/proving_test_2_b20r177_attempt1/run.log',
        'B20R177-SEEN': 'evidence/proving_test_2_b20r177_attempt2/run.log',
        'B20R158-TEMPLATE': 'evidence/open_conjectures_b20r158_attempt1/run.log'}

SYNTHETIC = '''Traceback (most recent call last):
  File "/somewhere/else/scripts/b20r999_x.py", line 10, in <module>
    main()
  File "/somewhere/else/src/genesis/frontier/engine.py", line 117, in advance
    pts, arts = self.domain.step(d['problem'], d, b['seed'], b['t'], self.quantum)
  File "/somewhere/else/src/genesis/autonomy/feedback.py", line 42, in judge
    raise ValueError('refused')
ValueError: refused
'''


class Capture(unittest.TestCase):
    def test_the_real_crashes_parse_and_sign(self):
        want = {'B20R177-LIBRARY': (['StopIteration', 'RuntimeError'], 'src/genesis/conjecture/library.py',
                                    '<genexpr>'),
                'B20R177-SEEN': (['KeyError'], 'src/genesis/conjecture/statement.py', 'score'),
                'B20R158-TEMPLATE': (['OverflowError'], 'src/genesis/conjecture/abstraction.py', 'mutate')}
        for defect, path in LOGS.items():
            f = C.parse((ROOT / path).read_text())
            sig = C.signature(f)
            self.assertEqual((sig['exceptions'], sig['file'], sig['func']), want[defect], defect)
            self.assertFalse(C.escalate(f), defect)                   # all three were Genesis's own to repair
            self.assertTrue(all(fr['file'].startswith(('src/', 'scripts/')) for fr in f['frames']), defect)

    def test_the_boundary(self):
        for p in ('src/genesis/autonomy/feedback.py', 'src/genesis/architecture/judge.py', 'src/genesis/kernel/x.py',
                  'src/genesis/conjecture/sealed.py', 'src/genesis/conjecture/verify.py', 'scripts/run_test_matrix.py',
                  'tests_genesis/test_x.py', 'src/genesis/repair/vault.py', 'src/genesis/frontier/manifest.py'):
            self.assertEqual(C.where(p), 'protected', p)
        for p in ('src/genesis/conjecture/library.py', 'src/genesis/frontier/meta.py', 'src/genesis/senses/graph.py'):
            self.assertEqual(C.where(p), 'repairable', p)
        for p in ('/usr/lib/python3.13/json/decoder.py', 'src/genesis/cli.py'):
            self.assertEqual(C.where(p), 'outside', p)                 # default deny: not repairable either
        self.assertEqual(C.relative('/home/claude/pt2b-wt/src/genesis/conjecture/attack.py'),
                         'src/genesis/conjecture/attack.py')
        for p in C.PROTECTED:                                          # every protected path exists
            if p.startswith('src/'):
                self.assertTrue((ROOT / p).exists(), p)

    def test_an_obstacle_inside_the_judge_is_escalated(self):
        f = C.parse(SYNTHETIC)
        self.assertEqual(f['exception'], 'ValueError')
        self.assertEqual([fr['side'] for fr in f['frames']], ['protected', 'repairable', 'protected'])
        self.assertTrue(C.escalate(f))
        self.assertIsNone(C.parse('no traceback here'))


class Vault(unittest.TestCase):
    def test_retrieval_finds_each_real_repair_and_nothing_left_one_out(self):
        for defect, path in LOGS.items():
            sig = C.signature(C.parse((ROOT / path).read_text()))
            got = V.retrieve(sig)
            self.assertEqual(got[0]['id'], defect)
            self.assertEqual(V.retrieve(sig, exclude=[defect]), [])   # SR-1's leave-one-out: nothing else matches

    def test_the_entries(self):
        ids = [e['id'] for e in V.ENTRIES]
        self.assertEqual(len(ids), len(set(ids)))
        for e in V.ENTRIES:
            self.assertIn(e['class'], ('ordering', 'guard', 'missing-capability', 'design'))
            self.assertTrue((ROOT / e['test'].split('::')[0]).exists(), e['id'])
            self.assertEqual(C.where(e['signature']['file']), 'repairable', e['id'])


if __name__ == '__main__':
    unittest.main()
