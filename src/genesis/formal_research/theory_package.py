"""Theory packages: build, accept, compile into a method, and replay (roadmap W08, W11).

A TheoryPackage holds, as the roadmap requires:
  * assumptions: the allowed axioms, the axioms actually used, the pinned workspace and
    the conventions;
  * definitions: each with its origin, the domain contract or a named generator;
  * formal statements, each with an outcome (CHECKED, DISPROVED, UNRESOLVED or
    UNSUPPORTED) and its proof or counterexample;
  * proofs: the module sources, the recipe that found each one, and its axioms;
  * dependencies: package declarations, taken transitively, and workspace modules;
  * the executable method, scope and known counterexamples;
  * costs: every search attempt and acceptance run;
  * provenance.

`run` produces one package. `replay` rechecks a package from its sources alone, in fresh
sandboxes against the audited workspace. It compares statuses, declaration types and
axioms, and re-accepts the recorded task certificates. A replay never reads anything a
search produced.
"""
import json
from pathlib import Path
import time

from ..common import atomic_write, bytes_hash, canonical, code_identity, digest, utcnow
from . import checker as C
from . import search as S
from . import triangle_theory as T

SCHEMA = 'genesis-theory-package-v1'
REPO = Path(__file__).resolve().parents[3]
CONJ_MODULE = 'GTConj'
METHOD_LEMMAS = ('bound_card', 'bound_union', 'bound_mono')


def _conj_source(conjectures):
    lines = [f'import {T.CONCEPTS_MODULE}', 'set_option linter.unusedVariables false', f'namespace {CONJ_MODULE}']
    for c in conjectures:
        lines.append(f'/-- Generated conjecture `{c["id"]}` ({c["origin"]}). -/')
        lines.append(f'def {c["id"]} : Prop := {c["lean"]}')
        if c['counterexample']:
            lines.append(f'def {c["id"]}_negation : Prop := ¬ {c["id"]}')
    lines += [f'end {CONJ_MODULE}', '']
    return '\n'.join(lines)


def _gadget_conjectures(catalog):
    out = []
    for g in catalog:
        args = ' '.join(str(i) for i in range(g['vertices']))
        inst = f'(GT.{g["name"]} {args})'
        out.append({'id': f'gadget_{g["name"]}_bound', 'lean': f'GT.TFBound {inst} {g["bound"]}', 'binders': [],
                    'origin': 'generated:gadget-search', 'counterexample': None})
        out.append({'id': f'gadget_{g["name"]}_tight', 'lean': f'¬ GT.TFBound {inst} {g["bound"] - 1}',
                    'binders': [], 'origin': 'generated:gadget-search', 'counterexample': None})
    return out


def generate(seed=0):
    """Concepts and screened conjectures (pure Python, no Lean)."""
    catalog, examined = T.gadget_search(max_vertices=5, max_edges=7)
    conjectures, unsupported = [], []
    for name, binders, concl in T.TEMPLATES:
        if not T.supported(binders, concl):
            unsupported.append({'id': name, 'status': 'UNSUPPORTED', 'origin': 'generated:template',
                                'reason': 'mentions a definition this theory does not have'})
            continue
        queue = [(name, binders, concl, 'generated:template')]
        while queue:
            nm, bs, cc, origin = queue.pop(0)
            cx, relevant = T.screen(nm, bs, cc, seed=seed)
            row = {'id': nm, 'lean': T.lean_statement(bs, cc), 'origin': origin, 'screened_instances': relevant,
                   'binders': [{k: v for k, v in b.items() if k != 'model'} for b in bs],
                   'counterexample': None}
            if cx is not None:
                row['counterexample'] = {'values': {b['name']: T.lean_value(cx[b['name']], b['type'])
                                                    for b in bs if not b.get('hyp')},
                                         'model': {k: (sorted(v) if isinstance(v, frozenset) else v)
                                                   for k, v in cx.items()}}
                if T.breaks_normal_form(bs, cx) and not nm.endswith('_simple'):
                    n2, b2, c2 = T.corrected(nm, bs, cc)
                    queue.append((n2, b2, c2, f'generated:hypothesis-correction-of:{nm}'))
            conjectures.append(row)
    conjectures += _gadget_conjectures(catalog)
    return {'catalog': catalog, 'examined': examined, 'conjectures': conjectures, 'unsupported': unsupported}


class Session:
    """Search-side compiled context (untrusted; acceptance never uses these oleans)."""

    def __init__(self, env, base_modules):
        self.env, self.artifacts, self.imports, self.charged = env, {}, [], []
        for m in base_modules:
            self.add(m)

    def add(self, m):
        r = C.compile_module(m['name'], m['source'], dict(self.artifacts), self.env)
        self.charged.append({'kind': 'search-context-compile', 'module': m['name'], **r['stats']})
        if r['result'] != 'COMPILED':
            raise RuntimeError(f'search context {m["name"]} did not compile: {r["result"]}\n{r["log"][-2000:]}')
        self.artifacts.update(r['artifacts'])
        self.imports.append(m['name'])


def run(out, *, seed=0, certificate_tasks=(), method_tasks=(), log=print):
    """Generate, search, accept, package. `certificate_tasks` get Lean-checked certificates;
    `method_tasks` (with certified optima) measure the method's soundness and gap."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    env = C._env()
    gen = generate(seed)
    concepts = T.concepts_source(gen['catalog'])
    conj_src = _conj_source(gen['conjectures'])
    base = [{'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True},
            {'name': T.CONCEPTS_MODULE, 'source': concepts, 'trusted': True},
            {'name': CONJ_MODULE, 'source': conj_src, 'trusted': True}]
    session = Session(env, base)
    cache = {}          # acceptance-owned compilations (never the search's)
    library, proofs, statements, attempts, acceptances = [], [], [], [], []
    for c in gen['conjectures']:
        const = f'{CONJ_MODULE}.{c["id"]}'
        cx = c['counterexample']
        res = S.search(c, conj_const=const, context={'imports': list(session.imports), 'artifacts': session.artifacts},
                       library=library, unfold=T.UNFOLD, counterexample=cx, env=env)
        attempts.append({'statement': c['id'], 'target': res['target'], 'attempts': res['attempts'],
                         'charged': res['charged'], 'result': res['result']})
        row = {'id': c['id'], 'lean': c['lean'], 'origin': c['origin'], 'spec_const': const,
               'screened_instances': c.get('screened_instances'),
               'counterexample': cx and {'values': cx['values']}}
        if res['found'] is None:
            row.update(status='UNRESOLVED', reason='no recipe compiled' if not cx else
                       'the counterexample did not refute the statement in Lean')
            statements.append(row); log(f'{c["id"]}: UNRESOLVED'); continue
        recipe, tactic = res['found']
        name = f'GTP{len(proofs) + 1}'
        target, unfold_first = S.target_of(const, cx)
        src = S.proof_module(name, target, unfold_first, session.imports, tactic)
        module = {'name': name, 'source': src, 'trusted': False}
        binding = {'spec': target, 'proof': f'{name}.proof'}
        chain = base + [p['module'] for p in proofs] + [module]
        receipt = C.accept(chain, [binding], cache=cache)
        acceptances.append({'statement': c['id'], 'status': receipt['status'],
                            'stats': receipt.get('check_stage', {}), 'receipt_sha256': digest(receipt)})
        b = receipt['bindings'][0]
        if b['status'] == 'CHECKED':
            status = 'DISPROVED' if cx else 'CHECKED'
            proofs.append({'statement': c['id'], 'module': module, 'binding': binding, 'recipe': recipe})
            session.add(module)
            if not cx:
                library.append({'const': f'{name}.proof', 'statement': c['id']})
            row.update(status=status, proof_module=name, proof_const=f'{name}.proof', recipe=recipe,
                       axioms=b.get('axioms'))
        else:
            row.update(status='UNRESOLVED', reason=f'the search candidate was not accepted ({b["status"]})',
                       rejected_status=b['status'])
        statements.append(row)
        log(f'{c["id"]}: {row["status"]} ({recipe})')
    # one acceptance of the whole package, with every binding
    modules = base + [p['module'] for p in proofs]
    bindings = [p['binding'] for p in proofs]
    final = C.accept(modules, bindings, cache=cache)
    if final['status'] != 'CHECKED':
        raise RuntimeError(f'the assembled package was not accepted: {final.get("reason")} '
                           f'{[b for b in final["bindings"] if b["status"] != "CHECKED"]}')
    names = {m['name'] for m in modules}
    closure = C.dependency_closure(final['declarations'], names)
    package = {
        'schema': SCHEMA, 'name': 'triangle-free obstruction by gadget packing', 'domain': 'triangle_free_host_v1',
        'assumptions': {'allowed_axioms': final['environment']['allowed_axioms'],
                        'axioms_used': sorted({a for b in final['bindings'] for a in b.get('axioms', [])}),
                        'workspace': final['environment']['workspace'], 'lean': final['environment']['lean'],
                        'conventions': ['edge sets are finite sets of ordered pairs of naturals',
                                        'hosts list each edge once as (u, v) with u < v']},
        'definitions': _definitions(final['declarations'], gen['catalog']),
        'statements': statements + gen['unsupported'],
        'modules': [{'name': m['name'], 'trusted': m['trusted'], 'source': m['source'],
                     'source_sha256': bytes_hash(m['source'].encode())} for m in modules],
        'bindings': bindings,
        'proofs': [{'statement': p['statement'], 'module': p['module']['name'], 'recipe': p['recipe']} for p in proofs],
        'dependencies': closure,
        'declarations': [{k: d[k] for k in ('module', 'name', 'kind', 'axioms')} | {'type_sha256': C.type_fingerprint(d)}
                         for d in final['declarations'] if not d['internal']],
        'gadget_search': {'catalog': gen['catalog'], 'examined': gen['examined']},
        'scope': ('Upper bounds on the largest triangle-free subgraph of a host given as pairs (u, v), u < v. '
                  'Bounds only, never optima. Elementary facts, rediscovered: a capability demonstration '
                  'with no novelty claim.'),
        'counterexamples': [{'statement': s['id'], 'values': s['counterexample']['values'], 'checked': True}
                            for s in statements if s['status'] == 'DISPROVED'],
        'acceptance': {'status': final['status'], 'receipt_sha256': digest(final),
                       'leanchecker': final['leanchecker'], 'check_stage': final['check_stage']},
    }
    method = compile_method(package)
    package['executable_method'] = method and {k: method[k] for k in ('entrypoint', 'code_sha256', 'gadgets',
                                                                      'lemmas', 'library_modules')}
    tasks_out = []
    for task, optimum in method_tasks:
        cert = T.packing_bound(task.n, [tuple(e) for e in task.edges], method)
        tasks_out.append({'task_id': task.task_id, 'edges': len(task.edges), 'bound': cert['bound'],
                          'optimum': optimum, 'sound': optimum is None or cert['bound'] >= optimum,
                          'gap': None if optimum is None else cert['bound'] - optimum,
                          'gadgets_used': len(cert['parts'])})
    certs = []
    for i, task in enumerate(certificate_tasks):
        cert = T.packing_bound(task.n, [tuple(e) for e in task.edges], method)
        spec, proof, binding = T.certificate_modules(f'{i}', task.n, task.edges, cert, method)
        r = C.accept(modules + [spec, proof], [binding], cache=cache)
        certs.append({'task_id': task.task_id, 'bound': cert['bound'], 'certificate': cert,
                      'modules': [spec, proof], 'binding': binding, 'status': r['bindings'][0]['status'],
                      'axioms': r['bindings'][0].get('axioms'),
                      'uses_package_lemmas': sorted(_package_uses(r, proof['name'], names)),
                      'stats': r.get('check_stage', {})})
        log(f'certificate {task.task_id}: {certs[-1]["status"]} bound {cert["bound"]}')
    package['method_evaluation'] = {'split': 'DEV', 'tasks': tasks_out,
                                    'all_sound': all(t['sound'] for t in tasks_out)}
    package['task_certificates'] = certs
    package['costs'] = {'search_runs': len(attempts),
                        'search_candidates': sum(a['charged']['candidates'] for a in attempts),
                        'search_cpu_ns': sum(a['charged']['cpu_ns'] or 0 for a in attempts),
                        'search_context_cpu_ns': sum(c.get('cpu_ns') or 0 for c in session.charged),
                        'acceptance_runs': len(acceptances) + 1 + len(certs),
                        'acceptance_check_cpu_ns': sum((a['stats'] or {}).get('cpu_ns') or 0 for a in acceptances),
                        'wall_seconds': round(time.monotonic() - started, 1),
                        'attempts': attempts, 'acceptances': acceptances}
    package['provenance'] = {'generator_code': code_identity(REPO)['sha256'], 'seed': seed, 'created_at': utcnow(),
                             'search': 'genesis.formal_research.search (builder-written recipes, see recipe names)',
                             'acceptance': 'genesis.formal_research.checker.accept'}
    package['package_sha256'] = digest(_core(package))
    atomic_write(out / 'package.json', json.dumps(package, indent=1, sort_keys=True, ensure_ascii=False).encode())
    (out / 'lean').mkdir()
    for m in package['modules'] + [m for c in certs for m in c['modules']]:
        atomic_write(out / 'lean' / f'{m["name"]}.lean', m['source'].encode())
    return package


def _core(package):
    """The content-addressed part: everything except costs, timings and provenance times."""
    return {k: v for k, v in package.items() if k not in ('costs', 'provenance', 'package_sha256', 'acceptance')} | {
        'acceptance': {'status': package['acceptance']['status']}}


def _definitions(decls, catalog):
    gadgets = {g['name'] for g in catalog}
    out = []
    for d in decls:
        if d['kind'] != 'def' or d['internal'] or d['module'] not in (T.DEFS_MODULE, T.CONCEPTS_MODULE):
            continue
        short = d['name'].split('.')[-1]
        origin = ('domain-contract' if d['module'] == T.DEFS_MODULE else
                  'generated:gadget-search' if short in gadgets else
                  'generated:instance' if short.startswith('inst') else 'generated:concept-template')
        out.append({'name': d['name'], 'module': d['module'], 'origin': origin, 'type_sha256': C.type_fingerprint(d)})
    return out


def _package_uses(receipt, module, package_modules):
    out = set()
    for d in receipt.get('declarations', []):
        if d['module'] == module:
            out |= {u for u, m in d['uses'] if m in package_modules and m.startswith('GTP')}
    return out


def compile_method(package):
    """The executable method compiled from a package: only CHECKED lemmas and gadgets whose
    bound lemma is CHECKED. None if the package lacks what the method needs."""
    st = {s['id']: s for s in package['statements']}
    if any(st.get(l, {}).get('status') != 'CHECKED' for l in METHOD_LEMMAS):
        return None
    gadgets = [g for g in package['gadget_search']['catalog']
               if st.get(f'gadget_{g["name"]}_bound', {}).get('status') == 'CHECKED']
    lemmas = {l: st[l]['proof_const'] for l in METHOD_LEMMAS}
    library = sorted({st[l]['proof_module'] for l in METHOD_LEMMAS} |
                     {p['module'] for p in package['proofs']})
    code = (Path(T.__file__)).read_bytes()
    return {'entrypoint': 'genesis.formal_research.triangle_theory:packing_bound', 'code_sha256': bytes_hash(code),
            'gadgets': gadgets, 'lemmas': lemmas, 'library_modules': library}


def integrity_problems(package):
    """Checks that need no Lean: hashes, and every claimed outcome backed by a binding."""
    out = []
    if package.get('schema') != SCHEMA:
        return ['not a theory package']
    for m in package['modules']:
        if bytes_hash(m['source'].encode()) != m['source_sha256']:
            out.append(f'module {m["name"]} source differs from its hash')
    if package.get('package_sha256') != digest(_core(package)):
        out.append('package content does not match its package_sha256')
    bound = {b['spec'] for b in package['bindings']}
    claimed = {s['spec_const'] + ('_negation' if s['status'] == 'DISPROVED' else '')
               for s in package['statements'] if s.get('status') in ('CHECKED', 'DISPROVED')}
    if bound != claimed:
        out.append(f'claimed outcomes and bindings differ: {sorted(bound ^ claimed)}')
    proofs = {m['name'] for m in package['modules'] if not m['trusted']}
    if {b['proof'].split('.')[0] for b in package['bindings']} - proofs:
        out.append('a binding names a proof module the package does not hold')
    return out


def replay(package):
    """Recheck a package from its sources alone. Returns a report with verdict REPLAYED or DIFFERS."""
    problems = integrity_problems(package)
    if problems:
        return {'schema': 'genesis-theory-replay-v1', 'verdict': 'DIFFERS', 'differences': problems,
                'checked_in_lean': False}
    modules = [{'name': m['name'], 'source': m['source'], 'trusted': m['trusted']} for m in package['modules']]
    cache = {}                                   # this replay's own compilations
    r = C.accept(modules, package['bindings'], cache=cache)
    differences = []
    if r['status'] != 'CHECKED':
        differences.append(f'acceptance status {r["status"]}: '
                           f'{[(b["proof"], b["status"]) for b in r["bindings"] if b["status"] != "CHECKED"]}')
    want = {(d['module'], d['name']): d for d in package['declarations']}
    got = {(d['module'], d['name']): {k: d[k] for k in ('module', 'name', 'kind', 'axioms')} |
           {'type_sha256': C.type_fingerprint(d)} for d in r.get('declarations', []) if not d['internal']}
    for key in sorted(set(want) | set(got)):
        if want.get(key) != got.get(key):
            differences.append(f'declaration {key[1]} differs')
    if r.get('declarations') is not None:
        names = {m['name'] for m in modules}
        if C.dependency_closure(r['declarations'], names) != package['dependencies']:
            differences.append('dependency closure differs')
    certs = []
    for c in package.get('task_certificates', []):
        rc = C.accept(modules + [{k: c['modules'][i][k] for k in ('name', 'source', 'trusted')} for i in (0, 1)],
                      [c['binding']], cache=cache)
        certs.append({'task_id': c['task_id'], 'status': rc['bindings'][0]['status']})
        if rc['bindings'][0]['status'] != c['status']:
            differences.append(f'certificate {c["task_id"]}: {rc["bindings"][0]["status"]} != {c["status"]}')
    return {'schema': 'genesis-theory-replay-v1', 'package_sha256': package.get('package_sha256'),
            'checked_in_lean': True, 'verdict': 'REPLAYED' if not differences else 'DIFFERS', 'differences': differences,
            'environment': r.get('environment'), 'bindings': [(b['proof'], b['status']) for b in r['bindings']],
            'certificates': certs, 'acceptance_receipt_sha256': digest(r), 'replayed_at': utcnow()}


__all__ = ['run', 'replay', 'integrity_problems', 'generate', 'compile_method', 'SCHEMA']
