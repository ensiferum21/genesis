"""Repair B (B20-REVIEW-02): research budgets are enforced and every pathway is charged.

Uses real subprocesses (CPU burners, a setsid grandchild) under the bounded executor, plus
deterministic fake provers for the accounting rules. No proof tool is needed.
"""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

from genesis.learning import budget as B
from genesis.learning import equational as Q
from genesis.learning import macros as M
from genesis.learning import research as RS
from genesis.learning.budget import NS, Account, StudyBudget, run_bounded

PY = sys.executable
FAKE_PROOF = "fof(c, plain, $false, inference(x, [], [file('p.p', ax0)])).\n"


def burner(seconds, then_print=True):
    """A real subprocess that burns `seconds` of CPU, then claims a proof."""
    code = (f"import time\nt=time.process_time()\nwhile time.process_time()-t<{seconds}: pass\n"
            + ("print('# SZS status Theorem')\nprint('# SZS output start')\nprint(" + repr(FAKE_PROOF) + ")\n"
               if then_print else ''))
    return [PY, '-c', code]


def subprocess_prover(seconds):
    """research.run prover: a real CPU-burning child under the reservation's outer budget."""
    def prover(axioms, goal, *, res, label):
        r = run_bounded(burner(seconds), cpu_ns=res.cpu_ns, wall_ns=res.wall_ns, label=label)
        ok = 'SZS status Theorem' in r['stdout']
        return {'status': 'THEOREM' if ok else 'RESOURCE_OUT', 'proof': FAKE_PROOF if ok else None,
                'resource': {k: r[k] for k in ('termination', 'exit_code', 'cpu_ns', 'wall_ns', 'meter')}}
    return prover


def instant_prover(cpu_ns=1_000_000, status='THEOREM'):
    def prover(axioms, goal, *, res, label):
        return {'status': status, 'proof': FAKE_PROOF if status == 'THEOREM' else None,
                'resource': {'termination': 'EXITED', 'exit_code': 0, 'cpu_ns': cpu_ns, 'wall_ns': cpu_ns,
                             'meter': {'kind': 'fake', 'lower_bound': False}}}
    return prover


def pool():
    return Q.true_equations('ba_sheffer', 4, per_bucket=3)


def supervised(cpu_s, attempt_s=1, **kw):
    return StudyBudget.from_seconds(cpu_s, attempt_s=attempt_s, enforcement='OUTER_SUPERVISED',
                                    quantum_ns=100_000_000, **kw)


def exact_meter():
    r = run_bounded([PY, '-c', 'pass'], cpu_ns=2 * NS, wall_ns=10 * NS)
    return not r['meter']['lower_bound']


class BoundedExecution(unittest.TestCase):
    def test_cpu_burner_is_killed_at_its_reservation(self):
        r = run_bounded(burner(30, then_print=False), cpu_ns=int(0.4 * NS), wall_ns=20 * NS)
        self.assertEqual(r['termination'], 'CPU_BUDGET_KILLED')
        self.assertGreaterEqual(r['cpu_ns'], int(0.4 * NS))
        self.assertLess(r['cpu_ns'], int(0.4 * NS) + int(0.5 * NS))          # a bounded kill latency

    def test_wall_deadline(self):
        r = run_bounded([PY, '-c', 'import time; time.sleep(30)'], cpu_ns=5 * NS, wall_ns=int(0.4 * NS))
        self.assertEqual(r['termination'], 'WALL_KILLED')

    def test_setsid_grandchild_is_metered(self):
        prog = ("import subprocess,sys,time\n"
                "subprocess.Popen([sys.executable,'-c','import time\\nt=time.process_time()\\n"
                "while time.process_time()-t<0.5: pass'], start_new_session=True)\n"
                "time.sleep(1.0)\n")
        r = run_bounded([PY, '-c', prog], cpu_ns=4 * NS, wall_ns=20 * NS)
        if r['meter']['lower_bound']:
            self.assertEqual(r['meter']['kind'], 'procfs-pgid+wait4')   # documented weaker meter
        else:
            self.assertGreaterEqual(r['cpu_ns'], int(0.45 * NS))         # the parent alone used ~0.05 s
        r = run_bounded([PY, '-c', prog], cpu_ns=int(0.3 * NS), wall_ns=20 * NS)
        if not r['meter']['lower_bound']:
            self.assertEqual(r['termination'], 'CPU_BUDGET_KILLED')

    def test_descendants_do_not_outlive_the_attempt(self):
        marker = Path(tempfile.mkdtemp()) / 'alive'
        prog = ("import subprocess,sys\n"
                f"subprocess.Popen([sys.executable,'-c','import time\\ntime.sleep(1.5)\\nopen({str(marker)!r},\"w\")'],"
                " start_new_session=True)\n")
        run_bounded([PY, '-c', prog], cpu_ns=2 * NS, wall_ns=10 * NS)
        time.sleep(2.0)
        if exact_meter():
            self.assertFalse(marker.exists())


class OriginalFinding(unittest.TestCase):
    """The B20 loop overruns its cap and credits late proofs; the repaired loop does not."""

    def test_legacy_loop_overruns_and_repaired_loop_stays_within_cap(self):
        def legacy_prove(axioms, conjecture, *, seconds, mode='auto', **kw):
            import subprocess
            subprocess.run(burner(min(seconds, 0.6), then_print=False), check=True)
            return {'status': 'THEOREM', 'proof': FAKE_PROOF}
        with mock.patch.object(RS, 'prove', legacy_prove):
            old = RS.run_legacy_b20('ba_sheffer', RS.Fixed(), pool(), budget_s=1.0, prove_s=1)
        self.assertGreater(old['cpu_s'], 1.0)                              # the B20 defect, reproduced
        account = Account(supervised(1.0), label='repaired')
        new = RS.run('ba_sheffer', RS.Fixed(), pool(), account=account, prover=subprocess_prover(0.6))
        acct = new['account']
        self.assertLessEqual(acct['cpu_ns_total'], NS + account.budget.tolerance_ns)   # kill latency is bounded
        if acct['overrun_ns'] == 0:
            self.assertTrue(acct['within_cap'])
        for a in acct['attempt_records']:
            if a['termination'] != 'EXITED':
                self.assertFalse(a['eligible'])
        credited = {a['attempt_id'] for a in acct['attempt_records'] if a['eligible']}
        for lem in new['library']:
            self.assertIn(lem['attempt_id'], credited)                   # no late or killed proof admitted

    def test_successful_output_after_the_deadline_is_not_credited(self):
        account = Account(supervised(3.0, overhead_ns=0), label='late')
        res = account.reserve('prover', purpose='late', cpu_ns=int(0.3 * NS))
        r = run_bounded(burner(0.6), cpu_ns=res.cpu_ns, wall_ns=res.wall_ns)
        rec = account.settle(res, cpu_ns=r['cpu_ns'], wall_ns=r['wall_ns'], termination=r['termination'],
                             status='THEOREM' if 'Theorem' in r['stdout'] else 'NONE', meter=r['meter'])
        self.assertFalse(rec['eligible'])
        res = account.reserve('prover', purpose='overrun', cpu_ns=int(0.2 * NS))
        rec = account.settle(res, cpu_ns=int(0.25 * NS), wall_ns=1, termination='EXITED', status='THEOREM',
                             meter={'kind': 'fake', 'lower_bound': False})
        self.assertFalse(rec['eligible'])
        self.assertIn('exceeded the reservation', rec['reason'])


class AccountRules(unittest.TestCase):
    def test_no_launch_without_an_admissible_quantum(self):
        a = Account(StudyBudget.from_seconds(1.0, attempt_s=1), label='q')     # PROVER_QUANTUM: needs 1.25 s
        res = RS.run('ba_sheffer', RS.Fixed(), pool(), account=a, prover=instant_prover())
        self.assertEqual(res['account']['stop_reason'], 'INSUFFICIENT_REMAINING_BUDGET')
        self.assertEqual(res['account']['attempts'], 0)
        self.assertEqual(res['library'], [])
        self.assertEqual(res['trajectory'][-1]['outcome'], 'NOT_ATTEMPTED')

    def test_fractional_remainder_is_never_rounded_up(self):
        a = Account(StudyBudget.from_seconds(2.0, attempt_s=1), label='r')    # 1.25 s per reservation
        r1 = a.reserve('prover', purpose='1')
        self.assertEqual(r1.prover_limit_s, 1)
        a.settle(r1, cpu_ns=int(0.9 * NS), wall_ns=1, termination='EXITED', status='x',
                 meter={'kind': 'fake', 'lower_bound': False})
        self.assertIsNone(a.reserve('prover', purpose='2'))                    # 1.1 s left < 1.25 s
        self.assertEqual(a.stop_reason, 'INSUFFICIENT_REMAINING_BUDGET')
        o = Account(supervised(1.0), label='o')
        r = o.reserve('prover', purpose='x')
        self.assertLessEqual(r.cpu_ns, NS - o.budget.tolerance_ns)             # never more than what is left

    def test_expensive_policy_preparation_and_choice_are_charged(self):
        class Slow(RS.Fixed):
            name = 'slow'

            def reset(self, pool, dev):
                t = time.process_time()
                while time.process_time() - t < 0.3:
                    pass
                super().reset(pool, dev)

            def choose(self, untried):
                t = time.process_time()
                while time.process_time() - t < 0.05:
                    pass
                return super().choose(untried)
        a = Account(supervised(1.0), label='slow')
        res = RS.run('ba_sheffer', Slow(), pool(), account=a, prover=instant_prover())
        acct = res['account']
        self.assertGreaterEqual(acct['cpu_ns_by_category']['preparation'], int(0.29 * NS))
        self.assertGreaterEqual(acct['cpu_ns_by_category']['policy'], int(0.04 * NS))
        self.assertLessEqual(acct['cpu_ns_total'] - acct['overrun_ns'], NS)

    def test_slow_decider_is_charged_and_stops_the_run(self):
        real = Q.holds

        def slow(eq_, decider):
            t = time.process_time()
            while time.process_time() - t < 0.4:
                pass
            return real(eq_, decider)
        a = Account(supervised(1.0), label='decider')
        with mock.patch.object(RS.Q, 'holds', slow):
            res = RS.run('ba_sheffer', RS.Fixed(), pool(), account=a, prover=instant_prover())
        acct = res['account']
        self.assertGreaterEqual(acct['cpu_ns_by_category']['decider'], int(0.79 * NS))
        self.assertEqual(acct['stop_reason'], 'BUDGET_EXHAUSTED_IN_PROCESS')
        self.assertGreater(acct['overrun_ns'], 0)                              # recorded, never hidden
        self.assertLessEqual(len(res['library']), 2)

    def test_interrupted_reservation_is_charged_on_restart(self):
        d = Path(tempfile.mkdtemp())
        b = StudyBudget.from_seconds(10.0, attempt_s=2)
        a = Account(b, label='crash', journal=d / 'j.jsonl')
        r = a.reserve('prover', purpose='never settled')
        del a                                                                  # the process "crashes" here
        with open(d / 'j.jsonl', 'a') as f:
            f.write('{"type": "SETT')                                          # a torn final line
        a2 = Account(b, label='crash', journal=d / 'j.jsonl')
        rec = a2.record()
        self.assertEqual(rec['attempt_statuses'], {'INTERRUPTED': 1})
        self.assertEqual(rec['cpu_ns_total'], r.cpu_ns)                        # charged in full
        self.assertEqual(rec['eligible_attempts'], 0)
        r2 = a2.reserve('prover', purpose='after restart')
        self.assertNotEqual(r2.attempt_id, r.attempt_id)                       # no reuse, no free retry
        with self.assertRaises(ValueError):
            Account(StudyBudget.from_seconds(99.0, attempt_s=2), label='crash', journal=d / 'j.jsonl')

    def test_macro_expansion_and_curriculum_use_the_same_authority(self):
        steps = [{'schema': Q.canon(e), 'text': Q.text(e), 'depends_on': [], 'budget_s': 1, 'source_lemma': 'L'}
                 for e in pool()[:3]]
        macro = {'schema': M.SCHEMA, 'name': 'm', 'source_system': 'ba_sheffer', 'precondition': {'ops': {'s': 2}},
                 'steps': steps, 'revoked': [], 'resource_bound_s': 3, 'macro_sha256': 'x'}
        a = Account(supervised(5.0), label='shared')
        lib, log = M.expand(macro, 'ba_sheffer', account=a, prover=instant_prover(cpu_ns=50_000_000))
        self.assertEqual(len(lib), 3)
        before = a.record()['attempts']
        cur = RS.run('ba_sheffer', RS.Fixed(), pool()[3:6], account=a, prover=instant_prover(cpu_ns=50_000_000))
        rec = cur['account']
        self.assertEqual(rec['attempts'], before + 3)                          # one account across both routes
        self.assertGreater(rec['cpu_ns_by_category']['induction'], 0)
        self.assertTrue(rec['within_cap'])
        for row in log:
            self.assertTrue(row['eligible'])

    def test_arms_share_one_frozen_budget_and_training_is_charged(self):
        b = StudyBudget.from_seconds(4.0, attempt_s=1, charging='AMORTIZED', amortize_uses=10)
        arms = {p: Account(b, label=p) for p in ('fixed', 'learned')}
        self.assertEqual({a.budget.identity() for a in arms.values()}, {b.identity()})
        arms['learned'].precharge_training(25 * NS)
        self.assertEqual(arms['learned'].cpu['amortized_training'], 25 * NS // 10)
        full = Account(StudyBudget.from_seconds(4.0, attempt_s=1), label='full')
        full.precharge_training(25 * NS)
        self.assertEqual(full.stop_reason, 'BUDGET_EXHAUSTED_IN_PROCESS')       # full cost can exhaust a campaign
        with self.assertRaises(ValueError):
            StudyBudget.from_seconds(4.0, attempt_s=1, charging='AMORTIZED')     # uses must be preregistered

    def test_grant_bridge_leases_and_charges_the_authority(self):
        from genesis.kernel.authority import AuthorityError, GrantLedger
        from genesis.store import Store
        d = tempfile.mkdtemp()
        s = Store(d)
        try:
            led = GrantLedger(s)
            root = led.root_grant({'cpu_seconds': 10, 'wall_seconds': 100, 'attempts': 100, 'output_bytes': 1 << 20,
                                   'paid_api_usd': 0}, ['execute_sandboxed_code'], issuer='test')
            b = StudyBudget.from_seconds(4.0, attempt_s=1, max_attempts=50)
            gid = B.grant_bridge(led, root, b, purpose='research campaign')
            a = Account(b, label='granted')
            r = a.reserve('prover', purpose='x')
            a.settle(r, cpu_ns=NS, wall_ns=NS, termination='EXITED', status='x',
                     meter={'kind': 'fake', 'lower_bound': False})
            remaining = B.settle_grant(led, gid, a)
            self.assertAlmostEqual(remaining['cpu_seconds'], 3.0)
            with self.assertRaises(AuthorityError):
                B.grant_bridge(led, root, StudyBudget.from_seconds(7.0, attempt_s=1, max_attempts=10),
                               purpose='too much')
        finally:
            s.close()

    def test_account_record_is_complete(self):
        a = Account(StudyBudget.from_seconds(3.0, attempt_s=1), label='rec')
        res = RS.run('ba_sheffer', RS.Fixed(), pool()[:4], account=a, prover=instant_prover())
        rec = res['account']
        for k in ('budget', 'budget_sha256', 'cpu_ns_by_category', 'cpu_ns_total', 'stop_reason', 'attempt_records',
                  'account_sha256', 'within_cap'):
            self.assertIn(k, rec)
        self.assertEqual(set(rec['cpu_ns_by_category']), set(B.CATEGORIES))
        json.dumps(rec)


class ProverStatus(unittest.TestCase):
    def test_e_resource_out_is_not_recorded_as_error(self):
        from genesis.verification.eprover import _parse
        self.assertEqual(_parse('%% Failure: Resource limit exceeded (time)\n%% SZS status ResourceOut\n'),
                         ('RESOURCE_OUT', None))
        self.assertEqual(_parse('# SZS status Theorem\n# SZS output start CNFRefutation\nx\n')[0], 'THEOREM')
        self.assertEqual(_parse('% SZS status CounterSatisfiable\n')[0], 'COUNTERSATISFIABLE')
        self.assertEqual(_parse('')[0], 'RESOURCE_OUT')
        self.assertEqual(_parse('garbage')[0], 'ERROR')


if __name__ == '__main__':
    unittest.main()
