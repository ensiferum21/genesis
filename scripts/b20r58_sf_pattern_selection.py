#!/usr/bin/env python3
"""B20_R58 design pilot (DEV): does choosing *which* invented sum-free patterns to use matter? (GV4 headroom in the
certification setting)

    taskset -c 0 python3 scripts/b20r58_sf_pattern_selection.py OUT_DIR      (resumable) and analyse

A design diagnostic, not a study. It licenses no claim and adopts nothing.

**Why.** GV4 needs a setting where the research process's *choices* change the successor (B20R9-OPEN-1): no probed
domain has had such headroom so far (graph construction, nine equational settings, larger C4 rows). B20_R56 found a
possible one. The transferred sum-free rows tighten the root bound by 5-10 but their volume (3,924-10,429 separation
rows) slows easy hosts, so all 17 patterns are worse than none there, while they help on hard hosts. If a *subset*
of the patterns keeps most of the bound at a fraction of the rows, choosing patterns is a research decision with
headroom, and a learned-vs-fixed pattern-selection study (GV4) becomes designable. If neither a deployable nor an
optimistic subset beats both "none" and "all", there is no such headroom here either.

**Hosts.** B20_R56's settings ((N, p) = (300, 0.6), (360, 0.6); host i from `random.Random(seed + i)`) with fresh
seeds: 8 development hosts per setting (seed 20265801 and 20265811) and 8 evaluation hosts per setting (20265821 and
20265831). Each host gets B20_R56's witness (HiGHS, 10 s). Hosts are saved before running.

**Scoring (development hosts only).** For each of B20_R55's 17 patterns q, the root bound of the tree route with the
Schur rows plus q's copies alone (root separation as B20_R56), and the rows separation added. gain(q) = mean over
development hosts of (Schur-only root bound − root bound with q); score(q) = gain(q) per 1,000 added rows. TOP-k is
the k highest-scoring patterns (ties by pattern id), k in 1, 2, 4, 8. DEV-K, the deployable choice, is the smallest k
whose mean development root bound with TOP-k is within 0.5 of the mean with all 17 patterns (else 8).

**Evaluation hosts.** The tree route at 30 s per host (exact check included, B20_R56's route otherwise) with six
pattern sets: NONE (Schur rows only), ALL (17), TOP-1, TOP-2, TOP-4, TOP-8. ORACLE-K is the TOP-k with the most
certified evaluation hosts (ties: lower total wall time): an optimistic reference chosen on the evaluation hosts.

**Verdict (fixed here before running).** Let BASE be the better of NONE and ALL (more certified hosts, then lower
total wall time). H = certified(ORACLE-K) − certified(BASE).
  * SELECTION_HEADROOM if H >= 3 (of 16);
  * WEAK_HEADROOM if H is 1 or 2, or H = 0 and ORACLE-K's total wall time is at most 75% of BASE's;
  * NO_HEADROOM otherwise.
Reported descriptively: DEV-K's result against BASE (what a deployable rule gets), per-pattern scores, root bounds
and rows, and every set's certified count and wall time by setting.

**Development looks (disclosed).** The design follows B20_R56's full result (and B20_R57's screen, then running).
No host of this pilot was looked at before this commit. A smoke run of this script on 4 tiny hosts (seeds
999801-999831; N 60 and 80; 5 s per run, 1 s witnesses) completed end to end (every set certified both evaluation
hosts; all scores 0 on such small hosts). With 6 sets and 30 s per run, the pilot costs about 50
minutes of route time, plus about 15 minutes of development scoring.

Run pinned to one core (``taskset -c 0``).
"""
import json
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import generated_bnb_sf as GB  # noqa: E402
from genesis.verification import lp_dual_tree_sf as VT  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r56_sf_tree_certification as R56  # noqa: E402

SETTINGS = R56.SETTINGS
DEV_SEEDS, EVAL_SEEDS = (20265801, 20265811), (20265821, 20265831)
PER = 8
SECONDS = 30
KS = (1, 2, 4, 8)
WITHIN = 0.5
VERDICT = {'headroom': 3, 'time_share': 0.75}


def make_hosts(seeds, role):
    out = []
    for seed, (N, p) in zip(seeds, SETTINGS):
        for i in range(PER):
            rng = random.Random(seed + i)
            out.append({'domain': VT.DOMAIN, 'task_id': f'sf_N{N}_p{p}_{seed + i}', 'family': R56.setting_name(N, p),
                        'elements': [x for x in range(1, N + 1) if rng.random() < p], 'role': role})
    return out


def subset(reg, ids):
    return dict(reg, patterns={k: reg['patterns'][k] for k in sorted(ids)})


def hosts(out, log):
    path = out / 'hosts.json'
    if path.exists():
        saved = json.loads(path.read_text())
        log(f'resume: {len(saved["tasks"])} hosts reloaded')
        return saved['tasks']
    tasks = make_hosts(DEV_SEEDS, 'dev') + make_hosts(EVAL_SEEDS, 'eval')
    for t in tasks:
        m = GB.mip(R56.task_of(t), seconds=R56.WITNESS_S)
        t['witness'], t['mip_optimal'] = m['witness'], m['optimal']
    R11.dump(path, {'tasks': tasks})
    return tasks


def root(task, w, reg, separation):
    rec = GB.certify_with_tree(task, w, reg, seconds=0, separation=separation)
    r = next(s for s in rec['steps'] if s['step'] == 'root-lp')['bound']
    sep = next((s for s in rec['steps'] if s['step'] == 'separation'), None)
    return r, (sep['rows'] if sep else rec['rows'])


def score(out, tasks, reg, log):
    path = out / 'scores.json'
    if path.exists():
        return json.loads(path.read_text())
    dev = [t for t in tasks if t['role'] == 'dev']
    per = {}
    base = {}
    for t in dev:
        task = R56.task_of(t)
        base[t['task_id']] = root(task, t['witness'], GB.empty_registry(reg), None)
    for q in sorted(reg['patterns']):
        rows = []
        for t in dev:
            task = R56.task_of(t)
            b, nb = base[t['task_id']]
            r, n = root(task, t['witness'], subset(reg, [q]), R56.SEPARATION)
            rows.append({'task_id': t['task_id'], 'root': r, 'gain': b - r, 'rows_added': n - nb})
        gain = statistics.mean(x['gain'] for x in rows)
        added = statistics.mean(x['rows_added'] for x in rows)
        per[q] = {'gain': gain, 'rows_added': added, 'score': gain / max(added, 1) * 1000, 'hosts': rows}
        log(f'pattern {q}: gain {gain:.2f}, rows {added:.0f}, score {per[q]["score"]:.3f}')
    ranked = sorted(per, key=lambda q: (-per[q]['score'], q))
    mean_root = {}
    for k in KS + (len(ranked),):
        ids = ranked[:k]
        mean_root[k] = statistics.mean(root(R56.task_of(t), t['witness'], subset(reg, ids), R56.SEPARATION)[0]
                                       for t in dev)
        log(f'dev mean root bound with top-{k}: {mean_root[k]:.2f}')
    all_k = len(ranked)
    dev_k = next((k for k in KS if mean_root[k] <= mean_root[all_k] + WITHIN), KS[-1])
    s = {'per_pattern': per, 'ranked': ranked, 'mean_root': {str(k): v for k, v in mean_root.items()},
         'mean_root_none': statistics.mean(v[0] for v in base.values()), 'dev_k': dev_k}
    R11.dump(path, s)
    return s


def sets_of(sc, reg):
    out = {'NONE': [], 'ALL': sorted(reg['patterns'])}
    for k in KS:
        out[f'TOP{k}'] = sc['ranked'][:k]
    return out


def evaluate(out, tasks, reg, sc, log):
    path = out / 'rows.jsonl'
    done = {(r['task_id'], r['set']) for r in (json.loads(l) for l in path.read_text().splitlines() if l.strip())} \
        if path.exists() else set()
    R56.SECONDS = SECONDS
    sets = sets_of(sc, reg)
    with path.open('a') as fh:
        for i, t in enumerate(x for x in tasks if x['role'] == 'eval'):
            task = R56.task_of(t)
            order = list(sets) if i % 2 == 0 else list(reversed(list(sets)))
            for name in order:
                if (t['task_id'], name) in done:
                    continue
                ids = sets[name]
                side, _ = R56.route(task, t['witness'], subset(reg, ids), separation=R56.SEPARATION if ids else None)
                r = {'task_id': t['task_id'], 'stratum': t['family'], 'set': name, 'patterns': ids, 'side': side}
                fh.write(json.dumps(r, sort_keys=True) + '\n')
                fh.flush()
            log(f'eval {t["task_id"]} done')


def table(rows):
    by = {}
    for r in rows:
        s = by.setdefault(r['set'], {'certified': 0, 'wall_s': 0.0, 'sound': True, 'hosts': 0})
        side = r['side']
        s['hosts'] += 1
        s['certified'] += side['lower'] == side['upper']
        s['wall_s'] = round(s['wall_s'] + side['wall_s'], 3)
        s['sound'] = s['sound'] and side['check']['verdict'] == 'VALID' and side['check']['bound'] == side['upper'] \
            and side['witness_valid'] and side['witness_value'] == side['lower']
    return by


def better(a, b, t):
    return (t[a]['certified'], -t[a]['wall_s']) > (t[b]['certified'], -t[b]['wall_s'])


def verdict(rows, sc, rule=VERDICT):
    t = table(rows)
    base = 'NONE' if better('NONE', 'ALL', t) else 'ALL'
    oracle = None
    for k in KS:
        name = f'TOP{k}'
        if oracle is None or better(name, oracle, t):
            oracle = name
    H = t[oracle]['certified'] - t[base]['certified']
    if H >= rule['headroom']:
        v = 'SELECTION_HEADROOM'
    elif H >= 1 or (H == 0 and t[oracle]['wall_s'] <= rule['time_share'] * t[base]['wall_s']):
        v = 'WEAK_HEADROOM'
    else:
        v = 'NO_HEADROOM'
    dev = f'TOP{sc["dev_k"]}'
    vals = sorted({r['task_id'] for r in rows})
    # values must agree wherever two sets certify a host
    agree = all(len({r['side']['upper'] for r in rows if r['task_id'] == h and r['side']['lower'] == r['side']['upper']}) <= 1
                for h in vals)
    return {'verdict': v if all(s['sound'] for s in t.values()) and agree else 'DEFECT_FOUND', 'H': H, 'base': base,
            'oracle': oracle, 'dev_k': sc['dev_k'], 'dev_set': dev,
            'dev_minus_base': t[dev]['certified'] - t[base]['certified'], 'table': t, 'values_agree': agree,
            'rule': rule}


def analyse(out, tasks, reg, sc):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    ev = {t['task_id'] for t in tasks if t['role'] == 'eval'}
    if {(r['task_id'], r['set']) for r in rows} != {(h, s) for h in ev for s in sets_of(sc, reg)}:
        raise RuntimeError('not every (host, set) pair has been run')
    v = verdict(rows, sc)
    by_setting = {f: table([r for r in rows if r['stratum'] == f]) for f in sorted({r['stratum'] for r in rows})}
    summary = dict(v, by_setting=by_setting, schema='genesis-b20r58-sf-pattern-selection-v1', budget_s=SECONDS,
                   ks=list(KS), within=WITHIN, registry={'package_sha256': reg['package_sha256'], 'sha256': digest(reg)},
                   code_identity=code_identity(ROOT)['sha256'], status='DESIGN_PILOT_DEV',
                   claim='none; a GV4 headroom diagnostic in the certification setting')
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    reg = GB.load_registry()
    tasks = hosts(out, log)
    sc = score(out, tasks, reg, log)
    log(f'ranked {sc["ranked"][:8]}; dev k {sc["dev_k"]}')
    evaluate(out, tasks, reg, sc, log)
    s = analyse(out, tasks, reg, sc)
    log(f'verdict {s["verdict"]}: H {s["H"]} (oracle {s["oracle"]} vs base {s["base"]}); dev {s["dev_set"]} - base '
        f'{s["dev_minus_base"]}; table {json.dumps({k: (v["certified"], v["wall_s"]) for k, v in s["table"].items()})}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
