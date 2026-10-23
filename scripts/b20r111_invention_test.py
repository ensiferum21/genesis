#!/usr/bin/env python3
"""B20_R111: the invention test: has Genesis autonomously invented a fundamentally new algorithm? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r111_invention_test.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** Daniel (23 Oct 2026): "Genesis autonomously invented a fundamentally new algorithm. Not yet demonstrated:
test this too." The claim needs a test that can fail, fixed before any candidate is judged. Each part below rules out
one way such a claim could be true in name only.
  * **Autonomous.** The algorithm comes from the system's own recorded search, and the builder did not write or edit
    it.
  * **An algorithm, not a setting.** It is a program in the system's solver language (`invention.solver_programs`,
    with B20_R82's library), not a configuration of an engine the builder wrote. So B20_R105's choices for `mcx-v1`
    are out of scope.
  * **Useful beyond prior art.** It beats the known algorithms that the same language can express, each tuned with
    the same procedure, on hosts neither has seen.
  * **New.** Its essential core is not one of those known algorithms. The core is found by deleting statements while
    performance holds.

**Design (fixed before running).**
  * **Candidates (autonomous):** the four programs found by the system's searches. gen1 is B20_R79's search from random
    programs; gen2 and gen3 are B20_R83's and B20_R85's, with the earlier generations callable; control is
    B20_R84's, gen2's search without the library. Each is read as recorded, with its SHA-256.
  * **Prior-art library, written before any run:** eight known algorithm families in the same language, each with a
    small grid of variants (every licensed representation, and one or two parameters):
      - T1 multistart descent;
      - T2 iterated local search (random relabel kick, descent, return to the best);
      - T3 simulated annealing;
      - T4 annealing then descent (quench);
      - T5 restarted annealing;
      - T6 plateau search in edge space (sideways drop sweeps);
      - T7 edge-space iterated local search with forced-edge kicks (the directed perturbation of breakout local
        search);
      - T8 cut-space annealing followed by edge-space plateau search.
    68 variants in all (`LIBRARY`).
  * **Hosts:** fresh DEV hosts of `triangle_free_large_v1` in B20_R99's four cells: planted clusters and G(n, 0.5) at
    n = 128 and 256. Every recorded large-domain identity is excluded. 8 per cell: 2 for tuning (8 in all), 6 held out
    (24).
  * **Runs:** every program in-process through the interpreter, one seed per (host, arm), 2.0 CPU s on the process
    clock, pinned to the study's core, as B20_R99 ran the programs. The returned edge set is re-checked
    triangle-free and a subset of the host; the value is its size.
  * **Tuning (equal procedure for prior art):** every variant on the 8 tuning hosts. A variant's score is its mean
    gap below the best value of any variant on that host; each template keeps its best-scoring variant. The prior-art
    champion is the tuned template with the lowest score (ties: the order above).
  * **Held out:** the 8 tuned templates and the 4 candidates on the 24 held-out hosts. Also, as references only, the
    builder's engines: `tfxw` (B20_R95's configuration, runc) and `hybrid-swap-v1`, at 2 s.
  * **Test 1, useful beyond prior art (per candidate):** sign test over the 24 held-out hosts against the prior-art
    champion (ties dropped, two-sided, alpha 0.05 / 4): BEATS_PRIOR_ART / BEHIND_PRIOR_ART / NOT_DISTINGUISHABLE.
  * **Test 2, a new core (only for a candidate that BEATS_PRIOR_ART):** greedy deletion on the tuning hosts. Delete one
    statement at a time, taking the deletion with the highest mean value, while the mean stays within DELTA = 0.1
    edges of the full program's. The final core's structural signature (the statement tree with numbers and the
    representation dropped and library macros expanded in place) is compared with the eight templates'. KNOWN_CORE if
    it equals a template's, or uses only statement kinds that one template has (a reduced known algorithm);
    NOVEL_CORE otherwise. NOVEL_CORE is necessary for the claim, not sufficient: a core that passes is a combination
    no template in the library has, and it goes to a review against the literature before anything is claimed.
  * **Verdict:**
      - INVENTION_DEMONSTRATED if some candidate BEATS_PRIOR_ART with a NOVEL_CORE;
      - BETTER_BUT_KNOWN if some candidate beats prior art but every such core is known;
      - NOT_DEMONSTRATED otherwise, with each candidate's label.
  * **Validity:** median CPU at least 0.9 of the budget per arm; no invalid edge set (any is a defect that stops the
    study).

**Development looks (disclosed).** None for the templates. The candidates' values at 2 s on 16 other large hosts are
in B20_R99 (gen1 4,234.4, gen2 4,233.6, gen3 4,234.7, control 4,229.5 mean; tfxw 4,244.7; hybrid-swap-v1 4,234.6).

**Expectation, stated before running.** NOT_DEMONSTRATED. The candidates contain annealing-then-descent phases (T4,
T8). Tuned with modest effort, those templates should be NOT_DISTINGUISHABLE from them or ahead (B20_R80 and R81
found random programs of the language as good as the search's). All of them far behind the builder's tfxw.
**Cost.** Tuning 68 x 8 x 2 s, held out 12 x 24 x 2 s, references 2 x 24 x 2 s: about 32 min, more if a deletion
search runs. **Status.** DEV; licenses nothing; whatever the verdict, it is a statement about this language, these
candidates and these hosts.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r111'
HOST_SEED = 20291101
CELLS = (('planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 128, 'p': 0.5}),
         ('planted_cluster', {'n': 256, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 256, 'p': 0.5}))
PER_CELL, TUNE_PER_CELL = 8, 2
BUDGET = 2.0
ALPHA = 0.05 / 4
DELTA = 0.1
EV = ROOT / 'evidence'
SOURCES = {'gen1': EV / 'program_search_b20r79' / 'discovered_program.json',
           'gen2': EV / 'generation2_b20r83' / 'program.json',
           'gen3': EV / 'generation3_b20r85' / 'program.json',
           'control': EV / 'generation2_control_b20r84' / 'program.json'}
TFXW_CONFIG = EV / 'configure_tfxw_b20r95' / 'config.json'
REPS = ('cross_2', 'adjacent_2', 'adjacent_3', 'ordered_2')
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def _variants(name, make, values):
    return [(f'{name}|{rep}|{v}', {'rep': rep, 'body': make(v)}) for rep in REPS for v in values]


ANNEAL = ['relabel', 'random', 'anneal', 1000]
LIBRARY = {
    'T1': _variants('T1', lambda v: [['init'], ['descent']], ['-']),
    'T2': _variants('T2', lambda v: [['descent'], ['loop', [['relabel', 'random', 'always', v], ['descent'], ['best']]]],
                    [1, 10, 100]),
    'T3': _variants('T3', lambda v: [['loop', [['relabel', 'random', 'anneal', v]]]], [100, 1000]),
    'T4': _variants('T4', lambda v: [['split', v, [ANNEAL], [['descent']]]], [0.5, 0.75, 0.9]),
    'T5': _variants('T5', lambda v: [['repeat', v, [['init'], ANNEAL, ['descent']]]], [3, 10]),
    'T6': _variants('T6', lambda v: [['descent'], ['loop', [['sweep', 'drop', 'sideways']]]], ['-']),
    'T7': _variants('T7', lambda v: [['descent'], ['loop', [['edges', 'force', 'always', v], ['sweep', 'drop', 'sideways'],
                                                            ['best']]]], [1, 10]),
    'T8': _variants('T8', lambda v: [['split', v, [ANNEAL, ['descent']], [['loop', [['sweep', 'drop', 'sideways']]]]]],
                    [0.25, 0.5, 0.75]),
}


def candidates():
    out = {}
    for arm, path in SOURCES.items():
        if not path.exists():
            raise SystemExit(f'{path} is missing: the study needs all four candidates')
        out[arm] = (json.loads(path.read_text())['program'], hashlib.sha256(path.read_bytes()).hexdigest())
    return out


def signature(program):
    """The statement tree with numbers and the representation dropped and library macros expanded."""
    lib = program.get('library', [])

    def block(b):
        out = []
        for s in b:
            op = s[0]
            if op == 'macro':
                out.extend(block(lib[s[1]]))          # a macro runs its entry in place, with the enclosing share
            elif op in ('init', 'descent', 'best'):
                out.append((op,))
            elif op == 'relabel':
                out.append((op, s[1], s[2]))
            elif op == 'edges':
                out.append((op, s[1], s[2]))
            elif op == 'sweep':
                out.append((op, s[1], s[2]))
            elif op == 'repeat':
                out.append((op, block(s[2])))
            elif op == 'loop':
                out.append((op, block(s[1])))
            elif op == 'split':
                out.append((op, block(s[2]), block(s[3])))
            else:
                raise ValueError(f'unknown statement {op!r}')
        return tuple(out)
    return block(program['body'])


TEMPLATE_SIGNATURES = {t: signature(vs[0][1]) for t, vs in LIBRARY.items()}


def kinds(sig):
    """The set of statement kinds in a signature (control statements by name, steps with their labels)."""
    out = set()
    for s in sig:
        if s[0] in ('repeat', 'loop', 'split'):
            out.add((s[0],))
            for sub in s[1:]:
                out |= kinds(sub)
        else:
            out.add(s)
    return out


def core_label(sig):
    """KNOWN_CORE if the core is a template's statement tree, or uses only statement kinds that one template has
    (a reduced known algorithm); NOVEL_CORE otherwise (a combination no template has)."""
    known = [t for t, s in TEMPLATE_SIGNATURES.items() if s == sig or kinds(sig) <= kinds(s)]
    return ('KNOWN_CORE' if known else 'NOVEL_CORE'), known


def deletions(program):
    """Every program with one statement deleted (no block left empty), with macros' library entries editable too."""
    import copy
    out = []

    def walk(block, path):
        for i, s in enumerate(block):
            if len(block) > 1:
                out.append(path + [i])
            if s[0] == 'repeat':
                walk(s[2], path + [i, 2])
            elif s[0] == 'loop':
                walk(s[1], path + [i, 1])
            elif s[0] == 'split':
                walk(s[2], path + [i, 2])
                walk(s[3], path + [i, 3])
    roots = [('body', program['body'])] + [(('library', k), b) for k, b in enumerate(program.get('library', []))]
    for root, b in roots:
        before = len(out)
        walk(b, [])
        for j in range(before, len(out)):
            out[j] = (root, out[j])
    progs = []
    for root, path in out:
        p = copy.deepcopy(program)
        b = p['body'] if root == 'body' else p['library'][root[1]]
        for k in path[:-1]:
            b = b[k]
        del b[path[-1]]
        progs.append(p)
    return progs


def sign(xs, ys, alpha=ALPHA):
    from scipy.stats import binomtest
    wins = sum(x > y for x, y in zip(xs, ys))
    losses = sum(x < y for x, y in zip(xs, ys))
    p = float(binomtest(wins, wins + losses, 0.5).pvalue) if wins + losses else 1.0
    label = ('NOT_DISTINGUISHABLE' if p >= alpha else ('BEATS_PRIOR_ART' if wins > losses else 'BEHIND_PRIOR_ART'))
    return {'wins': wins, 'losses': losses, 'ties': len(xs) - wins - losses, 'p': p, 'label': label}


def tune(values, hosts):
    """values: {arm: {host: value}} -> (best variant per template, the champion template, scores)."""
    best_on = {h: max(values[a][h] for a in values) for h in hosts}
    score = {a: statistics.mean((best_on[h] - values[a][h]) / best_on[h] for h in hosts) for a in values}
    tuned = {}
    for t, vs in LIBRARY.items():
        names = [n for n, _ in vs]
        tuned[t] = min(names, key=lambda n: (score[n], names.index(n)))
    champion = min(LIBRARY, key=lambda t: (score[tuned[t]], list(LIBRARY).index(t)))
    return tuned, champion, score


def verdict(test1, cores):
    beating = [c for c, r in test1.items() if r['label'] == 'BEATS_PRIOR_ART']
    if any(cores.get(c, {}).get('label') == 'NOVEL_CORE' for c in beating):
        return 'INVENTION_DEMONSTRATED'
    return 'BETTER_BUT_KNOWN' if beating else 'NOT_DEMONSTRATED'


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (EV / 'invention_test_b20r111').resolve():
        raise SystemExit('the registered output is evidence/invention_test_b20r111')
    cands = candidates()
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r99_headroom as R99
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    from genesis.autonomy import qet
    from genesis.invention import representations as R
    from genesis.invention import solver_library as SL
    from genesis.invention import solver_programs as SP
    from genesis.candidate_kinds import solver_program as KP
    licensed = KP.licensed_reps('triangle_free_host_v1')
    for t, vs in LIBRARY.items():
        for name, prog in vs:
            if SP.problems(prog, licensed):
                raise SystemExit(f'{name} is not in the language: {SP.problems(prog, licensed)}')
    tasks = qet.hosts({'study': STUDY, 'cells': [list(c) for c in CELLS], 'per_cell': PER_CELL, 'host_seed': HOST_SEED},
                      out, ROOT, log)
    tune_hosts = [t for i, t in enumerate(tasks) if i < TUNE_PER_CELL * len(CELLS)]
    held = [t for i, t in enumerate(tasks) if i >= TUNE_PER_CELL * len(CELLS)]
    path = out / 'runs.jsonl'
    cache = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r['key']] = r
    reps = {r['id']: r for r in R.proposals()}
    tfx = None

    def value(task, arm, prog):
        nonlocal tfx
        key = f'{task.task_id}|{arm}'
        if key not in cache:
            if time.monotonic() - t0 > SLICE_S:
                raise Paused
            E = [tuple(e) for e in task.edges]
            seed = int(digest({'study': STUDY, 'task': task.task_id, 'arm': arm})[:12], 16)
            if arm in ('tfxw', 'hybrid'):
                if tfx is None:
                    tfx = R99.tfxw_descriptors()
                sel, cpu_s, how = R99.state(task, arm, BUDGET, None, tfx) if arm == 'tfxw' else \
                    R99.state(task, 'hybrid', BUDGET, None, tfx)
            else:
                c0 = time.process_time()
                run = SL.run if 'library' in prog else SP.run
                sel = run(prog, reps[prog['rep']], task.n, E, BUDGET, seed)
                cpu_s, how = time.process_time() - c0, 'in-process'
            S = {R99.key(*e) for e in sel}
            if not S <= {R99.key(*e) for e in E} or not R99.is_triangle_free(S, task.n):
                raise RuntimeError(f'{arm} returned an invalid edge set on {task.task_id}')
            cache[key] = {'key': key, 'task': task.task_id, 'arm': arm, 'value': len(S), 'cpu_s': round(cpu_s, 3),
                          'how': how, 'program_sha256': digest(prog) if prog else None}
            with path.open('a') as f:
                f.write(json.dumps(cache[key], sort_keys=True) + '\n')
        return cache[key]['value']

    variants = {n: p for vs in LIBRARY.values() for n, p in vs}
    try:
        values = {n: {t.task_id: value(t, n, p) for t in tune_hosts} for n, p in variants.items()}
        tuned, champion, score = tune(values, [t.task_id for t in tune_hosts])
        log(f'tuned: {tuned}; prior-art champion {champion} ({tuned[champion]})')
        arms = {**{t: variants[tuned[t]] for t in LIBRARY}, **{c: cands[c][0] for c in cands}}
        held_values = {a: {t.task_id: value(t, a if a in cands else tuned[a], p) for t in held} for a, p in arms.items()}
        for ref in ('tfxw', 'hybrid'):
            held_values[ref] = {t.task_id: value(t, ref, None) for t in held}
        hs = [t.task_id for t in held]
        test1 = {c: sign([held_values[c][h] for h in hs], [held_values[champion][h] for h in hs]) for c in cands}
        log('test 1: ' + '; '.join(f'{c} {r["label"]} {r["wins"]}-{r["losses"]}' for c, r in test1.items()))
        cores = {}
        for c, r in test1.items():
            if r['label'] != 'BEATS_PRIOR_ART':
                continue
            prog = cands[c][0]
            full = statistics.mean(value(t, c, prog) for t in tune_hosts)
            steps = []
            while True:
                trials = []
                for k, p in enumerate(deletions(prog)):
                    if (SL.problems(p, licensed) if 'library' in p else SP.problems(p, licensed)):
                        continue
                    arm = f'{c}-core-{digest(p)[:12]}'
                    trials.append((statistics.mean(value(t, arm, p) for t in tune_hosts), k, p))
                ok = [x for x in trials if x[0] >= full - DELTA]
                if not ok:
                    break
                m, _, prog = max(ok, key=lambda x: (x[0], -x[1]))
                steps.append({'mean': m, 'program': prog})
            label, known = core_label(signature(prog))
            cores[c] = {'core': prog, 'steps': len(steps), 'full_mean': full, 'known_as': known, 'label': label}
            log(f'{c}: core after {len(steps)} deletions: {"known as " + ",".join(known) if known else "NOVEL"}')
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(cache)} runs')
        return PAUSED
    v = verdict(test1, cores)
    cpu_by = {}
    for r in cache.values():
        a = r['arm'].split('|')[0].split('-core-')[0]
        cpu_by.setdefault(a, []).append(r['cpu_s'] / BUDGET)
    med = {a: statistics.median(xs) for a, xs in sorted(cpu_by.items())}
    valid = all(m >= 0.9 for m in med.values())
    means = {a: statistics.mean(vs.values()) for a, vs in held_values.items()}
    summary = {'study': STUDY, 'schema': 'genesis-b20r111-invention-test-v1', 'verdict': v, 'test1': test1,
               'cores': cores, 'tuned': tuned, 'champion': champion, 'tuning_scores': score,
               'held_out_means': means, 'held_out': held_values, 'valid': valid, 'cpu_median_by_arm': med,
               'candidates': {c: {'path': str(SOURCES[c].relative_to(ROOT)), 'sha256': cands[c][1]} for c in cands},
               'template_signatures': {t: repr(s) for t, s in TEMPLATE_SIGNATURES.items()},
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'valid {valid}; verdict {v}; held-out means ' + ', '.join(f'{a} {m:.1f}' for a, m in
                                                                   sorted(means.items(), key=lambda x: -x[1])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
