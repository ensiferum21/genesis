#!/usr/bin/env python3
"""CRPD-2 (B20_R2): Lean-check the codegree characterisation of C4-freeness.

    b20r_codegree.py OUT_DIR

Screens the statement on random small edge sets (loops and both orientations included),
searches with the builder-written recipe, accepts it through the sandboxed checker,
assembles a theory package and replays it from its sources. Writes package.json,
replay.json and soundness.json (the EQ-mode record) to OUT_DIR. A known result; the
proof is builder-written.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.formal_research import loop as L  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402
from genesis.invention import codegree as CG  # noqa: E402


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    state = L.prove_all([CG.conjecture()], base_modules=CG.base_modules(), conj_name='CDConj', proof_prefix='CDP',
                        unfold=['G4.C4Free', 'CD.CodegLeOne', 'CD.commonNbrs', 'G4.adj', 'G4.verts'],
                        extra_recipes=CG.recipes, log=log)
    st = state['statements'][0]
    if st['status'] != 'CHECKED':
        (out / 'state.json').write_text(json.dumps({'statements': state['statements'],
                                                    'attempts': state['attempts']}, indent=1, default=str) + '\n')
        log(f'not checked: {st}')
        return 1
    pkg, _ = L.assemble(state, name='Codegree characterisation of C4-freeness (CRPD-2)', domain='c4_host_v2',
                        scope='every finite edge set over ℕ (GT.Edges), loops and both orientations included',
                        conventions=['known elementary result; statement and proof recipe are builder-written',
                                     'adjacency is symmetric by definition (G4.adj)'])
    (out / 'package.json').write_text(json.dumps(pkg, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    rep = TP.replay(pkg)
    (out / 'replay.json').write_text(json.dumps(rep, indent=1, sort_keys=True, default=str) + '\n')
    rec = CG.soundness_record(pkg)
    (out / 'soundness.json').write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
    log(f'statement {st["status"]} (screened {st.get("screened_instances")} instances); replay {rep["verdict"]}; '
        f'mode {rec["established"]}')
    return 0 if rep['verdict'] == 'REPLAYED' and rec['established'] == 'EQ' else 1


if __name__ == '__main__':
    sys.exit(main())
