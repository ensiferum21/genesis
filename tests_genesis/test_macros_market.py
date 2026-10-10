"""Research IR macros replay from IR; market selection, calibration and stop rule; registry honesty."""
from itertools import combinations
from pathlib import Path
import tempfile
import unittest

from genesis.ir import Interpreter, Value, replay, OVERLOADS, CONTRACTS
from genesis.macros import IMPLEMENTED, ghost_census, barrier_escape, local_to_global, gap_engine, cognitive_compile
from genesis.market import Calibration, MarketPolicy, Proposal, allocate, should_stop, pareto
from genesis.models import GraphTask, SolverProgram
from genesis.registry import ENGINES, PRIMITIVES, registry, summary
from genesis.verification.tools import available

SAT = available('cadical') and available('drat-trim')


def host(n=10, seed=3, p=0.45):
    import random
    rng = random.Random(seed)
    return GraphTask(task_id=f'h{seed}', n=n, edges=tuple(e for e in combinations(range(n), 2) if rng.random() < p),
                     family='random')


class IR(unittest.TestCase):
    def test_overloads_only_use_the_sixteen_primitives(self):
        self.assertEqual({o[0] for o in OVERLOADS}, set(CONTRACTS))
        self.assertEqual(set(PRIMITIVES), set(CONTRACTS))

    def test_ambiguous_or_unknown_parameters_are_refused(self):
        ir = Interpreter()
        goal = ir.invoke('FORMALIZE', [Value('RawTask', host().model_dump(mode='json'))])
        with self.assertRaises(ValueError):
            ir.invoke('TRANSFORM', [goal], {'permutation': list(range(10)), 'induced': [0, 1]})
        with self.assertRaises(ValueError):
            ir.invoke('VERIFY', [goal, Value('Witness', ())], {'contract': 'something_else'})

    def test_replay_detects_a_tampered_program(self):
        res = local_to_global(host(), SolverProgram(rounds=4))
        ok, bad = replay(res['program'])
        self.assertTrue(ok, bad)
        res['program']['nodes'][-1]['output_digest'] = '0' * 64
        ok, bad = replay(res['program'])
        self.assertFalse(ok)


class Macros(unittest.TestCase):
    def test_each_macro_uses_its_characteristic_operators_and_replays(self):
        t = host(12, 4, 0.5)
        p = SolverProgram(rounds=4)
        runs = {'Local-to-Global Engine': local_to_global(t, p),
                'Gap Engine': gap_engine(t, p, [{'optimum': 30, 'value': 25, 'family': 'f', 'status': 'SUCCESS'}]),
                'Cognitive Compilation': cognitive_compile([t, host(9, 5)], p)}
        if SAT:
            runs['Ghost Census'] = ghost_census(t, 5, p)
            runs['Barrier & Escape'] = barrier_escape(t, p, verify_seconds=30)
        for name, res in runs.items():
            self.assertTrue(IMPLEMENTED[name][1] <= set(res['ops']), (name, res['ops']))
            ok, bad = replay(res['program'])
            self.assertTrue(ok, (name, bad))

    @unittest.skipUnless(SAT, 'pinned SAT tools missing')
    def test_ghost_census_keeps_states_distinct(self):
        t = host(12, 4, 0.5)
        p = SolverProgram(rounds=4)
        self.assertEqual(ghost_census(t, 3, p)['status'], 'GHOST_FOUND')
        high = ghost_census(t, len(t.edges), p)
        self.assertEqual(high['status'], 'PROVED')
        self.assertTrue(high['proof'])
        bad = ghost_census(t.model_copy(update={'n': 2}), 3, p)  # invalid task -> harness error, not a result
        self.assertEqual(bad['status'], 'HARNESS_ERROR')

    def test_local_to_global_reglues_and_rechecks(self):
        a, b = host(6, 1, 0.6), host(5, 2, 0.6)
        edges = tuple(sorted(list(a.edges) + [(u + 6, v + 6) for u, v in b.edges]))
        t = GraphTask(task_id='two', n=11, edges=edges, family='glued')
        res = local_to_global(t, SolverProgram(rounds=8))
        self.assertEqual(res['status'], 'GLUED')
        self.assertGreaterEqual(res['components'], 2)


class Market(unittest.TestCase):
    def proposal(self, pid, cls='a', progress=1.0, cost=1.0, **kw):
        return Proposal(proposal_id=pid, kind=kw.pop('kind', 'k'), structural_class=cls, world='w',
                        expected_progress=progress, info_gain=kw.pop('info', 0.0), future_capability=0.0,
                        option_value=0.0, expected_cost=cost, **kw)

    def test_pareto_prefilter_and_budget(self):
        good = self.proposal('good', progress=5, cost=1)
        dominated = self.proposal('dominated', progress=1, cost=2)
        pricey = self.proposal('pricey', progress=50, cost=100, info=1)
        selected, record = allocate([good, dominated, pricey], 10, MarketPolicy())
        self.assertNotIn('dominated', record['pareto_front'])
        self.assertEqual([p.proposal_id for p in selected], ['good'])
        self.assertLessEqual(record['spent'], 10)

    def test_diversity_slot_under_premature_convergence(self):
        a = self.proposal('same', cls='greedy', progress=5)
        b = self.proposal('different', cls='exact', progress=0.5, info=0.1)
        selected, record = allocate([a, b], 10, MarketPolicy(), recent_classes=['greedy'] * 3)
        self.assertIn('different', record['reserved_for_diversity'])
        self.assertIn('different', [p.proposal_id for p in selected])

    def test_calibration_learns_from_realized_outcomes(self):
        cal = Calibration(); p = self.proposal('x', kind='search', progress=10)
        for _ in range(5):
            cal.observe(p, 1.0, 1.0)
        self.assertLess(cal.adjust(p).expected_progress, 3)

    def test_stop_thinking_rule(self):
        worthless = self.proposal('w', progress=0, cost=1000)
        self.assertTrue(should_stop([worthless], MarketPolicy())[0])
        self.assertFalse(should_stop([worthless], MarketPolicy(), pending_critical=True)[0])
        self.assertFalse(should_stop([self.proposal('v', progress=3)], MarketPolicy())[0])


class Registry(unittest.TestCase):
    def test_registry_is_complete_and_honest(self):
        self.assertEqual(len(ENGINES), 137)
        for name, ops in ENGINES:
            self.assertTrue(set(ops) <= set(PRIMITIVES), name)
        rows = registry()
        implemented = {r['engine'] for r in rows if r['status'] == 'IMPLEMENTED_BOUNDED'}
        self.assertEqual(implemented, set(IMPLEMENTED))
        for r in rows:
            if r['engine'] in IMPLEMENTED:
                self.assertEqual(set(r['composition']), IMPLEMENTED[r['engine']][1])
        self.assertEqual(sum(summary().values()), 137)


@unittest.skipUnless(SAT, 'pinned SAT tools missing')
class WorldLoop(unittest.TestCase):
    def test_loop_promotes_only_math_levels_and_replays(self):
        from genesis.worldstep import ResearchLoop, LoopConfig
        from genesis.store import Store
        from genesis.common import canonical
        with tempfile.TemporaryDirectory() as d:
            with ResearchLoop(d, LoopConfig(tasks=2, epochs=2, cpu_budget_per_epoch=30, verify_seconds=20)) as loop:
                summary = loop.run()
            self.assertFalse(summary['promotion_allowed'])
            self.assertGreaterEqual(summary['optimality_checked'], 1)
            with Store(d) as s:
                s.verify()
                levels = [s.state(f'claimlevels:{cid}') for (cid,) in s.db.execute("SELECT id FROM entities WHERE kind='claim'")]
                self.assertTrue(levels)
                for lv in levels:
                    self.assertIn(lv['math'], ('WITNESS_VALID', 'OPTIMALITY_CHECKED'))
                    self.assertEqual(lv['utility'], 'NOT_TESTED')
                    self.assertEqual(lv['improver'], 'NOT_TESTED')
                programs = [s.get(h) for (h,) in s.db.execute("SELECT object_hash FROM entities WHERE kind='ir_program'")]
                self.assertTrue(programs)
                for prog in programs[:4]:
                    self.assertTrue(replay(prog)[0])
            self.assertTrue((Path(d) / 'reports' / 'world_loop.md').exists())


if __name__ == '__main__':
    unittest.main()
