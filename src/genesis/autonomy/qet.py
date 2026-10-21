"""The generic quality-at-equal-time study (B20_R96): who finds the better answer within the same budget.

A study is a DESIGN (a dict, embedded in its preregistered script by `studygen`):
  study            batch name, e.g. 'B20_R97'
  cells            [[family, params], ...] in the large domain; per_cell hosts each; host_seed (cell i uses seed + i)
  focal            {'arm', 'kind', 'config'}: the system's method (tfxw-v1 or tfxw-v2)
  extra            [{'arm', 'kind', 'config'}]: further configurations of the system's method (ablations, the previous
                   generation), compared with the focal one
  champions        [[arm, solver], ...] for `maxsat-anytime-large-v1`
  budget           the main budget (CPU s for the system's method; wall s from the end of encoding for the champions)
  focal_short      shorter budgets at which the focal method also runs (e.g. a tenth of the main one)
  probes           [{'arm', 'solver', 'budget', 'hosts'}]: champions run once at a home budget on the first hosts
  looks            host counts at which the preregistered interim analyses happen (the last is every host)
  alpha, delta     family-wise error over the looks (Bonferroni) and the equivalence margin of the anytime score
  boot, boot_seed  bootstrap resamples and seed
  bound_seconds    time for the certified clique-packing bound per host (0: none)

Rows (one per host, written as each finishes; the study resumes from them): every arm's value, run status and metered
CPU at every budget it runs; probes; the host's best known value (the best of every run); the certified upper bound and
its certificate's digest.

Analysis at each look, on the hosts so far: per host and arm the MaxSAT Evaluation 2026 anytime score
(best known cost + 1) / (cost + 1) (`genesis.anytime`), and the paired bootstrap of the mean score difference, focal
minus other, at level 1 - alpha / len(looks), against the margin delta:
  * `qet_champions`: FOCAL_BETTER_THAN_EVERY_CHAMPION (A_BETTER against all), A_CHAMPION_BETTER (any B_BETTER),
    FOCAL_MATCHES_CHAMPIONS (all EQUIVALENT), MIXED;
  * `qet_vbs`: against the per-host best champion value: FOCAL_BETTER_THAN_VBS, VBS_BETTER, FOCAL_MATCHES_VBS,
    UNRESOLVED;
  * `short_vs_vbs_<b>`: the focal method at a shorter budget b against the champions' VBS at the main budget, the same
    four labels;
  * `extra_<arm>`: the focal method against each extra configuration: HELPS (focal better), HURTS, NO_MEASURABLE_EFFECT
    (equivalent), UNRESOLVED;
  * `probe_<arm>`: RESPONDS if the probed champion reaches 95% of the best known value on at least half the probed
    hosts at its home budget, else NO_RESPONSE.
The study stops at the first look where every focal-versus-champion comparison and the VBS comparison are decided
(better, worse or equivalent). Validity first: INVALID_CPU_DELIVERY if some arm's median metered CPU at the main budget
is below 0.9 of it (the champions' encoding time comes on top, so theirs is higher), INVALID_FAILURES if some arm's
share of failed runs exceeds 1%; then every label is the invalidity.
"""
import json
from pathlib import Path
import statistics
import sys
import time

from .. import anytime as AT
from ..common import canonical, digest

LARGE = 'triangle_free_large_v1'
PAUSED = 3


def large_exposure(root):
    """Identities of every large-domain host recorded under evidence/."""
    from ..domains import adapter
    from ..models_large import LargeGraphTask
    a = adapter(LARGE)
    seen = set()
    for p in sorted(Path(root, 'evidence').glob('*/hosts.json')):
        try:
            data = json.loads(p.read_text())
        except ValueError:
            continue
        for t in data.get('tasks', []) if isinstance(data, dict) else []:
            if isinstance(t, dict) and t.get('domain') == LARGE:
                seen.add(a.exposure_identity(LargeGraphTask.model_validate_json(canonical(t)))['canonical'])
    return seen


def hosts(design, out, root, log):
    from ..domains import adapter
    from ..models_large import LargeGraphTask
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [LargeGraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    excluded = large_exposure(root)
    log(f'large-domain exposure: {len(excluded)} identities excluded')
    a = adapter(LARGE)
    by_cell, seen = [], set(excluded)
    for ci, (fam, params) in enumerate(design['cells']):
        tasks, seen, _ = a.generate(design['host_seed'] + ci, design['per_cell'], 'DEV', fam, params, excluded=seen)
        by_cell.append(tasks)
    order = [by_cell[c][i] for i in range(design['per_cell']) for c in range(len(design['cells']))]
    path.write_text(json.dumps({'study': design['study'], 'cells': design['cells'], 'per_cell': design['per_cell'],
                                'host_seed': design['host_seed'], 'excluded_identities': len(excluded),
                                'tasks': [t.model_dump(mode='json') for t in order]}, indent=1, sort_keys=True) + '\n')
    return order


def descriptors(design):
    from .. import candidates_large as CL
    from ..candidate_kinds import maxsat_large as ML
    D = {}
    systems = [design['focal']] + list(design.get('extra', ()))
    for a in systems:
        budgets = [design['budget']] + (list(design.get('focal_short', ())) if a is design['focal'] else [])
        for b in budgets:
            D[(a['arm'], b)] = CL.build_descriptor(a['kind'], {'cpu_seconds': b, 'config': a['config']},
                                                   cpu_seconds=b, wall_seconds=max(30, int(3 * b) + 30))
    for arm, solver in design['champions']:
        b = design['budget']
        D[(arm, b)] = CL.build_descriptor('maxsat-anytime-large-v1', {'solver': solver, 'cpu_seconds': b},
                                          cpu_seconds=b + ML.ENCODING_ALLOWANCE_S,
                                          wall_seconds=max(60, int(3 * b) + 60))
    for p in design.get('probes', ()):
        D[(p['arm'], p['budget'])] = CL.build_descriptor(
            'maxsat-anytime-large-v1', {'solver': p['solver'], 'cpu_seconds': p['budget']},
            cpu_seconds=p['budget'] + ML.ENCODING_ALLOWANCE_S, wall_seconds=max(60, int(3 * p['budget']) + 60))
    return D


def run_seed(design, task_id, arm, budget):
    return int(digest({'study': design['study'], 'task': task_id, 'arm': arm, 'budget': budget})[:12], 16)


def _value(receipt):
    if receipt.get('status') == 'SUCCESS':
        return receipt['result']['value'], 'SUCCESS'
    return None, receipt.get('status', 'FAILED')


def run_host(design, task, D, *, isolation='runc', with_probe=False):
    from .. import candidates_large as CL
    runs = {}
    for (arm, b), desc in D.items():
        if any(p['arm'] == arm for p in design.get('probes', ())):
            continue
        r = CL.run(task, desc, seed=run_seed(design, task.task_id, arm, b), isolation=isolation)
        v, st = _value(r)
        runs.setdefault(arm, {})[f'{b:g}'] = {'value': v, 'run': st, 'cpu_ns': r.get('cpu_ns')}
    probes = {}
    if with_probe:
        for p in design.get('probes', ()):
            r = CL.run(task, D[(p['arm'], p['budget'])], seed=run_seed(design, task.task_id, p['arm'], p['budget']),
                       isolation=isolation)
            v, st = _value(r)
            probes[p['arm']] = {'budget_s': p['budget'], 'value': v, 'run': st, 'cpu_ns': r.get('cpu_ns')}
    vals = [x['value'] for a in runs.values() for x in a.values() if x['value'] is not None]
    vals += [x['value'] for x in probes.values() if x['value'] is not None]
    row = {'task_id': task.task_id, 'family': task.family.split(':')[0], 'n': task.n, 'edges': len(task.edges),
           'runs': runs, 'probes': probes, 'best_value': max(vals) if vals else None}
    if design.get('bound_seconds'):
        from ..bounds_large import best_bound
        cert = best_bound(task, seconds=design['bound_seconds'], seed=run_seed(design, task.task_id, 'bound', 0))
        row['upper'] = {'value': cert['upper'], 'method': cert['method'],
                        'certificate_sha256': digest(cert['certificate'])}
        if row['best_value'] is not None and row['best_value'] > cert['upper']:
            raise RuntimeError('a value above the certified bound: the bound or a checker is wrong')
    return row


# ------------------------------------------------------------------------------------------------- analysis

def _scores(rows, arm, budget):
    out = []
    for r in rows:
        best = r['best_value']
        x = r['runs'].get(arm, {}).get(f'{budget:g}')
        v = x['value'] if x else None
        out.append(AT.score(r['edges'] - best, None if v is None else r['edges'] - v))
    return out


def _vbs_scores(rows, design):
    out = []
    for r in rows:
        vals = [r['runs'][a][f"{design['budget']:g}"]['value'] for a, _ in design['champions']
                if r['runs'].get(a, {}).get(f"{design['budget']:g}", {}).get('value') is not None]
        out.append(AT.score(r['edges'] - r['best_value'], (r['edges'] - max(vals)) if vals else None))
    return out


def _four(v, better, worse, match, other):
    return {'A_BETTER': better, 'B_BETTER': worse, 'EQUIVALENT': match}.get(v, other)


def analyse(rows, design, level):
    focal, b = design['focal']['arm'], design['budget']
    kw = {'level': level, 'resamples': design['boot'], 'seed': design['boot_seed']}
    f = _scores(rows, focal, b)
    comps = {a: AT.compare(f, _scores(rows, a, b), design['delta'], **kw) for a, _ in design['champions']}
    vs = [c['verdict'] for c in comps.values()]
    if all(v == 'A_BETTER' for v in vs):
        lab = 'FOCAL_BETTER_THAN_EVERY_CHAMPION'
    elif 'B_BETTER' in vs:
        lab = 'A_CHAMPION_BETTER'
    elif all(v == 'EQUIVALENT' for v in vs):
        lab = 'FOCAL_MATCHES_CHAMPIONS'
    else:
        lab = 'MIXED'
    vbs = AT.compare(f, _vbs_scores(rows, design), design['delta'], **kw)
    labels = {'qet_champions': lab,
              'qet_vbs': _four(vbs['verdict'], 'FOCAL_BETTER_THAN_VBS', 'VBS_BETTER', 'FOCAL_MATCHES_VBS',
                               'UNRESOLVED')}
    short = {}
    for s in design.get('focal_short', ()):
        c = AT.compare(_scores(rows, focal, s), _vbs_scores(rows, design), design['delta'], **kw)
        short[f'{s:g}'] = c
        labels[f'short_vs_vbs_{s:g}'] = _four(c['verdict'], 'FOCAL_BETTER_THAN_VBS', 'VBS_BETTER',
                                              'FOCAL_MATCHES_VBS', 'UNRESOLVED')
    extra = {}
    for e in design.get('extra', ()):
        c = AT.compare(f, _scores(rows, e['arm'], b), design['delta'], **kw)
        extra[e['arm']] = c
        labels[f"extra_{e['arm']}"] = _four(c['verdict'], 'HELPS', 'HURTS', 'NO_MEASURABLE_EFFECT', 'UNRESOLVED')
    for p in design.get('probes', ()):
        probed = [r for r in rows if p['arm'] in r.get('probes', {})]
        ok = [r for r in probed if r['probes'][p['arm']]['value'] is not None
              and r['probes'][p['arm']]['value'] >= 0.95 * r['best_value']]
        key = p['arm'] if p['arm'].startswith('probe_') else f"probe_{p['arm']}"
        labels[key] = 'RESPONDS' if probed and len(ok) * 2 >= len(probed) else 'NO_RESPONSE'
    decided = all(v in ('A_BETTER', 'B_BETTER', 'EQUIVALENT') for v in vs + [vbs['verdict']])
    wins = sum(1 for r in rows
               if r['runs'][focal][f'{b:g}']['value'] is not None
               and all((r['runs'][a][f'{b:g}']['value'] or -1) < r['runs'][focal][f'{b:g}']['value']
                       for a, _ in design['champions']))
    return labels, {'champions': comps, 'vbs': vbs, 'short': short, 'extra': extra, 'decided': decided,
                    'hosts': len(rows), 'focal_strictly_best_hosts': wins,
                    'mean_scores': {a: round(statistics.mean(_scores(rows, a, b)), 6)
                                    for a in [focal] + [x for x, _ in design['champions']]
                                    + [e['arm'] for e in design.get('extra', ())]},
                    'vbs_mean_score': round(statistics.mean(_vbs_scores(rows, design)), 6)}


def validity(rows, design):
    b = design['budget']
    arms = [design['focal']['arm']] + [e['arm'] for e in design.get('extra', ())] + [a for a, _ in design['champions']]
    cpu, fail = {}, {}
    for a in arms:
        xs = [r['runs'][a][f'{b:g}'] for r in rows]
        c = [x['cpu_ns'] / 1e9 for x in xs if x.get('cpu_ns') is not None and x['run'] == 'SUCCESS']
        cpu[a] = statistics.median(c) if c else 0.0
        allx = [x for r in rows for x in r['runs'][a].values()]
        fail[a] = sum(x['run'] != 'SUCCESS' for x in allx) / len(allx) if allx else 0.0
    if any(v < 0.9 * b for v in cpu.values()):
        return 'INVALID_CPU_DELIVERY', cpu, fail
    if any(v > 0.01 for v in fail.values()):
        return 'INVALID_FAILURES', cpu, fail
    return None, cpu, fail


# ------------------------------------------------------------------------------------------------- run

def main(design, out, root, *, slice_s=6600, isolation='runc', one_core=True):
    """Run (or resume) the study into `out`; returns 0 when finished, PAUSED (3) when the time slice ran out."""
    from ..candidate_kinds import tfxw as TW
    from ..common import code_identity
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    import os
    cores = os.sched_getaffinity(0)
    if one_core and len(cores) != 1:
        raise SystemExit(f'the study must run on one core, not {sorted(cores)}')
    log(f'pinned to CPU {min(cores)}; design sha256 {digest(design)[:16]}; tfxw {TW.binary_digest()[:16]}')
    D = descriptors(design)
    tasks = hosts(design, out, root, log)
    path = out / 'rows.jsonl'
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    looks = list(design['looks'])
    level = AT.look_level(design['alpha'], len(looks))
    looked = {json.loads(l)['hosts'] for l in (out / 'looks.jsonl').read_text().splitlines() if l.strip()} \
        if (out / 'looks.jsonl').exists() else set()
    stopped = None
    for i, task in enumerate(tasks):
        if i < len(rows):
            continue
        if time.monotonic() - t0 > slice_s:
            log(f'time slice used ({slice_s} s): paused after {len(rows)} hosts')
            return PAUSED
        probe = i < max((p['hosts'] for p in design.get('probes', ())), default=0)
        row = run_host(design, task, D, isolation=isolation, with_probe=probe)
        rows.append(row)
        with path.open('a') as fh:
            fh.write(json.dumps(row, sort_keys=True) + '\n')
        b = f"{design['budget']:g}"
        log(f"host {i} {task.task_id} ({task.n} vertices, {len(task.edges)} edges): best {row['best_value']}"
            + (f", bound {row['upper']['value']}" if 'upper' in row else '') + ' | '
            + ' '.join(f"{a} {row['runs'][a][b]['value']}" for a in row['runs'] if b in row['runs'][a]))
        if len(rows) in looks and len(rows) not in looked:
            labels, detail = analyse(rows, design, level)
            with (out / 'looks.jsonl').open('a') as fh:
                fh.write(json.dumps({'hosts': len(rows), 'labels': labels, 'decided': detail['decided']},
                                    sort_keys=True) + '\n')
            looked.add(len(rows))
            log(f'look at {len(rows)} hosts: {labels}; decided {detail["decided"]}')
            if detail['decided']:
                stopped = len(rows)
                break
    invalid, cpu, fail = validity(rows, design)
    labels, detail = analyse(rows, design, level)
    if invalid:
        labels = {k: invalid for k in labels}
    summary = {'schema': 'genesis-qet-study-v1', 'study': design['study'], 'design': design,
               'design_sha256': digest(design), 'labels': labels, 'detail': detail, 'level': level,
               'stopped_at': stopped, 'hosts_run': len(rows),
               'validity': {'cpu_s_median_at_budget': {k: round(v, 3) for k, v in cpu.items()},
                            'failure_share': {k: round(v, 5) for k, v in fail.items()}},
               'descriptors': {f'{a}@{b:g}': d['descriptor_id'] for (a, b), d in D.items()},
               'code_identity': code_identity(root)['sha256'],
               'status': 'DEV comparison; licenses nothing; no package changed'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'labels {labels}')
    return 0


if __name__ == '__main__':
    sys.exit('run a study through its preregistered script')
