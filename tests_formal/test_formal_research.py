"""B17 / W08: the pinned Lean/Mathlib workspace, sandboxed acceptance, proof search kept
apart from acceptance, the Lean statement domain, and the first theory package.

Pure tests need no Lean. The Lean tests need the pinned toolchain, the built workspace
(toolchain/build_formal_workspace.py) and the sandbox. The formal suite accepts no
skips, so a missing workspace fails the release matrix instead of passing silently.
"""
import copy
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

from genesis import sandbox
from genesis.common import canonical, digest
from genesis.domains import Unsupported
from genesis.formal_research import checker as C
from genesis.formal_research import search as S
from genesis.formal_research import theory_package as TP
from genesis.formal_research import triangle_theory as T
from genesis.formal_research import workspace as W
from genesis.formal_research.lean_domain import ADAPTER, ContextModule, LeanStatementTask
from genesis.kernel import receipts as R

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / 'evidence' / 'formal_research_b17'


def _ready():
    try:
        W.environment()
        return sandbox.available()
    except Exception:
        return False


READY = _ready()


class Pure(unittest.TestCase):
    def test_gadget_search_keeps_only_gadgets_that_beat_packings(self):
        catalog, examined = T.gadget_search(max_vertices=5, max_edges=7)
        self.assertEqual([(g['name'], g['bound'], g['deficit']) for g in catalog], [('Gad3e3', 2, 1), ('Gad4e6', 4, 2)])
        k4e = [r for r in examined if r['vertices'] == 4 and r['edges'] == 5]
        self.assertEqual(len(k4e), 1)
        self.assertFalse(k4e[0]['kept'])                       # deficit 1 = one triangle
        self.assertTrue(all(r['kept'] == (r['deficit'] > r['best_packing_of_smaller']) for r in examined))

    def test_generation_is_deterministic_and_screens_honestly(self):
        a, b = TP.generate(0), TP.generate(0)
        self.assertEqual(canonical(a['conjectures']), canonical(b['conjectures']))
        by = {c['id']: c for c in a['conjectures']}
        self.assertIsNone(by['down_closed']['counterexample'])
        self.assertIsNotNone(by['union_closed']['counterexample'])
        # a counterexample outside the normal form leads to a corrected hypothesis
        self.assertIn('bound_zero_empty_simple', by)
        self.assertIsNotNone(by['bound_zero_empty']['counterexample'])
        self.assertIsNone(by['bound_zero_empty_simple']['counterexample'])
        self.assertTrue(by['bound_zero_empty_simple']['origin'].endswith('bound_zero_empty'))
        self.assertEqual([u['id'] for u in a['unsupported']], ['c4_down_closed'])

    def test_python_model_reads_pairs_like_the_lean_definition(self):
        self.assertFalse(T.tf({(0, 0)}))                       # a loop matches the triangle pattern
        self.assertTrue(T.tf({(0, 1), (1, 2)}))
        self.assertFalse(T.tf({(0, 1), (1, 2), (0, 2)}))
        self.assertTrue(T.tf_bound({(0, 1), (1, 2), (0, 2)}, 2))
        self.assertFalse(T.tf_bound({(0, 1), (1, 2), (0, 2)}, 1))

    def test_packing_bound_is_sound_and_certified_by_parts(self):
        catalog, _ = T.gadget_search()
        method = {'gadgets': catalog}
        rng = random.Random(5)
        for _ in range(60):
            n = rng.randrange(3, 7)
            edges = sorted({(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < 0.6})
            cert = T.packing_bound(n, edges, method)
            self.assertGreaterEqual(cert['bound'], T.tf_opt(set(edges)))
            covered = [e for p in cert['parts'] for e in
                       ((p['vertices'][i], p['vertices'][j]) for i, j in
                        next(g for g in catalog if g['name'] == p['gadget'])['pattern'])] + \
                [tuple(e) for e in cert['rest']]
            self.assertEqual(sorted(covered), edges)          # edge-disjoint cover of the host

    def test_method_compilation_fails_closed(self):
        pkg = {'statements': [{'id': 'bound_card', 'status': 'CHECKED', 'proof_const': 'GTP1.proof',
                               'proof_module': 'GTP1'},
                              {'id': 'bound_union', 'status': 'UNRESOLVED'},
                              {'id': 'bound_mono', 'status': 'CHECKED', 'proof_const': 'GTP2.proof',
                               'proof_module': 'GTP2'}],
               'gadget_search': {'catalog': []}, 'proofs': []}
        self.assertIsNone(TP.compile_method(pkg))

    def test_prescreen(self):
        ok = lambda src: C.prescreen(src, permitted={'GTDefs'})
        self.assertIsNone(ok('import GTDefs\ntheorem proof : True := trivial\n'))
        for src, kind in (('import GTDefs\ntheorem proof : False := sorry', 'FORBIDDEN_CONSTRUCT'),
                          ('axiom cheat : False', 'FORBIDDEN_CONSTRUCT'),
                          ('set_option debug.skipKernelTC true', 'FORBIDDEN_CONSTRUCT'),
                          ('set_option pp.all true', 'FORBIDDEN_CONSTRUCT'),
                          ('theorem x : 1 = 1 := by native_decide', 'FORBIDDEN_CONSTRUCT'),
                          ('module\nimport GTDefs', 'FORBIDDEN_CONSTRUCT'),
                          ('import Lean\ntheorem proof : True := trivial', 'DISALLOWED_IMPORT')):
            self.assertEqual(ok(src)[0], kind, src)
        self.assertIsNone(ok('set_option maxRecDepth 4000 in\ntheorem proof : True := trivial'))

    def test_outcome_classes(self):
        self.assertEqual(C.outcome_class('CHECKED'), 'CHECKED')
        self.assertEqual(C.outcome_class('STATEMENT_MISMATCH'), 'ELABORATION_FAILURE')
        self.assertEqual(C.outcome_class('RESOURCE_LIMIT'), 'TIMEOUT')
        self.assertEqual(C.outcome_class('anything-else'), 'CHECKER_FAILURE')
        self.assertEqual(set(C.OUTCOME_CLASSES), {'CHECKED', 'DISPROVED', 'UNRESOLVED', 'UNSUPPORTED',
                                                  'ELABORATION_FAILURE', 'TIMEOUT', 'CHECKER_FAILURE'})

    def test_recipes_are_named_and_library_strategies_need_a_library(self):
        gen = TP.generate(0)
        c = next(x for x in gen['conjectures'] if x['id'] == 'bound_union')
        bare = [rid for rid, _ in S.recipes(c, [], T.UNFOLD)]
        self.assertFalse(any(r.startswith('cover-split') for r in bare))
        lib = [rid for rid, _ in S.recipes(c, [{'const': 'GTP1.proof', 'statement': 'down_closed'}], T.UNFOLD)]
        self.assertIn('cover-split:GTP1.proof', lib)
        neg = S.disproof_recipe(next(x for x in gen['conjectures'] if x['id'] == 'union_closed'),
                                next(x for x in gen['conjectures'] if x['id'] == 'union_closed')['counterexample'])
        self.assertIn('decide +kernel', neg)

    def test_dependency_closure_is_transitive_within_the_package(self):
        decls = [{'module': 'A', 'name': 'a', 'uses': [['Finset.card', 'Mathlib.Data.Finset.Card']]},
                 {'module': 'B', 'name': 'b', 'uses': [['a', 'A']]},
                 {'module': 'C', 'name': 'c', 'uses': [['b', 'B'], ['Nat', 'Init.Prelude']]}]
        out = C.dependency_closure(decls, {'A', 'B', 'C'})
        self.assertEqual(out['c']['package'], ['a', 'b'])
        self.assertEqual(out['c']['workspace_modules'], ['Init.Prelude'])


class LeanDomainPure(unittest.TestCase):
    task = LeanStatementTask(task_id='dev-x', context=(ContextModule(name='GTDefs', source=T.DEFS_SOURCE),),
                             statement='∀ S : GT.Edges, S ⊆ S', family='theory-template')

    def test_views_contract_and_explicit_unsupported(self):
        view = ADAPTER.candidate_view(self.task).model_dump(mode='json')
        self.assertEqual(set(view), {'domain', 'context', 'statement'})
        self.assertIsInstance(ADAPTER.supports(self.task, 'exact_reference'), Unsupported)
        self.assertIsInstance(ADAPTER.reference(self.task), Unsupported)
        self.assertNotIn(ADAPTER.name, R.DOMAINS)              # no sealed receipt can name it yet
        spaced = self.task.model_copy(update={'statement': '∀  S : GT.Edges,\n  S ⊆ S'})
        self.assertEqual(ADAPTER.exposure_identity(spaced), ADAPTER.exposure_identity(self.task))
        self.assertIsInstance(ADAPTER.parse({'domain': 'lean_statement_v1', 'task_id': 'x'}), Unsupported)
        bad = self.task.model_copy(update={'statement': 'by native_decide'})
        self.assertIsInstance(ADAPTER.supports(bad, 'execute'), Unsupported)

    def test_generated_tasks_exclude_refuted_conjectures(self):
        tasks, seen, _ = ADAPTER.generate(0, 50, 'DEV', 'theory-template', {'theory': 'triangle-obstruction'})
        ids = {t.task_id for t in tasks}
        self.assertIn('dev-down_closed', ids)
        self.assertNotIn('dev-union_closed', ids)
        self.assertEqual(len(seen), len(tasks))


class WorkspaceAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        lib = base / 'src' / '.lake' / 'build' / 'lib' / 'lean' / 'Mathlib'
        lib.mkdir(parents=True)
        for stem in ('A', 'B'):
            for suf in ('.olean', '.olean.server', '.ilean', '.olean.hash'):
                (lib / f'{stem}{suf}').write_bytes(f'{stem}{suf}'.encode())
        (base / 'lean' / 'bin').mkdir(parents=True)
        (base / 'lean' / 'bin' / 'lean').write_bytes(b'not really lean')
        self.out = base / 'ws'
        self.manifest = W.collect(self.out, base / 'src', lean_root=base / 'lean', build_command=['test'])

    def _chmod_writable(self):
        for p in [self.out / 'olean', *(self.out / 'olean').rglob('*')]:
            p.chmod(0o755 if p.is_dir() else 0o644)

    def test_clean_build_audits(self):
        self.assertEqual(sorted(self.manifest['modules']), ['Mathlib.A', 'Mathlib.B'])
        self.assertEqual(set(self.manifest['modules']['Mathlib.A']), {'.olean', '.olean.server'})   # no .ilean/.hash
        self.assertEqual(W.audit(self.out)[1], [])
        with self.assertRaises(FileExistsError):
            W.collect(self.out, Path(self.tmp.name) / 'src', lean_root=Path(self.tmp.name) / 'lean',
                      build_command=['again'])

    def test_tampering_is_detected(self):
        self._chmod_writable()
        olean = self.out / 'olean' / 'Mathlib'
        (olean / 'A.olean').write_bytes(b'edited')
        (olean / 'C.olean').write_bytes(b'added')
        (olean / 'B.olean.server').unlink()
        (olean / 'D.olean').symlink_to(olean / 'B.olean')
        problems = W.audit(self.out)[1]
        for frag in ('artifacts of Mathlib.A differ', 'unlisted artifacts for Mathlib.C',
                     'artifacts of Mathlib.B differ', 'symlink in the artifact tree'):
            self.assertTrue(any(frag in p for p in problems), (frag, problems))

    def test_other_pins_or_lean_are_refused(self):
        pins = json.loads(W.PINS_PATH.read_text())
        pins['mathlib']['rev'] = '0' * 40
        other = Path(self.tmp.name) / 'pins.json'
        other.write_text(json.dumps(pins))
        self.assertTrue(any('other pins' in p for p in W.audit(self.out, pins_path=other)[1]))
        self.assertTrue(any('another Lean' in p for p in W.audit(self.out, lean_sha256='f' * 64)[1]))

    def test_checker_refuses_a_workspace_built_with_another_lean(self):
        with mock.patch.dict(os.environ, {'GENESIS_FORMAL_WORKSPACE': str(self.out)}):
            r = C.accept([{'name': 'X', 'source': 'theorem t : True := trivial', 'trusted': True}], [])
        self.assertEqual(r['status'], 'CHECKER_ERROR')


@unittest.skipUnless(READY, 'pinned Lean toolchain, formal workspace or sandbox unavailable')
class Acceptance(unittest.TestCase):
    SPEC = ('import Mathlib.Data.Finset.Powerset\nnamespace GXSpec\n'
            'def s : Prop := ∀ n : ℕ, n + 0 = n\ndef f : Prop := ∀ n : ℕ, n = 0\nend GXSpec\n')

    def proof(self, name, body, imports=('GXSpec',)):
        return {'name': name, 'trusted': False,
                'source': ''.join(f'import {i}\n' for i in imports) + f'namespace {name}\n{body}\nend {name}\n'}

    def test_adversarial_proofs_are_rejected_and_honest_ones_accepted(self):
        mods = [{'name': 'GXSpec', 'source': self.SPEC, 'trusted': True},
                self.proof('GXHonest', 'theorem proof : GXSpec.s := by unfold GXSpec.s; intro n; rfl'),
                self.proof('GXSorry', 'theorem proof : GXSpec.f := by unfold GXSpec.f; exact sorryAx _ false'),
                self.proof('GXWeak', 'theorem proof : True := trivial'),
                self.proof('GXShadow', 'def _root_.GXSpec.f : Prop := True\ntheorem proof : GXSpec.f := trivial'),
                self.proof('GXSide', 'def GXSpec.f2 : Prop := True\ntheorem proof : GXSpec.f2 := trivial'),
                self.proof('GXAxiom', 'axiom cheat : False\ntheorem proof : GXSpec.f := cheat.elim'),
                self.proof('GXImport', 'theorem proof : GXSpec.s := by unfold GXSpec.s; intro n; rfl',
                           imports=('GXSpec', 'Lean')),
                self.proof('GXDepends', 'theorem proof : GXSpec.f := GXAxiom.proof', imports=('GXSpec', 'GXAxiom')),
                self.proof('GXOption', 'set_option maxRecDepth 2000 in\ntheorem proof : GXSpec.s := '
                                       'by unfold GXSpec.s; intro n; simp')]
        binds = [{'spec': 'GXSpec.s', 'proof': 'GXHonest.proof'}, {'spec': 'GXSpec.f', 'proof': 'GXSorry.proof'},
                 {'spec': 'GXSpec.f', 'proof': 'GXWeak.proof'}, {'spec': 'GXSpec.f', 'proof': 'GXShadow.proof'},
                 {'spec': 'GXSpec.f', 'proof': 'GXSide.proof'},
                 {'spec': 'GXSpec.f', 'proof': 'GXAxiom.proof'}, {'spec': 'GXSpec.s', 'proof': 'GXImport.proof'},
                 {'spec': 'GXSpec.f', 'proof': 'GXDepends.proof'}, {'spec': 'GXSpec.s', 'proof': 'GXOption.proof'}]
        r = C.accept(mods, binds)
        got = {b['proof'].split('.')[0]: b['status'] for b in r['bindings']}
        self.assertEqual(got, {'GXHonest': 'CHECKED', 'GXSorry': 'DISALLOWED_AXIOM', 'GXWeak': 'STATEMENT_MISMATCH',
                               'GXShadow': 'ELABORATION_ERROR', 'GXSide': 'STATEMENT_MISMATCH',
                               'GXAxiom': 'FORBIDDEN_CONSTRUCT',
                               'GXImport': 'DISALLOWED_IMPORT', 'GXDepends': 'NOT_ATTEMPTED',
                               'GXOption': 'CHECKED'}, r['bindings'])
        self.assertEqual(r['status'], 'REJECTED')
        honest = next(b for b in r['bindings'] if b['proof'] == 'GXHonest.proof')
        self.assertTrue(set(honest['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'})
        self.assertTrue(all(r['leanchecker'].values()))
        self.assertTrue(any(d['name'] == 'GXHonest.proof' and d['kind'] == 'theorem' for d in r['declarations']))
        self.assertIn('source_identity', r['environment']['workspace'])

    def test_trusted_modules_cannot_import_untrusted_ones(self):
        with self.assertRaises(C.ChainError):
            C.accept([self.proof('GXU', 'theorem proof : True := trivial', imports=()),
                      {'name': 'GXT', 'source': 'import GXU\n', 'trusted': True}], [])

    def test_search_reports_but_never_accepts(self):
        gen = TP.generate(0)
        env = C._env()
        conj = next(c for c in gen['conjectures'] if c['id'] == 'bound_card')
        base = [{'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True},
                {'name': T.CONCEPTS_MODULE, 'source': T.concepts_source(gen['catalog']), 'trusted': True},
                {'name': TP.CONJ_MODULE, 'source': TP._conj_source(gen['conjectures']), 'trusted': True}]
        session = TP.Session(env, base)
        res = S.search(conj, conj_const='GTConj.bound_card', context={'imports': session.imports,
                                                                      'artifacts': session.artifacts},
                       library=[], unfold=T.UNFOLD, env=env)
        self.assertEqual(len(res['attempts']), res['charged']['candidates'])
        self.assertIsNotNone(res['found'])
        self.assertNotIn('status', res)                  # a search has no acceptance verdict
        self.assertFalse(all(a['compiled'] for a in res['attempts']))     # failures are kept and charged


@unittest.skipUnless(READY, 'pinned Lean toolchain, formal workspace or sandbox unavailable')
class CommittedPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads((EVIDENCE / 'package' / 'package.json').read_text())

    def test_the_package_meets_the_contract(self):
        p = self.package
        for field in ('assumptions', 'definitions', 'statements', 'proofs', 'dependencies', 'executable_method',
                      'scope', 'counterexamples', 'costs', 'provenance'):
            self.assertTrue(p.get(field), field)
        status = {s['id']: s['status'] for s in p['statements']}
        self.assertEqual(status['down_closed'], 'CHECKED')
        self.assertEqual(status['bound_union'], 'CHECKED')
        self.assertEqual(status['union_closed'], 'DISPROVED')
        self.assertEqual(status['c4_down_closed'], 'UNSUPPORTED')
        self.assertIn('UNRESOLVED', status.values())
        self.assertEqual(TP.integrity_problems(p), [])
        # reuse: bound_union's proof depends on the generated down_closed lemma
        union_proof = next(s['proof_const'] for s in p['statements'] if s['id'] == 'bound_union')
        down = next(s['proof_const'] for s in p['statements'] if s['id'] == 'down_closed')
        self.assertIn(down, p['dependencies'][union_proof]['package'])
        self.assertTrue(p['method_evaluation']['all_sound'])
        self.assertTrue(p['task_certificates'])
        for c in p['task_certificates']:
            self.assertEqual(c['status'], 'CHECKED')
            self.assertTrue(set(p['executable_method']['lemmas'].values()) <= set(c['uses_package_lemmas']))

    def test_tampering_is_detected_without_lean(self):
        p = copy.deepcopy(self.package)
        p['modules'][-1]['source'] += '\n-- edited\n'
        self.assertEqual(TP.replay(p)['verdict'], 'DIFFERS')
        p = copy.deepcopy(self.package)
        next(s for s in p['statements'] if s['id'] == 'mantel')['status'] = 'CHECKED'
        p['package_sha256'] = digest(TP._core(p))                   # even with a recomputed hash
        report = TP.replay(p)
        self.assertEqual(report['verdict'], 'DIFFERS')
        self.assertFalse(report['checked_in_lean'])

    def test_the_package_replays_from_its_sources_alone(self):
        report = TP.replay(self.package)
        self.assertEqual(report['verdict'], 'REPLAYED', report['differences'])
        self.assertTrue(report['certificates'])
        self.assertTrue(all(c['status'] == 'CHECKED' for c in report['certificates']))


@unittest.skipUnless(READY, 'pinned Lean toolchain, formal workspace or sandbox unavailable')
class LeanDomainAcceptance(unittest.TestCase):
    def test_validate_is_acceptance(self):
        task = LeanStatementTask(task_id='dev-refl', context=(ContextModule(name='GTDefs', source=T.DEFS_SOURCE),),
                                 statement='∀ S : GT.Edges, S ⊆ S', family='theory-template')
        good = ('import GTDefs\nimport GTStmt\nnamespace GTWitness\ntheorem proof : GTStmt.stmt := by\n'
                '  unfold GTStmt.stmt; intro S; exact Finset.Subset.refl S\nend GTWitness\n')
        bad = good.replace('exact Finset.Subset.refl S', 'exact sorryAx _ false')
        self.assertEqual(ADAPTER.validate(task, good)['status'], 'VALID')
        out = ADAPTER.validate(task, bad)
        self.assertEqual((out['status'], out['reason']), ('INVALID', 'DISALLOWED_AXIOM'))
        self.assertEqual(ADAPTER.replay({'task': task.model_dump(mode='json'), 'witness': good})['status'], 'REPLAYED')


if __name__ == '__main__':
    unittest.main()
