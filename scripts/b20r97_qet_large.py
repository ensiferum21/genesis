#!/usr/bin/env python3
"""B20_R97: quality at equal time against the MaxSAT champions on large hosts (DEV, preregistered; written by genesis.autonomy.studygen from the adaptation cell's design)

    taskset -c 0 python3 scripts/b20r97_qet_large.py OUT_DIR      run alone (resumable; pauses before the background limit)

**Why (the adaptation cell's reasons).** SATURATION@B20_R70 (CHRONIC, last seen in B20_R92) is answered by quality_at_equal_time_on_larger_instances (here: values at equal time on n = 128, 256); SIZE_CAP@B20_R75 (CHRONIC, last seen in B20_R92) is answered by extend_domain (here: the large domain (triangle_free_large_v1, n <= 1023)); UNCERTIFIED_TARGETS@B20_R75 (CHRONIC, last seen in B20_R92) is answered by longer_certification (here: a certified bound per host (60 s)); ARM_NOT_RESPONDING[deepdistc]@B20_R92 (OPEN, last seen in B20_R92) is answered by probe_at_home_budget (here: probe_deepdistc at 60 s on 4 hosts); REGIME_GAP@B20_R70 (IMPROVING, last seen in B20_R92) is answered by add_home_budgets (here: the 10 s budget here; 60 s left for the next study (staged)); INTERRUPTED@B20_R81 (CHRONIC, last seen in B20_R92) is answered by sequential_stopping (here: interim looks at 19, 38, 56 hosts); UNRESOLVED_VERDICT@B20_R76 (RELAPSE, last seen in B20_R92) is answered by more_hosts (here: 56 fresh hosts); COMPONENT_EFFECT_UNRESOLVED@B20_R92 (OPEN, last seen in B20_R92) is answered by dedicated_ablation_with_more_power (here: extra arms previous_generation, no_cross, no_relink_restart, first_design on every host, and the study does not stop before they are decided; components the focal configuration already has off: no_dsb, no_pt); the cell's whole design is over its cost limit, so its budgets are staged: 68473 s against a limit of 35253 s, and deferring every caveat the membrane lets the cell defer would not bring it within the limit (high-severity and chronic caveats are not deferred to save time); the largest share is REGIME_GAP@B20_R70 (35847 s): split the study there or raise the limit; this study, staged, is estimated at 15574 s if it runs every host.

**Design (fixed before running).** DESIGN below: 56 fresh hosts in the large domain (planted_cluster n128, erdos n128, planted_cluster n256, erdos n256), every arm in the
runc sandbox through `candidates_large`; the system's method (tfxw-v1, `evidence/configure_tfxw_b20r95/config.json`) at 10 s and at
1 s; 13 champions at 10 s (`maxsat-anytime-large-v1`: each solver's budget starts after the
encoding); extra arms previous_generation, no_cross, no_relink_restart, first_design; probes probe_deepdistc 60 s on 4 hosts. The analysis, labels, validity rule and stopping rule are
`genesis.autonomy.qet`'s (its docstring): the MaxSAT Evaluation 2026 anytime score against each host's best known value,
paired bootstrap of mean score differences at level 1 - 0.1 / 3 at each look (19, 38, 56 hosts), margin
0.002; a certified bound per host (the better of a clique packing and a triangle packing; 60 s). The study stops at the first look where the
comparisons named in `decide` (champions, vbs, extra) are decided. Budgets left for a later study: 60 s. **Cost (estimate):** about
273.6 s per host; about 5449 s if it stops at the first look, 15574 s if it runs every host.

**Expectation, stated before running.** The adaptation cell predicts that this design resolves SATURATION and SIZE_CAP (instances where values, not only times, separate the methods) and narrows UNCERTIFIED_TARGETS (a certified bound per host). From the development looks (B20_R94: on one G(256, 0.5) host the system's method at 1-3 s found more than every champion at 30 s), the builder expects FOCAL_BETTER_THAN_EVERY_CHAMPION and FOCAL_BETTER_THAN_VBS at the main budget; on the planted hosts, where the dense half is small, the margin is smaller and equivalence with the strongest champions is possible there (visible in the per-cell means, which carry no label). At a tenth of the budget (short_vs_vbs): FOCAL_BETTER_THAN_VBS or UNRESOLVED; the dense n256 hosts should carry it, while on the others a run of a tenth of the time may fall short of the champions' best. For the extra arms (previous_generation, no_cross, no_relink_restart, first_design): NO_MEASURABLE_EFFECT expected for most. In B20_R95's final round the frozen configuration, DEFAULT and B20_R89's were within 0.0007 of anytime score of each other at 1 and 5 s, a third of the margin, and in B20_R96's development look the iterated search after the warm starts hardly changed the best on dense hosts; a component that matters would show as HELPS.

**Disclosed before running.** Before preregistering, the builder rehearsed this study's own code path (`qet.run_host` in runc: every arm, the bound, the kept evidence) on four dev-only hosts, one per cell, drawn by the domain's generator with seeds 99970001-99970004 (outside the 2026NNNN blocks studies draw from): all 76 runs succeeded, median metered CPU 10.16-10.55 s at the 10 s budget, 250-284 s per host (studygen's estimate: 274 s), kept evidence 16-37 KB per host, re-checked. Seen there, after the expectation above was written: the system's method at 10 s ahead of the best champion on all four hosts, by 2, 17 and 20 edges (planted n128, G(128, 0.5), planted n256) and by 379 on G(256, 0.5); the extra arms within 5 edges of it either way; DeepDist-c on every host and NuWLS-c-2026 on the two n256 hosts ended at 40-60% of the best value; on G(256, 0.5) the clique bound's linear program did not finish and the triangle bound (25% above the best value) was used. The cell's reading of this study is preregistered with it as `tests_genesis/test_autonomy.py::ProspectiveB20R97` (eight items).

**What it decides.** Nothing about packages, rules or comparators. **Status.** A DEV diagnostic; licenses nothing.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.autonomy import qet  # noqa: E402

DESIGN = {'alpha': 0.1,
 'asked_by': {'ARM_NOT_RESPONDING[deepdistc]@B20_R92': 'probe_at_home_budget',
              'COMPONENT_EFFECT_UNRESOLVED@B20_R92': 'dedicated_ablation_with_more_power',
              'INTERRUPTED@B20_R81': 'sequential_stopping',
              'REGIME_GAP@B20_R70': 'add_home_budgets',
              'SATURATION@B20_R70': 'quality_at_equal_time_on_larger_instances',
              'SIZE_CAP@B20_R75': 'extend_domain',
              'UNCERTIFIED_TARGETS@B20_R75': 'longer_certification',
              'UNRESOLVED_VERDICT@B20_R76': 'more_hosts'},
 'boot': 4000,
 'boot_seed': 20269710,
 'bound_seconds': 60,
 'budget': 10.0,
 'cells': [['planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06}],
           ['erdos', {'n': 128, 'p': 0.5}],
           ['planted_cluster', {'n': 256, 'p_in': 0.8, 'p_out': 0.06}],
           ['erdos', {'n': 256, 'p': 0.5}]],
 'champions': [['aperture', 'aperture'],
               ['aperture_gbg', 'aperture-gbg'],
               ['aperture_ibi', 'aperture-ibi'],
               ['aperture_kbg', 'aperture-kbg'],
               ['deepdist', 'deepdist'],
               ['deepdistc', 'deepdist-c'],
               ['nuwls', 'nuwls-c-ibr'],
               ['nuwls26', 'nuwls-c-2026'],
               ['nuwls26ub', 'nuwls-c-2026-ub'],
               ['pasmaxsat', 'pasmaxsat-c'],
               ['sgat', 'sgat-nuwls-c'],
               ['spb', 'spb-maxsat-c-fps'],
               ['tt', 'tt-open-wbo-inc']],
 'components_already_off': ['no_dsb', 'no_pt'],
 'decide': ['champions', 'vbs', 'extra'],
 'delta': 0.002,
 'domain': 'triangle_free_large_v1',
 'extra': [{'arm': 'previous_generation',
            'config': {'K': 12,
                       'acc': 1,
                       'cross': 5,
                       'dshare': 0.5,
                       'femlam': 1.2,
                       'femlr': 0.3,
                       'femsteps': 300,
                       'frac': 0.3,
                       'kicks': 3,
                       'kpick': 1,
                       'pherw': 0.0,
                       'pw': 0.05,
                       'relink': 20,
                       'repl': 8,
                       'restart': 50,
                       'rho': 0.1,
                       'steps': 400,
                       'tmax': 4.0,
                       'tmin': 0.3,
                       'ws': 3,
                       'xchg': 20},
            'from': 'evidence/configure_tfx_b20r89/config.json',
            'kind': 'tfxw-v1'},
           {'arm': 'no_cross',
            'config': {'K': 6,
                       'acc': 0,
                       'cross': 0,
                       'dshare': 0.5,
                       'femlam': 2.0,
                       'femlr': 0.1,
                       'femsteps': 300,
                       'frac': 0.3,
                       'kicks': 2,
                       'kpick': 4,
                       'pherw': 0.0,
                       'pw': 0.2,
                       'relink': 20,
                       'repl': 16,
                       'restart': 200,
                       'rho': 0.0,
                       'steps': 100,
                       'tmax': 4.0,
                       'tmin': 0.3,
                       'ws': 2,
                       'xchg': 200},
            'from': "evidence/configure_tfxw_b20r95/config.json with {'cross': 0}",
            'kind': 'tfxw-v1'},
           {'arm': 'no_relink_restart',
            'config': {'K': 6,
                       'acc': 0,
                       'cross': 5,
                       'dshare': 0.5,
                       'femlam': 2.0,
                       'femlr': 0.1,
                       'femsteps': 300,
                       'frac': 0.3,
                       'kicks': 2,
                       'kpick': 4,
                       'pherw': 0.0,
                       'pw': 0.2,
                       'relink': 0,
                       'repl': 16,
                       'restart': 0,
                       'rho': 0.0,
                       'steps': 100,
                       'tmax': 4.0,
                       'tmin': 0.3,
                       'ws': 2,
                       'xchg': 200},
            'from': "evidence/configure_tfxw_b20r95/config.json with {'relink': 0, 'restart': 0}",
            'kind': 'tfxw-v1'},
           {'arm': 'first_design',
            'config': {'K': 4,
                       'acc': 0,
                       'cross': 0,
                       'dshare': 0.5,
                       'femlam': 1.5,
                       'femlr': 0.0,
                       'femsteps': 300,
                       'frac': 0.3,
                       'kicks': 1,
                       'kpick': 1,
                       'pherw': 0.0,
                       'pw': 0.1,
                       'relink': 0,
                       'repl': 32,
                       'restart': 0,
                       'rho': 0.0,
                       'steps': 400,
                       'tmax': 2.0,
                       'tmin': 0.3,
                       'ws': 3,
                       'xchg': 50},
            'from': 'tfxw-v1 DEFAULT',
            'kind': 'tfxw-v1'}],
 'focal': {'arm': 'tfxw',
           'config': {'K': 6,
                      'acc': 0,
                      'cross': 5,
                      'dshare': 0.5,
                      'femlam': 2.0,
                      'femlr': 0.1,
                      'femsteps': 300,
                      'frac': 0.3,
                      'kicks': 2,
                      'kpick': 4,
                      'pherw': 0.0,
                      'pw': 0.2,
                      'relink': 20,
                      'repl': 16,
                      'restart': 200,
                      'rho': 0.0,
                      'steps': 100,
                      'tmax': 4.0,
                      'tmin': 0.3,
                      'ws': 2,
                      'xchg': 200},
           'from': 'evidence/configure_tfxw_b20r95/config.json',
           'kind': 'tfxw-v1'},
 'focal_short': [1.0],
 'host_seed': 20269701,
 'later_budgets': [60.0],
 'looks': [19, 38, 56],
 'per_cell': 14,
 'probes': [{'arm': 'probe_deepdistc', 'budget': 60.0, 'hosts': 4, 'solver': 'deepdist-c'}],
 'study': 'B20_R97'}


def main(argv=None):
    argv = argv or sys.argv[1:]
    return qet.main(DESIGN, Path(argv[0]), ROOT)


if __name__ == '__main__':
    sys.exit(main())
