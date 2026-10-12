"""H08 (W21, B14-OPEN-3): research-lineage records and their validator.

A deterministic DEV fixture of three transitions validates and forms a qualifying chain
(labelled a fixture: it is not GV5 evidence). Every adversarial case from the handoff's
s20.7 list is rejected with a stable problem code and stops the qualifying chain.
"""
import copy
import unittest

from genesis import lineage as LN
from genesis.common import digest
from genesis.kernel.version import SystemVersion


def version(gen, parent, rounds, **over):
    v = SystemVersion(generation=gen, parent=parent, solver={'rounds': rounds}, tool_library=(),
                      memory_snapshot=f'head-{gen}-{rounds}', curriculum_policy={}, research_policy={'policy': 'uniform'},
                      model_configuration=None, cognitive_kernel='ck-v1', verifier_set={'drat-trim': 'h1'},
                      resolved_config={}, dependency_lock='lock-1', environment_digest='env-1',
                      source='src-1').model_dump(mode='json')
    v.update(over)
    return digest(v), v


def fixture():
    """v0 -> v1 -> v2 -> v3, one research run per transition, plus a rejected DEV branch."""
    versions, frozen, runs, ts = {}, {}, {}, []
    v0, d0 = version(0, None, 4)
    versions[v0], frozen[v0] = d0, 1
    parent, clock = v0, 1
    for i, rounds in enumerate((8, 16, 32), start=1):
        vid, d = version(i, parent, rounds)
        run = LN.run_record(parent_version=parent, policy_identity='uniform', permitted_inputs={'exposure_root': 'x'},
                            seed=100 + i, budget_sha256='b', account_sha256=f'acct-{i}',
                            attempts=[f'a{i}-1', f'a{i}-2'],
                            candidates=[{'identity': vid, 'score': 10 + i, 'attempt_id': f'a{i}-1'},
                                        {'identity': f'prog-{i}-alt', 'score': 5, 'attempt_id': f'a{i}-2'}],
                            selection={'rule': 'max_score_then_lowest_identity', 'selected': vid},
                            interventions=[], start_event=clock + 1, end_event=clock + 2)
        runs[run['run_id']] = run
        versions[vid], frozen[vid] = d, clock + 3
        ts.append(LN.transition_record(index=i, from_version=parent, to_version=vid, research_run=run['run_id'],
                                       declared_changes=['solver'], panel_id=f'P{i}', receipt_id=f'R{i}',
                                       claim_id='c', plan_id='p', receipt_event=clock + 4, decision='ACCEPTED'))
        parent, clock = vid, clock + 4
    # a rejected DEV branch from v1 does not break the chain
    vb, db = version(2, ts[0]['to_version'], 12)
    versions[vb], frozen[vb] = db, 50
    rb = LN.run_record(parent_version=ts[0]['to_version'], policy_identity='adaptive', permitted_inputs={}, seed=7,
                       budget_sha256='b', account_sha256='acct-branch', attempts=['ab'],
                       candidates=[{'identity': vb, 'score': 1, 'attempt_id': 'ab'}],
                       selection={'rule': 'max_score_then_lowest_identity', 'selected': vb}, interventions=[],
                       start_event=48, end_event=49)
    runs[rb['run_id']] = rb
    ts.append(LN.transition_record(index=2, from_version=ts[0]['to_version'], to_version=vb, research_run=rb['run_id'],
                                   declared_changes=['solver'], panel_id='PB', receipt_id='RB', claim_id='c', plan_id='p',
                                   receipt_event=51, decision='REJECTED'))
    return {'versions': versions, 'frozen_at': frozen, 'runs': runs, 'transitions': ts}


def rehash_t(t):
    return LN.transition_record(**{k: v for k, v in t.items() if k not in ('transition_id', 'schema')})


def rehash_run(r):
    return LN.run_record(**{k: v for k, v in r.items() if k not in ('run_id', 'schema')})


def codes(export, tc=None):
    return {p['code'] for p in LN.lineage_problems(export, tc)}


class Positive(unittest.TestCase):
    def test_three_transition_fixture_forms_a_chain(self):
        ex = fixture()
        self.assertEqual(LN.lineage_problems(ex), [])
        chain = LN.accepted_chain(ex)
        self.assertEqual(len(chain['transitions']), 3)
        self.assertIsNone(chain['stopped_at'])
        self.assertIn('not GV5 evidence', chain['note'])


class Attacks(unittest.TestCase):
    def setUp(self):
        self.ex = fixture()
        self.acc = [t for t in self.ex['transitions'] if t['decision'] == 'ACCEPTED']

    def assertRejected(self, ex, code, tc=None):
        self.assertIn(code, codes(ex, tc))
        self.assertLess(len(LN.accepted_chain(ex, tc)['transitions']), 3)

    def test_duplicate_receipt_wrappers(self):
        ex = copy.deepcopy(self.ex)
        t = dict(self.acc[1], plan_id='another wrapper')
        ex['transitions'].append(rehash_t(t))                     # same transition, new wrapper id
        self.assertIn('DUPLICATE_TRANSITION', codes(ex))
        self.assertRejected(ex, 'RECEIPT_REUSED')

    def test_reordered_generations(self):
        ex = copy.deepcopy(self.ex)
        a, b = self.acc[1], self.acc[2]
        ex['transitions'] = [self.acc[0], rehash_t(dict(a, index=3)), rehash_t(dict(b, index=2))] + \
            [t for t in ex['transitions'] if t['decision'] != 'ACCEPTED']
        self.assertRejected(ex, 'CHAIN_ORDER')

    def test_missing_parent(self):
        ex = copy.deepcopy(self.ex)
        del ex['versions'][self.acc[0]['from_version']]
        self.assertRejected(ex, 'VERSION_MISSING')

    def test_same_artifact_with_changed_generation_label(self):
        ex = copy.deepcopy(self.ex)
        last = self.acc[2]
        same = dict(ex['versions'][last['to_version']], generation=4, parent=last['to_version'], memory_snapshot='h')
        vid = digest(same)
        ex['versions'][vid], ex['frozen_at'][vid] = same, 200
        run = rehash_run(dict(ex['runs'][last['research_run']], parent_version=last['to_version'],
                              candidates=[{'identity': vid, 'score': 1, 'attempt_id': 'z'}], attempts=['z'],
                              selection={'rule': 'max_score_then_lowest_identity', 'selected': vid},
                              account_sha256='acct-z', start_event=150, end_event=160))
        ex['runs'][run['run_id']] = run
        ex['transitions'].append(LN.transition_record(index=4, from_version=last['to_version'], to_version=vid,
                                                      research_run=run['run_id'], declared_changes=[], panel_id='P4',
                                                      receipt_id='R4', claim_id='c', plan_id='p', receipt_event=201,
                                                      decision='ACCEPTED'))
        self.assertIn('LABEL_ONLY_CHANGE', codes(ex))
        self.assertEqual(len(LN.accepted_chain(ex)['transitions']), 3)   # the label-only fourth does not count

    def test_foreign_policy_run(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[1]
        run = rehash_run(dict(ex['runs'][t['research_run']], parent_version=self.acc[2]['to_version']))
        ex['runs'][run['run_id']] = run
        i = ex['transitions'].index(t)
        ex['transitions'][i] = rehash_t(dict(t, research_run=run['run_id']))
        self.assertRejected(ex, 'FOREIGN_RUN')

    def test_swapped_child(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[0]
        branch = next(x for x in ex['transitions'] if x['decision'] == 'REJECTED')
        i = ex['transitions'].index(t)
        ex['transitions'][i] = rehash_t(dict(t, to_version=branch['to_version']))
        self.assertRejected(ex, 'SELECTED_MISMATCH')

    def test_repeated_panel(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[2]
        ex['transitions'][ex['transitions'].index(t)] = rehash_t(dict(t, panel_id='P1'))
        self.assertRejected(ex, 'PANEL_REUSED')

    def test_undeclared_manual_patch(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[1]
        child = dict(ex['versions'][t['to_version']], source='src-patched-by-hand')
        self.assertIn('VERSION_ID_MISMATCH', codes(dict(ex, versions=dict(ex['versions'], **{t['to_version']: child}))))
        run = rehash_run(dict(ex['runs'][t['research_run']], interventions=[{'who': 'operator', 'what': 'edited'}]))
        ex['runs'][run['run_id']] = run
        ex['transitions'][ex['transitions'].index(t)] = rehash_t(dict(t, research_run=run['run_id']))
        self.assertRejected(ex, 'MANUAL_INTERVENTION')

    def test_undeclared_component_or_environment_change(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[0]
        child = dict(ex['versions'][t['to_version']], environment_digest='env-2', tool_library=['L'])
        vid = digest(child)
        ex['versions'][vid], ex['frozen_at'][vid] = child, ex['frozen_at'][t['to_version']]
        self.assertIn('UNDECLARED_ENVIRONMENT_CHANGE',
                      codes(dict(ex, transitions=[rehash_t(dict(t, to_version=vid))])))
        self.assertIn('DECLARED_CHANGES_MISMATCH', codes(dict(ex, transitions=[rehash_t(dict(t, to_version=vid))])))

    def test_cyclic_chain(self):
        ex = copy.deepcopy(self.ex)
        last, first = self.acc[2], self.acc[0]
        ex['transitions'].append(LN.transition_record(
            index=4, from_version=last['to_version'], to_version=first['from_version'],
            research_run=first['research_run'], declared_changes=['solver'], panel_id='P9', receipt_id='R9',
            claim_id='c', plan_id='p', receipt_event=999, decision='ACCEPTED'))
        self.assertIn('CYCLE', codes(ex))

    def test_ambiguous_parent_edge(self):
        ex = copy.deepcopy(self.ex)
        branch = next(x for x in ex['transitions'] if x['decision'] == 'REJECTED')
        ex['transitions'][ex['transitions'].index(branch)] = rehash_t(dict(branch, decision='ACCEPTED'))
        self.assertRejected(ex, 'AMBIGUOUS_PARENT')

    def test_mid_freeze_crash(self):
        ex = copy.deepcopy(self.ex)
        del ex['frozen_at'][self.acc[1]['to_version']]                 # the child never finished freezing
        self.assertRejected(ex, 'NOT_FROZEN')

    def test_receipt_before_freeze(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[1]
        ex['transitions'][ex['transitions'].index(t)] = rehash_t(dict(t, receipt_event=ex['frozen_at'][t['to_version']] - 1))
        self.assertRejected(ex, 'CHRONOLOGY')

    def test_resource_reservation_replay(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[2]
        run = rehash_run(dict(ex['runs'][t['research_run']], account_sha256='acct-1'))     # reuses run 1's account
        del ex['runs'][t['research_run']]
        ex['runs'][run['run_id']] = run
        ex['transitions'][ex['transitions'].index(t)] = rehash_t(dict(t, research_run=run['run_id']))
        self.assertRejected(ex, 'BUDGET_REUSED')

    def test_inherited_revocation(self):
        tc = {'revoked_versions': [self.acc[0]['to_version']]}
        ps = LN.lineage_problems(self.ex, tc)
        revoked = {p['transition'] for p in ps if p['code'] == 'REVOKED_ANCESTOR'}
        self.assertEqual(revoked, {t['transition_id'] for t in self.acc})          # every later transition too
        self.assertEqual(LN.accepted_chain(self.ex, tc)['transitions'], [])

    def test_selected_branch_absent_from_the_ledger(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[1]
        run = rehash_run(dict(ex['runs'][t['research_run']], attempts=['a2-2']))     # selected attempt missing
        del ex['runs'][t['research_run']]
        ex['runs'][run['run_id']] = run
        ex['transitions'][ex['transitions'].index(t)] = rehash_t(dict(t, research_run=run['run_id']))
        self.assertRejected(ex, 'LEDGER_INCOMPLETE')

    def test_selection_rule_violated_or_unverifiable(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[0]
        r = ex['runs'][t['research_run']]
        cands = [dict(c, score=(1 if c['identity'] == t['to_version'] else 99)) for c in r['candidates']]
        run = rehash_run(dict(r, candidates=cands))
        del ex['runs'][t['research_run']]
        ex['runs'][run['run_id']] = run
        ex['transitions'][ex['transitions'].index(t)] = rehash_t(dict(t, research_run=run['run_id']))
        self.assertRejected(ex, 'SELECTION_RULE_VIOLATED')
        cands = [{k: v for k, v in c.items() if k != 'score'} for c in r['candidates']]
        run2 = rehash_run(dict(r, candidates=cands))
        ex2 = copy.deepcopy(self.ex)
        del ex2['runs'][t['research_run']]
        ex2['runs'][run2['run_id']] = run2
        ex2['transitions'][ex2['transitions'].index(t)] = rehash_t(dict(t, research_run=run2['run_id']))
        self.assertRejected(ex2, 'SELECTION_UNVERIFIABLE')

    def test_tampered_records(self):
        ex = copy.deepcopy(self.ex)
        t = self.acc[1]
        ex['transitions'][ex['transitions'].index(t)] = dict(t, index=7)            # edited without rehash
        self.assertRejected(ex, 'TRANSITION_ID_MISMATCH')


class StoredCampaignExport(unittest.TestCase):
    """The B14-era three-generation DEV campaign export, read as lineage records (audit/lineage_b20r)."""

    def test_todays_export_cannot_support_counting_generations(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        ex = LN.export_from_campaign_zip(root / 'evidence' / 'v2-public-campaign.zip')
        self.assertEqual((len(ex['versions']), len(ex['transitions'])), (4, 3))
        got = {p['code'] for p in LN.lineage_problems(ex)}
        self.assertEqual(got, {'SELECTION_UNVERIFIABLE', 'LEDGER_INCOMPLETE', 'BUDGET_UNACCOUNTED',
                               'DECLARED_CHANGES_MISMATCH'})
        self.assertEqual(LN.accepted_chain(ex)['transitions'], [])
        t2 = sorted(ex['transitions'], key=lambda t: t['index'])[1]
        diff = LN.substantive(LN.version_diff(ex['versions'][t2['from_version']], ex['versions'][t2['to_version']]))
        self.assertEqual(diff, ['library'])                  # generation 1 left the solver program unchanged


class CustodianStillRefuses(unittest.TestCase):
    """B20_R4 changed this contract: the generation kind is no longer refused outright but checked
    against native lineage records (tests_genesis/test_campaign_lineage.py); the improver kind
    stays refused, and an export without native records (like the stored B14-era one) still
    cannot support a generation evaluation."""

    def test_improver_kind_stays_refused(self):
        from genesis import custodian
        self.assertIn('sealed_improver_evaluation', custodian.UNSUPPORTED_KINDS)

    def test_generation_kind_refused_without_native_lineage(self):
        from pathlib import Path
        from genesis import custodian
        root = Path(__file__).resolve().parents[1]
        legacy = LN.export_from_campaign_zip(root / 'evidence' / 'v2-public-campaign.zip')
        self.assertEqual(legacy['source'], 'legacy')
        request = {'generation_transition': {'index': 1, 'from_version': 'a' * 64, 'to_version': 'b' * 64}}
        for facts in ({'lineage': None}, {'lineage': legacy}):
            why = custodian.generation_problems(request, facts)
            self.assertEqual(len(why), 1)
            self.assertIn('native research-lineage records', why[0])


if __name__ == '__main__':
    unittest.main()
