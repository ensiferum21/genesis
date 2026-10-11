#!/usr/bin/env python3
"""B21 / W22 follow-up: the Lean bridge after the ground-hint repair, DEV only.

  b21_w22_lean_followup.py OUT_DIR         (writes OUT_DIR/w22_lean_followup.json)

Written after the main run (`b21_improvement.py`), whose W22 Lean bridge replayed none of
the 11 primitive-arm successor proofs (ELABORATION_ERROR). The cause was the step-hint
generator in `fof_lean.ground_hints`, not the definitional bridge: E steps of the form
rw(…rw(spm(A, B), C)…) on Wolfram's axiom, often with ordered rewriting by a derived
commutativity law, got no ground instances, and `grind` alone could not close them.
The repair: the overlap result is rewritten towards a normal form by the other parents
(size-decreasing rules, matching modulo a commutativity parent) before it is matched to
the conclusion, the rule and commutativity instances used become hints, and matched
overlaps are tried before blind enumeration.

The main run kept no proof objects for its libraries, so this follow-up regenerates the
same arms on seed 610 under the same rules (a CPU budget: the libraries can differ from the
main run's) and replays, with lemma chains:
  * every primitive-arm successor proof that used library lemmas, bound to the *base*
    statement with the primitive instantiated by its λ-term (the W22 bridge);
  * every base-arm successor proof that used library lemmas (plain Wolfram chains).
The main run's record is not changed.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b21_improvement as B  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.formal_research import fof_lean as F  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import primitives as PR  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SEED = 610


def replay_all(system_for_chain, res, ev, definitions, tag, log):
    out = []
    for r in ev['rows']:
        if r['status'] != 'PROVED' or not r['lemmas_used']:
            continue
        entries, gd, gp = RS.lean_chain(res['library'], r['proof'], r['premise_ids'],
                                        len(Q.axioms(system_for_chain)))
        t = time.monotonic()
        rec = F.replay(f'b21-w22f-{tag}-{digest(r["target"])[:10]}', Q.axioms(B.SYSTEM), Q.closed(r['eq']),
                       r['proof'], lemmas=entries, goal_deps=gd, goal_positions=gp, definitions=definitions)
        out.append({'target': r['target'], 'chain_lemmas': len(entries), 'status': rec['status'],
                    'reason': rec.get('reason'), 'errors': rec.get('errors', [])[:4], 'steps': rec.get('steps'),
                    'hinted_steps': rec.get('hinted_steps'), 'seconds': round(time.monotonic() - t, 1)})
        log(f'{tag}: {rec["status"]} ({len(entries)} chained lemmas)')
    return out


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    path = out / 'w22_lean_followup.json'
    if path.exists():
        raise FileExistsError(path)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    summary = json.loads((out / 'w22' / 'summary.json').read_text())
    prim = PR.primitive(tuple_tree(summary['primitive']['pattern']), name=summary['primitive']['name'])
    ext = PR.extend(B.SYSTEM, prim)
    assert Q.SYSTEMS[ext]['axioms'][-1] == summary['contract']['definition']
    base_pool, dev = B.materials(B.SYSTEM, SEED)
    ext_pool = Q.true_equations(ext, B.CFG['pool_size'], per_bucket=B.CFG['per_bucket'], seed=SEED) + \
        Q.false_equations(ext, B.CFG['pool_size'], B.CFG['false_conjectures'], seed=SEED)
    renamed, seen = [], set()
    for e in ext_pool:
        u = Q.canon((PR.unfold(e[0], prim), PR.unfold(e[1], prim)))
        if u not in seen and u[0] != u[1]:
            seen.add(u); renamed.append(u)
    ev_targets = B.panel(SEED * 3 + 1, base_pool + dev + renamed)
    main_targets = [r['target'] for r in summary['rows'][0]['lean']]
    rows = {}
    for arm, (sysname, pool) in {'primitive': (ext, ext_pool), 'base': (B.SYSTEM, base_pool)}.items():
        res = RS.run(sysname, RS.Fixed(SEED), pool, budget_s=B.CFG['budget_s'], dev_targets=dev,
                     prove_s=B.CFG['prove_s'], premise_k=B.CFG['premise_k'])
        ev = RS.evaluate_successor(sysname, res['library'], ev_targets, eval_s=B.CFG['eval_s'],
                                   premise_k=B.CFG['premise_k'])
        log(f'{arm}: library {len(res["library"])}, successor {ev["proved"]}/{len(ev_targets)}')
        defs = [PR.lean_definition(prim)] if arm == 'primitive' else []
        reps = replay_all(sysname, res, ev, defs, arm, log)
        rows[arm] = {'library': len(res['library']), 'library_sha256': res['library_sha256'],
                     'successor': ev['proved'], 'targets': len(ev_targets),
                     'replays': reps, 'checked': sum(r['status'] == 'THEOREM_CHECKED' for r in reps),
                     'attempted': len(reps)}
    record = {'seed': SEED, 'panel_sha256': digest([Q.text(e) for e in ev_targets]),
              'panel_matches_main_run_targets': sorted(set(main_targets) - {Q.text(e) for e in ev_targets}) == [],
              'rows': rows, 'note': 'regenerated libraries under a CPU budget; not the main run\'s libraries'}
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    log(f'wrote {path}')
    return 0


def tuple_tree(x):
    """JSON lists back to the tuple terms the learning code uses."""
    if isinstance(x, list):
        return tuple(tuple_tree(a) for a in x)
    return x


if __name__ == '__main__':
    sys.exit(main())
