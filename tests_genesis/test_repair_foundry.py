"""The obstacle loop on the state-management testbed (`docs/OMEGA_SELF_REPAIR.md`; the Foundry's first milestone):
the static guard, the defect catalogue, the independent verifier, the Supervisor's policy and rollback, the probe's
conservation laws, the causal obstacle model, whole episodes on development defects (never the held-out ones), the
controls (no obstacle; a fault in the kernel, which must be escalated), the one-proposal rule, the boundary between
the research plane and the kernel, and, where the operating system allows it, the isolation of the parties
(measured: what each can read and write)."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repair import capture as CP  # noqa: E402
from genesis.repair import loop as LP  # noqa: E402
from genesis.repair import obstacle as OB  # noqa: E402
from genesis.repair import probe as PR  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import guard as GD  # noqa: E402
from genesis.repairkernel import supervisor as SV  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

DEV = [d['id'] for d in DF.DEFECTS if d['split'] == 'dev']


def _can_isolate():
    if os.geteuid() != 0 or not shutil.which('unshare') or not shutil.which('setpriv'):
        return False
    p = subprocess.run(['unshare', '-m', '--propagation', 'private', 'true'], capture_output=True)
    return p.returncode == 0


class Guard(unittest.TestCase):
    SRC = TG.SOURCES['lru']

    def test_it_admits_a_rearrangement_and_the_methods_a_repair_needs(self):
        self.assertIsNone(GD.check(self.SRC, self.SRC))
        self.assertIsNone(GD.check(self.SRC, self.SRC.replace('self.d.move_to_end(k)\n        return',
                                                              'self.d.move_to_end(k, last=True)\n        return')))
        self.assertIsNone(GD.check(self.SRC, self.SRC.replace('return list(self.d)', 'return sorted(self.d)')))

    def test_it_refuses_input_output_imports_new_names_and_dunders(self):
        for bad, why in (('return list(self.d)', 'return open("x").read()'),
                         ('return list(self.d)', 'return eval("1")'),
                         ('return list(self.d)', 'return self.secret'),
                         ('return list(self.d)', 'return self.__class__'),
                         ('from collections import OrderedDict', 'import os')):
            with self.subTest(why=why):
                self.assertIsNotNone(GD.check(self.SRC, self.SRC.replace(bad, why)))
        self.assertTrue(GD.check(self.SRC, 'def (').startswith('syntax'))


class Catalogue(unittest.TestCase):
    def test_every_defect_applies_once_and_the_splits_are_disjoint(self):
        ids = [d['id'] for d in DF.DEFECTS]
        self.assertEqual(len(ids), len(set(ids)))
        for d in DF.DEFECTS:
            self.assertEqual(TG.SOURCES[d['target']].count(d['old']), 1, d['id'])
            self.assertNotEqual(DF.source(d['id'], TG.SOURCES), TG.SOURCES[d['target']])
        self.assertEqual({d['split'] for d in DF.DEFECTS}, {'dev', 'heldout'})

    def test_every_defect_interrupts_its_job_and_the_clean_component_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            for i, dd in enumerate(DF.DEFECTS):
                job, _ = BN.make(dd['id'], 1, Path(d) / str(i))
                self.assertEqual(job.run()['status'], 'failed', dd['id'])
            for t in TG.SOURCES:
                job, _ = BN.make_clean(t, 1, Path(d) / f'clean-{t}')
                self.assertEqual(job.run()['status'], 'done', t)


class Verifier(unittest.TestCase):
    def test_it_accepts_the_correct_source_and_rejects_defects_and_degenerate_repairs(self):
        with tempfile.TemporaryDirectory() as d:
            job, _ = BN.make('M1', 1, Path(d) / 'job')
            job.run()
            args = (job.dir, job.target, job.seed, job.n_ops, job.every)
            self.assertTrue(VF.verify(*args, TG.SOURCES['memo'])['accepted'])
            self.assertFalse(VF.verify(*args, DF.source('M1', TG.SOURCES) + '\n#\n')['accepted'])
            # a "repair" that empties the memo on every call: right answers, no memoisation; the hidden test sees it
            lazy = TG.SOURCES['memo'].replace('if len(self._seen) >= self.limit:', 'if True:')
            v = VF.verify(*args, lazy)
            self.assertFalse(v['accepted'])
            self.assertFalse(v['checks']['hidden']['ok'])
            refused = VF.verify(*args, TG.SOURCES['memo'].replace('return self._seen[key]',
                                                                  'return open("/etc/passwd").read()'))
            self.assertFalse(refused['accepted'])
            self.assertTrue(refused['checks']['boundary']['guard'].startswith('denied'))


class KernelVersion2(unittest.TestCase):
    """B20_R180's kernel: kept checkpoints and rollback, the resource check, the policy that requires it."""

    def test_a_resume_rolls_back_past_a_checkpoint_the_defect_corrupted(self):
        from genesis.repairkernel import defects2 as DF2
        with tempfile.TemporaryDirectory() as d:
            for version in (1, 2):
                job, _ = BN.make('D4', 1, Path(d) / f'v{version}', version=version)
                first = job.run()
                self.assertEqual((first['status'], first['op']), ('failed', 1800))
                self.assertEqual(job.run(resume=True)['status'], 'failed')      # same source: nothing to undo
                job.file.write_text(TG.ALL_SOURCES['ledger'])
                r = job.run(resume=True)
                if version == 1:
                    self.assertEqual(r['status'], 'failed')                      # the saved index is wrong
                else:
                    self.assertEqual((r['status'], r['started'], r['rolled_back_from']), ('done', 0, 1800))
            self.assertIn('D4', DF2.BY_ID)

    def test_the_resource_check_refuses_a_leak_and_the_policy_requires_it(self):
        with tempfile.TemporaryDirectory() as d:
            job, _ = BN.make('R2', 1, Path(d) / 'job', version=2)
            job.run()
            leak = DF.source('R2', TG.SOURCES).replace('        self.items.pop(i)\n', '', 1)
            v = VF.verify(job.dir, job.target, 1, job.n_ops, job.every, leak)
            self.assertFalse(v['checks']['resource']['ok'])
            self.assertTrue(all(v['checks'][c]['ok'] for c in ('boundary', 'visible', 'hidden', 'fresh')))
            self.assertFalse(v['accepted'])
            self.assertEqual(v['version'], 2)
        passed = {'checks': {c: {'ok': True} for c in SV.POLICY['required']}}
        self.assertTrue(SV.decide(passed, 'testbed')['promote'])
        self.assertFalse(SV.decide(dict(passed, version=2), 'testbed')['promote'])
        self.assertTrue(SV.decide({'version': 2, 'checks': dict(passed['checks'], resource={'ok': True})},
                                  'testbed')['promote'])

    def test_a_method_may_be_called_open_but_a_candidate_may_not_call_open(self):
        src = TG.ALL_SOURCES['ledger']
        self.assertIsNone(GD.check(src, src.replace('if self.balances[acct] < amount:',
                                                     'if self.balances[acct] <= amount:')))
        self.assertIsNotNone(GD.check(src, src.replace('return list(self.by_acct[acct])', 'return open("x")')))

    def test_the_whole_workload_trial_starts_from_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            job, h = BN.make('T2', 1, Path(d) / 'job', version=2)
            job.run()
            self.assertEqual(h.trial(whole=True).cost, len(job.ops))
            self.assertEqual(h.trial().cost, len(job.ops) - 1800)


class Supervisor(unittest.TestCase):
    def test_promotion_needs_every_check_and_an_automatic_scope_and_can_be_rolled_back(self):
        ok = {'checks': {c: {'ok': True} for c in SV.POLICY['required']}}
        self.assertTrue(SV.decide(ok, 'testbed')['promote'])
        self.assertFalse(SV.decide(ok, 'repository')['promote'])
        bad = {'checks': dict(ok['checks'], hidden={'ok': False})}
        self.assertFalse(SV.decide(bad, 'testbed')['promote'])
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'c.py'
            f.write_text('old\n')
            rec = SV.promote(f, 'new\n', ok, 'testbed', Path(d) / 'log.jsonl', 'r1')
            self.assertEqual(f.read_text(), 'new\n')
            self.assertTrue(SV.rollback(rec))
            self.assertEqual(f.read_text(), 'old\n')
            self.assertEqual(len((Path(d) / 'log.jsonl').read_text().splitlines()), 1)


class Probe(unittest.TestCase):
    def test_conservation_laws_are_mined_and_the_first_break_names_the_method(self):
        with tempfile.TemporaryDirectory() as d:
            job, h = BN.make('S1', 1, Path(d) / 'job')
            src = h.source()
            obs = []
            for k in range(6):
                r = h.trial(seed=f't{k}', n=12)(TG.SOURCES['stats'], observe='full')
                self.assertEqual(r['status'], 'pass')
                obs.append(PR.Observation(r))
            laws = [n for n, _ in PR.mine(obs)]
            self.assertIn('_total is None or _total == sum(values)', laws)
            failing = [PR.Observation(h.trial(seed=f'f{k}', n=120)(src, observe='full')) for k in range(6)]
            breaks = {PR.first_break(o, PR.mine(obs)) for o in failing} - {None}
            self.assertIn(('add', '_total is None or _total == sum(values)'), breaks)


class ObstacleModel(unittest.TestCase):
    def test_bayes_moves_belief_to_the_lines_failing_trials_share(self):
        m = OB.ObstacleModel('p', {}, [1, 2, 3, 4], {1: 'a', 2: 'a', 3: 'b', 4: 'b'})
        m.update(10, {1, 2, 3}, True)
        m.update(10, {1, 2}, False)
        m.update(10, {3, 4}, True)
        self.assertEqual(m.ranked_lines()[0], 3)
        self.assertEqual(m.ranked_methods()[0][0], 'b')
        self.assertIn(m.next_length(), OB.LENGTHS)
        self.assertGreaterEqual(m.gain(40), 0.0)
        rec = m.summary()
        for k in ('problem', 'observed_failure', 'competing_causes', 'missing_capability', 'intervention',
                  'predicted_effect', 'cost', 'uncertainty_bits', 'evidence'):
            self.assertIn(k, rec)


class Episodes(unittest.TestCase):
    """Whole episodes, in one process, on development defects only."""

    def test_dev_defects_are_repaired_verified_promoted_resumed_and_retained(self):
        with tempfile.TemporaryDirectory() as d:
            for did in ('M1', 'S1', 'G2'):
                job, _ = BN.make(did, 1, Path(d) / did)
                first = job.run()
                rec, krec = FD.handle_obstacle(job, vault_dir=Path(d) / 'vault', repair_id=did, isolated=False,
                                               log_path=Path(d) / 'supervisor.jsonl')
                self.assertEqual(rec['outcome'], 'repaired', did)
                self.assertTrue(krec['verdict']['accepted'])
                self.assertEqual(rec['steps']['resume']['from_op'], first['op'])     # resumed, not restarted
                self.assertEqual(job.run(resume=True)['status'], 'done')
                self.assertTrue(Path(str(job.file) + f'.before-{did}').exists())     # rollback kept
            vault = LP.Vault(Path(d) / 'vault' / 'vault.jsonl')
            self.assertEqual([e['id'] for e in vault.entries], ['M1', 'S1', 'G2'])
            self.assertTrue(all(e['verified'] for e in vault.entries))

    def test_a_retained_hunk_is_retrieved_for_the_same_defect_in_another_job(self):
        with tempfile.TemporaryDirectory() as d:
            job, _ = BN.make('W2', 1, Path(d) / 'a')
            job.run()
            rec, _ = FD.handle_obstacle(job, vault_dir=Path(d) / 'vault', repair_id='W2-a', isolated=False,
                                        log_path=Path(d) / 's.jsonl')
            self.assertEqual(rec['outcome'], 'repaired')
            repaired_src = job.file.read_text()
            vault = LP.Vault(Path(d) / 'vault' / 'vault.jsonl')
            got = vault.hunks(DF.source('W2', TG.SOURCES))
            self.assertEqual([s for _, s in got], [repaired_src])
            self.assertEqual(vault.hunks(DF.source('W2', TG.SOURCES), exclude=('W2-a',)), [])
            self.assertEqual(LP.kind_of(got[0][0]), vault.entries[0]['operator'])
            job2, _ = BN.make('W2', 2, Path(d) / 'b')
            job2.run()
            rec2, _ = FD.handle_obstacle(job2, vault_dir=Path(d) / 'vault', repair_id='W2-b', isolated=False,
                                         log_path=Path(d) / 's.jsonl')
            self.assertEqual(rec2['outcome'], 'repaired')
            self.assertEqual(rec2['steps']['synthesise']['first_solution'], 1)      # the retrieved hunk, first

    def test_controls_no_obstacle_and_a_kernel_fault_change_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            for name, fault in (('clean', None), ('fault', 700)):
                job, _ = BN.make_clean('lru', 2, Path(d) / name, fault_at=fault)
                job.run()
                rec, krec = FD.handle_obstacle(job, vault_dir=Path(d) / 'v', repair_id=name, isolated=False,
                                               log_path=Path(d) / 's.jsonl')
                self.assertEqual(rec['outcome'], 'no-obstacle' if fault is None else 'escalated')
                self.assertEqual(krec['proposals'], 0)
                self.assertEqual(job.file.read_text(), TG.SOURCES['lru'])

    def test_one_proposal_per_obstacle(self):
        with tempfile.TemporaryDirectory() as d:
            job, _ = BN.make('W2', 1, Path(d) / 'job')
            job.run()
            k = FD.Kernel(job, log_path=Path(d) / 's.jsonl', separate=False)
            self.assertFalse(k.propose(DF.source('W2', TG.SOURCES) + '\n#\n')['accepted'])
            second = k.propose(TG.SOURCES['window'])
            self.assertFalse(second['accepted'])
            self.assertIn('one proposal', second['why'])
            self.assertEqual(job.file.read_text(), DF.source('W2', TG.SOURCES))


class Boundary(unittest.TestCase):
    def test_the_research_plane_never_imports_the_kernel(self):
        for f in sorted((ROOT / 'src/genesis/repair').glob('*.py')):
            for n in ast.walk(ast.parse(f.read_text())):
                names = []
                if isinstance(n, ast.Import):
                    names = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom):
                    names = [n.module or '']
                for name in names:
                    self.assertNotIn('repairkernel', name, f.name)

    def test_the_kernel_and_the_loop_are_protected(self):
        for p in ('src/genesis/repairkernel/verify.py', 'src/genesis/repairkernel/supervisor.py',
                  'src/genesis/repair/loop.py', 'src/genesis/autonomy/feedback.py'):
            self.assertEqual(CP.where('/any/clone/' + p), 'protected', p)


@unittest.skipUnless(_can_isolate(), 'needs root and mount namespaces')
class Isolation(unittest.TestCase):
    def test_each_party_sees_and_changes_only_what_it_should(self):
        with tempfile.TemporaryDirectory() as d:
            rep = FD.isolation_report(Path(d) / 'vault')
        r, x = rep['research'], rep['executor']
        self.assertEqual(r['uid'], FD.RESEARCH_ID)
        self.assertEqual(x['uid'], FD.EXECUTOR_ID)
        for k in ('read hidden tests (own view)', 'read defect catalogue (own view)',
                  'read reference models (own view)', 'read hidden tests (repository path)',
                  'read repository history', 'write the Judge', 'write the Judge (repository path)',
                  'write the Supervisor policy', 'write the verifier (repository path)',
                  'create a file in the source tree', 'write /tmp'):
            self.assertIn(r[k], ('FileNotFoundError', 'PermissionError', 'OSError'), k)
        self.assertEqual(r['write the vault'], 'ok')
        self.assertEqual(r['list /home'], '[]')
        for k in ('read hidden tests (own view)', 'read defect catalogue (own view)', 'write the Judge',
                  'write the Supervisor policy', 'create a file in the source tree', 'write /tmp'):
            self.assertIn(x[k], ('FileNotFoundError', 'PermissionError', 'OSError'), k)

    def test_an_isolated_episode_repairs_a_dev_defect(self):
        with tempfile.TemporaryDirectory() as d:
            job, _ = BN.make('L2', 1, Path(d) / 'job')
            job.run()
            rec, krec = FD.handle_obstacle(job, vault_dir=Path(d) / 'vault', repair_id='L2', isolated=True,
                                           log_path=Path(d) / 's.jsonl')
            self.assertEqual(rec['outcome'], 'repaired', json.dumps(rec, default=str)[:600])
            self.assertEqual(rec['uid'], FD.RESEARCH_ID)
            self.assertEqual(krec['exit']['research'], 0)
            self.assertTrue((Path(d) / 'vault' / 'vault.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
