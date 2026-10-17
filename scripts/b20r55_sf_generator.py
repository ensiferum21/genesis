#!/usr/bin/env python3
"""B20_R55: the row-invention procedure transferred to additive combinatorics: generated, Lean-checked inequalities
for sum-free subsets of integer hosts (GV6 path, second target; s15.3 relaxation family, transfer).

    taskset -c 0 python3 scripts/b20r55_sf_generator.py OUT_DIR

**Why.** B20_R46-R49 transferred the system's row-invention procedure from triangle-free to C4-free subgraphs and
attributed a certification utility to the transferred rows. That is near-domain transfer (roadmap E5: "C4-free to
triangle-free transfer is useful near-domain evidence"). The roadmap names "a different theorem family" as a more
distinct setting. B20_R53 and R54 found no research headroom in the equational target. Sum-free sets (Schur, Erdős;
additive combinatorics) are a different theorem family whose objects are integers under addition, not graph edges.
The builder's structural caveat stands (`handoff/gv6/README.md`): abstractly both are hypergraph-free packings, and
whether this counts as structurally different is the reviewer's decision (B20R46-OPEN-1).

**The registered adaptation (fixed before running).** `invention/cuts_sf.py` (this commit) is generator v2 with only
the motif-specific parts changed:
  * structures are sets P ⊆ {1..m} (max P = m, gcd 1, every element in a Schur triple of P), m <= 8, in place of
    graphs on up to 6-7 vertices;
  * Schur rows (x_a + x_b + x_c <= 2 for a + b = c, a < b; x_a + x_{2a} <= 1) in place of motif rows;
  * copies are injective maps preserving Schur triples (Freiman-type), in place of graph embeddings;
  * the trusted Lean definition module `SFDefs` (new: `SF.SumFree`, `SF.ind`) and a bridge per row shape;
  * pattern statements quantify over values satisfying the pattern's additive relations (no distinctness).
The search, the kept rule and the proof method (an integer rounding of the LP dual, summed, then omega) are unchanged.
The adaptation budget is this one module, about 330 lines.

**This step (engineering plus formal checking; no study).**
  1. Generate the patterns, recording counts at each filter.
  2. Screen every obligation by sampling against its Python model.
  3. Prove them through formal_research.loop with the builder-written recipes named in every receipt.
  4. Assemble a theory package.
A pattern counts only if Lean CHECKED its bound and the three base lemmas (the indicator bound and the two bridges).

**Not in this step.** Certification on sum-free hosts (an exact tree checker over these rows and its utility, with
the registered ablation) is B20_R56, preregistered separately. This package is its input.

**Development looks (disclosed).**
  1. A probe on 12 random hosts (subsets of [N] for N 40-120; HiGHS, no Lean) before writing the module: small
     subsets of [1..9] as patterns with dilation copies only moved the host LP by at most 0.14; with Freiman-type
     copies of patterns up to 8 the LP fell by 0.07-1.30 against gaps of 0.07-3.03 (13-100% of each host's gap,
     median about 36%). Those hosts are not reused.
  2. The kept rule on m <= 8 keeps 17 patterns (214 candidates, 133 covered by triples, 100 implied by Schur rows,
     16 by earlier patterns); every one has an integer rounding certificate.
  3. A Lean run in a scratch copy over the three base lemmas and the first three patterns: the bridges first failed
     (a missing `exfalso`; fixed in the recipe), then all six checked: ind-split, sf-bridge-subst,
     sf-bridge-double-subst and lp-certificate-sum x3.
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
from genesis.invention import cuts_sf as SF  # noqa: E402

import b20r17_relation_invention as R17  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

BASE = ('sf_ind_le_one', 'sf_bridge', 'sf_bridge_double')


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
    patterns = SF.generate(stats=stats)
    log(f'generated {len(patterns)} patterns: {stats["candidates"]} candidates, {stats["triple_covered"]} covered by '
        f'triples, {stats["implied_by_schur_rows"]} implied by Schur rows, '
        f'{len(stats["implied_by_earlier_patterns"])} by earlier patterns')
    conjs = SF.conjectures(patterns)
    screened = {}
    for c in conjs:
        cx, relevant = L.screen(c)
        screened[c['id']] = {'result': 'COUNTEREXAMPLE' if cx is not None else 'NO_COUNTEREXAMPLE',
                             'instances_meeting_hypotheses': relevant}
    log(f'screen: {sum(s["result"] == "COUNTEREXAMPLE" for s in screened.values())} counterexamples among '
        f'{len(screened)} obligations')
    base = [{'name': SF.MODULE, 'source': SF.SOURCE, 'trusted': True}]
    state = L.prove_all(conjs, base_modules=base, conj_name='SFConj', proof_prefix='SFP', unfold=['SF.SumFree'],
                        extra_recipes=SF.recipes(patterns), log=log)
    statuses, usable = SF.obligations_ok(state, patterns)
    pkg, _ = L.assemble(state, name='generated sum-free pattern inequalities v1 (s15.3 relaxation family, transferred)',
                        domain=SF.DOMAIN,
                        scope=('the 0/1 membership indicator, the two Schur bridges, and one bound per pattern '
                               'generated over every set P of positive integers with max P <= 8, gcd 1 and every '
                               'element in a Schur triple, for values satisfying the pattern\'s additive relations. '
                               'Conservative definitions only.'),
                        conventions=['hosts are finite sets of positive integers',
                                     'a set is sum-free when no a + b (a = b allowed) of it lies in it',
                                     'pattern statements quantify over values satisfying the pattern\'s Schur '
                                     'relations; they need no distinctness'],
                        extra={'generation': stats,
                               'patterns': [{k: p[k] for k in ('id', 'elements', 'ex', 'ex_witness', 'lp',
                                                               'lp_schur_rows', 'triples')} for p in patterns]})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    R17.dump(out / 'package.json', pkg)
    summary = {'schema': 'genesis-b20r55-sf-generator-v1', 'generation': stats,
               'patterns': [{'id': p['id'], 'elements': p['elements'], 'triples': len(p['triples']), 'ex': p['ex'],
                             'lp_schur_rows': p['lp_schur_rows'], 'lp_with_earlier': p['lp']} for p in patterns],
               'usable': [p['id'] for p in usable], 'obligations': statuses, 'screen': screened,
               'base_checked': all(statuses.get(k) == 'CHECKED' for k in BASE),
               'construction_cpu_s': round(construction, 3), 'checker_cpu_s_reported': round(checker, 3),
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'engineering and formal checking; licenses nothing; certification on hosts is B20_R56'}
    R17.dump(out / 'summary.json', summary)
    log(f'usable {len(usable)} of {len(patterns)}; base checked {summary["base_checked"]}; construction '
        f'{construction:.1f} CPU s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
