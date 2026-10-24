#!/usr/bin/env python3
"""B20_R133: the Problem Compiler. Does Genesis solve verifiable problems it was not built for, as well as the
specialists do? (DEV, preregistered; Genesis Ω engine 1 and contract stage Ω11)

    taskset -c 0 python3 scripts/b20r133_problem_compiler.py OUT_DIR     run ALONE (resumable)

**Why.** Daniel, 24 Oct 2026: a solver of anything verifiable. Genesis's strongest engine is a max-cut engine
(`mcx2`; 45 of 54 Gset best-known values matched). The Problem Compiler (`genesis.compiler`) turns other verifiable
problems into a binary quadratic program and, for Genesis's engine, into max-cut. Each family's own checker judges
every answer, from the instance alone. This study asks whether that makes Genesis a competitive solver of problems
nobody tuned it for, against the specialist each family has: the MaxSAT Evaluation 2026 anytime solvers on the
families' natural MaxSAT encodings, and a general MILP solver.

**Families (each with its own generator and verifier; `compiler.families`) and sizes (fresh seeds from SEED):**
  * `mis`: maximum independent set, G(n, 5/n), n = 500 and 2,000;
  * `coloring`: 4-colouring with fewest conflicts, G(n, 9/n) (near the 4-colourability threshold), n = 150 and 500;
  * `max2sat`: random 2-CNF, m = 4.5 n clauses, n = 500 and 2,000;
  * `maxcut`: unweighted max-cut, G(n, 6/n), n = 500 and 2,000 (the control: Genesis's native problem).
N_PER = 10 instances per (family, size): 80 instances.

**Arms** (one core, the same CPU budget, BUDGETS = 1 s and 10 s; one seed per run):
  * `genesis`: the penalised QUBO reduced to max-cut, solved by `mcx2` with its default configuration REX (not tuned
    for any of these families), decoded and repaired (`compiler.backends.genesis`);
  * `maxsat`: PASMaxSAT-c, the 2026 Evaluation's first in the unweighted anytime track at 60 s, on the family's
    natural encoding (`compiler.families.wcnf`); and `maxsat2`: NuWLS-c-2026, also an entrant, reported;
  * `milp`: HiGHS (`scipy.optimize.milp`) on the exact linearised model, its best incumbent.
Every answer is decoded and checked by the family's verifier; an invalid or missing answer scores the worst value
(0 for maximisation, the number of edges for colouring) and counts as a failure.

**Primary tests** (one per non-control family at 10 s, Holm over the three, alpha 0.05): `genesis` against `maxsat`
on verified scores, a two-sided sign test over the family's 20 instances (ties dropped): GENESIS_BETTER /
SPECIALIST_BETTER / NOT_DISTINGUISHABLE.
**Verdict:** COMPETITIVE_WITH_SPECIALISTS if no family is SPECIALIST_BETTER after Holm; BEHIND_SPECIALISTS_ON
followed by the families where it is; and BEYOND_SPECIALISTS_ON for the families where GENESIS_BETTER.
**Secondary:** the same at 1 s; `genesis` against `milp` and against `maxsat2` at both budgets; the control family;
the failure rate per arm; mean verified scores; the share of `genesis`'s raw answers that needed repair.
**Human knowledge in each adapter (contract §13):** the generator; the verifier; the BQP form (one penalty term per
constraint kind, from the textbook QUBO formulations, e.g. Lucas 2014); the natural MaxSAT encoding (the standard
one). No family-specific search code; the engine and its configuration are the same for all.

**Development looks (disclosed).** The tests (`test_compiler`: every form exact by brute force, every back-end at
the optimum on small instances). One look at 2 s on two instances per family (seeds 9,200,000-9,200,001; sizes mis
1,000, colouring 300, Max-2-SAT 1,000, max-cut 1,000) with NuWLS-c-2026 as the MaxSAT arm: independent set 442 / 436
(genesis) against 442 / 437 (MaxSAT) and 382 / 96 (HiGHS); colouring conflicts 15 / 19 against 10 / 7 and 86 / 89;
Max-2-SAT 4,149 / 4,142 against 4,149 / 4,141 and 3,378 / 3,347; max-cut 2,387 / 2,388 against 2,387 / 2,388 and
27 / 23.
**Expectation, stated before running.** Colouring: SPECIALIST_BETTER (the one-hot penalties make a rugged QUBO);
independent set and Max-2-SAT: NOT_DISTINGUISHABLE at 10 s; HiGHS far behind on every family at these sizes; the
control a tie. Verdict: BEHIND_SPECIALISTS_ON coloring.
**Cost.** 80 instances x 2 budgets x 4 arms: about 1 h 15 min. **Status.** DEV; licenses nothing.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r133'
SEED = 20491331
SIZES = {'mis': [{'n': 500, 'd': 5}, {'n': 2000, 'd': 5}],
         'coloring': [{'n': 150, 'd': 9, 'k': 4}, {'n': 500, 'd': 9, 'k': 4}],
         'max2sat': [{'n': 500, 'm': 2250}, {'n': 2000, 'm': 9000}],
         'maxcut': [{'n': 500, 'd': 6}, {'n': 2000, 'd': 6}]}
FAMILIES = ('mis', 'coloring', 'max2sat', 'maxcut')
CONTROL = 'maxcut'
N_PER = 10
BUDGETS = (1.0, 10.0)
ARMS = ('genesis', 'maxsat', 'maxsat2', 'milp')
SOLVER = {'maxsat': 'pasmaxsat-c', 'maxsat2': 'nuwls-c-2026'}
ALPHA = 0.05


def instances():
    out = []
    for fi, fam in enumerate(FAMILIES):
        for si, params in enumerate(SIZES[fam]):
            for k in range(N_PER):
                out.append({'family': fam, 'size': si, 'params': params, 'seed': SEED + 1000 * fi + 100 * si + k})
    return out


def worst(fam, inst):
    from genesis.compiler import families as FM
    return len(inst['edges']) if FM.SENSE[fam] == 'min' else 0


def sign(a, b, sense, names):
    """Two-sided sign test of a against b (better per `sense`); names = (a better, b better, none)."""
    from scipy.stats import binomtest
    better = (lambda x, y: x > y) if sense == 'max' else (lambda x, y: x < y)
    w = sum(better(x, y) for x, y in zip(a, b))
    lo = sum(better(y, x) for x, y in zip(a, b))
    p = float(binomtest(w, w + lo, 0.5).pvalue) if w + lo else 1.0
    return {'wins': w, 'losses': lo, 'ties': len(a) - w - lo, 'p': p,
            'label': names[2] if p >= ALPHA else (names[0] if w > lo else names[1])}


def holm(ps, alpha=ALPHA):
    order = sorted(ps, key=lambda k: (ps[k], k))
    out, going = {}, True
    for r, k in enumerate(order):
        going = going and ps[k] <= alpha / (len(order) - r)
        out[k] = going
    return out


def analyse(rows):
    from genesis.compiler import families as FM
    by = {(r['seed'], r['arm'], r['budget']): r for r in rows}
    out = {'tests': {}, 'secondary': {}, 'means': {}, 'failures': {}}
    for fam in FAMILIES:
        seeds = sorted({r['seed'] for r in rows if r['family'] == fam})
        sense = FM.SENSE[fam]
        for b in BUDGETS:
            col = {a: [by[(s, a, b)]['score'] for s in seeds] for a in ARMS}
            out['means'][f'{fam}@{b}'] = {a: statistics.mean(v) for a, v in col.items()}
            names = ('GENESIS_BETTER', 'SPECIALIST_BETTER', 'NOT_DISTINGUISHABLE')
            t = sign(col['genesis'], col['maxsat'], sense, names)
            if b == BUDGETS[-1] and fam != CONTROL:
                out['tests'][fam] = t
            else:
                out['secondary'][f'{fam}@{b}:genesis_vs_maxsat'] = t
            out['secondary'][f'{fam}@{b}:genesis_vs_maxsat2'] = sign(col['genesis'], col['maxsat2'], sense, names)
            out['secondary'][f'{fam}@{b}:genesis_vs_milp'] = sign(col['genesis'], col['milp'], sense,
                                                                   ('GENESIS_BETTER', 'MILP_BETTER',
                                                                    'NOT_DISTINGUISHABLE'))
    for a in ARMS:
        rs = [r for r in rows if r['arm'] == a]
        out['failures'][a] = sum(not r['valid'] for r in rs) / len(rs) if rs else None
    g = [r for r in rows if r['arm'] == 'genesis' and r['family'] in ('mis', 'coloring')]
    out['secondary']['genesis_repaired_share'] = (sum(r['info'].get('violations_before_repair', 0) > 0 for r in g)
                                                  / len(g)) if g else None
    rej = holm({f: t['p'] for f, t in out['tests'].items()})
    out['holm'] = rej
    behind = sorted(f for f, t in out['tests'].items() if rej[f] and t['label'] == 'SPECIALIST_BETTER')
    beyond = sorted(f for f, t in out['tests'].items() if rej[f] and t['label'] == 'GENESIS_BETTER')
    v = 'COMPETITIVE_WITH_SPECIALISTS' if not behind else 'BEHIND_SPECIALISTS_ON ' + ','.join(behind)
    if beyond:
        v += '; BEYOND_SPECIALISTS_ON ' + ','.join(beyond)
    out['verdict'] = v
    return out


def checks(rows):
    """Every planned run present once; every recorded score re-verifiable is checked by the record test."""
    keys = [(r['seed'], r['arm'], r['budget']) for r in rows]
    return len(keys) == len(set(keys)) == len(instances()) * len(ARMS) * len(BUDGETS)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[3])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'problem_compiler_b20r133').resolve():
        raise SystemExit('the registered output is evidence/problem_compiler_b20r133')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis.compiler import backends as BK
    from genesis.compiler import families as FM
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    path = out / 'runs.jsonl'
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    done = {(r['seed'], r['arm'], r['budget']) for r in rows}
    for spec in instances():
        fam = spec['family']
        inst = FM.generate(fam, spec['seed'], spec['params'])
        problem = FM.compile(fam, inst)
        for b in BUDGETS:
            for arm in ARMS:
                if (spec['seed'], arm, b) in done:
                    continue
                kw = {'solver': SOLVER[arm], 'native': FM.wcnf(fam, inst)} if arm in SOLVER else {}
                be = 'maxsat' if arm in SOLVER else arm
                c0 = time.process_time()
                w0 = time.monotonic()
                try:
                    x, info = BK.run(be, problem, b, spec['seed'], **kw)
                    ok, score, why = FM.verify(fam, inst, FM.decode(fam, inst, x))
                    err = None
                except Exception as e:                      # a crash is a failed run, recorded
                    x, info, ok, score, why, err = None, {}, False, None, 'crashed', repr(e)[:300]
                row = {'family': fam, 'size': spec['size'], 'params': spec['params'], 'seed': spec['seed'],
                       'arm': arm, 'budget': b, 'valid': ok, 'score': score if ok else worst(fam, inst),
                       'why': why, 'error': err, 'assignment': x, 'info': json.loads(json.dumps(info, default=str)),
                       'cpu_s': round(time.process_time() - c0, 3), 'wall_s': round(time.monotonic() - w0, 3)}
                with path.open('a') as f:
                    f.write(json.dumps(row, sort_keys=True) + '\n')
                rows.append(row)
                done.add((spec['seed'], arm, b))
        log(f"{fam} n={spec['params']['n']} seed {spec['seed']}: " + ', '.join(
            f"{r['arm']}@{r['budget']:g} {r['score']}" for r in rows if r['seed'] == spec['seed']))
    valid = checks(rows)
    res = analyse(rows)
    summary = dict(res, study=STUDY, schema='genesis-b20r133-problem-compiler-v1', valid=valid, runs=len(rows),
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; verdict {res['verdict']}; " + '; '.join(f"{f} {t['label']} ({t['wins']}-{t['losses']})"
                                                               for f, t in res['tests'].items()))
    return 0 if valid else 1


if __name__ == '__main__':
    sys.exit(main())
