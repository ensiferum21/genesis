"""A generic conjecture loop: screen, search, accept, assemble (shared by B17-style theories,
representations, worlds and concept recovery).

A conjecture is a dict:
  {'id', 'binders': [{'name', 'type'} | {'name', 'hyp': True, 'lean'}], 'concl': lean text,
   'origin', 'model': python callable(values) -> bool or None, 'sampler': callable(rng) -> values}
Its Lean statement is `∀ (binders...), concl`. Screening evaluates the model on sampled
instances. A falsifying instance becomes a counterexample, and then a Lean proof of the
trusted negation constant. Survivors go to recipe search. Every proof is recompiled and
judged by `checker.accept` before it joins the library.

The assembled record uses the B17 package schema, so `theory_package.replay` and
`integrity_problems` apply unchanged.
"""
import random
import time

from ..common import bytes_hash, digest, utcnow
from . import checker as C
from . import search as S
from .theory_package import SCHEMA, _core

DISCHARGE = '(by first | decide +kernel | (intro v; omega) | omega | (intros; omega))'


def statement(c):
    parts = [f'({b["name"]} : {b["lean"] if b.get("hyp") else b["type"]})' for b in c['binders']]
    return f'∀ {" ".join(parts)}, {c["concl"]}' if parts else c['concl']


def conj_module(name, imports, conjectures, header=''):
    lines = [f'import {m}' for m in imports] + ['set_option linter.unusedVariables false', header,
                                                f'namespace {name}']
    for c in conjectures:
        lines.append(f'/-- Generated conjecture `{c["id"]}` ({c["origin"]}). -/')
        lines.append(f'def {c["id"]} : Prop := {statement(c)}')
        if c.get('counterexample'):
            lines.append(f'def {c["id"]}_negation : Prop := ¬ {c["id"]}')
    lines += [f'end {name}', '']
    return '\n'.join(lines)


def screen(c, *, samples=3000, seed=0):
    """(counterexample values or None, number of instances meeting the hypotheses)."""
    if c.get('model') is None:
        return None, 0
    rng = random.Random(int(digest({'screen': c['id'], 'seed': seed})[:12], 16))
    best, relevant = None, 0
    for _ in range(samples):
        v = c['sampler'](rng)
        if not all(h['model'](v) for h in c['binders'] if h.get('hyp')):
            continue
        relevant += 1
        if not c['model'](v):
            size = sum(_size(x) for x in v.values())
            if best is None or size < best[0]:
                best = (size, v)
    return (None if best is None else best[1]), relevant


def _size(x):
    if isinstance(x, (frozenset, set, tuple, list)):
        return len(x)
    if isinstance(x, dict):
        return sum(1 for y in x.values() if y)
    return x if isinstance(x, int) else 1


def disproof_tactic(c, cx):
    args = ' '.join(f'({cx["values"][b["name"]]})' if not b.get('hyp') else DISCHARGE for b in c['binders'])
    return f'intro h\nexact absurd (h {args}) (by decide +kernel)'


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


def prove_all(conjectures, *, base_modules, conj_name, proof_prefix, unfold, extra_recipes=None, env=None,
              cache=None, library=None, log=print, screen_seed=0):
    """Screen, search and accept every conjecture in order. Returns the loop state."""
    env = env or C._env()
    cache = {} if cache is None else cache
    library = list(library or [])
    unsupported = [c for c in conjectures if c.get('unsupported')]
    live = [c for c in conjectures if not c.get('unsupported')]
    for c in live:
        if c.get('preset_counterexample'):
            c['counterexample'], c['screened_instances'] = c['preset_counterexample'], None
            continue
        cx, relevant = screen(c, seed=screen_seed)
        c['screened_instances'] = relevant
        c['counterexample'] = None if cx is None else {'values': {b['name']: c['lean_value'](b, cx[b['name']])
                                                                   for b in c['binders'] if not b.get('hyp')},
                                                        'model': {k: _plain(x) for k, x in cx.items()}}
    conj_src = conj_module(conj_name, [m['name'] for m in base_modules if m['trusted']], live)
    base = list(base_modules) + [{'name': conj_name, 'source': conj_src, 'trusted': True}]
    session = Session(env, base)
    proofs, statements, attempts, acceptances = [], [], [], []
    for c in live:
        const = f'{conj_name}.{c["id"]}'
        cx = c['counterexample']
        extra = []
        if cx:
            extra = [('counterexample-evaluation', c.get('disproof_tactic') or disproof_tactic(c, cx))]
        elif extra_recipes:
            extra = extra_recipes(c, library)
        res = S.search(c, conj_const=const, context={'imports': list(session.imports), 'artifacts': session.artifacts},
                       library=library, unfold=unfold, counterexample=cx, env=env, extra=extra)
        attempts.append({'statement': c['id'], 'target': res['target'], 'attempts': res['attempts'],
                         'charged': res['charged'], 'result': res['result']})
        row = {'id': c['id'], 'lean': statement(c), 'origin': c['origin'], 'spec_const': const,
               'screened_instances': c.get('screened_instances'),
               'counterexample': cx and {'values': cx['values']}}
        for k in ('role', 'subject'):
            if k in c:
                row[k] = c[k]
        if res['found'] is None:
            row.update(status='UNRESOLVED', reason='no recipe compiled' if not cx else
                       'the counterexample did not refute the statement in Lean')
            statements.append(row); log(f'{c["id"]}: UNRESOLVED'); continue
        recipe, tactic = res['found']
        name = f'{proof_prefix}{len(proofs) + 1}'
        target, unfold_first = S.target_of(const, cx)
        module = {'name': name, 'source': S.proof_module(name, target, unfold_first, session.imports, tactic),
                  'trusted': False}
        binding = {'spec': target, 'proof': f'{name}.proof'}
        receipt = C.accept(base + [p['module'] for p in proofs] + [module], [binding], cache=cache)
        acceptances.append({'statement': c['id'], 'status': receipt['status'],
                            'stats': receipt.get('check_stage', {}), 'receipt_sha256': digest(receipt)})
        b = receipt['bindings'][0]
        if b['status'] == 'CHECKED':
            proofs.append({'statement': c['id'], 'module': module, 'binding': binding, 'recipe': recipe})
            session.add(module)
            if not cx:
                library.append({'const': f'{name}.proof', 'statement': c['id']})
            row.update(status='DISPROVED' if cx else 'CHECKED', proof_module=name, proof_const=f'{name}.proof',
                       recipe=recipe, axioms=b.get('axioms'))
        else:
            row.update(status='UNRESOLVED', reason=f'the search candidate was not accepted ({b["status"]})',
                       rejected_status=b['status'])
        statements.append(row)
        log(f'{c["id"]}: {row["status"]} ({recipe})')
    for c in unsupported:
        statements.append({'id': c['id'], 'status': 'UNSUPPORTED', 'origin': c['origin'],
                           'reason': c['unsupported']})
    return {'base': base, 'proofs': proofs, 'statements': statements, 'attempts': attempts,
            'acceptances': acceptances, 'library': library, 'session': session, 'cache': cache, 'env': env}


def _plain(x):
    if isinstance(x, (frozenset, set)):
        return sorted(x)
    return x


def assemble(state, *, name, domain, scope, conventions, extra=None, trees=()):
    """Accept the whole chain once and build a package record (B17 schema). Modules in
    `trees` have their declaration value trees returned in `final['declarations']`."""
    modules = state['base'] + [p['module'] for p in state['proofs']]
    bindings = [p['binding'] for p in state['proofs']]
    final = C.accept(modules, bindings, cache=state['cache'], trees=trees)
    if final['status'] != 'CHECKED':
        raise RuntimeError(f'the assembled package was not accepted: {final.get("reason")} '
                           f'{[b for b in final["bindings"] if b["status"] != "CHECKED"]}')
    names = {m['name'] for m in modules}
    package = {
        'schema': SCHEMA, 'name': name, 'domain': domain,
        'assumptions': {'allowed_axioms': final['environment']['allowed_axioms'],
                        'axioms_used': sorted({a for b in final['bindings'] for a in b.get('axioms', [])}),
                        'workspace': final['environment']['workspace'], 'lean': final['environment']['lean'],
                        'conventions': conventions},
        'definitions': [{'name': d['name'], 'module': d['module'], 'type_sha256': C.type_fingerprint(d),
                         'origin': 'trusted-generated'}
                        for d in final['declarations'] if d['kind'] == 'def' and not d['internal']
                        and d['module'] in {m['name'] for m in state['base']}],
        'statements': state['statements'],
        'modules': [{'name': m['name'], 'trusted': m['trusted'], 'source': m['source'],
                     'source_sha256': bytes_hash(m['source'].encode())} for m in modules],
        'bindings': bindings,
        'proofs': [{'statement': p['statement'], 'module': p['module']['name'], 'recipe': p['recipe']}
                   for p in state['proofs']],
        'dependencies': C.dependency_closure(final['declarations'], names),
        'declarations': [{k: d[k] for k in ('module', 'name', 'kind', 'axioms')} | {'type_sha256': C.type_fingerprint(d)}
                         for d in final['declarations'] if not d['internal']],
        'scope': scope,
        'counterexamples': [{'statement': s['id'], 'values': s['counterexample']['values'], 'checked': True}
                            for s in state['statements'] if s.get('status') == 'DISPROVED'],
        'acceptance': {'status': final['status'], 'receipt_sha256': digest(final),
                       'leanchecker': final['leanchecker'], 'check_stage': final['check_stage']},
        **(extra or {}),
    }
    package['costs'] = {'search_runs': len(state['attempts']),
                        'search_candidates': sum(a['charged']['candidates'] for a in state['attempts']),
                        'search_cpu_ns': sum(a['charged']['cpu_ns'] or 0 for a in state['attempts']),
                        'search_context_cpu_ns': sum(c.get('cpu_ns') or 0 for c in state['session'].charged),
                        'acceptance_runs': len(state['acceptances']) + 1,
                        'acceptance_check_cpu_ns': sum((a['stats'] or {}).get('cpu_ns') or 0
                                                       for a in state['acceptances']),
                        'attempts': state['attempts'], 'acceptances': state['acceptances']}
    package['provenance'] = {'created_at': utcnow(), 'loop': 'genesis.formal_research.loop',
                             'search': 'genesis.formal_research.search (builder-written recipes, named per proof)',
                             'acceptance': 'genesis.formal_research.checker.accept'}
    package['package_sha256'] = digest(_core(package))
    return package, final


__all__ = ['prove_all', 'assemble', 'screen', 'statement', 'conj_module', 'Session', 'disproof_tactic']
