"""Repair A (B20-REVIEW-01): globally disjoint research and evaluation material.

The original four overlapping evaluation slots are detected from the stored B20 evidence
without any prover. The partition builder rejects exact, alpha-renamed and instance
collisions across seeds, quarantines generalizations, fails explicitly when material runs
out, reconstructs deterministically, admits unrelated tasks, and its insertion screen
covers every route without leaking reserved statements.
"""
import json
from pathlib import Path
import unittest

from genesis.fol import parse
from genesis.learning import equational as Q
from genesis.learning import partitions as P

ROOT = Path(__file__).resolve().parents[1]
B20 = ROOT / 'evidence' / 'learning_b20'
SALT = b'test-salt-0123456789abcdef'


def eq(text):
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    return (f[1], f[2])


def stream(items):
    def sample(unit, system, rng):
        yield from items
    return sample


class OriginalFinding(unittest.TestCase):
    """B20-REVIEW-01 reproduced from the stored setup, no prover involved."""

    def test_the_four_review_slots_are_detected(self):
        material = json.loads((B20 / 'setup.json').read_text())['material']
        ex = P.ExposureSet(P.EquationalAdapter())
        for key, m in material.items():
            system, seed = key.rsplit('@', 1)
            if int(seed) in (101, 102, 103):
                for t in m['dev']:
                    ex.add(system, eq(t), unit=key, route='development')
        ex.freeze()
        slots, unique = [], set()
        for key, m in sorted(material.items()):
            system, seed = key.rsplit('@', 1)
            if int(seed) not in (201, 202, 203, 204):
                continue
            for i, t in enumerate(m['eval']):
                rel, _ = ex.screen(system, eq(t))
                if rel == 'EXACT':
                    slots.append((key, i))
                    unique.add(t)
        self.assertEqual(len(slots), 4)
        self.assertEqual(len(unique), 3)
        self.assertEqual(sorted({k for k, _ in slots}), ['ba_huntington@201', 'ba_huntington@203',
                                                        'ba_huntington@204'])

    def test_audit_record_matches(self):
        f = json.loads((ROOT / 'audit' / 'review_b20' / 'findings.json').read_text())
        r01 = next(x for x in f['findings'] if x['finding'] == 'B20-REVIEW-01')
        self.assertEqual((r01['status'], r01['evaluation_slots'], r01['unique_statements']), ('REPRODUCED', 4, 3))


class Relations(unittest.TestCase):
    def setUp(self):
        self.a = P.EquationalAdapter()

    def test_exact_alpha_instance_generalization(self):
        comm = eq('![X,Y]: s(X,Y) = s(Y,X)')
        self.assertEqual(self.a.relation(comm, comm), 'EXACT')
        self.assertEqual(self.a.relation(eq('![A,B]: s(B,A) = s(A,B)'), comm), 'ALPHA')
        inst = eq('![X,Y]: s(s(X,X),Y) = s(Y,s(X,X))')
        self.assertEqual(self.a.relation(inst, comm), 'INSTANCE')         # candidate is an instance of visible
        self.assertEqual(self.a.relation(comm, inst), 'GENERALIZES')      # visible is an instance of candidate
        self.assertIsNone(self.a.relation(eq('![X]: s(s(X,X),s(X,X)) = X'), comm))

    def test_same_text_in_another_signature_is_another_theory(self):
        self.assertNotEqual(self.a.theory('ba_sheffer'), self.a.theory('ba_huntington'))
        self.assertEqual(self.a.theory('ba_sheffer'), self.a.theory('ba_wolfram'))   # same variety and signature


class Builder(unittest.TestCase):
    system = 'ba_sheffer'

    def visible(self):
        pool = Q.true_equations(self.system, 4, per_bucket=3)
        return [(self.system, e, 'train@1', 'pool') for e in pool], pool

    def _exposure(self, vis):
        ex = P.ExposureSet(P.EquationalAdapter())
        for s, x, u, r in vis:
            ex.add(s, x, unit=u, route=r)
        ex.freeze()
        return ex

    def test_cross_seed_collisions_are_rejected(self):
        vis, pool = self.visible()
        comm = eq('![X,Y]: s(X,Y) = s(Y,X)')
        vis.append((self.system, comm, 'train@1', 'development'))
        renamed = eq('![A,B]: s(B,A) = s(A,B)')
        instance = eq('![X,Y]: s(s(X,X),Y) = s(Y,s(X,X))')
        fresh = Q.sample_targets(self.system, 40, min_total=6, max_total=8, seed=11)
        cands = [comm, renamed, instance] + fresh
        m = P.build_partition(study='t', study_seed=1, visible=vis, units=[('eval@1', self.system)],
                              sampler=stream(cands), count=3)
        rej = m['units']['eval@1']['rejected_counts']
        self.assertGreaterEqual(rej.get('EXACT', 0), 1)
        self.assertGreaterEqual(rej.get('INSTANCE', 0) + rej.get('ALPHA', 0) + rej.get('DUPLICATE_IN_UNIT', 0), 2)
        ex = self._exposure(vis)
        for a in m['units']['eval@1']['accepted']:
            self.assertIsNone(ex.screen(self.system, eq(a['text']))[0])
        self.assertEqual(P.partition_problems(m, vis), [])

    def test_generalization_is_quarantined_with_a_reason(self):
        inst = eq('![X,Y]: s(s(X,X),Y) = s(Y,s(X,X))')
        vis = [(self.system, inst, 'train@1', 'development')]
        comm = eq('![X,Y]: s(X,Y) = s(Y,X)')
        other = eq('![X]: s(s(X,X),s(X,X)) = X')
        m = P.build_partition(study='t', study_seed=1, visible=vis, units=[('eval@1', self.system)],
                              sampler=stream([comm, other]), count=1)
        q = m['units']['eval@1']['quarantined']
        self.assertEqual([x['relation'] for x in q], ['GENERALIZES'])
        self.assertEqual(m['units']['eval@1']['accepted'][0]['text'], Q.text(Q.canon(other)))

    def test_insufficient_material_fails_explicitly(self):
        vis, pool = self.visible()
        with self.assertRaises(P.PartitionError) as cm:
            P.build_partition(study='t', study_seed=1, visible=vis, units=[('eval@1', self.system)],
                              sampler=stream(pool[:5]), count=3)
        self.assertEqual(cm.exception.code, 'INSUFFICIENT_DISTINCT_MATERIAL')
        self.assertEqual(cm.exception.detail['accepted'], 0)

    def test_cross_unit_duplicates_are_rejected(self):
        a = eq('![X]: s(s(X,X),s(X,X)) = X')
        b = eq('![X,Y]: s(X,s(Y,s(Y,Y))) = s(X,X)')
        m = P.build_partition(study='t', study_seed=1, visible=[], units=[('u1', self.system), ('u2', self.system)],
                              sampler=stream([a, b]), count=1)
        self.assertNotEqual(m['units']['u1']['accepted'][0]['text'], m['units']['u2']['accepted'][0]['text'])
        self.assertEqual(m['units']['u2']['rejected_counts'].get('CROSS_UNIT_EXACT'), 1)

    def test_deterministic_reconstruction_and_unrelated_tasks_admitted(self):
        vis, _ = self.visible()
        sampler = P.equational_sampler(min_total=6, max_total=8, max_term=5)
        kw = dict(study='t', study_seed=7, visible=vis, units=[('e1', self.system), ('e2', self.system)],
                  sampler=sampler, count=6)
        m1, m2 = P.build_partition(**kw), P.build_partition(**kw)
        self.assertEqual(m1['partition_id'], m2['partition_id'])
        self.assertEqual(sum(len(u['accepted']) for u in m1['units'].values()), 12)     # not an always-reject
        self.assertEqual(P.partition_problems(m1, vis), [])
        m3 = P.build_partition(**dict(kw, study_seed=8))
        self.assertNotEqual(m1['partition_id'], m3['partition_id'])

    def test_tampering_and_changed_exposure_are_detected(self):
        vis, pool = self.visible()
        m = P.build_partition(study='t', study_seed=7, visible=vis, units=[('e1', self.system)],
                              sampler=P.equational_sampler(min_total=6, max_total=8, max_term=5), count=4)
        bad = json.loads(json.dumps(m))
        bad['units']['e1']['accepted'][0]['text'] = Q.text(pool[0])
        codes = {p['code'] for p in P.partition_problems(bad, vis)}
        self.assertIn('VISIBLE_COLLISION', codes)
        self.assertIn('PARTITION_ID_MISMATCH', codes)
        more = vis + [(self.system, eq(m['units']['e1']['accepted'][1]['text']), 'late', 'memory')]
        codes = {p['code'] for p in P.partition_problems(m, more)}
        self.assertIn('EXPOSURE_ROOT_MISMATCH', codes)
        self.assertIn('VISIBLE_COLLISION', codes)

    def test_policy_must_be_complete(self):
        with self.assertRaises(P.PartitionError):
            P.policy_identity({'EXACT': 'REJECT'})


class Screen(unittest.TestCase):
    system = 'ba_sheffer'
    reserved_text = '![X,Y,Z]: s(s(X,Y),Z) = s(Z,s(X,Y))'          # an instance of commutativity

    def screen(self, **kw):
        return P.InsertionScreen([(self.system, eq(self.reserved_text))], salt=SALT, **kw)

    def test_blocks_related_insertions_on_every_route(self):
        sc = self.screen()
        target = eq(self.reserved_text)
        general = eq('![X,Y]: s(X,Y) = s(Y,X)')          # the reserved target is an instance of it
        for route in ('lemma', 'macro_step', 'memory', 'curriculum', 'import', 'pool', 'development'):
            self.assertEqual(sc(route, self.system, target), {'decision': 'BLOCK'})
            self.assertEqual(sc(route, self.system, general), {'decision': 'BLOCK'})
        unrelated = eq('![X]: s(s(X,X),s(X,X)) = X')
        self.assertEqual(sc('lemma', self.system, unrelated), {'decision': 'ALLOW'})
        self.assertEqual(sc('lemma', 'ba_huntington', eq('![X,Y]: plus(X,Y) = plus(Y,X)')), {'decision': 'ALLOW'})

    def test_fails_closed_and_leaks_nothing(self):
        sc = self.screen(query_budget=3)
        self.assertEqual(sc('unknown-route', self.system, eq(self.reserved_text)), {'decision': 'BLOCK'})
        self.assertEqual(sc('lemma', self.system, ('garbage',)), {'decision': 'BLOCK'})
        sc('lemma', self.system, eq('![X]: s(s(X,X),s(X,X)) = X'))
        self.assertEqual(sc('lemma', self.system, eq('![X]: s(s(X,X),s(X,X)) = X')), {'decision': 'BLOCK'})
        public = json.dumps([sc.commitment(), sc.summary()])
        reserved = Q.text(Q.canon(eq(self.reserved_text)))
        for needle in (reserved, self.reserved_text, 's(s(X,Y),Z)'):
            self.assertNotIn(needle, public)
        self.assertNotIn(reserved, json.dumps(sc.private_ledger()))      # even the private ledger holds digests
        with self.assertRaises(P.PartitionError):
            P.InsertionScreen([], salt=b'short')

    def test_commitment_is_salted(self):
        a = P.InsertionScreen([(self.system, eq(self.reserved_text))], salt=SALT).commitment()
        b = P.InsertionScreen([(self.system, eq(self.reserved_text))], salt=SALT[::-1]).commitment()
        self.assertNotEqual(a['root'], b['root'])


class Contamination(unittest.TestCase):
    def test_exposed_panel_items_mark_the_unit_contaminated(self):
        m = P.build_partition(study='t', study_seed=1, visible=[], units=[('u1', 'ba_sheffer'), ('u2', 'ba_sheffer')],
                              sampler=P.equational_sampler(min_total=6, max_total=8, max_term=5), count=2)
        sha = m['units']['u1']['accepted'][0]['structural_sha256']
        lab = P.contamination_label(m, [('u1', sha, 'memory')])
        self.assertEqual(lab['u1']['status'], 'CONTAMINATED')
        self.assertEqual(lab['u2']['status'], 'CLEAN')


if __name__ == '__main__':
    unittest.main()
