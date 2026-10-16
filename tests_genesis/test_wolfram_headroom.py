"""B20_R53: the Wolfram hard-setting headroom pilot. Design: B20's hard rules unchanged; fresh seeds; the evaluation
targets avoid each seed's pool and development targets; ORACLE@cap is B20_R3's; the GAP arm keeps only conjectures
its cheap attempt cannot prove and charges both attempts; the verdict follows the preregistered rule. Record tests
are added with the result."""
from pathlib import Path
import sys
import unittest

from genesis.learning import equational as Q
from genesis.learning.budget import Account

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20_curriculum_control as B20  # noqa: E402
import b20r3_headroom_pilot as R3  # noqa: E402
import b20r53_wolfram_headroom as M  # noqa: E402

PROOF = "fof(c, plain, $false, inference(x, [], [file('p.p', ax0)])).\n"


def fake_prover(cheap, full, cpu_ns=1_000_000):
    """THEOREM on a cheap attempt for equations in `cheap`, on a full attempt for those in `full`."""
    calls = []

    def prover(axioms, goal, *, res, label):
        is_cheap = res.purpose.startswith('cheap ')
        text = res.purpose.split(' ', 1)[1]
        calls.append((text, is_cheap))
        ok = text in cheap if is_cheap else text in full
        return {'status': 'THEOREM' if ok else 'ResourceOut', 'proof': PROOF if ok else None,
                'resource': {'termination': 'EXITED', 'exit_code': 0, 'cpu_ns': cpu_ns, 'wall_ns': cpu_ns,
                             'meter': {'kind': 'fake', 'lower_bound': False}}}
    prover.calls = calls
    return prover


class Design(unittest.TestCase):
    def test_rules_are_b20s_hard_rules_and_seeds_are_fresh(self):
        for k, v in M.RULES.items():
            self.assertEqual(B20.RULES[k], v, k)
        self.assertEqual(M.SYSTEM, B20.SYSTEM)
        self.assertFalse(set(M.SEEDS) & set(M.PRIOR_SEEDS) | set(M.SEEDS) & set(B20.SEEDS))
        self.assertEqual(M.CAPS, (60, 30))

    def test_material_is_disjoint(self):
        pool, dev, ev = M.material(M.SEEDS[0])
        self.assertEqual((len(dev), len(ev)), (10, 15))
        seen = {Q.canon(e) for e in pool + dev}
        self.assertFalse(any(Q.canon(e) in seen for e in ev))
        self.assertTrue(all(Q.holds(e, 'nand') for e in ev))

    def test_oracle_at_is_b20r3s(self):
        lib = [{'id': f'L{i}', 'text': f't{i}', 'uses': [f'L{i - 1}'] if i % 2 else []} for i in range(6)]
        uses = {'L1': 3, 'L4': 2, 'L5': 1}
        cpu = {f't{i}': 1.0 + i for i in range(6)}
        for cap in (0, 3, 5, 9, 30):
            self.assertEqual(M.oracle_at(lib, uses, cpu, cap), R3.oracle_at(lib, uses, cpu, cap))


class GapArm(unittest.TestCase):
    def test_cheaply_derivable_conjectures_are_not_kept_and_both_attempts_are_charged(self):
        pool = Q.true_equations(M.SYSTEM, 3, per_bucket=3, seed=1)[:4]
        texts = [Q.text(e) for e in sorted(pool, key=lambda e: (Q.size(e[0]) + Q.size(e[1]), repr(e)))]
        p = fake_prover(cheap={texts[0]}, full={texts[1], texts[2]})
        out = M.run_gap(pool, Account(M.budget(60), label='t'), prover=p)
        self.assertEqual([l['text'] for l in out['library']], [texts[1], texts[2]])
        self.assertEqual([s['outcome'] for s in out['trajectory']],
                         ['CHEAP_DERIVABLE', 'PROVED', 'PROVED', 'UNPROVED'])
        self.assertEqual(p.calls, [(texts[0], True)] + [(t, c) for t in texts[1:] for c in (True, False)])
        self.assertEqual(out['cpu_s'] > 0, True)

    def test_the_cap_stops_the_arm(self):
        pool = Q.true_equations(M.SYSTEM, 3, per_bucket=3, seed=1)
        p = fake_prover(cheap=set(), full=set(), cpu_ns=4_000_000_000)
        out = M.run_gap(pool, Account(M.budget(15), label='t'), prover=p)
        self.assertEqual(out['library'], [])
        self.assertTrue(out['account']['stop_reason'])
        self.assertLessEqual(out['account']['cpu_ns_total'], 15 * 10 ** 9 + 4 * 10 ** 9)


def synthetic(h60, h30, noise, base=5):
    rows = []
    for i, (a, b, n) in enumerate(zip(h60, h30, noise)):
        rows.append({'seed': i, 'targets': ['t'] * 15, 'empty': {'proved': 0}, 'exhaust': {'proved': 12},
                     'caps': {'60': {'fixed': {'proved': base}, 'oracle': {'proved': base + a}, 'gap': {'proved': base},
                                     'repeat': {'proved': base + n}},
                              '30': {'fixed': {'proved': base}, 'oracle': {'proved': base + b}, 'gap': {'proved': base - 1}}}})
    return rows


class Verdict(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(M.verdict(synthetic([2, 3, 2, 1], [0] * 4, [0] * 4))['verdict'], 'SELECTION_HEADROOM')
        self.assertEqual(M.verdict(synthetic([0] * 4, [3, 2, 2, 1], [0] * 4))['verdict'], 'SELECTION_HEADROOM')
        self.assertEqual(M.verdict(synthetic([1, 0, 1, 1], [0, 1, 0, 0], [1] * 4))['verdict'], 'NO_HEADROOM')
        self.assertEqual(M.verdict(synthetic([2, 2, 1, 1], [0] * 4, [0] * 4))['verdict'], 'WEAK_HEADROOM')
        # headroom no larger than the evaluation noise does not count
        self.assertEqual(M.verdict(synthetic([2, 2, 2, 2], [0] * 4, [2, 1, 2, 1]))['verdict'], 'WEAK_HEADROOM')
        v = M.verdict(synthetic([2, 3, 2, 1], [0] * 4, [0] * 4))
        self.assertEqual(v['per_cap']['30']['gap_minus_fixed'], [-1] * 4)
        self.assertEqual(v['library_headroom'], [12] * 4)
        self.assertEqual(v['ceiling_gap'], [3] * 4)


if __name__ == '__main__':
    unittest.main()
