#!/usr/bin/env python3
"""B20_R135: do representations Genesis invents beat the textbook ones? (DEV, preregistered; Genesis Ω3/Ω7)

    taskset -c 0 python3 scripts/b20r135_invented_representations.py OUT_DIR     run ALONE (resumable)

**Why.** Daniel's directive of 24 Oct 2026, 15:35, items 6-8: Genesis must synthesise executable representations
(objects, relations, operators, transformations, decoders), preserve them exactly with their lineage, verify them,
and let them reactivate dormant work. The representation language (`genesis.representation`, built on fixtures)
does this; this study asks whether it is useful on real instances. **Preregistered before B20_R133's colouring
results were seen** (that study's runs had not reached colouring when this was committed), so nothing here is tuned
to them.

**Part B (primary): colouring with an encoding Genesis chooses, against one-hot.** k in (3, 4, 5) colours; graphs
G(n, d/n) with d = 4.5, 9, 13.5 (near the k-colourability thresholds), n in (300, 1000), 10 fresh graphs per (k, n)
(`compiler.families.generate('coloring', ...)`, seeds from SEED).
  * **Genesis's choice, per k** (on 4 training graphs of n = 300, their own seeds): the encoding search
    (`encodings.search`: every code table in b = ceil(log2 k) and b + 1 bits (at most k) up to bit symmetry (the
    colour relation is symmetric under renaming colours, so one order per table), each planned as the cheaper of
    whole lifted relations and discovered factorisations, scored by variables then non-zero coefficients) gives its 3
    cheapest feasible tables other than one-hot; with one-hot they are the candidates. Each candidate runs at 2 s on the training graphs; the lowest mean
    conflicts wins (ties to the cheaper table, one-hot last).
  * **The pipeline, identical for every encoding:** the finite-domain problem through the encoding's plan
    (`encodings.compile_fd`), validity weight W = 1 + (largest degree) x (the edge plan's largest sum of |coefficients|),
    one BQP (`compile`, Max-CSP mode), Genesis's engine (`compiler.backends.genesis`: max-cut, `mcx2` REX at the
    budget), decoded; a vertex left with an invalid code gets the colour with the fewest conflicts given the others
    (in vertex order). Conflicts are counted by the family's checker (`compiler.families.verify`) and again by an
    independent count.
  * **Arms at 10 s, one seed per (graph, arm):** `chosen`, `one_hot` (the textbook representation through the same
    pipeline), `compiler` (B20_R133's path: the compiler's one-hot BQP with its penalty and repair), `maxsat`
    (PASMaxSAT-c on the natural encoding).
  * **Primary family (Holm, alpha 0.05):** per k where Genesis chose something other than one-hot, `chosen` against
    `one_hot` on conflicts, two-sided sign test over the 20 graphs: INVENTED_BETTER / INVENTED_WORSE /
    NOT_DISTINGUISHABLE. **Verdict:** INVENTED_REPRESENTATION_BETTER if some k is INVENTED_BETTER after Holm and none
    is INVENTED_WORSE; INVENTED_REPRESENTATION_WORSE if the reverse; MIXED if both; NO_INVENTION if Genesis chose
    one-hot for every k; NOT_SHOWN otherwise.

**Part A (secondary): synthesis.** Every orbit of non-trivial arity-3 relations and 40 random arity-4 relations: the
MILP synthesiser (up to 2 ancillas, coefficients in [-8, 8], 30 s) against the local-search baseline given the same
CPU time; exact gadgets found by each (an exact McNemar sign test on the discordant relations), ancillas where both
succeed; uniform gadgets by the MILP. Every admitted gadget passes both checkers (validity).

**Part C (secondary): families whose reductions Genesis synthesises, through the vault.** 1-in-3 SAT (m = 0.6 n),
NAE-3SAT (2.1 n), XOR-3SAT (0.9 n) and Max-3-SAT (4.2 n), n in (500, 2000), 10 instances per (family, n). Each family
is first parked in a fresh vault as a dormant ProblemSpec lacking its relation; the four gadgets are synthesised,
admitted, archived and announced; the vault's cascade (fuel 4, depth 1) must reactivate exactly the four families
(and a null trigger nothing). Arms at 10 s: `genesis` (the synthesised Max-CSP BQP through the engine) and `maxsat`
(PASMaxSAT-c on the natural encoding); satisfied constraints by the family's checker and an independent count; a
two-sided sign test per family. The CPU of synthesis, archiving and the cascade is reported (overhead).

**Validity:** every gadget exact under both checkers; every answer checked twice; the engine's median CPU at least 0.9
of the budget; the cascade reactivates exactly the parked families. **Human knowledge (contract §13):** the families'
definitions as predicates, their generators and checkers, the natural MaxSAT encodings, the pipeline's validity
weight and repair rule. No QUBO, penalty form or reduction for any family was written by the builder.

**Prior art** (no novelty is claimed; any candidate is checked first): penalty synthesis by MILP/SMT (Bian et al.
2016); QUBO formulations (Lucas 2014; Glover, Kochenberger and Du 2019); higher-order reductions (Rosenberg 1975;
Ishikawa 2011); finite-domain encodings (one-hot, log, order and domain-wall encodings: Tamura et al. 2009; Chancellor
2019).

**Development looks (disclosed).** The fixtures only (`test_representation_*`); one look at the encoding search's
cost tables (no solver run; n = 300 and the study's degrees), as variables / non-zero coefficients: k = 3: the 2-bit
code {00, 01, 10} 600 / 7,725, a 3-bit code with a discovered factorisation 900 / 5,850, one-hot 900 / 4,125; k = 4:
3-bit codes 900 / 25,200-30,900, the 2-bit code (one ancilla per edge) 1,950 / 17,550, one-hot 1,200 / 8,700; k = 5:
3 of 30 tables feasible, 3-bit codes (one ancilla per edge) 2,925 / 41,700-43,125, one-hot 1,500 / 14,925. A smoke run
of main() with a fake engine and a small design (no solver). No solver was run on any colouring or family instance
through this pipeline.

**Expectation, stated before running.** Part B: the pilot keeps one-hot for k = 5 (the alternatives need an ancilla
per edge); for k = 3 and 4 a denser code may win the pilot; P_k NOT_DISTINGUISHABLE or INVENTED_WORSE (denser
couplings make a harder max-cut instance), verdict NOT_SHOWN or INVENTED_REPRESENTATION_WORSE. `maxsat` best on colouring. Part A:
the MILP finds a gadget for every arity-3 orbit and most arity-4 relations, the search for fewer. Part C: the cascade
reactivates the four families; `maxsat` ahead on Max-3-SAT and 1-in-3 SAT, ties on NAE-3SAT and XOR-3SAT possible.
**Cost.** Part B about 45 min, Part C about 27 min, Part A about 15 min: about 1.5 h. **Status.** DEV; licenses
nothing.
"""
import json
from pathlib import Path
import random
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r135'
SEED = 20531351
KS = (3, 4, 5)
DEG = {3: 4.5, 4: 9.0, 5: 13.5}
SIZES = (300, 1000)
N_PER, N_TRAIN = 10, 4
BUDGET, PILOT = 10.0, 2.0
N_CANDIDATES = 3
FAMILY_RATIO = {'one_in_three': 0.6, 'nae3': 2.1, 'xor3': 0.9, 'max3sat': 4.2}
FAMILY_SIZES = (500, 2000)
N_RANDOM4 = 40
ALPHA = 0.05
SOLVER = 'pasmaxsat-c'
NEQ = {'neq': (lambda v: v[0] != v[1], 2)}


def synth(rel, uniform):
    from genesis.representation import gadgets as GD
    return GD.synthesize_milp(rel, max_ancillas=2, bound=8, uniform=uniform, time_limit=30)


# ------------------------------------------------------------------------------------------- instances

def colouring_graphs():
    """{k: {'train': [inst], 'test': [inst]}} (instances carry their seed and size)."""
    from genesis.compiler import families as FM
    out = {}
    for ki, k in enumerate(KS):
        tr = []
        for i in range(N_TRAIN):
            s = SEED + 10000 * ki + i
            tr.append(dict(FM.generate('coloring', s, {'n': 300, 'd': DEG[k], 'k': k}), seed=s, size=300))
        te = []
        for si, n in enumerate(SIZES):
            for i in range(N_PER):
                s = SEED + 10000 * ki + 1000 * (si + 1) + i
                te.append(dict(FM.generate('coloring', s, {'n': n, 'd': DEG[k], 'k': k}), seed=s, size=n))
        out[k] = {'train': tr, 'test': te}
    return out


def family_instances():
    from genesis.representation import families as F
    out = []
    for fi, fam in enumerate(F.FAMILIES):
        for si, n in enumerate(FAMILY_SIZES):
            for i in range(N_PER):
                s = SEED + 50000 + 1000 * fi + 100 * si + i
                out.append(dict(F.generate(fam, s, {'n': n, 'm': round(FAMILY_RATIO[fam] * n)}), seed=s, size=n))
    return out


def part_a_relations():
    from genesis.representation import relations as R
    reps = [r for r in R.orbit_representatives(3) if 0 < r.size() < 8]
    rng = random.Random(f'{STUDY}|random4')
    rand = []
    while len(rand) < N_RANDOM4:
        r = R.random_relation(4, rng)
        if 0 < r.size() < 16 and r.id() not in {x.id() for x in rand}:
            rand.append(r)
    return reps, rand


# ------------------------------------------------------------------------------------------- the pipeline

def fd_problem(inst):
    return {'n': inst['n'], 'D': inst['k'], 'constraints': [{'name': 'neq', 'vars': list(e), 'weight': 1}
                                                            for e in inst['edges']]}


def validity_weight(inst, plan, lib):
    """1 + (largest degree) x (the edge plan's largest sum of |coefficients|)."""
    from genesis.representation import library as LB
    from genesis.representation import relations as R
    deg = [0] * inst['n']
    for u, v in inst['edges']:
        deg[u] += 1
        deg[v] += 1
    s = 0
    for piece in plan['neq']['pieces']:
        g = LB.lookup(lib, R.relation_from_json(piece['relation']), True)
        s += abs(g.c) + sum(abs(x) for x in g.h) + sum(abs(x) for x in g.J.values())
    return 1 + max(deg) * s


def repair_colours(inst, col):
    """A vertex left without a valid colour gets the colour with the fewest conflicts with its coloured neighbours
    (vertices in order)."""
    adj = [[] for _ in range(inst['n'])]
    for u, v in inst['edges']:
        adj[u].append(v)
        adj[v].append(u)
    col = list(col)
    for v in range(inst['n']):
        if col[v] is None:
            counts = [sum(col[w] == c for w in adj[v]) for c in range(inst['k'])]
            col[v] = min(range(inst['k']), key=lambda c: (counts[c], c))
    return col


def independent_conflicts(inst, col):
    import numpy as np
    c = np.asarray(col)
    E = np.asarray(inst['edges'])
    return int((c[E[:, 0]] == c[E[:, 1]]).sum())


def independent_satisfied(inst, x):
    """Satisfied constraints counted apart from `representation.families` (numpy, from the literals)."""
    import numpy as np
    C = np.asarray(inst['constraints'])
    z = np.asarray(x[:inst['n']])
    t = (z[np.abs(C) - 1] == (C > 0)).sum(axis=1)
    fam = inst['family']
    ok = {'one_in_three': t == 1, 'nae3': (t > 0) & (t < 3), 'xor3': t % 2 == 1, 'max3sat': t >= 1}[fam]
    return int(ok.sum())


def child_cpu():
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime


def solve_encoded(inst, enc, plan, lib, budget, seed, run=None):
    """(colours, info) through the representation pipeline with Genesis's engine."""
    from genesis.compiler import backends as BK
    from genesis.representation import compile as C
    from genesis.representation import encodings as E
    run = run or BK.run
    bp = E.compile_fd(fd_problem(inst), enc, NEQ, plan, validity_weight(inst, plan, lib))
    bqp, info = C.compile(bp, lib, 'max_csp')
    c0 = child_cpu()
    x, rinfo = run('genesis', bqp, budget, seed)
    cpu = child_cpu() - c0
    col0 = E.decode_fd(C.decode(x, info), enc, inst['n'])
    invalid = sum(v is None for v in col0)
    return repair_colours(inst, col0), {'variables': bqp['n'], 'terms': len(bqp['linear']) + len(bqp['quadratic']),
                                        'invalid_before_repair': invalid, 'cpu': cpu}


def solve_compiler(inst, budget, seed, run=None):
    from genesis.compiler import backends as BK
    from genesis.compiler import families as FM
    run = run or BK.run
    c0 = child_cpu()
    x, info = run('genesis', FM.compile('coloring', inst), budget, seed)
    cpu = child_cpu() - c0
    col = FM.decode('coloring', inst, x)['colours']
    col = repair_colours(inst, [c if c >= 0 else None for c in col])
    return col, {'cpu': cpu, 'violations_before_repair': info.get('violations_before_repair')}


def solve_maxsat_colouring(inst, budget, seed, run=None):
    from genesis.compiler import backends as BK
    from genesis.compiler import families as FM
    run = run or BK.run
    c0 = child_cpu()
    x, info = run('maxsat', FM.compile('coloring', inst), budget, seed, solver=SOLVER, native=FM.wcnf('coloring', inst))
    cpu = child_cpu() - c0
    col = FM.decode('coloring', inst, x)['colours']
    col = repair_colours(inst, [c if c >= 0 else None for c in col])
    return col, {'cpu': cpu, 'model': info.get('model')}


# ------------------------------------------------------------------------------------------- statistics

def sign(a, b, names, lower_better=True):
    from scipy.stats import binomtest
    better = (lambda x, y: x < y) if lower_better else (lambda x, y: x > y)
    w = sum(better(x, y) for x, y in zip(a, b))
    lo = sum(better(y, x) for x, y in zip(a, b))
    p = float(binomtest(w, w + lo, 0.5).pvalue) if w + lo else 1.0
    return {'wins': w, 'losses': lo, 'ties': len(a) - w - lo, 'p': p,
            'label': names[2] if p >= ALPHA else (names[0] if w > lo else names[1])}


def holm(ps):
    order = sorted(ps, key=lambda k: (ps[k], k))
    out, going = {}, True
    for r, k in enumerate(order):
        going = going and ps[k] <= ALPHA / (len(order) - r)
        out[k] = going
    return out


def analyse(choices, rows, family_rows, synthesis):
    """choices: {k: {'chosen': encoding json, 'is_one_hot': bool}}; rows: [{k, seed, arm, conflicts}];
    family_rows: [{family, seed, arm, satisfied}]; synthesis: [{set, relation, milp, search, ...}]."""
    out = {'colouring': {}, 'families': {}}
    by = {(r['k'], r['seed'], r['arm']): r['conflicts'] for r in rows}
    ps = {}
    names = ('INVENTED_BETTER', 'INVENTED_WORSE', 'NOT_DISTINGUISHABLE')
    for k in KS:
        seeds = sorted({r['seed'] for r in rows if r['k'] == k})
        arms = sorted({r['arm'] for r in rows if r['k'] == k})
        res = {'means': {a: statistics.mean(by[(k, s, a)] for s in seeds) for a in arms},
               'chosen': choices[k]['chosen'], 'is_one_hot': choices[k]['is_one_hot']}
        if not choices[k]['is_one_hot']:
            res['P'] = sign([by[(k, s, 'chosen')] for s in seeds], [by[(k, s, 'one_hot')] for s in seeds], names)
            ps[str(k)] = res['P']['p']
        res['chosen_vs_compiler'] = sign([by[(k, s, 'chosen')] for s in seeds], [by[(k, s, 'compiler')] for s in seeds],
                                         ('CHOSEN_BETTER', 'COMPILER_BETTER', 'NOT_DISTINGUISHABLE'))
        res['chosen_vs_maxsat'] = sign([by[(k, s, 'chosen')] for s in seeds], [by[(k, s, 'maxsat')] for s in seeds],
                                       ('CHOSEN_BETTER', 'MAXSAT_BETTER', 'NOT_DISTINGUISHABLE'))
        out['colouring'][str(k)] = res
    rej = holm(ps) if ps else {}
    out['holm'] = rej
    better = [k for k in ps if rej[k] and out['colouring'][k]['P']['label'] == 'INVENTED_BETTER']
    worse = [k for k in ps if rej[k] and out['colouring'][k]['P']['label'] == 'INVENTED_WORSE']
    if not ps:
        out['verdict'] = 'NO_INVENTION'
    elif better and worse:
        out['verdict'] = 'MIXED'
    elif better:
        out['verdict'] = 'INVENTED_REPRESENTATION_BETTER'
    elif worse:
        out['verdict'] = 'INVENTED_REPRESENTATION_WORSE'
    else:
        out['verdict'] = 'NOT_SHOWN'
    fb = {(r['family'], r['seed'], r['arm']): r['satisfied'] for r in family_rows}
    for fam in sorted({r['family'] for r in family_rows}):
        seeds = sorted({r['seed'] for r in family_rows if r['family'] == fam})
        out['families'][fam] = {
            'means': {a: statistics.mean(fb[(fam, s, a)] for s in seeds) for a in ('genesis', 'maxsat')},
            'test': sign([fb[(fam, s, 'genesis')] for s in seeds], [fb[(fam, s, 'maxsat')] for s in seeds],
                         ('GENESIS_BETTER', 'MAXSAT_BETTER', 'NOT_DISTINGUISHABLE'), lower_better=False)}
    syn = {}
    for st in ('arity3', 'arity4'):
        rs = [r for r in synthesis if r['set'] == st]
        if not rs:
            continue
        m_only = sum(r['milp'] and not r['search'] for r in rs)
        s_only = sum(r['search'] and not r['milp'] for r in rs)
        from scipy.stats import binomtest
        both = [r for r in rs if r['milp'] and r['search']]
        syn[st] = {'relations': len(rs), 'milp_found': sum(r['milp'] for r in rs),
                   'search_found': sum(r['search'] for r in rs), 'milp_only': m_only, 'search_only': s_only,
                   'p_mcnemar': float(binomtest(m_only, m_only + s_only).pvalue) if m_only + s_only else 1.0,
                   'uniform_found': sum(r['uniform'] for r in rs),
                   'ancillas_milp_mean': statistics.mean(r['milp_ancillas'] for r in both) if both else None,
                   'ancillas_search_mean': statistics.mean(r['search_ancillas'] for r in both) if both else None}
    out['synthesis'] = syn
    return out


# ------------------------------------------------------------------------------------------- the study

def run_seed(*parts):
    return int(digest({'study': STUDY, 'parts': list(parts)})[:12], 16)


def choose_encoding(k, train, log, run=None):
    """Genesis's choice for k: candidates from the encoding search plus one-hot, piloted on the training graphs."""
    from genesis.representation import encodings as E
    from genesis.representation import library as LB
    n = 300
    m = round(DEG[k] * n / 2)
    b0 = max(1, (k - 1).bit_length())
    best, lib, scored = E.search(k, NEQ, {'neq': m}, n, range(b0, min(k, b0 + 1) + 1), synth=synth,
                                 value_symmetric=True)
    feas = sorted((r for r in scored if r['feasible']), key=lambda r: (r['variables'], r['nonzero'],
                                                                       json.dumps(r['encoding'])))
    oh = E.one_hot(k).to_json()
    cands = [r['encoding'] for r in feas if r['encoding'] != oh][:N_CANDIDATES] + [oh]
    plans, pilot = {}, {}
    for ci, ej in enumerate(cands):
        enc = E.Encoding.from_json(ej)
        c = E.cost(enc, NEQ, {'neq': m}, n, lib, synth)
        if c is None:
            continue
        lib, plans[ci] = c[2], c[3]
        vals = []
        for t in train:
            col, _ = solve_encoded(t, enc, plans[ci], lib, PILOT, run_seed('pilot', k, ci, t['seed']), run)
            vals.append(independent_conflicts(t, col))
        pilot[ci] = statistics.mean(vals)
        log(f'k={k} candidate {ci} {ej["code"]}: pilot conflicts {pilot[ci]:.1f}')
    win = min(pilot, key=lambda ci: (pilot[ci], ci))
    return {'candidates': cands, 'pilot': {str(c): v for c, v in pilot.items()}, 'chosen': cands[win],
            'is_one_hot': cands[win] == oh, 'plans': {str(c): p for c, p in plans.items()},
            'searched_tables': len(scored), 'feasible_tables': len(feas)}, lib


def main(argv=None, run=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'invented_representations_b20r135').resolve():
        raise SystemExit('the registered output is evidence/invented_representations_b20r135')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis.compiler import families as FM
    from genesis.representation import compile as C
    from genesis.representation import encodings as E
    from genesis.representation import families as F
    from genesis.representation import gadgets as GD
    from genesis.representation import library as LB
    from genesis.vault import Vault
    from genesis.compiler import backends as BK
    run = run or BK.run
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')

    # Part B: colouring
    G = colouring_graphs()
    cpath = out / 'choices.json'
    choices = json.loads(cpath.read_text()) if cpath.exists() else {}
    libs = {}
    for k in KS:
        if str(k) not in choices:
            ch, lib = choose_encoding(k, G[k]['train'], log, run)
            choices[str(k)] = ch
            cpath.write_text(json.dumps(choices, indent=1, sort_keys=True) + '\n')
    rpath = out / 'runs.jsonl'
    rows = [json.loads(line) for line in rpath.read_text().splitlines() if line.strip()] if rpath.exists() else []
    done = {(r['k'], r['seed'], r['arm']) for r in rows}
    for k in KS:
        ch = choices[str(k)]
        n = 300
        m = round(DEG[k] * n / 2)
        encs = {'chosen': E.Encoding.from_json(ch['chosen']), 'one_hot': E.one_hot(k)}
        plans, lib = {}, LB.EMPTY
        for arm, enc in encs.items():
            c = E.cost(enc, NEQ, {'neq': m}, n, lib, synth)
            lib, plans[arm] = c[2], c[3]
        libs[k] = lib
        arms = ['chosen', 'compiler', 'maxsat'] + ([] if ch['is_one_hot'] else ['one_hot'])
        for inst in G[k]['test']:
            for arm in arms:
                if (k, inst['seed'], arm) in done:
                    continue
                seed = run_seed('test', k, inst['seed'], arm)
                if arm in encs:
                    col, info = solve_encoded(inst, encs[arm], plans[arm], lib, BUDGET, seed, run)
                elif arm == 'compiler':
                    col, info = solve_compiler(inst, BUDGET, seed, run)
                else:
                    col, info = solve_maxsat_colouring(inst, BUDGET, seed, run)
                ok, conf, why = FM.verify('coloring', inst, {'colours': col})
                row = {'part': 'B', 'k': k, 'seed': inst['seed'], 'size': inst['size'], 'arm': arm, 'valid': ok,
                       'conflicts': conf, 'independent': independent_conflicts(inst, col), 'colours': col,
                       'info': info}
                with rpath.open('a') as f:
                    f.write(json.dumps(row, sort_keys=True) + '\n')
                rows.append(row)
                done.add((k, inst['seed'], arm))
            log(f"k={k} n={inst['size']} seed {inst['seed']}: " + ', '.join(
                f"{r['arm']} {r['conflicts']}" for r in rows if r['k'] == k and r['seed'] == inst['seed']))
        if ch['is_one_hot']:                                 # identical arms: one_hot is chosen
            for inst in G[k]['test']:
                if (k, inst['seed'], 'one_hot') not in done:
                    r0 = [r for r in rows if r['k'] == k and r['seed'] == inst['seed'] and r['arm'] == 'chosen'][0]
                    row = dict(r0, arm='one_hot', info={'same_as': 'chosen'})
                    with rpath.open('a') as f:
                        f.write(json.dumps(row, sort_keys=True) + '\n')
                    rows.append(row)
                    done.add((k, inst['seed'], 'one_hot'))

    # Part C: families, through the vault
    fpath = out / 'families.jsonl'
    frows = [json.loads(line) for line in fpath.read_text().splitlines() if line.strip()] if fpath.exists() else []
    fdone = {(r['family'], r['seed'], r['arm']) for r in frows}
    vpath = out / 'cascade.json'
    if vpath.exists():
        casc = json.loads(vpath.read_text())
        flib = json.loads((out / 'family_library.json').read_text())
    else:
        c0 = time.process_time()
        v = Vault(out / 'vault')
        parked = {}
        for fam in F.FAMILIES:
            spec = {'family': fam, 'params': {'ratio': FAMILY_RATIO[fam], 'sizes': list(FAMILY_SIZES)}}
            rel = F.BASE[fam]
            parked[fam] = LB.park(v, spec, [rel], creator=STUDY, score=1.0)
        null = v.put(v.record('CapabilityRecord', {'name': 'null trigger', 'unlocks': []}, domain=STUDY,
                              creator=STUDY))
        null_log = LB.cascade(v, [null], lambda a, t: [], fuel=4, depth=1)
        flib, caps, synth_cpu = LB.EMPTY, [], {}
        for fam in F.FAMILIES:
            s0 = time.process_time()
            g, rep = synth(F.BASE[fam], True)
            synth_cpu[fam] = time.process_time() - s0
            flib = LB.register(flib, F.BASE[fam], g, {'synthesizer': 'milp', 'for': fam, 'tried': rep['tried']})
            rid = LB.archive(v, flib, F.BASE[fam], creator=STUDY)
            caps.append(LB.announce(v, F.BASE[fam], rid, creator=STUDY))
        woke = []
        log_ = LB.cascade(v, caps, lambda a, t: woke.append(a) or [], fuel=4, depth=1)
        integrity = v.verify()
        v.close()
        casc = {'parked': parked, 'null_reactivated': len(null_log), 'reactivated': sorted(a for _, _, a in log_),
                'exact': sorted(parked.values()) == sorted(a for _, _, a in log_), 'synthesis_cpu_s': synth_cpu,
                'overhead_cpu_s': time.process_time() - c0, 'vault_verify': str(integrity)[:200]}
        (out / 'family_library.json').write_text(json.dumps(flib, indent=1, sort_keys=True) + '\n')
        vpath.write_text(json.dumps(casc, indent=1, sort_keys=True) + '\n')
    log(f"cascade: reactivated {len(casc['reactivated'])} of {len(casc['parked'])}; null {casc['null_reactivated']}")
    for inst in family_instances():
        fam = inst['family']
        for arm in ('genesis', 'maxsat'):
            if (fam, inst['seed'], arm) in fdone:
                continue
            seed = run_seed('family', fam, inst['seed'], arm)
            c0 = child_cpu()
            if arm == 'genesis':
                bqp, info = C.compile(F.spec(inst), flib, 'max_csp')
                x, rinfo = run('genesis', bqp, BUDGET, seed)
                x = C.decode(x, info)
            else:
                w = F.wcnf(inst)
                x, rinfo = run('maxsat', {'n': inst['n'], 'constant': 0, 'linear': [], 'quadratic': [], 'hard': {}},
                               BUDGET, seed, solver=SOLVER, native=(w['hard'], [tuple(s) for s in w['soft']],
                                                                    w['n_vars']))
            cpu_s = child_cpu() - c0
            ok, sat = F.check(inst, x)
            indep = independent_satisfied(inst, x) if ok else None
            row = {'part': 'C', 'family': fam, 'seed': inst['seed'], 'size': inst['size'], 'arm': arm, 'valid': ok,
                   'satisfied': sat if ok else 0, 'independent': indep, 'assignment': list(x[:inst['n']]),
                   'cpu': cpu_s}
            with fpath.open('a') as f:
                f.write(json.dumps(row, sort_keys=True) + '\n')
            frows.append(row)
            fdone.add((fam, inst['seed'], arm))
        log(f"{fam} n={inst['size']} seed {inst['seed']}: " + ', '.join(
            f"{r['arm']} {r['satisfied']}" for r in frows if r['family'] == fam and r['seed'] == inst['seed']))

    # Part A: synthesis (no engine runs)
    spath = out / 'synthesis.jsonl'
    srows = [json.loads(line) for line in spath.read_text().splitlines() if line.strip()] if spath.exists() else []
    sdone = {r['relation'] for r in srows}
    reps, rand = part_a_relations()
    for st, rels in (('arity3', reps), ('arity4', rand)):
        for rel in rels:
            if rel.id() + st in sdone:
                continue
            c0 = time.process_time()
            g, rep = GD.synthesize_milp(rel, max_ancillas=2, bound=8, uniform=False, time_limit=30)
            t_milp = time.process_time() - c0
            gu, _ = GD.synthesize_milp(rel, max_ancillas=2, bound=8, uniform=True, time_limit=30)
            found = None
            rng = random.Random(f'{STUDY}|search|{rel.id()}')
            deadline = time.process_time() + max(0.5, t_milp)
            for m in range(3):
                left = deadline - time.process_time()
                if left <= 0:
                    break
                gs, srep = synthesize_search_timed(rel, m, rng, left)
                if gs is not None:
                    found = gs
                    break
            row = {'set': st, 'relation': rel.id() + st, 'table': rel.table, 'k': rel.k, 'milp': g is not None,
                   'milp_ancillas': g.m if g is not None else None, 'milp_cpu_s': t_milp,
                   'milp_exact_both': bool(g is not None and GD.check(g, rel)['exact'] and GD.check_matrix(g, rel)),
                   'uniform': gu is not None, 'search': found is not None,
                   'search_ancillas': found.m if found is not None else None,
                   'search_exact_both': bool(found is not None and GD.check(found, rel)['exact'] and
                                             GD.check_matrix(found, rel))}
            with spath.open('a') as f:
                f.write(json.dumps(row, sort_keys=True) + '\n')
            srows.append(row)
    log(f'synthesis: {len(srows)} relations')
    res = analyse({int(k): v for k, v in choices.items()}, [r for r in rows], frows, srows)
    cpus = [r['info']['cpu'] / BUDGET for r in rows if r['arm'] != 'maxsat' and 'cpu' in r['info']] + \
           [r['cpu'] / BUDGET for r in frows if r['arm'] == 'genesis']
    valid = (all(r['valid'] and r['independent'] == r['conflicts'] for r in rows) and
             all(r['valid'] and r['independent'] == r['satisfied'] for r in frows) and
             all(r['milp_exact_both'] == r['milp'] and r['search_exact_both'] == r['search'] for r in srows) and
             casc['exact'] and casc['null_reactivated'] == 0 and
             (statistics.median(cpus) >= 0.9 if cpus else False))
    summary = dict(res, study=STUDY, schema='genesis-b20r135-invented-representations-v1', valid=valid,
                   verdict=res['verdict'] if valid else 'INVALID', cascade=casc,
                   engine_cpu_median=statistics.median(cpus) if cpus else None,
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; verdict {summary['verdict']}; " + '; '.join(
        f"k={k} chosen {v['chosen']['code']} {v.get('P', {}).get('label', 'one-hot chosen')}"
        for k, v in res['colouring'].items()))
    return 0 if valid else 1


def synthesize_search_timed(rel, m, rng, seconds):
    """The local-search baseline at m ancillas for at most `seconds` of CPU."""
    from genesis.representation import gadgets as GD
    deadline = time.process_time() + seconds
    while time.process_time() < deadline:
        g, rep = GD.synthesize_search(rel, m, rng, evaluations=2000)
        if g is not None:
            return g, rep
    return None, {'synthesizer': 'search'}


if __name__ == '__main__':
    sys.exit(main())
