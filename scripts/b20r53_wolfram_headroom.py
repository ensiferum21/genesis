#!/usr/bin/env python3
"""B20_R53 design pilot (DEV): is there research-selection headroom on Wolfram's axiom at the hard settings?

    b20r53_wolfram_headroom.py OUT_DIR            (resumable: a seed whose file exists is skipped)
    b20r53_wolfram_headroom.py OUT_DIR --summary  (recomputes summary.json from the seed files)

A design diagnostic, not a study. It licenses no claim and adopts nothing.

**Why.** GV4 (better improver) and the equational target of GV6 both need a setting where *which* research
the system does changes the successor. B20_R3, R6 and R9 measured that headroom on eight equational
systems with 1 s attempts and found none (ORACLE - FIXED@CAP at most 1 of 12). Wolfram's single axiom
sat at the floor there: E proves no pool equation in 1 s. B20's hard follow-up showed that with 10 s
attempts and 60 CPU-s of research the successor rises from 0 to 8-12 of 15 (`evidence/learning_b20/
curriculum_control.json`). Selection headroom at those settings was never measured. That is the open
cell this pilot fills (B20R9-OPEN-1; `handoff/gv6/README.md`, target 2).

**Settings.** B20's hard rules, unchanged (`b20_curriculum_control.py`): 10 s per research attempt,
3 s per evaluation target, the 8 most relevant lemmas, 15 evaluation and 10 development targets of
5-8 nodes, a pool of true equations up to 5 nodes (8 per bucket) plus 30 false ones. Fresh seeds
5301-5304; every pool, development and evaluation statement is written to OUT_DIR, so later studies
count it as exposed. Each seed's evaluation targets avoid its pool and development targets.

**Libraries per seed**, each evaluated on the 15 targets under the same rule:
  * EMPTY;
  * EXHAUST: the fixed policy (smallest first) over the whole pool, 1800 CPU-s cap;
  * ORACLE: the lemmas that eligible EXHAUST target proofs used, closed under lemma dependencies (an
    optimistic reference built from the evaluation targets themselves, not an arm);
  * for each cap in CAPS (60 and 30 CPU-s):
      - FIXED@cap: the fixed policy under the cap;
      - ORACLE@cap: B20_R3's ``oracle_at``: exhaust lemmas by how many target proofs used them, each
        with its dependency closure, while their summed attempt CPU fits the cap;
      - GAP@cap: the GV6 draft's mapping of the transferred procedure ("keep an equation the decider
        says is true but bounded E with the current library cannot prove; prove it with a larger
        budget"). Smallest first; a true conjecture first gets a CHEAP_S attempt with the current
        library; if that proves it, it is cheaply derivable and not kept (the analogue of a pattern
        whose LP bound equals its maximum); otherwise it gets a full 10 s attempt and is kept if
        proved. Both attempts are charged to the same account. This arm is descriptive only.
  * FIXED@60 evaluated a second time (REPEAT), to measure evaluation noise near E's time limit
    (B20's concurrency caveat).

**Verdict (fixed here before running).** Per seed s and cap c, the selection headroom is
h(s, c) = ORACLE@c - FIXED@c; the noise is |FIXED@60 - REPEAT|.
  * SELECTION_HEADROOM if, for some cap, the mean of h over seeds is at least 2 (of 15), h >= 2 on at
    least 3 of the 4 seeds, and the mean h exceeds the mean noise by at least 1;
  * NO_HEADROOM if h <= 1 for every seed and cap;
  * WEAK_HEADROOM otherwise.
Reported descriptively: GAP@c - FIXED@c, the library headroom EXHAUST - EMPTY, and the ceiling gap
15 - EXHAUST.

**Development looks (disclosed).** Before writing this file the builder computed pool sizes for seeds
5301, 5302 and 311 (88, 89 and 87 true equations; no prover calls), and read B20's hard-system and
B20_R3's pilot evidence. No prover call on these seeds' material preceded the run. CHEAP_S = 1 s is the
B20_R3 attempt budget, at which E proves no Wolfram pool equation from the axioms alone.

Run pinned to one core (``taskset -c 0``).
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import research as RS  # noqa: E402
from genesis.learning.budget import Account, StudyBudget  # noqa: E402

SYSTEM = 'ba_wolfram'
SEEDS = [5301, 5302, 5303, 5304]
RULES = {'prove_s': 10, 'eval_s': 3, 'premise_k': 8, 'eval_targets': 15, 'dev_targets': 10, 'target_range': [5, 8],
         'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30}
CAPS = (60, 30)
EXHAUST_S = 1800
CHEAP_S = 1
KW = {'enforcement': 'OUTER_SUPERVISED', 'quantum_ns': 100_000_000}
VERDICT = {'min_mean': 2, 'min_seed': 2, 'min_seeds': 3, 'noise_margin': 1, 'none_max': 1}
PRIOR_SEEDS = (311, 312, 313, 314, 510, 511, 512, 513, 611, 612, 613, 614, 700, 710, 711, 712, 800, 801)


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def budget(cap_s):
    return StudyBudget.from_seconds(cap_s, attempt_s=RULES['prove_s'], **KW)


def material(seed):
    pool = Q.true_equations(SYSTEM, RULES['pool_size'], per_bucket=RULES['per_bucket'], seed=seed) + \
        Q.false_equations(SYSTEM, RULES['pool_size'], RULES['false_conjectures'], seed=seed)
    lo, hi = RULES['target_range']
    dev = Q.sample_targets(SYSTEM, RULES['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=pool)
    ev = Q.sample_targets(SYSTEM, RULES['eval_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 2,
                          exclude=pool + dev)
    return pool, dev, ev


def closure(library, ids):
    by, out, stack = {l['id']: l for l in library}, set(), list(ids)
    while stack:
        i = stack.pop()
        if i not in out:
            out.add(i)
            stack += by[i]['uses']
    return [l for l in library if l['id'] in out]


def oracle_at(library, uses, attempt_cpu, cap):
    """B20_R3's ORACLE@cap, unchanged."""
    chosen, cost = set(), 0.0
    for u in sorted(uses, key=lambda k: (-uses[k], int(k[1:]))):
        add = {l['id'] for l in closure(library, [u])} - chosen
        c = sum(attempt_cpu.get(l['text'], 0.0) for l in library if l['id'] in add)
        if cost + c <= cap:
            chosen |= add
            cost += c
    return [l for l in library if l['id'] in chosen], round(cost, 3)


def run_gap(pool, account, *, cheap_s=CHEAP_S, prove_s=None, premise_k=None, prover=None):
    """The GV6 draft's mapping of the transferred procedure (see the module docstring)."""
    prove_s = prove_s or RULES['prove_s']
    premise_k = premise_k or RULES['premise_k']
    prover = prover or RS._default_prover
    with account.measure('preparation', 'policy reset and axioms'):
        spec = Q.SYSTEMS[SYSTEM]
        ax = Q.axioms(SYSTEM)
        policy = RS.Fixed()
        policy.reset(list(pool), [])
        untried = set(pool)
    library, trajectory = [], []
    cheap_ns = int(cheap_s * 1e9) + account.budget.overhead_ns          # the same overhead reserve as a full attempt
    while untried and not account.stop_reason:
        with account.measure('policy', 'choose'):
            eq = policy.choose(untried)
            untried.discard(eq)
        with account.measure('decider'):
            truth = Q.holds(eq, spec['decider'])
        if not truth:
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'FALSE'})
            continue
        with account.measure('retrieval'):
            prem = RS.premises(library, eq, premise_k)
        inputs = ax + [Q.closed(p['eq']) for p in prem]
        res = account.reserve('prover', purpose=f'cheap {Q.text(eq)}', cpu_ns=cheap_ns)
        if res is None:
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'NOT_ATTEMPTED',
                               'reason': account.stop_reason})
            break
        r = prover(inputs, Q.closed(eq), res=res, label=res.attempt_id)
        settled = RS._settle(account, res, r)
        cheap_cpu = settled['cpu_ns']
        if r['status'] == 'THEOREM' and r.get('proof') and settled['eligible']:
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'CHEAP_DERIVABLE',
                               'cpu_s': round(cheap_cpu / 1e9, 3)})
            continue
        res = account.reserve('prover', purpose=f'prove {Q.text(eq)}')
        if res is None:
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'NOT_ATTEMPTED',
                               'reason': account.stop_reason, 'cheap_cpu_s': round(cheap_cpu / 1e9, 3)})
            break
        r = prover(inputs, Q.closed(eq), res=res, label=res.attempt_id)
        settled = RS._settle(account, res, r)
        proved = r['status'] == 'THEOREM' and bool(r.get('proof')) and settled['eligible']
        rec = {'step': len(trajectory), 'eq': Q.text(eq), 'cheap_cpu_s': round(cheap_cpu / 1e9, 3),
               'cpu_s': round(settled['cpu_ns'] / 1e9, 3), 'outcome': 'PROVED' if proved else 'UNPROVED'}
        if proved:
            used = RS.used_inputs(r['proof'], len(inputs))
            library.append({'id': f'G{len(library)}', 'eq': eq, 'text': Q.text(eq), 'proof': r['proof'],
                            'proof_sha256': RS._sha_text(r['proof']),
                            'uses': [prem[i - len(ax)]['id'] for i in used if i >= len(ax)],
                            'premise_ids': [p['id'] for p in prem]})
        trajectory.append(rec)
    acct = account.record()
    return {'library': library, 'trajectory': trajectory, 'cpu_s': round(acct['cpu_ns_total'] / 1e9, 3),
            'account': {k: acct[k] for k in ('cpu_ns_total', 'stop_reason') if k in acct}}


def lib_texts(lib):
    return [l['text'] for l in lib]


def one_seed(seed, out, log):
    path = out / f'seed_{seed}.json'
    if path.exists():
        log(f'seed {seed}: already done')
        return json.loads(path.read_text())
    pool, dev, ev = material(seed)
    k = dict(eval_s=RULES['eval_s'], premise_k=RULES['premise_k'])

    def evaluate(lib, label):
        e = RS.evaluate_successor(SYSTEM, lib, ev, label=f'r53-{label}:{seed}', **k)
        return {'proved': e['proved'], 'statuses': [r['status'] for r in e['rows']], 'lemma_use': e['lemma_use']}
    t0 = time.monotonic()
    row = {'seed': seed, 'pool': [Q.text(e) for e in pool], 'dev': [Q.text(e) for e in dev],
           'targets': [Q.text(e) for e in ev], 'pool_sha256': digest([Q.text(e) for e in pool])}
    row['empty'] = evaluate([], 'empty')
    ex = RS.run(SYSTEM, RS.Fixed(), pool, account=Account(budget(EXHAUST_S), label=f'r53-exhaust:{seed}'),
                prove_s=RULES['prove_s'], premise_k=RULES['premise_k'])
    attempt_cpu = {s['eq']: s.get('cpu_s', 0.0) for s in ex['trajectory']}
    row['exhaust_run'] = {'library': lib_texts(ex['library']), 'cpu_s': ex['cpu_s'],
                          'stop_reason': ex['account'].get('stop_reason'),
                          'untried': len(pool) - len(ex['trajectory']),
                          'outcomes': [[s['eq'], s['outcome'], s.get('cpu_s')] for s in ex['trajectory']]}
    row['exhaust'] = evaluate(ex['library'], 'exhaust')
    uses = row['exhaust']['lemma_use']
    orc = closure(ex['library'], list(uses))
    row['oracle'] = dict(evaluate(orc, 'oracle'), library=lib_texts(orc),
                         cost_s=round(sum(attempt_cpu.get(l['text'], 0.0) for l in orc), 3))
    log(f'seed {seed}: pool {len(pool)}, exhaust {len(ex["library"])} lemmas in {ex["cpu_s"]} s '
        f'({row["exhaust_run"]["stop_reason"]}); empty {row["empty"]["proved"]}, exhaust {row["exhaust"]["proved"]}, '
        f'oracle {row["oracle"]["proved"]} ({len(orc)} lemmas, {row["oracle"]["cost_s"]} s)')
    row['caps'] = {}
    for cap in CAPS:
        fc = RS.run(SYSTEM, RS.Fixed(), pool, account=Account(budget(cap), label=f'r53-fixed{cap}:{seed}'),
                    prove_s=RULES['prove_s'], premise_k=RULES['premise_k'])
        oc, ocost = oracle_at(ex['library'], uses, attempt_cpu, cap)
        gp = run_gap(pool, Account(budget(cap), label=f'r53-gap{cap}:{seed}'))
        c = {'fixed': dict(evaluate(fc['library'], f'fixed{cap}'), library=lib_texts(fc['library']), cpu_s=fc['cpu_s']),
             'oracle': dict(evaluate(oc, f'oracle{cap}'), library=lib_texts(oc), cost_s=ocost),
             'gap': dict(evaluate(gp['library'], f'gap{cap}'), library=lib_texts(gp['library']), cpu_s=gp['cpu_s'],
                         cheap_derivable=sum(s['outcome'] == 'CHEAP_DERIVABLE' for s in gp['trajectory']),
                         trajectory=gp['trajectory'])}
        if cap == CAPS[0]:
            c['repeat'] = evaluate(fc['library'], f'repeat{cap}')
        row['caps'][str(cap)] = c
        log(f'seed {seed} cap {cap}: fixed {c["fixed"]["proved"]} ({len(fc["library"])} lemmas), '
            f'oracle {c["oracle"]["proved"]} ({len(oc)} lemmas, {ocost} s), gap {c["gap"]["proved"]} '
            f'({len(gp["library"])} kept, {c["gap"]["cheap_derivable"]} cheaply derivable)'
            + (f', repeat {c["repeat"]["proved"]}' if 'repeat' in c else ''))
    row['wall_s'] = round(time.monotonic() - t0, 1)
    row['status'] = 'DESIGN_PILOT_DEV'
    dump(path, row)
    return row


def verdict(rows, caps=CAPS, rule=VERDICT):
    """The preregistered verdict over per-seed rows (see the module docstring)."""
    noise = [abs(r['caps'][str(caps[0])]['fixed']['proved'] - r['caps'][str(caps[0])]['repeat']['proved'])
             for r in rows]
    per_cap, any_head = {}, False
    hs_all = []
    for cap in caps:
        h = [r['caps'][str(cap)]['oracle']['proved'] - r['caps'][str(cap)]['fixed']['proved'] for r in rows]
        g = [r['caps'][str(cap)]['gap']['proved'] - r['caps'][str(cap)]['fixed']['proved'] for r in rows]
        hs_all += h
        ok = (statistics.mean(h) >= rule['min_mean'] and sum(x >= rule['min_seed'] for x in h) >= rule['min_seeds']
              and statistics.mean(h) - statistics.mean(noise) >= rule['noise_margin'])
        any_head = any_head or ok
        per_cap[str(cap)] = {'selection_headroom': h, 'mean': round(statistics.mean(h), 3), 'passes': ok,
                             'gap_minus_fixed': g, 'gap_mean': round(statistics.mean(g), 3)}
    v = 'SELECTION_HEADROOM' if any_head else 'NO_HEADROOM' if max(hs_all) <= rule['none_max'] else 'WEAK_HEADROOM'
    return {'verdict': v, 'per_cap': per_cap, 'noise': noise, 'mean_noise': round(statistics.mean(noise), 3),
            'library_headroom': [r['exhaust']['proved'] - r['empty']['proved'] for r in rows],
            'ceiling_gap': [len(r['targets']) - r['exhaust']['proved'] for r in rows],
            'rule': rule, 'seeds': [r['seed'] for r in rows]}


def summarize(out, log):
    rows = [json.loads((out / f'seed_{s}.json').read_text()) for s in SEEDS if (out / f'seed_{s}.json').exists()]
    if len(rows) != len(SEEDS):
        raise SystemExit(f'only {len(rows)} of {len(SEEDS)} seeds present')
    s = verdict(rows)
    table = [{'seed': r['seed'], 'empty': r['empty']['proved'], 'exhaust': r['exhaust']['proved'],
              'oracle': r['oracle']['proved'], 'exhaust_cpu_s': r['exhaust_run']['cpu_s'],
              **{f'{k}@{cap}': r['caps'][str(cap)][k]['proved'] for cap in CAPS for k in ('fixed', 'oracle', 'gap')},
              'repeat@60': r['caps'][str(CAPS[0])]['repeat']['proved']} for r in rows]
    summary = dict(s, table=table, system=SYSTEM, rules=RULES, caps=list(CAPS), exhaust_s=EXHAUST_S, cheap_s=CHEAP_S,
                   status='DESIGN_PILOT_DEV', claim='none; a design diagnostic for GV4 and the GV6 equational target')
    dump(out / 'summary.json', summary)
    log(f'verdict {summary["verdict"]}; per cap {json.dumps(s["per_cap"])}; noise {s["noise"]}')
    return summary


def main(argv=None):
    a = argv or sys.argv[1:]
    out = Path(a[0])
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    if '--summary' not in a:
        for seed in SEEDS:
            one_seed(seed, out, log)
    summarize(out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
