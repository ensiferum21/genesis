#!/usr/bin/env python3
"""B20_R57: the transferred sum-free rows on hosts that are hard for the conventional route (hardness-enriched
follow-up to B20_R56; GV6 second target; DEV).

    taskset -c 0 python3 scripts/b20r57_sf_hard_certification.py OUT_DIR      run (resumable) and analyse

**Why.** B20_R56 found NO_CERTIFICATION_UTILITY for the transferred rows on 40 fresh sum-free hosts: 28 vs 26
certified, wall saving −1.61 s [−4.14, +1.37]. After the fact the rows did better on hosts the conventional route
found hard. This is the pattern B20_R32 → R35 followed: a negative result on an unenriched sample, then a test on
the population where the conventional route struggles. This study is that test, with the population defined by the
conventional route alone, and with one more endpoint fixed in advance: the certified upper bound at the budget.

**Population (candidate-blind screen).** Hosts are drawn exactly as in B20_R56 (random subsets of {1..N}, density p,
(N, p) = (300, 0.6) and (360, 0.6), host i from `random.Random(seed + i)`), with fresh seeds 20265701 and 20265711.
Each candidate gets B20_R56's witness (HiGHS over the Schur rows, 10 s). Route a alone then runs for 20 s from it.
A candidate is **included** when route a does not certify it within those 20 s. Candidates are screened in order
until 20 are included per setting, or 80 have been screened. The screen never runs route c. Every screen outcome is
saved (screen.jsonl) before the next candidate, and reloaded on resume.

**Routes** on the included hosts, unchanged from B20_R56: fresh runs of 60 s each from the same witness,
alternating order, wall time including the exact check.
  * **a (conventional = ablation):** the tree over the Schur and double rows only;
  * **c (transferred):** the same tree plus B20_R55's pattern rows through root separation (30 rounds, 400 a round).

**Primary verdict: coverage.** B20_R56's rule (B20_R35's): CERTIFICATION_UTILITY iff c is sound, c ≥ a, McNemar
one-sided p < 0.05, and the bootstrap 90% interval of the per-host wall saving a − c, stratified by setting, is above
0. DEFECT_FOUND on any soundness failure, NO_CERTIFICATION_UTILITY otherwise.

**Secondary verdict, fixed now: certified bound.** BOUND_UTILITY iff soundness holds, the mean per-host difference
of certified upper bounds a − c (each route's VALID certificate bound at its budget; 0 when both certify) is at least
2, and its stratified bootstrap 90% interval is above 0. NO_BOUND_UTILITY otherwise. It decides only what it names:
the transferred rows give a stronger *certified bound* at the budget, not that they certify more optima.

**Development looks (disclosed).** The design follows B20_R56's full result. On B20_R56's 24 hosts that route a did
not certify within 20 s: a certified 10, c 12 (2 by c only), mean wall saving +2.87 s with most hosts at 0 (both
timed out); c's certified upper bound was below a's on every host neither certified. So the primary verdict is
uncertain and the secondary is expected to pass. No new host was looked at before this commit.

A DEV measurement. It licenses no claim and persists nothing to custody.
"""
import gzip
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
import b20r32_generated_certification as R32  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r56_sf_tree_certification as R56  # noqa: E402

SETTINGS = R56.SETTINGS
SEEDS = (20265701, 20265711)
PER, MAX_CANDIDATES = 20, 80
SCREEN_S = 20
SECONDS = R56.SECONDS
WITNESS_S = R56.WITNESS_S
SEPARATION = R56.SEPARATION
BOOT_SEED = 20265799
BOUND_MIN = 2


def candidate(seed, i, N, p):
    rng = random.Random(seed + i)
    A = [x for x in range(1, N + 1) if rng.random() < p]
    return {'domain': VT.DOMAIN, 'task_id': f'sf_N{N}_p{p}_{seed + i}', 'family': R56.setting_name(N, p),
            'elements': A}


def screen(out, reg, log):
    """Included hosts (with their saved witnesses), screening and saving each candidate in order."""
    path = out / 'screen.jsonl'
    seen = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    by = {s['task_id']: s for s in seen}
    abl = GB.empty_registry(reg)
    included = []
    with path.open('a') as fh:
        for seed, (N, p) in zip(SEEDS, SETTINGS):
            got = 0
            for i in range(MAX_CANDIDATES):
                if got >= PER:
                    break
                t = candidate(seed, i, N, p)
                s = by.get(t['task_id'])
                if s is None:
                    task = R56.task_of(t)
                    m = GB.mip(task, seconds=WITNESS_S)
                    rec = GB.certify_with_tree(task, m['witness'], abl, seconds=SCREEN_S)
                    s = {'task_id': t['task_id'], 'family': t['family'], 'index': i, 'size': len(t['elements']),
                         'witness': m['witness'], 'witness_value': len(m['witness']), 'mip_optimal': m['optimal'],
                         'screen_lower': rec['lower'], 'screen_upper': rec['upper'], 'screen_wall_s': rec['wall_s'],
                         'included': rec['lower'] != rec['upper']}
                    fh.write(json.dumps(s, sort_keys=True) + '\n')
                    fh.flush()
                    log(f'screen {t["task_id"]} |A|={len(t["elements"])}: a {rec["lower"]}..{rec["upper"]} in '
                        f'{rec["wall_s"]:.1f}s -> {"IN" if s["included"] else "out"}')
                if s['included']:
                    included.append((t, s))
                    got += 1
    return included


def run(out, included, reg, log):
    path = out / 'rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    certs = out / 'certificates'
    certs.mkdir(exist_ok=True)
    abl = GB.empty_registry(reg)
    R56.SECONDS = SECONDS
    with path.open('a') as fh:
        for i, (t, s) in enumerate(included):
            if t['task_id'] in done:
                continue
            task = R56.task_of(t)
            w = s['witness']
            if i % 2 == 0:
                a, ca = R56.route(task, w, abl, separation=None); c, cc = R56.route(task, w, reg, separation=SEPARATION)
            else:
                c, cc = R56.route(task, w, reg, separation=SEPARATION); a, ca = R56.route(task, w, abl, separation=None)
            for side, cert, name in ((a, ca, 'a'), (c, cc, 'c')):
                raw = json.dumps(cert, sort_keys=True).encode() if cert is not None else b''
                side['certificate_sha256'] = digest(cert) if cert is not None else None
                side['certificate_bytes'] = len(raw)
                other = c if name == 'a' else a
                if cert is not None and R56.certified(side) and not R56.certified(other):
                    (certs / f'{t["task_id"]}.{name}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
            r = {'task_id': t['task_id'], 'stratum': t['family'], 'size': len(t['elements']),
                 'order': 'ac' if i % 2 == 0 else 'ca',
                 'witness': {'value': len(w), 'elements': w, 'mip_optimal': s['mip_optimal'], 'mip_wall_s': None},
                 'a': a, 'c': c}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{i:02d} {t["task_id"]} |A|={len(t["elements"])} w {len(w)}: a {a["lower"]}..{a["upper"]} '
                f'{a["wall_s"]:.1f}s (root {a["root_bound"]}); c {c["lower"]}..{c["upper"]} {c["wall_s"]:.1f}s '
                f'(root {c["root_bound"]}); checks {a["check"]["verdict"]}/{c["check"]["verdict"]}')


def bound_verdict(rows):
    sound = all(R56.sound_row(r) for r in rows)
    by = {}
    for r in rows:
        by.setdefault(r['stratum'], []).append(r['a']['upper'] - r['c']['upper'])
    real = R32.BOOT_SEED
    R32.BOOT_SEED = BOOT_SEED
    try:
        est, ci = R32.boot_mean(by)
    finally:
        R32.BOOT_SEED = real
    ok = sound and est >= BOUND_MIN and ci[0] > 0
    return {'verdict': 'BOUND_UTILITY' if ok else 'NO_BOUND_UTILITY', 'mean': est, 'interval_90': ci,
            'per_host': [r['a']['upper'] - r['c']['upper'] for r in rows], 'min': BOUND_MIN, 'sound': sound}


def verdict_of(rows):
    real = R56.BOOT_SEED
    R56.BOOT_SEED = BOOT_SEED
    try:
        v = R56.verdict_of(rows)
    finally:
        R56.BOOT_SEED = real
    v['bound'] = bound_verdict(rows)
    return v


def analyse(out, included, reg):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t['task_id'] for t, _ in included}:
        raise RuntimeError('not every included host has been run')
    screened = [json.loads(l) for l in (out / 'screen.jsonl').read_text().splitlines() if l.strip()]
    v = verdict_of(rows)
    summary = dict(v, schema='genesis-b20r57-sf-hard-certification-v1', seeds=list(SEEDS),
                   settings=[{'N': N, 'p': p} for N, p in SETTINGS], budget_s=SECONDS, screen_s=SCREEN_S,
                   witness_s=WITNESS_S, separation=SEPARATION,
                   screen={'candidates': len(screened), 'included': sum(s['included'] for s in screened),
                           'by_setting': {f: {'candidates': sum(s['family'] == f for s in screened),
                                              'included': sum(s['family'] == f and s['included'] for s in screened)}
                                          for f in sorted({s['family'] for s in screened})}},
                   registry={'package_sha256': reg['package_sha256'], 'patterns': len(reg['patterns']),
                             'sha256': digest(reg)},
                   checker_identity=VT.checker_identity(), code_identity=code_identity(ROOT)['sha256'],
                   status='DEV measurement; licenses nothing; route and checker not wired into anything')
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
    log(f'registry: {len(reg["patterns"])} sum-free patterns from {reg["package_sha256"][:16]}')
    included = screen(out, reg, log)
    log(f'screen: {len(included)} hosts included')
    run(out, included, reg, log)
    s = analyse(out, included, reg)
    log(f'verdict {s["verdict"]}: certified a {s["pooled"]["certified_a"]} c {s["pooled"]["certified_c"]}; McNemar p '
        f'{s["mcnemar_p_one_sided"]}; wall saving {s["wall_saving_a_minus_c"]}; passes {s["passes"]}; bound '
        f'{s["bound"]["verdict"]} mean {s["bound"]["mean"]} {s["bound"]["interval_90"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
