"""B20_R4 (H08, B14-OPEN-3, B20R-OPEN-2): campaigns write research-lineage records, the export
completes and checks them from the event log, and the custodian accepts a generation-evaluation
request only for a qualifying transition.

Real DEV campaigns (small configuration), real crashes (genesis.faults) and a real custodian
registration and evaluation with a fixture key. Nothing here is GV5 evidence: the panels are
builder-generated and the custodian is the builder's.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from genesis import lineage as L
from genesis.campaign import Campaign
from genesis.common import digest, load_json
from genesis.models import Config
from tests_genesis.test_crash_consistency import crash

CFG = dict(seed=20261101, generations=3, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8)


def rehash_run(ex, rid, **changes):
    """Edit a run record, recompute its identity and repoint its transitions (a consistent forgery)."""
    run = dict(ex['runs'].pop(rid), **changes)
    body = {k: v for k, v in run.items() if k != 'run_id'}
    run = dict(body, run_id=digest(body))
    ex['runs'][run['run_id']] = run
    for i, t in enumerate(ex['transitions']):
        if t['research_run'] == rid:
            tb = {k: v for k, v in t.items() if k != 'transition_id'}
            tb['research_run'] = run['run_id']
            ex['transitions'][i] = dict(tb, transition_id=digest(tb))
    return run


def rehash_transition(ex, i, **changes):
    tb = {k: v for k, v in ex['transitions'][i].items() if k != 'transition_id'}
    tb.update(changes)
    ex['transitions'][i] = dict(tb, transition_id=digest(tb))


class NativeLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'campaign'
        Campaign.initialize(cls.root, Config(**CFG))
        with Campaign(cls.root) as c:
            cls.summary = c.run()
            cls.ex = L.export_from_store(c.store)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def codes(self, ex):
        return {p['code'] for p in L.lineage_problems(ex)}

    def test_records_are_native_and_clean(self):
        self.assertEqual(self.ex['source'], 'native')
        self.assertEqual(len(self.ex['runs']), CFG['generations'])
        self.assertEqual(L.lineage_problems(self.ex), [])
        retained = sum(g['retained_in_dev'] for g in self.summary['generations'])
        self.assertEqual(len(L.accepted_chain(self.ex)['transitions']), retained)

    def test_versions_carry_lineage_depth(self):
        for t in self.ex['transitions']:
            a, b = self.ex['versions'][t['from_version']], self.ex['versions'][t['to_version']]
            self.assertEqual(b['generation'], a['generation'] + 1)
            self.assertEqual(b['parent'], t['from_version'])

    def test_candidates_are_bound_to_select_trials_and_scores_recomputed(self):
        for run in self.ex['runs'].values():
            self.assertEqual(sorted(c['policy'] for c in run['candidates']), ['adaptive', 'uniform'])
            for c in run['candidates']:
                self.assertEqual(c['score_recomputed'], c['score'])
                self.assertEqual(c['attempt_problems'], [])
                self.assertEqual(len(c['attempt_ids']), CFG['tasks_per_panel'])
                self.assertTrue(set(c['attempt_ids']) <= set(run['attempts']))
            self.assertIn(run['selection']['selected'], {c['identity'] for c in run['candidates']})

    def test_account_recomputed_from_receipts(self):
        for run in self.ex['runs'].values():
            self.assertEqual(run['account_recomputed_sha256'], run['account_sha256'])
            self.assertTrue(run['account']['within_cap'])
            self.assertEqual(run['unledgered_attempts'], [])
            self.assertLessEqual(max(run['account']['research_trials_by_policy'].values()), CFG['research_trials'])

    def test_export_zip_gives_the_same_records(self):
        from genesis.cli import export_replication
        out = Path(self.tmp.name) / 'export.zip'
        with Campaign(self.root) as c:
            export_replication(self.root, out, store=c.store)
        self.assertEqual(L.export_from_campaign_zip(out), self.ex)

    def test_forged_records_are_rejected(self):
        rid = next(iter(self.ex['runs']))
        run = self.ex['runs'][rid]
        cases = []
        ex = copy.deepcopy(self.ex)                       # a better recorded score than the receipts show
        cands = copy.deepcopy(run['candidates']); cands[0]['score'] += 5
        rehash_run(ex, rid, candidates=cands); cases.append((ex, 'SELECTION_RULE_VIOLATED'))
        ex = copy.deepcopy(self.ex)                       # an edited account
        acct = dict(run['account'], cpu_ns=1)
        rehash_run(ex, rid, account=acct); cases.append((ex, 'BUDGET_UNACCOUNTED'))
        ex = copy.deepcopy(self.ex)                       # an account claiming to be within cap when it is not
        acct = dict(run['account'], within_cap=False)
        rehash_run(ex, rid, account=acct, account_sha256=digest(acct), account_recomputed_sha256=digest(acct))
        cases.append((ex, 'BUDGET_EXCEEDED'))
        ex = copy.deepcopy(self.ex)                       # a candidate trial dropped from the ledger
        rehash_run(ex, rid, attempts=[a for a in run['attempts'] if a != run['candidates'][0]['attempt_ids'][0]])
        cases.append((ex, 'LEDGER_INCOMPLETE'))
        ex = copy.deepcopy(self.ex)                       # an undeclared component change
        rehash_transition(ex, 0, declared_changes=['solver'])
        if set(self.ex['transitions'][0]['declared_changes']) != {'solver'}:
            cases.append((ex, 'DECLARED_CHANGES_MISMATCH'))
        for forged, code in cases:
            self.assertIn(code, self.codes(forged), code)
            self.assertNotEqual(L.accepted_chain(forged)['transitions'], L.accepted_chain(self.ex)['transitions'])


class DishonestCampaign(unittest.TestCase):
    def test_an_attempt_kept_out_of_the_ledger_is_found_in_the_event_log(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(**dict(CFG, generations=1)))
            real, seen = Campaign._note, []

            def leaky(self, aid):
                seen.append(aid)
                if len(seen) != 5:
                    real(self, aid)
            with mock.patch.object(Campaign, '_note', leaky):
                with Campaign(root) as c:
                    c.run()
                    ex = L.export_from_store(c.store)
            run = next(iter(ex['runs'].values()))
            self.assertEqual(run['unledgered_attempts'], [seen[4]])
            self.assertIn('LEDGER_INCOMPLETE', {p['code'] for p in L.lineage_problems(ex)})
            self.assertEqual(L.accepted_chain(ex)['transitions'], [])


class ResumedCampaigns(unittest.TestCase):
    def check(self, fault):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(**dict(CFG, generations=2)))
            crash(self, '''
                from genesis.campaign import Campaign
                with Campaign(P['root']) as c: c.run()
            ''', fault, root=str(root))
            with Campaign(root) as c:
                c.run(resume=True)
                ex = L.export_from_store(c.store)
                interrupted = [a for (a,) in c.store.db.execute("SELECT id FROM attempts WHERE status='INTERRUPTED'")]
        self.assertEqual(L.lineage_problems(ex), [])
        return ex, interrupted

    def test_crash_mid_research_charges_the_interrupted_attempt_to_the_run(self):
        ex, interrupted = self.check('campaign.trial:7')
        self.assertEqual(len(interrupted), 1)
        run = min(ex['runs'].values(), key=lambda r: r['round'])
        self.assertIn(interrupted[0], run['attempts'])
        self.assertEqual(run['account']['statuses'].get('INTERRUPTED'), 1)
        self.assertEqual(run['account']['cost_unknown_attempts'], 1)

    def test_crash_after_freeze_keeps_the_frozen_successor_and_a_clean_lineage(self):
        ex, interrupted = self.check('campaign.frozen')
        self.assertEqual(interrupted, [])
        self.assertEqual(len(ex['transitions']), 2)


class CustodianGenerationRequests(unittest.TestCase):
    """The custodian's export check for sealed_generation_evaluation (custodian.generation_problems)."""

    @classmethod
    def setUpClass(cls):
        from genesis.cli import generation_request_bundle
        from genesis.custodian import campaign_facts
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'campaign'
        Campaign.initialize(cls.root, Config(**CFG))
        with Campaign(cls.root) as c:
            c.run()
            ex = L.export_from_store(c.store)
            cls.changing = [t['index'] for t in ex['transitions'] if t['decision'] == 'ACCEPTED'
                            and ex['versions'][t['to_version']]['solver'] != ex['versions'][t['from_version']]['solver']]
            cls.same = [t['index'] for t in ex['transitions'] if t['decision'] == 'ACCEPTED'
                        and ex['versions'][t['to_version']]['solver'] == ex['versions'][t['from_version']]['solver']]
            cls.request = load_json(generation_request_bundle(c, cls.changing[0], 3))
        cls.export = cls.root / 'exports' / 'campaign_export.zip'
        cls.facts = campaign_facts(cls.export)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def problems(self, request):
        from genesis.custodian import check_request_against_export
        return check_request_against_export(request, self.facts)

    def test_campaign_has_a_program_changing_transition(self):
        self.assertTrue(self.changing)

    def test_qualifying_transition_passes_the_export_check(self):
        self.assertEqual(self.facts['lineage']['source'], 'native')
        self.assertEqual(self.problems(self.request), [])

    def test_other_transitions_or_arms_are_refused(self):
        r = copy.deepcopy(self.request)
        r['generation_transition'] = dict(r['generation_transition'], index=r['generation_transition']['index'] + 7)
        self.assertTrue(any('not a qualifying transition' in p for p in self.problems(r)))
        r = copy.deepcopy(self.request)
        r['programs'] = {'candidate': r['programs']['baseline'], 'baseline': r['programs']['candidate']}
        why = self.problems(r)
        self.assertTrue(any('candidate arm' in p for p in why) and any('baseline arm' in p for p in why))
        r = copy.deepcopy(self.request)
        r['generation_transition'] = dict(r['generation_transition'], from_version='0' * 64)
        self.assertTrue(any('not a qualifying transition' in p for p in self.problems(r)))

    def test_transition_that_keeps_the_program_is_refused(self):
        self.assertTrue(self.same)                         # deterministic for CFG: transitions 2 and 3
        from genesis.custodian import generation_problems
        t = next(x for x in self.facts['lineage']['transitions'] if x.get('index') == self.same[0])
        r = copy.deepcopy(self.request)
        v = self.facts['lineage']['versions']
        r['generation_transition'] = {'index': t['index'], 'from_version': t['from_version'], 'to_version': t['to_version']}
        r['programs'] = {'candidate': v[t['to_version']]['solver'], 'baseline': v[t['from_version']]['solver']}
        self.assertTrue(any('does not change the evaluated program' in p for p in generation_problems(r, self.facts)))

    def test_forged_lineage_in_the_facts_is_refused(self):
        facts = copy.deepcopy(self.facts)
        rid = next(iter(facts['lineage']['runs']))
        run = facts['lineage']['runs'][rid]
        acct = dict(run['account'], cpu_ns=0)
        rehash_run(facts['lineage'], rid, account=acct)
        from genesis.custodian import generation_problems
        why = generation_problems(self.request, facts)
        self.assertTrue(why and 'BUDGET_UNACCOUNTED' in why[0])

    def test_improver_kind_is_still_refused(self):
        r = dict(self.request, evidence_kind='sealed_improver_evaluation', generation_transition=None)
        self.assertTrue(any('sealed_improver_evaluation' in p and 'refused' in p for p in self.problems(r)))


from tests_genesis.test_custodian_registry import Fixture  # noqa: E402


class EndToEndGenerationEvaluation(Fixture):
    """Register and evaluate a generation request at a (fixture-key) custodian: the sealed
    receipt names the transition and compares the child's solver with the parent's."""

    def test_generation_request_registers_and_evaluates(self):
        from genesis.cli import generation_request_bundle
        from genesis.custodian import evaluate, register, verify
        root = self.base / 'campaign'
        Campaign.initialize(root, Config(**dict(CFG, generations=1)))
        with Campaign(root) as c:
            c.run()
            request = load_json(generation_request_bundle(c, 1, 2))
        export = root / 'exports' / 'campaign_export.zip'
        from genesis.exposure import GraphIndex, campaign_hosts
        from genesis.research import make_panel
        seen = GraphIndex()
        for k, es in campaign_hosts(export):
            seen.add(k, es, 'campaign')
        tasks = [t for t in make_panel(9917, 40, 'c4_host_v2', 'CONFIRM')[0]
                 if seen.find(t.n, t.edges) is None and not seen.near(t.n, t.edges)][:2]
        self.assertEqual(len(tasks), 2)
        pool = self.pool(tasks, 'gen_pool.json')
        anchor = register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest,
                          campaign_export=export, pool=pool)
        self.assertEqual(verify(anchor, self.public)['evidence_kind'], 'sealed_generation_evaluation')
        receipt = verify(evaluate(self.root, digest(request), pool, self.key, 'fixture'), self.public)
        self.assertEqual(receipt['evidence_kind'], 'sealed_generation_evaluation')
        self.assertEqual(receipt['generation_transition'], request['generation_transition'])
        self.assertEqual(receipt['candidate_version'], request['generation_transition']['to_version'])
        self.assertTrue(receipt['raw_evidence_complete'])
        self.assertEqual(receipt['completed_rows'], 4)


if __name__ == '__main__':
    unittest.main()
