"""Repair C (B20-REVIEW-03): successor proofs are in custody before they are counted.

A real research run (pinned E) produces a successor and scored targets; every scored
proof is recoverable from a content-addressed store; replay rebuilds the Lean chain from
the manifest and objects alone (never re-running proof search) and binds the checked
theorem to the requested statement. Tampering, wrong targets, omitted premises, foreign
lemmas, revocation, checker timeouts and environment changes are all caught. Requires E
and the formal workspace; missing tools fail (formal suite: no skips).
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from genesis.learning import custody as C
from genesis.learning import equational as Q
from genesis.learning import research as RS
from genesis.learning.budget import Account, StudyBudget
from genesis.verification.tools import tool


class _Fixture:
    built = None

    @classmethod
    def get(cls):
        if cls.built is None:
            tool('eprover')                      # fail, not skip, when the pinned prover is absent
            s = 'ba_sheffer'
            tmp = tempfile.mkdtemp(prefix='custody-')
            objs = C.ObjectStore(Path(tmp) / 'objects')
            pool = Q.true_equations(s, 4, per_bucket=3)
            T = Q.sample_targets(s, 6, min_total=6, max_total=8, seed=9, exclude=pool)
            run = RS.run(s, RS.Fixed(), pool, account=Account(StudyBudget.from_seconds(60, attempt_s=1), label='cust'),
                         dev_targets=T, run_id='custody-test-run')
            ev = RS.evaluate_successor(s, run['library'], T, eval_s=1)
            man = C.successor_manifest(run, objs)
            recs = C.target_records(ev, man, objs, panel_id='custody-test')
            empty = dict(run, library=[], run_id='custody-test-empty')
            ev0 = RS.evaluate_successor(s, [], T, eval_s=1)
            man0 = C.successor_manifest(empty, objs)
            recs0 = C.target_records(ev0, man0, objs, panel_id='custody-test')
            cls.built = dict(system=s, tmp=tmp, objs=objs, pool=pool, T=T, run=run, ev=ev, man=man, recs=recs,
                             man0=man0, recs0=recs0)
        return cls.built


def chain_record(f):
    return next(r for r in f['recs'] if r['prover_reported'] and r['closure_uids'])


def axiom_record(f):
    return next(r for r in f['recs0'] if r['prover_reported'])


def rehash(obj, key):
    obj[key] = C.digest({k: v for k, v in obj.items() if k != key})
    return obj


class Custody(unittest.TestCase):
    def setUp(self):
        self.f = _Fixture.get()

    def test_every_scored_proof_is_recoverable_and_bound(self):
        self.assertEqual(C.successor_problems(self.f['man'], self.f['objs']), [])
        reported = [r for r in self.f['recs'] if r['prover_reported']]
        self.assertTrue(reported)
        for r in reported:
            self.assertTrue(self.f['objs'].has(r['proof_sha256']))
            self.assertEqual(C.target_problems(r, self.f['man'], task_statement=r['statement'],
                                               objects=self.f['objs']), [])
        for lem in self.f['man']['lemmas']:
            self.assertTrue(self.f['objs'].has(lem['proof_sha256']))

    def test_wrong_target_with_a_valid_proof(self):
        r = chain_record(self.f)
        other = next(x['statement'] for x in self.f['recs'] if x['statement'] != r['statement'])
        out = C.replay_target(r, self.f['man'], self.f['objs'], task_statement=other)
        self.assertEqual(out['status'], 'REJECTED_CUSTODY')
        self.assertIn('WRONG_TARGET', out['problems'])

    def test_tampered_ancestor_and_corrupted_object(self):
        man = json.loads(json.dumps(self.f['man']))
        r = chain_record(self.f)
        victim = next(l for l in man['lemmas'] if l['uid'] in r['closure_uids'])
        victim['statement'] = '![X]: (s(s(X,X),s(X,X)) = X)'          # a different (true) lemma, same uid
        rehash(man, 'manifest_id')
        self.assertIn('UID_MISMATCH', {p['code'] for p in C.successor_problems(man, self.f['objs'])})
        d = Path(tempfile.mkdtemp())
        shutil.copytree(self.f['objs'].root, d / 'o')
        bad = C.ObjectStore(d / 'o')
        (bad.root / victim['proof_sha256']).write_bytes(b'corrupted')
        self.assertIn('PROOF_MISSING_OR_ALTERED', {p['code'] for p in C.successor_problems(self.f['man'], bad)})
        (bad.root / r['proof_sha256']).unlink()
        out = C.replay_target(r, self.f['man'], bad, task_statement=r['statement'])
        self.assertEqual(out['status'], 'REJECTED_CUSTODY')

    def test_omitted_premise_and_foreign_lemma(self):
        r = chain_record(self.f)
        man = json.loads(json.dumps(self.f['man']))
        used = r['lemmas_used_uids'][0]
        man['lemmas'] = [l for l in man['lemmas'] if l['uid'] != used]
        rehash(man, 'manifest_id')
        r2 = rehash(dict(r, manifest_id=man['manifest_id']), 'record_id')
        codes = {p['code'] for p in C.target_problems(r2, man, task_statement=r['statement'], objects=self.f['objs'])}
        self.assertIn('FOREIGN_OR_MISSING_PREMISE', codes)

    def test_duplicate_local_name_from_another_run(self):
        man = json.loads(json.dumps(self.f['man']))
        man['lemmas'].append(dict(man['lemmas'][0], uid=C.digest('another run')))     # same local name L0
        rehash(man, 'manifest_id')
        codes = {p['code'] for p in C.successor_problems(man, self.f['objs'])}
        self.assertIn('DUPLICATE_LOCAL_NAME', codes)
        self.assertIn('UID_MISMATCH', codes)                              # uids are bound to their run

    def test_changed_axioms_are_disallowed(self):
        man = json.loads(json.dumps(self.f['man']))
        man['axioms'] = man['axioms'][:-1]
        rehash(man, 'manifest_id')
        self.assertIn('DISALLOWED_AXIOMS', {p['code'] for p in C.successor_problems(man, self.f['objs'])})

    def test_revoked_lemma_blocks_dependent_targets(self):
        r = chain_record(self.f)
        tc = {'revoked_uids': [r['closure_uids'][0]]}
        out = C.replay_target(r, self.f['man'], self.f['objs'], task_statement=r['statement'], trust_context=tc)
        self.assertEqual(out['status'], 'REJECTED_CUSTODY')
        self.assertIn('REVOKED_ANCESTOR', out['problems'])
        s = C.score([r], {r['record_id']: {'status': 'CHECKED'}}, trust_context=tc)
        self.assertEqual((s['prover_reported'], s['checked'], s['eligible']), (1, 0, 0))

    def test_checker_timeout_is_incomplete_not_false(self):
        r = chain_record(self.f)
        out = C.replay_target(r, self.f['man'], self.f['objs'], task_statement=r['statement'],
                              replay_fn=lambda *a, **k: {'status': 'NOT_REPLAYED', 'outcome': 'TIMEOUT'})
        self.assertEqual(out['status'], 'CHECK_INCOMPLETE')
        s = C.score([r], {r['record_id']: out})
        self.assertEqual((s['checked'], s['check_incomplete']), (0, 1))
        crash = C.replay_target(r, self.f['man'], self.f['objs'], task_statement=r['statement'],
                                replay_fn=lambda *a, **k: (_ for _ in ()).throw(OSError('sandbox down')))
        self.assertEqual(crash['status'], 'CHECK_INFRASTRUCTURE_ERROR')

    def test_three_metrics_are_kept_apart(self):
        r = chain_record(self.f)
        late = dict(r, budget_eligible=False, record_id='late')
        hidden = dict(r, exposure_ok=False, record_id='hidden')
        checks = {x['record_id']: {'status': 'CHECKED', 'checker': 'k1'} for x in (r, late, hidden)}
        s = C.score([r, late, hidden], checks)
        self.assertEqual((s['prover_reported'], s['checked'], s['eligible']), (3, 3, 1))
        s = C.score([r], checks, trust_context={'checker_identity': 'k2'})
        self.assertEqual((s['checked'], s['needs_recheck_environment']), (0, 1))
        s = C.score([r], checks, trust_context={'revoked_checkers': ['k1']})
        self.assertEqual(s['checked'], 0)


class LeanReplay(unittest.TestCase):
    """Real Lean replays from custody (a lemma chain and an axioms-only proof)."""

    def setUp(self):
        self.f = _Fixture.get()

    def _replay_without_producer(self, rec, man):
        def refuse(*a, **k):
            raise AssertionError('replay must not invoke proof search')
        with mock.patch('genesis.verification.eprover.prove', refuse), \
                mock.patch('genesis.verification.eprover.prove_bounded', refuse):
            return C.replay_target(rec, man, self.f['objs'], task_statement=rec['statement'],
                                   trust_context={'checker_identity': C.checker_identity()['identity']})

    def test_lemma_chain_target_replays_from_custody(self):
        r = chain_record(self.f)
        out = self._replay_without_producer(r, self.f['man'])
        self.assertEqual(out['status'], 'CHECKED', out)
        self.assertGreaterEqual(out['chain_lemmas'], 1)
        s = C.score(self.f['recs'], {r['record_id']: out},
                    trust_context={'checker_identity': C.checker_identity()['identity']})
        self.assertEqual(s['checked'], 1)

    def test_axioms_only_target_still_needs_and_gets_acceptance(self):
        r = axiom_record(self.f)
        self.assertEqual(r['closure_uids'], [])
        out = self._replay_without_producer(r, self.f['man0'])
        self.assertEqual(out['status'], 'CHECKED', out)


if __name__ == '__main__':
    unittest.main()
