"""The study generator (B20_R96): it turns the adaptation cell's design into a preregistered study script.

The cell (B20_R93) writes a design in its own vocabulary (ladder, long budgets, competitors, sizes, hosts, quality at
equal time, sequential stopping, probes, ablations, ...). When that design asks for quality at equal time on instances
beyond n = 63, it is a study of `genesis.autonomy.qet` in the large domain; this module writes it:

  * cells: planted_cluster (p_in 0.8, p_out 0.06) and G(n, 0.5) at every size above 63 the design asks for; hosts per
    cell = the design's hosts divided by the cells, rounded up;
  * the budget: the cell's long budgets are staged when the design is over its cost limit (the cell says to split at
    the largest share): this study takes the shortest long budget at least 10 s, the next study the rest;
  * the focal method: the system's newest frozen configuration (the newest `evidence/configure_*/config.json`), and
    as extra arms the previous generation's frozen configuration (to see whether the generation helped) and, when the
    cell asks for an ablation, the focal configuration without each component it uses (B20_R92's ablations: no_dsb,
    no_pt, no_cross, no_relink_restart; a component the configuration already has off gives no arm) and the engine's
    first design (its DEFAULT); then the study does not stop before those comparisons are decided too (`decide`);
  * the champions: every leading solver the design names, plus the rest of the 13 pinned ones (they are cheap at this
    budget relative to what an exclusion would cost in credibility), each as an arm;
  * probes: the design's probes (a champion at its home budget on a few hosts);
  * looks at a third, two thirds and all of the hosts; alpha 0.10; delta 0.002 (a fifth of a per cent of anytime
    score: the 2026 ranking's adjacent entrants differ by about 0.003); 4,000 bootstrap resamples;
  * seeds: a block of ten, 2026NNk1 .. 2026NNk1 + 9 for batch NN, that no script in the tree has used (checked here
    and by the tests);
  * the script: the design embedded as JSON, a docstring that states what the cell asked for, how this study answers
    each request (`implementation`) and what it costs (`estimate_seconds`), and the call to `qet.main`. The builder commits it and sends its SHA-256 before it runs (the membrane), as for every study.
"""
import json
import math
from pathlib import Path
import pprint
import re

PLANTED = {'p_in': 0.8, 'p_out': 0.06}
ERDOS_P = 0.5
DELTA, ALPHA, BOOT = 0.002, 0.10, 4000
# B20_R92's ablations of the system's method, each switching one component off (the same keys in tfx-v1 and tfxw-v1)
ABLATIONS = (('no_dsb', {'ws': 2}), ('no_pt', {'acc': 0}), ('no_cross', {'cross': 0}),
             ('no_relink_restart', {'relink': 0, 'restart': 0}))
RUN_OVERHEAD_S = 0.35      # per run (the cell's metabolism model, B20_R93: 0.3495 s measured)
ENCODING_S = 2.0           # a champion's encoding of a G(256, 0.5) host: 1.2 s of Python measured (B20_R94), rounded up
SOLVER_ARMS = {'pasmaxsat-c': 'pasmaxsat', 'sgat-nuwls-c': 'sgat', 'aperture-gbg': 'aperture_gbg',
               'nuwls-c-2026-ub': 'nuwls26ub', 'aperture-kbg': 'aperture_kbg', 'aperture-ibi': 'aperture_ibi',
               'deepdist-c': 'deepdistc', 'nuwls-c-2026': 'nuwls26', 'deepdist': 'deepdist',
               'spb-maxsat-c-fps': 'spb', 'nuwls-c-ibr': 'nuwls', 'tt-open-wbo-inc': 'tt', 'aperture': 'aperture'}


def used_seeds(root):
    seen = set()
    for p in Path(root, 'scripts').glob('*.py'):
        seen |= {int(x) for x in re.findall(r'\b(20\d{6})\b', p.read_text())}
    return seen


def fresh_seed(root, batch):
    """The first base 20260000 + 100 * batch + 10 * k + 1 (k = 0..9) such that no script in the tree uses any of
    base .. base + 9 (cells use base + i, the bootstrap base + 9)."""
    if not 0 < batch < 100:
        raise ValueError('batch must be 1..99')
    seen = used_seeds(root)
    for k in range(10):
        base = 20260000 + 100 * batch + 10 * k + 1
        if not set(range(base, base + 10)) & seen:
            return base
    raise RuntimeError(f'no fresh seed block for batch {batch}')


def frozen_configs(root):
    """[(path, kind, config)] of the system's frozen configurations, oldest first (by batch number)."""
    out = []
    for p in Path(root, 'evidence').glob('configure_*_b20r*/config.json'):
        m = re.search(r'b20r(\d+)$', p.parent.name)
        data = json.loads(p.read_text())
        kind = 'tfxw-v1' if 'tfxw' in p.parent.name else 'tfx-v1'
        out.append((int(m.group(1)), str(p.relative_to(root)), kind, data['config']))
    return [x[1:] for x in sorted(out)]


def qet_design(cell_design, plan, root, batch, *, budget=None):
    sizes = sorted(s for s in cell_design.get('sizes', ()) if s > 63)
    if not sizes or not cell_design.get('quality_at_equal_time'):
        raise ValueError('the design does not ask for quality at equal time beyond n = 63')
    cells = []
    for n in sizes:
        cells.append(['planted_cluster', dict(PLANTED, n=n)])
        cells.append(['erdos', {'n': n, 'p': ERDOS_P}])
    per_cell = math.ceil(cell_design.get('hosts', 36) / len(cells))
    longs = sorted(b for b in cell_design.get('long_budgets', ()) if b >= 10) or [10.0]
    b = budget if budget is not None else longs[0]
    frozen = [x for x in frozen_configs(root) if x[1] == 'tfxw-v1']
    if not frozen:
        raise ValueError('no frozen configuration of the large-graph engine')
    path, kind, config = frozen[-1]
    focal = {'arm': 'tfxw', 'kind': kind, 'config': config, 'from': path}
    extra = []
    older = [x for x in frozen_configs(root) if x[0] != path]
    if older:
        p_old, k_old, c_old = older[-1]
        old = dict(c_old, kpick=1) if k_old == 'tfx-v1' else dict(c_old)
        if old != config:
            extra.append({'arm': 'previous_generation', 'kind': 'tfxw-v1', 'config': old, 'from': p_old})
    already_off = []
    if cell_design.get('ablation'):
        from ..candidate_kinds import tfxw as TW
        variants = [(name, dict(config, **change), f'{path} with {change}') for name, change in ABLATIONS]
        variants.append(('first_design', dict(TW.DEFAULT), 'tfxw-v1 DEFAULT'))
        for name, cfg, src in variants:
            if cfg == config:
                already_off.append(name)
            elif all(cfg != e['config'] for e in extra):
                extra.append({'arm': name, 'kind': 'tfxw-v1', 'config': cfg, 'from': src})
    champions = sorted({SOLVER_ARMS[k] for k in cell_design.get('competitors', ()) if k in SOLVER_ARMS}
                       | set(SOLVER_ARMS.values()))
    champions = [[a, next(k for k, v in SOLVER_ARMS.items() if v == a)] for a in champions]
    probes = []
    for arm, p in sorted((cell_design.get('probes') or {}).items()):
        solver = next((k for k, v in SOLVER_ARMS.items() if v == arm), None)
        if solver:
            probes.append({'arm': f'probe_{arm}', 'solver': solver, 'budget': float(p['budget_s']),
                           'hosts': int(p['hosts'])})
    hosts = per_cell * len(cells)
    looks = sorted({math.ceil(hosts / 3), math.ceil(2 * hosts / 3), hosts})
    seed = fresh_seed(root, batch)
    return {'study': f'B20_R{batch}', 'domain': 'triangle_free_large_v1', 'cells': cells, 'per_cell': per_cell,
            'host_seed': seed, 'focal': focal, 'extra': extra, 'champions': champions, 'budget': float(b),
            'focal_short': [float(b) / 10], 'probes': probes, 'looks': looks, 'alpha': ALPHA, 'delta': DELTA,
            'boot': BOOT, 'boot_seed': seed + 9, 'bound_seconds': 60,
            'later_budgets': [x for x in longs if x != b],
            'decide': ['champions', 'vbs'] + (['extra'] if cell_design.get('ablation') and extra else []),
            'components_already_off': already_off,
            'asked_by': {k: v for k, v in plan.get('chosen', {}).items()}}


def estimate_seconds(design):
    """{'per_host_s', 'first_look_s', 'all_hosts_s'}: budgets plus the measured per-run overhead, a champion's
    encoding, the bound's time limit and the probes (an estimate: the bound often finishes sooner)."""
    b = design['budget']
    own = [b] * (1 + len(design.get('extra', ()))) + list(design.get('focal_short', ()))
    per_host = (sum(x + RUN_OVERHEAD_S for x in own) + len(design['champions']) * (b + ENCODING_S + RUN_OVERHEAD_S)
                + design.get('bound_seconds', 0))
    probes = sum(p['hosts'] * (p['budget'] + ENCODING_S + RUN_OVERHEAD_S) for p in design.get('probes', ()))
    hosts = design['per_cell'] * len(design['cells'])
    return {'per_host_s': round(per_host, 1), 'first_look_s': round(per_host * design['looks'][0] + probes),
            'all_hosts_s': round(per_host * hosts + probes)}


def implementation(design):
    """How this study carries out each response the cell chose: {response: text}."""
    hosts = design['per_cell'] * len(design['cells'])
    extras = [e['arm'] for e in design.get('extra', ())]
    probes = ', '.join(f"{p['arm']} at {p['budget']:g} s on {p['hosts']} hosts" for p in design.get('probes', ()))
    later = ', '.join(f'{x:g} s' for x in design.get('later_budgets', ())) or 'none'
    off = ', '.join(design.get('components_already_off', ())) or 'none'
    return {
        'quality_at_equal_time_on_larger_instances': 'values at equal time on n = '
        + ', '.join(sorted({str(p['n']) for _, p in design['cells']}, key=int)),
        'extend_domain': 'the large domain (triangle_free_large_v1, n <= 1023)',
        'longer_certification': f"a certified bound per host ({design.get('bound_seconds', 0)} s)",
        'upper_bounds': f"a certified bound per host ({design.get('bound_seconds', 0)} s)",
        'probe_at_home_budget': probes or 'no probe',
        'add_home_budgets': f"the {design['budget']:g} s budget here; {later} left for the next study (staged)",
        'sequential_stopping': 'interim looks at ' + ', '.join(map(str, design['looks'])) + ' hosts',
        'resumable_design': 'pauses before the background limit and resumes from its rows',
        'more_hosts': f'{hosts} fresh hosts',
        'dedicated_ablation_with_more_power': (f"extra arms {', '.join(extras)} on every host, and the study does not "
                                               "stop before they are decided; components the focal configuration "
                                               f"already has off: {off}")
        if 'extra' in design.get('decide', ()) else 'not carried out by this study (no ablation arm)',
    }


TEMPLATE = '''#!/usr/bin/env python3
"""{study}: {title} (DEV, preregistered; written by genesis.autonomy.studygen from the adaptation cell's design)

    taskset -c 0 python3 {script} OUT_DIR      run alone (resumable; pauses before the background limit)

**Why (the adaptation cell's reasons).** {why}

**Design (fixed before running).** DESIGN below: {n_hosts} fresh hosts in the large domain ({cells}), every arm in the
runc sandbox through `candidates_large`; the system's method ({focal_kind}, `{focal_from}`) at {budget:g} s and at
{short} s; {n_champ} champions at {budget:g} s (`maxsat-anytime-large-v1`: each solver's budget starts after the
encoding); extra arms {extra}; probes {probes}. The analysis, labels, validity rule and stopping rule are
`genesis.autonomy.qet`'s (its docstring): the MaxSAT Evaluation 2026 anytime score against each host's best known value,
paired bootstrap of mean score differences at level 1 - {alpha} / {n_looks} at each look ({looks} hosts), margin
{delta}; a certified bound per host (the better of a clique packing and a triangle packing; {bound} s). The study stops at the first look where the
comparisons named in `decide` ({decide}) are decided. Budgets left for a later study: {later}. **Cost (estimate):** about
{per_host:g} s per host; about {first_look} s if it stops at the first look, {all_hosts} s if it runs every host.

**Expectation, stated before running.** {expectation}
{disclosure}
**What it decides.** Nothing about packages, rules or comparators. **Status.** A DEV diagnostic; licenses nothing.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.autonomy import qet  # noqa: E402

DESIGN = {design}


def main(argv=None):
    argv = argv or sys.argv[1:]
    return qet.main(DESIGN, Path(argv[0]), ROOT)


if __name__ == '__main__':
    sys.exit(main())
'''


def write_script(design, path, *, title, why, expectation, disclosure=None):
    text = TEMPLATE.format(
        study=design['study'], title=title, script=f'scripts/{Path(path).name}', why=why,
        n_hosts=design['per_cell'] * len(design['cells']),
        cells=', '.join(f"{f} n{p['n']}" for f, p in design['cells']), focal_kind=design['focal']['kind'],
        focal_from=design['focal']['from'], budget=design['budget'], short=', '.join(f'{s:g}' for s in
                                                                                     design['focal_short']),
        n_champ=len(design['champions']), extra=', '.join(e['arm'] for e in design['extra']) or 'none',
        probes=', '.join(f"{p['arm']} {p['budget']:g} s on {p['hosts']} hosts" for p in design['probes']) or 'none',
        alpha=design['alpha'], n_looks=len(design['looks']), looks=', '.join(map(str, design['looks'])),
        delta=design['delta'], bound=design['bound_seconds'],
        later=', '.join(f'{b:g} s' for b in design['later_budgets']) or 'none', expectation=expectation,
        disclosure=f'\n**Disclosed before running.** {disclosure}\n' if disclosure else '',
        decide=', '.join(design.get('decide', ('champions', 'vbs'))),
        **{k[:-2]: v for k, v in estimate_seconds(design).items()},
        design=pprint.pformat(design, width=110, sort_dicts=True))
    Path(path).write_text(text)
    return text
