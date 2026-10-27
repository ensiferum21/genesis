#!/usr/bin/env python3
"""B20_R158 (F5): Genesis poses its own conjectures, attacks them, and learns from what it settles, generation after
generation. Does the self-improving inventor settle more than its predecessor? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r158_open_conjectures.py evidence/open_conjectures_b20r158     run ALONE (resumable; slices exit 3)

**Why.** Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md`): "without requiring humans to specify
each problem, concept, or method in advance". Here no problem comes from a human. Genesis generates its own data,
poses its own conjectures from it, attacks them, abstracts representations from what converges, extracts the
procedures behind its discoveries, and carries all of it into the next generation.

**A generation k = 1..G (G = 3):**
  1. *data* D_k:
     - D_1 is 600 graphs Genesis draws itself (`conjecture.generate.data`, from DATA_SEED);
     - D_{k+1} is D_k plus every graph certified as a counterexample in generation k by either arm (TxGraffiti's
       "Red Burton" rule: a refuted conjecture's counterexample joins the data, so it is not posed again);
  2. *conjectures* C_k: `generate.conjectures(D_k)` (local upper bounds on mu that hold on all the data, are sharp
     somewhere and are not dominated), minus any equivalent to one posed in an earlier generation;
  3. *the kernel's filter* (logged, not explained to the research plane):
     - conjectures equivalent on random points to a bound held out for the proving test (18, 21, 24, 30, 40) are
       withheld;
     - conjectures equivalent to a published bound are labelled (rediscoveries) by status;
  4. *the attack*: two arms on the same posed set, at the same budget B_k = |posed| x B_PER evaluations:
     - **FULL**, the self-improving inventor: the policy 'procedure' with abstraction on. Its library holds the
       procedures extracted from its own discoveries in earlier generations. The templates it abstracted earlier are
       available as representations;
     - **PLAIN**, its predecessor: the Frontier's allocation alone, no abstraction, no library, no templates;
  5. *verification* (kernel side): a refutation counts if the Rayleigh certificate and a second check confirm it.
     The second check is the Sturm count on the characteristic polynomial for n <= 40, and an independently written
     matrix-form Rayleigh check from a power-stepped vector above that;
  6. *consolidation*: FULL's procedures (`frontier.procedure.extract`) and templates carry into generation k + 1.

**Primary.** P1: over all generations, certified refutations by FULL against PLAIN on the same posed conjectures,
by the exact one-sided McNemar test on the conjectures refuted by exactly one arm. Verdict:
  * INVALID if validity fails;
  * else FULL_BETTER if p < 0.05;
  * else NOT_SHOWN.
**Secondary:**
  * S1: per generation, the number posed, withheld, refuted (each arm) and surviving;
  * S2: the survivors, conjectures neither arm refuted. Each is checked on every connected graph with up to 7
    vertices (the networkx atlas, a kernel-side check) and kept as a candidate. **Never a theorem.**
  * S3: rediscoveries by status;
  * S4: compounding. Discoveries made through templates abstracted in an earlier generation, and through
    procedures extracted earlier;
  * S5: CPU per arm. The arms are matched in evaluations; template graphs are larger, so their evaluations cost
    more, and the CPU ratio is reported.
**Validity:**
  * no certified refutation of a conjecture equivalent to a proved bound (Brankov-Hansen-Stevanovic's 22, or
    Anderson-Morley, Merris, Li-Pan, 2 Delta);
  * the forbidden-concept audit of the research plane is clean;
  * the budgets were spent;
  * the pins.

**Expectation, stated before running (low confidence).**
  * Generation 1 poses about 20-30 conjectures.
  * Several are rediscoveries of published bounds: in development, Merris's bound and Brankov-Hansen-Stevanovic's
    10 and 29 appeared, and 18 and 21 would be withheld.
  * Most of the refutable ones fall to both arms.
  * Few are refuted by one arm only: P1 NOT_SHOWN.
  * The survivors are mostly proved published bounds.

**Development looks (disclosed).**
  * The conjecture generator ran once on 500 of Genesis's own graphs (another seed); the builder recognised
    published bounds among its 25 conjectures (`docs/OMEGA_FRONTIER.md` §5.6, §6), which is where the withholding
    rule comes from.
  * No generation of this study's data seed was run.

**Cost.** G = 3 generations, about 25 conjectures each, B_PER = 100,000 evaluations: about 2.5M per arm per
generation. About 1.5 h, in slices of 6,600 s. **Status.** DEV; licenses nothing; adopts nothing.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r158'
DATA_SEED = 73159460
G, DATA_COUNT, B_PER, QUANTUM = 3, 600, 100_000, 500
CHUNK = 400
ALPHA = 0.05
SLICE_S, PAUSED = 6600, 3
CLASSICAL_PROVED = {'Anderson-Morley 1985': ('di + dj', 'edge'), 'Merris 1998': ('d + m', 'vertex'),
                    'Li-Pan 2001': ('sqrt(2*d^2 + 2*d*m)', 'vertex'), '2 Delta': ('2*d', 'vertex')}
MODULES = ('frontier/direction.py', 'frontier/curves.py', 'frontier/converge.py', 'frontier/allocate.py',
           'frontier/engine.py', 'frontier/manifest.py', 'frontier/procedure.py', 'conjecture/expr.py',
           'conjecture/graphs.py', 'conjecture/attack.py', 'conjecture/domain.py', 'conjecture/abstraction.py',
           'conjecture/generate.py', 'conjecture/sealed.py', 'conjecture/verify.py', 'conjecture/audit.py')
PINNED = {             # `pins()` at preregistration; checked at run time
    'frontier/direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'frontier/curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'frontier/converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'frontier/allocate.py': 'd28d0d8bd9a85f38d335f5680ad24a444ed5f5cad5420fa075c8079ccde28177',
    'frontier/engine.py': '849b9bfd611c5cbc8899a55e9ec11348741ecdb7e93e47f10d606ff117e84fe3',
    'frontier/manifest.py': '75587e359fcb37a9ab97109a79f1ec5d3417e9618d3bc52cc9f9be8a134055e1',
    'frontier/procedure.py': 'eddf430405175a7989fdc08f5017d9b3adf6b0ccadfef94bfad2e8cf9b68ea49',
    'conjecture/expr.py': '75690202d6a7ab54f75a76500ada6e675b51cf23e7b78b20b4c33f90bc62adf9',
    'conjecture/graphs.py': 'f84059118cf6d74a8ca218fefc98593110e5634353655323b2b108fbca42a972',
    'conjecture/attack.py': '088d22a0ab76c2f42d2d57657024c600bc9bff196e43cf4031e061849a4ed239',
    'conjecture/domain.py': 'e619811ac5a6b16d705575727d54c5364d708dd5f952c47e109bc43b82f229df',
    'conjecture/abstraction.py': '5134dd21cc2e478d419621f2a0dc5b220339817bc4df427e48139af7501e5725',
    'conjecture/generate.py': '386d17bc934b6959e5ee7dc6e96cf9d7f0e742b8854dd6ecf2e6596cb3b6644e',
    'conjecture/sealed.py': 'ae7d429c76e12171f9918213eaef9c33d83a1ffbd7d905953b9a79d129f41bcf',
    'conjecture/verify.py': '712c5fc1ed0c4404ac2f423c12cb7356cf9e9a90b305e19ebd293b5ec2cc0706',
    'conjecture/audit.py': '8b573dfd6c4dd890a65db32f8e300afde6296ce12625377918897715276961e7',
}


class Paused(Exception):
    pass


def h(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def tuplify(x):
    """JSON lists back to tuples (templates are nested tuples), recursively; dicts keep their keys."""
    if isinstance(x, dict):
        return {k: tuplify(v) for k, v in x.items()}
    if isinstance(x, list):
        return tuple(tuplify(v) for v in x)
    return x


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis' / m).read_bytes()).hexdigest() for m in MODULES}


# ------------------------------------------------------------------------------------------- the kernel's side

def labels(formula):
    """(withheld, label): the kernel's view of a vertex-kind conjecture (equivalence on random points)."""
    from genesis.conjecture import generate as GN
    from genesis.conjecture import sealed as SD
    for k in SD.PROVING_TEST_HOLDOUT:
        f, kind = SD.BOUNDS[k][0], SD.kind(k)
        if kind == 'vertex' and GN.equivalent(formula, f):
            return True, f'withheld (proving test, bound {k})'
    for k, (f, *_rest) in sorted(SD.BOUNDS.items()):
        if SD.kind(k) == 'vertex' and GN.equivalent(formula, f):
            return False, f'rediscovery of bound {k} ({SD.status(k)})'
    for name, (f, kind) in CLASSICAL_PROVED.items():
        if kind == 'vertex' and GN.equivalent(formula, f):
            return False, f'rediscovery of {name} (proved)'
    return False, None


def double_check(formula, kind, art):
    from fractions import Fraction
    from genesis.conjecture import verify as V
    try:
        edges = [tuple(e) for e in art['edges']]
        x = [Fraction(v) for v in art['x']]
        if V.check(formula, kind, art['n'], edges, x)['verdict'] != 'REFUTED':
            return 'REJECTED'
        second = V.check_charpoly(formula, kind, art['n'], edges) if art['n'] <= 40 else \
            V.check_matrix_form(formula, kind, art['n'], edges, x)
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        return 'REJECTED'
    return 'CONFIRMED' if second and second['verdict'] == 'REFUTED' else 'UNCONFIRMED'


def survives_small(formula, kind):
    """Whether no connected graph on 2-7 vertices violates the conjecture in floating point (a kernel check)."""
    import networkx as nx
    import numpy as np
    from genesis.conjecture import attack as AT
    B = AT.Bound(formula, kind)
    for g in nx.graph_atlas_g():
        if g.number_of_nodes() < 2 or not nx.is_connected(g):
            continue
        A = nx.to_numpy_array(g, dtype=np.int64)
        s = B.score(A)
        if s > 1e-9:
            return False
    return True


def proved_equivalent(formula):
    from genesis.conjecture import generate as GN
    from genesis.conjecture import sealed as SD
    if any(SD.kind(k) == 'vertex' and SD.status(k) == 'proved' and GN.equivalent(formula, SD.BOUNDS[k][0])
           for k in SD.BOUNDS):
        return True
    return any(kind == 'vertex' and GN.equivalent(formula, f) for f, kind in CLASSICAL_PROVED.values())


def mcnemar_one_sided(b, c):
    from math import comb
    n = b + c
    return 1.0 if n == 0 else sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


# ------------------------------------------------------------------------------------------- one generation

def run_arm(arm, posed, b_per, library, templates, state_path, deadline):
    """One arm on one generation's posed set. Returns its record; pauses at the deadline (state saved)."""
    from genesis.conjecture import verify as V
    from genesis.conjecture.domain import ConjectureDomain
    from genesis.frontier import procedure as PR
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    full = arm == 'FULL'
    dom = ConjectureDomain(posed, abstraction=full)
    if full:
        dom.templates = {k: v for k, v in templates.items()}
    m = Manifest(dom, V.verifier(posed), b_per * len(posed), quantum=QUANTUM,
                 description={'study': STUDY, 'arm': arm})
    if state_path.exists():
        tpath = state_path.with_suffix('.templates.json')
        if full and tpath.exists():
            dom.templates.update(tuplify(json.loads(tpath.read_text())))
        e = Frontier.load(state_path, m, policy_params={'procedures': library} if full else None)
    else:
        e = Frontier(m, 'procedure' if full else 'frontier', seed=int(h(STUDY, arm)[:8], 16), abstraction=full,
                     branch_out=False, policy_params={'procedures': library} if full else None)
    c0 = time.process_time()
    while True:
        status = e.run(CHUNK)
        if status == 'done':
            break
        e.save(state_path)
        if full:
            state_path.with_suffix('.templates.json').write_text(json.dumps(dom.templates, default=list))
        if time.monotonic() > deadline:
            raise Paused
    procs = []
    if full:
        for p in sorted(e.best_verified):
            if e.best_verified[p] > 0:
                pr = PR.extract(e, p)
                if pr is not None:
                    procs.append(pr)
    via = {}
    for ev in e.events:
        if ev['kind'] == 'verified':
            d = e.branches[ev['branch']]['direction']
            via[ev['problem']] = {'representation': d['representation'], 'method': d['method'],
                                  'op': d.get('op'), 'inherited_template': d['representation'] in templates}
    return {'arm': arm, 'spent': e.spent, 'budget': b_per * len(posed),
            'refuted': sorted(p for p, v in e.best_verified.items() if v > 0),
            'artifacts': {p: {k: a[k] for k in ('n', 'edges', 'x')} for p, a in e.best_artifact.items()},
            'via': via, 'procedures': procs, 'templates': dom.templates if full else {},
            'procedure_opens': sum(1 for ev in e.events if ev['kind'] == 'open' and ev.get('op') == 'procedure'),
            'cpu': round(time.process_time() - c0, 3)}


def main(argv=None, registered=True, b_per=B_PER, generations=G, data_count=DATA_COUNT):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    import numpy as np
    from genesis.conjecture import audit as AU
    from genesis.conjecture import generate as GN
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'open_conjectures_b20r158').resolve():
        raise SystemExit('the registered output is evidence/open_conjectures_b20r158')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    deadline = t0 + SLICE_S
    gens_path = out / 'generations.jsonl'
    done = [json.loads(x) for x in gens_path.read_text().splitlines()] if gens_path.exists() else []
    data = GN.data(np.random.default_rng(DATA_SEED), count=data_count)
    posed_before, library, templates = [], [], {}
    for g in done:                                        # replay the consolidated state
        posed_before += [f for f, _ in g['posed'].values()] + g['withheld']
        library += g['FULL']['procedures']
        templates.update(tuplify(g['FULL']['templates']))
        data += [(np.array(A), mu, np.array(dg), np.array(mm)) for A, mu, dg, mm in g['new_data']]
    made = 0
    try:
        for k in range(len(done) + 1, generations + 1):
            gdir = out / f'gen{k}'
            gdir.mkdir(exist_ok=True)
            cpath = gdir / 'conjectures.json'
            if cpath.exists():
                cj = json.loads(cpath.read_text())
            else:
                kept = [f for f, _ in GN.conjectures(data)]
                fresh = [f for f in kept if not any(GN.equivalent(f, q) for q in posed_before)]
                posed, withheld, lab = {}, [], {}
                for f in fresh:
                    w, label = labels(f)
                    if w:
                        withheld.append(f)
                    else:
                        pid = 'C' + h(STUDY, k, f)[:10]
                        posed[pid] = [f, 'vertex']
                        lab[pid] = label
                cj = {'posed': posed, 'withheld': withheld, 'labels': lab, 'kept': len(kept)}
                cpath.write_text(json.dumps(cj, indent=1, sort_keys=True))
            posed = {p: tuple(v) for p, v in cj['posed'].items()}
            rec = {}
            for arm in ('FULL', 'PLAIN'):
                rpath = gdir / f'{arm}.json'
                if rpath.exists():
                    rec[arm] = json.loads(rpath.read_text())
                    rec[arm]['templates'] = tuplify(rec[arm]['templates'])
                    continue
                if not posed:
                    rec[arm] = {'arm': arm, 'spent': 0, 'budget': 0, 'refuted': [], 'artifacts': {}, 'via': {},
                                'procedures': [], 'templates': dict(templates), 'procedure_opens': 0, 'cpu': 0.0}
                else:
                    rec[arm] = run_arm(arm, posed, b_per, library, templates, gdir / f'state_{arm}.json',
                                       deadline if made else deadline + 10 ** 9)
                rpath.write_text(json.dumps(rec[arm], sort_keys=True, default=list))
                made += 1
            # the kernel: double checks, new data, survivors
            confirmed = {}
            new_data = []
            for arm in ('FULL', 'PLAIN'):
                confirmed[arm] = []
                for p, art in sorted(rec[arm]['artifacts'].items()):
                    if p in rec[arm]['refuted'] and double_check(posed[p][0], 'vertex', art) == 'CONFIRMED':
                        confirmed[arm].append(p)
                        from genesis.conjecture import attack as AT
                        A = np.zeros((art['n'], art['n']), dtype=np.int64)
                        for u, v in art['edges']:
                            A[u, v] = A[v, u] = 1
                        if art['n'] <= 64:
                            deg = A.sum(axis=1).astype(float)
                            mm = (A @ deg) / deg
                            L = (np.diag(A.sum(axis=1)) - A).astype(float)
                            new_data.append((A.tolist(), float(np.linalg.eigvalsh(L)[-1]), deg.tolist(), mm.tolist()))
            survivors = sorted(p for p in posed if p not in confirmed['FULL'] and p not in confirmed['PLAIN'])
            g = {'k': k, 'kept': cj['kept'], 'posed': cj['posed'], 'withheld': cj['withheld'], 'labels': cj['labels'],
                 'confirmed': confirmed, 'survivors': survivors,
                 'survivors_small_exhaustive': {p: survives_small(posed[p][0], 'vertex') for p in survivors},
                 'FULL': rec['FULL'], 'PLAIN': rec['PLAIN'], 'new_data': new_data}
            with gens_path.open('a') as f:
                f.write(json.dumps(g, sort_keys=True, default=list) + '\n')
            done.append(g)
            posed_before += [f for f, _ in cj['posed'].values()] + cj['withheld']
            library += rec['FULL']['procedures']
            templates.update(tuplify(rec['FULL']['templates']))
            data += [(np.array(A), mu, np.array(dg), np.array(mm)) for A, mu, dg, mm in new_data]
    except Paused:
        return PAUSED
    # the analysis
    both = {'FULL': set(), 'PLAIN': set()}
    for g in done:
        for arm in both:
            both[arm] |= set(g['confirmed'][arm])
    b = len(both['FULL'] - both['PLAIN'])
    c = len(both['PLAIN'] - both['FULL'])
    p1 = {'full_only': b, 'plain_only': c, 'p': mcnemar_one_sided(b, c)}
    proved_hits = sorted({g['posed'][p][0] for g in done for arm in both for p in g['confirmed'][arm]
                          if proved_equivalent(g['posed'][p][0])})
    audit = AU.scan(AU.research_plane(ROOT))
    spent_ok = all(g[arm]['spent'] >= g[arm]['budget'] - QUANTUM - 1 for g in done for arm in ('FULL', 'PLAIN'))
    pins_ok = (not registered) or pins() == PINNED
    valid = not proved_hits and not audit and spent_ok and pins_ok
    verdict = 'INVALID' if not valid else ('FULL_BETTER' if p1['p'] < ALPHA else 'NOT_SHOWN')
    compounding = sum(1 for g in done for v in g['FULL']['via'].values() if v['inherited_template'])
    summary = {'study': STUDY, 'schema': 'genesis-b20r158-open-conjectures-v1', 'verdict': verdict, 'valid': valid,
               'P1': p1, 'proved_equivalents_refuted': proved_hits, 'audit_hits': audit, 'spent_ok': spent_ok,
               'pins_ok': pins_ok,
               'generations': [{'k': g['k'], 'kept': g['kept'], 'posed': len(g['posed']), 'withheld': len(g['withheld']),
                                'refuted_full': len(g['confirmed']['FULL']), 'refuted_plain': len(g['confirmed']['PLAIN']),
                                'survivors': len(g['survivors']),
                                'survivors_small_exhaustive': sum(g['survivors_small_exhaustive'].values()),
                                'templates': len(g['FULL']['templates']), 'procedures': len(g['FULL']['procedures']),
                                'procedure_opens': g['FULL']['procedure_opens'],
                                'cpu': {a: g[a]['cpu'] for a in ('FULL', 'PLAIN')}} for g in done],
               'rediscoveries': sorted({lab for g in done for lab in g['labels'].values() if lab}),
               'survivors': [{'k': g['k'], 'formula': g['posed'][p][0], 'label': g['labels'].get(p),
                              'small_exhaustive': g['survivors_small_exhaustive'][p]} for g in done
                             for p in g['survivors']],
               'compounding_inherited_template_discoveries': compounding,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'valid', 'P1', 'generations')}, indent=1, default=list))
    return 0


if __name__ == '__main__':
    sys.exit(main())
