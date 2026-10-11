#!/usr/bin/env python3
"""B20 follow-up on Wolfram's single axiom (DEV only), after `b20_e3_hard.py`.

  b20_hard_followup.py OUT_DIR

W20 memory: the evaluation seeds are taken in order. A seed's memory is the
fixed-policy libraries of the earlier seeds. Every memory lemma was proved from
Wolfram's axiom, so it is a theorem of this system. Memory is screened against the
seed's evaluation targets (EXACT, INSTANCE). The arms are:
  * the seed's own library;
  * that library plus retrieved memory (the 8 most relevant lemmas);
  * that library plus all memory as premises;
  * that library plus a curriculum, built from variants of the seed's failed development
    targets only and solved within 60 CPU-s.

Lean: every successor proof that used library lemmas, for the fixed and learned policies
on the first seed, is replayed with its whole lemma chain.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import digest  # noqa: E402
from genesis.fol import parse  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import memory as MEM  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SYSTEM = 'ba_wolfram'


def eq_of(text):
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    return Q.canon((f[1], f[2]))


def library_of(entries, prefix=''):
    return [{'id': prefix + e['id'], 'eq': eq_of(e['text']), 'text': e['text'], 'proof': e['proof'],
             'uses': [prefix + u for u in e['uses']], 'premise_ids': [prefix + u for u in e['premise_ids']]}
            for e in entries]


def main(argv=None):
    argv = argv or sys.argv[1:]
    base = Path(argv[0])
    out = base / 'hard_followup'
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    files = sorted((base / 'e3_hard').glob('seed_*.json'), key=lambda p: int(p.stem.split('_')[1]))
    runs = [json.loads(p.read_text()) for p in files]
    rules = runs[0]['rules']
    # ---------------- W20 memory across seeds
    rows, memory = [], []
    for i, r in enumerate(runs):
        seed = r['seed']
        ev = [eq_of(t) for t in r['targets']]
        own = library_of(r['policies']['fixed']['library_entries'], f'{seed}:')
        usable, excluded = MEM.screen(memory, ev)
        pool = Q.true_equations(SYSTEM, rules['pool_size'], per_bucket=rules['per_bucket'], seed=seed) + \
            Q.false_equations(SYSTEM, rules['pool_size'], rules['false_conjectures'], seed=seed)
        lo, hi = rules['target_range']
        dev = Q.sample_targets(SYSTEM, rules['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=pool)
        evd = RS.evaluate_successor(SYSTEM, own + usable, dev, eval_s=rules['eval_s'], premise_k=rules['premise_k'])
        failed = [d for d, x in zip(dev, evd['rows']) if x['status'] != 'PROVED']
        seen, cur = set(), []
        for d in failed:
            for v in MEM.variants(d, Q.SYSTEMS[SYSTEM]['decider']):
                if v['valid'] and v['eq'] not in seen:
                    seen.add(v['eq']); cur.append(v['eq'])
        cres = RS.run(SYSTEM, RS.Fixed(seed), cur, budget_s=60, dev_targets=dev, prove_s=rules['prove_s'],
                      premise_k=rules['premise_k']) if cur else {'library': [], 'cpu_s': 0.0}
        cur_lib = [dict(l, id=f'C{seed}:{l["id"]}', uses=[f'C{seed}:{u}' for u in l['uses']],
                        premise_ids=[f'C{seed}:{u}' for u in l['premise_ids']]) for l in cres['library']]
        arms = {'own': (own, None), 'retrieval': (own + usable, None),
                'replay_all': (own + usable, len(own) + len(usable)), 'curriculum': (own + cur_lib, None)}
        scores = {}
        for arm, (lib, k) in arms.items():
            scores[arm] = RS.evaluate_successor(SYSTEM, lib, ev, eval_s=rules['eval_s'],
                                                premise_k=k or rules['premise_k'])['proved']
        rows.append({'seed': seed, 'memory': len(memory), 'usable': len(usable), 'excluded': excluded,
                     'curriculum_variants': len(cur), 'curriculum_solved': len(cur_lib), 'scores': scores,
                     'empty': r['empty'], 'targets': len(ev)})
        log(f'w20 seed {seed}: memory {len(memory)} (usable {len(usable)}, excluded {len(excluded)}), '
            f'curriculum {len(cur_lib)}/{len(cur)}, scores {scores}, empty {r["empty"]}')
        memory += own
    (out / 'w20.json').write_text(json.dumps(rows, indent=1, sort_keys=True, default=str) + '\n')
    # ---------------- W18 diagnostic: non-strict macro expansion on Wolfram (post hoc)
    from genesis.learning import macros as M
    src = json.loads((base / 'w18' / 'ba_sheffer_macro.json').read_text())['macro']
    def tup(x):
        return (x[0], x[1]) if x[0] == 'var' else (x[0], x[1], tuple(tup(a) for a in x[2]))
    macro = dict(src, steps=[dict(st, schema=(tup(st['schema'][0]), tup(st['schema'][1])), budget_s=10)
                             for st in src['steps']])
    w = json.loads((base / 'w18' / 'wolfram_transfer.json').read_text())
    wpool = Q.true_equations(SYSTEM, 5, per_bucket=8, seed=201) + Q.false_equations(SYSTEM, 5, 30, seed=201)
    wt = Q.sample_targets(SYSTEM, 15, min_total=5, max_total=8, seed=201 * 11, exclude=wpool)
    lib, mlog = M.expand(macro, SYSTEM, budget_s=w['budget_s'] - w['induction_charge_cpu_s'], strict=False)
    evm = RS.evaluate_successor(SYSTEM, lib, wt, eval_s=3, premise_k=8)
    lenient = {'strict_successor': w['macro_successor'], 'nonstrict_successor': evm['proved'],
               'nonstrict_lemmas': len(lib), 'uncompressed_successor': w['uncompressed_successor'],
               'empty': w['empty'], 'targets': len(wt), 'steps_attempted': len(mlog),
               'note': 'post hoc: non-strict expansion added after the strict transfer failed at its first step'}
    (out / 'w18_nonstrict.json').write_text(json.dumps({'summary': lenient, 'log': mlog}, indent=1,
                                                       sort_keys=True) + '\n')
    log(f'w18 non-strict Wolfram: {lenient}')
    # ---------------- Lean chains on the first seed
    from genesis.formal_research import fof_lean as F
    lean = []
    first = runs[0]
    for pol in ('fixed', 'learned'):
        lib = library_of(first['policies'][pol]['library_entries'])
        for row in first['policies'][pol]['eval_rows']:
            if row['status'] != 'PROVED' or not row['lemmas_used']:
                continue
            entries, gd, gp = RS.lean_chain(lib, row['proof'], row['premise_ids'], len(Q.axioms(SYSTEM)))
            rec = F.replay(f'b20h-{pol}-{digest(row["target"])[:10]}', Q.axioms(SYSTEM),
                           Q.closed(eq_of(row['target'])), row['proof'], lemmas=entries, goal_deps=gd,
                           goal_positions=gp)
            lean.append({'policy': pol, 'target': row['target'], 'chain_lemmas': len(entries), 'status': rec['status'],
                         'reason': rec.get('reason')})
            log(f'lean {pol}: {rec["status"]} ({len(entries)} chained lemmas)')
    (out / 'lean.json').write_text(json.dumps(lean, indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
