#!/usr/bin/env python3
"""B20_R46: the row-invention procedure transferred to a structurally different domain (C4-free subgraphs):
generated, Lean-checked C4 pattern inequalities (GV6 path; s15.3 relaxation family, transfer).

    taskset -c 0 python3 scripts/b20r46_c4_generator.py OUT_DIR

**Why.** The system's clearest invention so far is a *procedure*. It enumerates small graphs, keeps those
whose LP exceeds their extremal number, and proves each bound in Lean from the LP's own dual. It
produced the K5-to-K7 rows that make dense triangle-free hosts certifiable (B20_R35, R37, R41). GV6 asks
whether a learned capability helps in a structurally different domain within a registered adaptation
budget. The C4-free domain (c4_host_v2) is such a domain. Its evaluator LP, over 4-cycle rows, is very
weak: 11.25 against ex = 7 on K6. That is why B20_R23's C4 causal pilot was UNSETTLED_REFERENCE.

**The registered adaptation (fixed before running).** `invention/cuts_c4.py` (this commit) is generator
v2 with only the motif-specific parts changed:
  * 4-cycle rows with 3 on the right;
  * a Lean bridge with the distinctness that `G4.C4Free` needs;
  * pattern statements over pairwise-distinct vertices;
  * the domain predicate `G4.C4Free` from B18's `G4Defs`.
The adaptation budget is this one module, about 300 lines, of which the search and kept rule are
unchanged. Patterns have at most 6 vertices.

**This step (engineering plus formal checking; no study).**
  1. Generate the patterns, recording counts at each filter.
  2. Screen every obligation by sampling against its Python model, as B20_R31/R37 did.
  3. Prove them through formal_research.loop. The recipes are builder-written and named in every
     receipt. The proofs come from each pattern's integer rounding certificate.
  4. Assemble a theory package.
A pattern counts only if Lean CHECKED its bound and the three base lemmas (adj ≤ 1, symmetry, the C4
bridge). The diagnostic recorded is each kept pattern's LP gap closed: LP under cycle rows minus LP
with the earlier patterns, against ex(F).

**Not in this step.** The exact checker for C4 certificates and the certification route on C4 hosts
are B20_R47, preregistered separately. This package is their input.

**Development looks (disclosed; no hosts were used).**
  1. Prototyping the kept rule on graphs up to 6 vertices kept 34 patterns. Among them: K4 (ex 4),
     K_{2,3} (ex 4), K5 (ex 6), K_{2,4} (ex 5) and K6 (ex 7; LP 11.25 → 7.5).
  2. A Lean run in a scratch copy, over the three base lemmas and the first three patterns (K4,
     K_{2,3}, K5), checked all six on the first attempt: adj-split, comm-or-swap, c4-bridge-verts,
     and lp-certificate-sum ×3.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity  # noqa: E402
from genesis.discovery import construct as K  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.invention import cuts_c4 as C4  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402

import b20r17_relation_invention as R17  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    import time
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    if (out / 'package.json').exists():
        log('package exists; not rebuilt')
        return 0
    budget = K.Budget(1e9)
    stats = {}
    patterns = C4.generate(stats=stats)
    log(f'generated {len(patterns)} patterns: {stats["graphs_in_range"]} graphs in range, '
        f'{stats["connected_cycle_covered"]} connected and cycle-covered, {stats["implied_by_cycle_rows"]} implied by '
        f'cycle rows, {len(stats["implied_by_earlier_patterns"])} by earlier patterns')
    conjs = C4.conjectures(patterns)
    screened = {}
    for c in conjs:
        cx, relevant = L.screen(c)
        screened[c['id']] = {'result': 'COUNTEREXAMPLE' if cx is not None else 'NO_COUNTEREXAMPLE',
                             'instances_meeting_hypotheses': relevant}
    log(f'screen: {sum(s["result"] == "COUNTEREXAMPLE" for s in screened.values())} counterexamples among '
        f'{len(screened)} obligations')
    base = [R17.DEFS, {'name': RP.C4_MODULE, 'source': RP.C4_SOURCE, 'trusted': True},
            {'name': C4.MODULE, 'source': C4.SOURCE, 'trusted': True}]
    state = L.prove_all(conjs, base_modules=base, conj_name='P4Conj', proof_prefix='P4P',
                        unfold=['G4.C4Free'], extra_recipes=C4.recipes(patterns), log=log)
    statuses, usable = C4.obligations_ok(state, patterns)
    pkg, _ = L.assemble(state, name='generated C4 pattern inequalities v1 (s15.3 relaxation family, transferred)',
                        domain=C4.DOMAIN,
                        scope=('0/1 adjacency, its symmetry, the C4 bridge (distinct opposite vertices), and one bound '
                               'per pattern generated over every graph on at most six vertices, for pairwise-distinct '
                               'vertices. Conservative definitions only.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'pattern statements quantify over pairwise-distinct assignments of the pattern '
                                     'vertices'],
                        extra={'generation': stats,
                               'patterns': [{k: p[k] for k in ('id', 'vertices', 'edges', 'ex', 'ex_witness', 'lp',
                                                               'lp_cycle_rows')} for p in patterns]})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    R17.dump(out / 'package.json', pkg)
    summary = {'schema': 'genesis-b20r46-c4-generator-v1', 'generation': stats,
               'patterns': [{'id': p['id'], 'vertices': p['vertices'], 'edges': len(p['edges']), 'ex': p['ex'],
                             'lp_cycle_rows': p['lp_cycle_rows'], 'lp_with_earlier': p['lp']} for p in patterns],
               'usable': [p['id'] for p in usable], 'obligations': statuses, 'screen': screened,
               'base_checked': all(statuses.get(k) == 'CHECKED' for k in ('p4_adj_le_one', 'p4_adj_comm', 'p4_bridge')),
               'construction_cpu_s': round(construction, 3), 'checker_cpu_s_reported': round(checker, 3),
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'engineering and formal checking; licenses nothing; checker and route are B20_R47'}
    R17.dump(out / 'summary.json', summary)
    log(f'usable {len(usable)} of {len(patterns)}; base checked {summary["base_checked"]}; construction '
        f'{construction:.1f} CPU s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
