"""Genesis Ω contract §9, §16.7: the interpretation engine. Exact simplification under declared ranges (B20_R129's
invented rule reduces to `max decall * pf^2` and behaves identically); a conjecture from agreement on a few worlds is
refuted by a counterexample on more; the conjecture is its own vault artifact, rejected, while the original rule's
bytes are untouched; ablation names the parts a rule depends on."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import interpret as I  # noqa: E402
from genesis import vault as V  # noqa: E402

INV1 = {'agg': 'max', 'expr': ['*', ['sqrt', ['sq', 'decall']], ['sq', ['min', 'pf', 1.0]]]}
DECFALL = {'agg': 'sum', 'expr': 'decfall'}


def domains(n, seed0):
    from genesis.causal import active3 as A3
    from genesis.causal import sem as S
    out = []
    for s in range(seed0, seed0 + n):
        view, truth = S.instance(s, 8, 2, 0.3, 'gauss', 3, 1500)
        out.append(A3.CausalDomain(A3.prepare(view, truth, 500, s), A3.THEORY))
    return out


class Interpret(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doms = domains(12, 4100)

    def test_simplification_is_exact_and_behaviour_preserving(self):
        simp, used = I.simplify(INV1)
        self.assertEqual(simp, {'agg': 'max', 'expr': ['*', 'decall', ['sq', 'pf']]})
        self.assertIn('sqrt(sq(x)) = x for x >= 0', used)
        self.assertIn('min(x, y) = x when x <= y everywhere', used)
        self.assertEqual(I.fingerprint(INV1, self.doms, 6), I.fingerprint(simp, self.doms, 6))
        # ranges matter: a feature that can be negative is not simplified
        neg = {'agg': 'sum', 'expr': ['sqrt', ['sq', ['-', 'eig', 'dec']]]}
        self.assertEqual(I.simplify(neg)[0], neg)

    def test_intervals(self):
        self.assertEqual(I.interval(['min', 'pf', 1.0]), (0.0, 1.0))
        self.assertEqual(I.interval(['-', 'pf', 'maxp']), (-1.0, 1.0))
        self.assertEqual(I.interval(['inv1', 'seen'])[1], 1.0)

    def test_conjecture_refuted_original_untouched(self):
        few, more = self.doms[:2], self.doms
        agree = [k for k in range(len(few)) if I.fingerprint(INV1, [few[k]], 1) == I.fingerprint(DECFALL, [few[k]], 1)]
        with tempfile.TemporaryDirectory() as d, V.Vault(Path(d) / 'v') as v:
            orig = v.put(V.Vault.record('ProgramSpec', {'language': 'science.acquire', 'source': INV1},
                                        domain='causal', creator={'process': 'test'}))
            raw = v.raw(orig)
            conj = v.put(V.Vault.record('DiscoveryRecord', {
                'kind': 'conjecture', 'statement': 'inv1 chooses the same experiments as decfall',
                'support': {'domains_agreeing_on_first_choice': agree}}, domain='causal',
                creator={'process': 'interpret'}, parents=[orig]))
            k = I.test_conjecture(INV1, DECFALL, more, 6)
            self.assertIsNotNone(k)                                     # a counterexample exists
            ev = v.put(V.Vault.record('EvidenceRecord', {'counterexample_domain': k, 'study': 'unit',
                                                        'record_test': 'test_interpret'}, domain='causal',
                                      creator={'process': 'interpret'}, parents=[conj]))
            v.annotate(conj, status='rejected', evidence=[ev], reason=f'counterexample on domain {k}')
            v.edge('contradicts', ev, conj, evidence=[ev], confidence=1.0, scope='these domains', provenance={})
            self.assertEqual(v.status(conj)['status'], 'rejected')
            self.assertEqual(v.raw(orig), raw)                          # the original is unchanged
            self.assertEqual(v.status(orig)['status'], 'generated')

    def test_ablation(self):
        def score(prog):
            fp = I.fingerprint(prog, self.doms[:4], 3)
            return sum(len(set(x) & set(y)) for x, y in zip(fp, I.fingerprint(INV1, self.doms[:4], 3)))
        rows = I.ablate(INV1, score)
        self.assertEqual(len(rows), 7)                                  # every proper subtree (8 nodes)
        self.assertTrue(all(len(r) == 4 for r in rows))


if __name__ == '__main__':
    unittest.main()
