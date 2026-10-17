"""B20_R62: power analyses bound to the custodian's families, and sizing at 10,000 simulations (B19-OPEN-4).

**Why.** The statistician's brief (B20_R61) found two things the builder can prepare, though not adopt:
  1. Four causal power analyses (E1b's ablation and placebo, B20_R28; E1b-C4's, B20_R50) are bound to the plan
     core of the `sealed_evaluation` family. The custodian assigns `<evidence kind>:<domain>` and refuses any
     other family at registration (`custody_records.registration_problems`), and a power analysis is bound to
     its plan core. These follow-ups cannot be registered with their current sample-size justification.
  2. Sizes are chosen from 1,000 simulations. Two chosen powers sit within two Monte Carlo standard errors of the
     0.8 target, and E1b-C4's placebo falls to 0.764 at its chosen size when re-simulated with 10,000.

**What this produces** (`evidence/power_rebind_b20r62/`). Nothing in the packages changes; a freeze authorised by
the reviewer would take these files in.
  * `power_analysis_centred_<analysis>_<family>.json`: for each of the four mismatched analyses, the power
    analysis recomputed exactly as registered (`required_sample`, 1,000 simulations, floor 10, centred
    headroom) under the family the custodian assigns.
  * `power_analysis_centred_<analysis>_<family>_10k.json`: for all nine analyses of the brief, the same under
    the assigned family with 10,000 simulations.
  * `summary.json`: per analysis, the stored, rebound and 10,000-simulation choices side by side.

**Rule for reading it** (fixed here, before running): a package's size CHANGES if the 10,000-simulation choice
under the assigned family differs from the stored choice. The builder's proposal for the statistician is to size
with 10,000 simulations; whether to adopt that is the statistician's (brief, question 2).

`python3 scripts/b20r62_power_rebind.py` writes the directory (about 4 minutes on one core).
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r61_statistician_brief as S  # noqa: E402
from genesis.power import required_sample  # noqa: E402

OUT = ROOT / 'evidence' / 'power_rebind_b20r62'
FINE = 10_000


def slug(name):
    return name.lower().replace(' ', '_').replace('-', '_')


def fine(a):
    _, _, _, _, domain, kind, _ = a
    return required_sample(S.pilot_rows(a), S.plan(domain, kind), sims=FINE, min_tasks_per_stratum=10,
                           headroom='centred')


def _choice(d):
    c = d['chosen']
    return None if c is None else {'tasks_per_stratum': c['tasks_per_stratum'], 'total_tasks': c['total_tasks'],
                                   'power': c['power']}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for a in S.ANALYSES:
        name, stored_rel, _, _, domain, kind, _ = a
        stored = S._load(stored_rel)
        bound, assigned = S.family_check(a)
        row = {'analysis': name, 'stored': stored_rel, 'stored_family': bound, 'assigned_family': assigned,
               'stored_choice': _choice(stored)}
        if bound != assigned:
            rb = S.recompute(a, assigned)
            f = OUT / f'power_analysis_centred_{slug(name)}_{assigned}.json'
            f.write_text(json.dumps(rb, indent=1, sort_keys=True) + '\n')
            row.update(rebound=str(f.relative_to(ROOT)), rebound_choice=_choice(rb))
        fd = fine(a)
        f = OUT / f'power_analysis_centred_{slug(name)}_{assigned}_10k.json'
        f.write_text(json.dumps(fd, indent=1, sort_keys=True) + '\n')
        row.update(fine=str(f.relative_to(ROOT)), fine_choice=_choice(fd),
                   fine_power_at_mue=fd['power_at_minimum_useful_effect'],
                   fine_rate_at_zero=fd['false_positive_rate_at_zero_effect'])
        row['size_changes'] = row['fine_choice']['tasks_per_stratum'] != row['stored_choice']['tasks_per_stratum']
        rows.append(row)
        print(json.dumps(row), flush=True)
    summary = {'schema': 'genesis-b20r62-power-rebind-v1', 'sims_registered': S.SIMS, 'sims_fine': FINE,
               'target': S.TARGET, 'analyses': rows,
               'changes': [r['analysis'] for r in rows if r['size_changes']],
               'status': 'DEV recomputation for the statistician; nothing adopted, packages unchanged'}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return summary


if __name__ == '__main__':
    run()
