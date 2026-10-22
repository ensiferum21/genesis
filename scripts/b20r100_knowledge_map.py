#!/usr/bin/env python3
"""B20_R100: does Genesis know what it knows? The knowledge map's first prospective test (L2; DEV, preregistered)

    python3 scripts/b20r100_knowledge_map.py predict OUT_DIR     before B20_R86 runs: fit, replay, write predictions
    python3 scripts/b20r100_knowledge_map.py score OUT_DIR       after B20_R86 is recorded: score them

**Why.** `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md`: a research policy that improves itself needs a model of its
own knowledge (predictive coding and curiosity: where its knowledge is thin, where it is wrong). `autonomy.kmap` is
that model for solver performance. A model of one's own knowledge is only worth something if its predictions hold on
results it has not seen, so this study writes the map's predictions for B20_R86 before B20_R86 runs, and scores them
after.

**Design (fixed before B20_R86 runs).**
  * **The map.** `autonomy.kmap.Map` fitted on every study the adaptation cell reads (through B20_R97; B20_R86 is not
    in it), with the sd scale learned from the replay of those studies (each predicted from the ones before).
  * **What it predicts.** For each of B20_R86's arms (gen1, gen2, gen3, control, engine) and run times (0.05, 0.1,
    0.25, 0.5, 2.0 s): the quality q (mean over a host's runs of min(1, value / target)) on a planted n63 host, as a
    function of the host's edge density, written on a grid (DENSITIES) and read off by linear interpolation at each
    B20_R86 host's density. gen2, gen3 and control are methods the map has never seen; it must say so through wider
    intervals (class-level predictions).
  * **Baseline.** Each method's mean quality over every recorded cell (unseen methods: the mean over every cell).
  * **Primary statistic.** Over B20_R86's cells (24 hosts x 5 arms x 5 run times), d = |baseline error| - |map
    error|; mean d with a host-stratified bootstrap 90% interval (4,000 resamples of hosts, seed BOOT_SEED).
    MAP_BETTER if the lower end > 0, MAP_WORSE if the upper end < 0, otherwise NO_DIFFERENCE.
  * **Secondary.** Coverage of the 90% intervals (overall, seen methods, unseen methods); mean interval width, seen
    against unseen (the map knows what it does not know if unseen methods get wider intervals *and* their coverage
    holds); surprises (|z| > 3 x scale) by method.

**Development looks (disclosed).** The replay over the recorded studies was run while building the map (22 Oct 2026):
the map's mean absolute error fell below the baseline's from B20_R81 on (0.060 vs 0.104 at B20_R81, 0.030 vs 0.052 at
B20_R92, 0.032 vs 0.036 at B20_R97); interval coverage was poor early and the sd scale was added after that look; at
B20_R97 the map flagged DeepDist-c and NuWLS-c-2026 among its surprises, the collapse that B20_R98 checks. The
prospective test (B20_R86) has not been looked at: its hosts are drawn when it runs.

**Expectation, stated before B20_R86 runs.** MAP_BETTER, weakly: on n63 planted hosts most arms reach the target at
2 s, so both predictors do well at long run times and the map's advantage comes from short run times and from the
engine and gen1 (seen methods). Coverage of the unseen methods' intervals is the less certain part. **Status.** DEV;
licenses nothing.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.autonomy import kmap as K  # noqa: E402
from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r100'
TARGET_STUDY = 'generations_b20r86'
ARMS = ('gen1', 'gen2', 'gen3', 'control', 'engine')
SEEN, UNSEEN = ('gen1', 'engine'), ('gen2', 'gen3', 'control')
LADDER = (0.05, 0.1, 0.25, 0.5, 2.0)
N = 63
DENSITIES = tuple(round(0.18 + 0.005 * i, 3) for i in range(25))     # 0.18 .. 0.30
BOOT_SEED, BOOT = 20270001, 4000


def corpus_digest(corp):
    return hashlib.sha256(json.dumps(corp, sort_keys=True).encode()).hexdigest()


def predict(out):
    corp = K.corpus(ROOT)
    names = [n for n, _ in corp]
    if any('b20r86' in n for n in names):
        raise SystemExit('B20_R86 is already in the corpus: the predictions would not be prospective')
    rep, zs = K.replay(corp)
    zs_scale = K.learned_scale(zs)
    train = [c for _, cs in corp for c in cs]
    M = K.Map(train, scale=zs_scale)
    base, allq = {}, [q for _, _, q in train]
    for meth, _, q in train:
        base.setdefault(meth, []).append(q)
    grid = {}
    for arm in ARMS:
        for t in LADDER:
            rows = []
            for d in DENSITIES:
                f = K.features(N, d * N * (N - 1) / 2, True, t)
                mu, sd, lvl = M.predict(arm, f)
                rows.append({'density': d, 'mean': mu, 'sd': sd, 'level': lvl})
            grid[f'{arm}@{t:g}'] = rows
    pred = {'study': STUDY, 'target_study': TARGET_STUDY, 'scale': zs_scale, 'grid': grid,
            'baseline': {a: (sum(base[a]) / len(base[a]) if a in base else sum(allq) / len(allq)) for a in ARMS},
            'corpus': {'studies': names, 'cells': len(train), 'sha256': corpus_digest(corp)},
            'code_identity': code_identity(ROOT)['sha256']}
    out.mkdir(parents=True, exist_ok=True)
    (out / 'predictions_b20r86.json').write_text(json.dumps(pred, indent=1, sort_keys=True) + '\n')
    (out / 'replay.json').write_text(json.dumps(rep, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'scale': zs_scale, 'corpus_cells': len(train), 'studies': names}, indent=1))
    return pred


def read(grid_rows, density):
    """Linear interpolation of (mean, sd) at a density (clamped to the grid)."""
    ds = [r['density'] for r in grid_rows]
    d = min(max(density, ds[0]), ds[-1])
    i = max(0, min(len(ds) - 2, int((d - ds[0]) / (ds[1] - ds[0]))))
    a, b = grid_rows[i], grid_rows[i + 1]
    w = (d - a['density']) / (b['density'] - a['density'])
    return a['mean'] + w * (b['mean'] - a['mean']), a['sd'] + w * (b['sd'] - a['sd'])


def verdict_of(lo, hi):
    """The preregistered label from the 90% interval of mean d (baseline error minus map error)."""
    return 'MAP_BETTER' if lo > 0 else ('MAP_WORSE' if hi < 0 else 'NO_DIFFERENCE')


def score(out):
    pred = json.loads((out / 'predictions_b20r86.json').read_text())
    ev = ROOT / 'evidence' / TARGET_STUDY
    rows = [json.loads(l) for l in (ev / 'rows.jsonl').read_text().splitlines() if l.strip()]
    cells = []
    for r in rows:
        n = r['n']
        m = r['edges'] if isinstance(r['edges'], int) else len(r['edges'])
        dens = m / (n * (n - 1) / 2)
        for arm in ARMS:
            for t in LADDER:
                runs = r['runs'].get(arm, {}).get(str(t)) or r['runs'].get(arm, {}).get(repr(t)) or []
                vals = [x['value'] for x in runs if x.get('run') == 'SUCCESS']
                if not vals:
                    continue
                q = sum(min(1.0, v / r['target']) for v in vals) / len(vals)
                mu, sd = read(pred['grid'][f'{arm}@{t:g}'], dens)
                b = pred['baseline'][arm]
                cells.append({'host': r['task_id'], 'arm': arm, 't': t, 'q': q, 'mean': mu, 'sd': sd,
                              'd': abs(q - b) - abs(q - mu), 'inside': abs(q - mu) <= K.Z90 * sd,
                              'z': (q - mu) / max(sd, 1e-9)})
    hosts = sorted({c['host'] for c in cells})
    by = {h: [c['d'] for c in cells if c['host'] == h] for h in hosts}
    est = sum(c['d'] for c in cells) / len(cells)
    rng = random.Random(BOOT_SEED)
    boots = []
    for _ in range(BOOT):
        pick = [rng.choice(hosts) for _ in hosts]
        ds = [x for h in pick for x in by[h]]
        boots.append(sum(ds) / len(ds))
    boots.sort()
    lo, hi = boots[int(0.05 * BOOT)], boots[int(0.95 * BOOT) - 1]
    verdict = verdict_of(lo, hi)
    cov = lambda cs: sum(c['inside'] for c in cs) / len(cs) if cs else None
    width = lambda cs: 2 * K.Z90 * sum(c['sd'] for c in cs) / len(cs) if cs else None
    seen = [c for c in cells if c['arm'] in SEEN]
    unseen = [c for c in cells if c['arm'] in UNSEEN]
    summary = {'study': STUDY, 'verdict': verdict, 'mean_d': est, 'interval90': [lo, hi], 'cells': len(cells),
               'mae_map': sum(abs(c['q'] - c['mean']) for c in cells) / len(cells),
               'mae_baseline': sum(abs(c['q'] - pred['baseline'][c['arm']]) for c in cells) / len(cells),
               'coverage90': {'all': cov(cells), 'seen': cov(seen), 'unseen': cov(unseen)},
               'interval_width': {'seen': width(seen), 'unseen': width(unseen)},
               'knows_what_it_does_not_know': (width(unseen) or 0) > (width(seen) or 0) and (cov(unseen) or 0) >= 0.8,
               'surprises': sorted({(c['arm'], c['t']) for c in cells if abs(c['z']) > 3}),
               'predictions_sha256': hashlib.sha256((out / 'predictions_b20r86.json').read_bytes()).hexdigest(),
               'code_identity': code_identity(ROOT)['sha256']}
    summary['surprises'] = [list(s) for s in summary['surprises']]
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    (out / 'cells.jsonl').write_text(''.join(json.dumps(c, sort_keys=True) + '\n' for c in cells))
    print(json.dumps(summary, indent=1))
    return summary


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ('predict', 'score'):
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[1]).resolve()
    if out != (ROOT / 'evidence' / 'knowledge_map_b20r100').resolve():
        raise SystemExit('the registered output is evidence/knowledge_map_b20r100')
    (predict if argv[0] == 'predict' else score)(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
