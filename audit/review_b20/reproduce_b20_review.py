#!/usr/bin/env python3
"""Read-only reproduction of the four B20 review findings (H01).

    python3 audit/review_b20/reproduce_b20_review.py [--out audit/review_b20/findings.json]

Inspects the stored B20/B19 evidence only. No prover, solver or network is used, and no
evidence file is modified. Each finding is reported as REPRODUCED or NOT_REPRODUCED with
the exact records it rests on, so the original observations stay citable after repair.

  B20-REVIEW-01  evaluation statements that also occur in training development material
                 (global holdout property false for those records)
  B20-REVIEW-02  research CPU above the nominal campaign cap (budget enforcement/accounting)
  B20-REVIEW-03  Lean replay coverage of reported successor scores
  B20-REVIEW-04  B19 joint upper bounds exported without witness or exact LP certificate
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
B20 = ROOT / 'evidence' / 'learning_b20'
B19 = ROOT / 'evidence' / 'discovery_b19'
TRAIN_SEEDS = (101, 102, 103)
EVAL_SEEDS = (201, 202, 203, 204)


def _load(p):
    return json.loads(p.read_text())


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def review_01():
    material = _load(B20 / 'setup.json')['material']
    overlaps = []
    for key, data in sorted(material.items()):
        system, seed = key.rsplit('@', 1)
        if int(seed) not in EVAL_SEEDS:
            continue
        for i, target in enumerate(data['eval']):
            for tkey, tdata in sorted(material.items()):
                tsys, tseed = tkey.rsplit('@', 1)
                if tsys != system or int(tseed) not in TRAIN_SEEDS:
                    continue
                for j, dev in enumerate(tdata['dev']):
                    if dev == target:
                        overlaps.append({'system': system, 'eval_seed': int(seed), 'eval_index': i,
                                         'training_seed': int(tseed), 'dev_index': j, 'statement': target,
                                         'eval_location': f'setup.json material[{key!r}].eval[{i}]',
                                         'training_location': f'setup.json material[{tkey!r}].dev[{j}]'})
    unique = sorted({o['statement'] for o in overlaps})
    slots = sorted({(o['system'], o['eval_seed'], o['eval_index']) for o in overlaps})
    expected = {('ba_huntington', 201): 1, ('ba_huntington', 203): 1, ('ba_huntington', 204): 2}
    got = {}
    for s, seed, _ in slots:
        got[(s, seed)] = got.get((s, seed), 0) + 1
    return {'finding': 'B20-REVIEW-01', 'title': 'evaluation statements visible in training development material',
            'status': 'REPRODUCED' if overlaps else 'NOT_REPRODUCED',
            'matches_review_statement': got == expected and len(unique) == 3,
            'evaluation_slots': len(slots), 'unique_statements': len(unique), 'overlaps': overlaps,
            'root_cause': 'scripts/b20_learning.py::material samples eval with exclude=pool+dev of the same seed '
                          'only; training dev targets of other seeds are not excluded',
            'comparison': 'exact TPTP text equality (the canonical form the script stores); no renaming or '
                          'instance screening was needed to find these',
            'sources': {'setup.json': _sha(B20 / 'setup.json')}}


def review_02():
    cal = _load(B20 / 'calibration.json')
    rows = _load(B20 / 'w19' / 'rows.json')
    out = []
    for r in rows:
        cap = cal[r['system']]['budget_s']
        out.append({'system': r['system'], 'seed': r['seed'], 'policy': r['policy'], 'cap_s': cap,
                    'research_cpu_s': r['research_cpu_s'], 'over_cap_s': round(r['research_cpu_s'] - cap, 2),
                    'ratio': round(r['research_cpu_s'] / cap, 3), 'successor_proved': r['successor_proved'],
                    'targets': r['targets']})
    over = [o for o in out if o['research_cpu_s'] > o['cap_s']]
    h204 = {o['policy']: (o['research_cpu_s'], o['successor_proved']) for o in out
            if o['system'] == 'ba_huntington' and o['seed'] == 204}
    by_system = {}
    for o in out:
        b = by_system.setdefault(o['system'], {'runs': 0, 'over_cap': 0, 'max_ratio': 0.0})
        b['runs'] += 1
        b['over_cap'] += o['research_cpu_s'] > o['cap_s']
        b['max_ratio'] = max(b['max_ratio'], o['ratio'])
    return {'finding': 'B20-REVIEW-02', 'title': 'research CPU above the nominal campaign cap',
            'status': 'REPRODUCED' if over else 'NOT_REPRODUCED',
            'matches_review_statement': h204.get('fixed') == (1.01, 24) and h204.get('learned') == (1.93, 25),
            'huntington_204': h204, 'runs': len(out), 'runs_over_cap': len(over), 'by_system': by_system,
            'additional_observation': 'every ba_sheffer run (cap 1.57 s) also exceeds its cap, by up to 63%; the '
                                      'review named the Huntington seed-204 case, the same mechanism applies to all',
            'root_cause': ['learning/research.py::run starts the CPU clock after policy.reset (preparation uncharged)',
                           'the cap is checked before action selection, so the last action may start with any '
                           'positive remainder',
                           'the per-attempt E limit is max(1, ceil(remaining)) s: a fractional remainder is rounded '
                           'up to at least one whole second of prover CPU',
                           'a PROVED result is accepted even when it finished after the cap'],
            'rows': out, 'sources': {'calibration.json': _sha(B20 / 'calibration.json'),
                                     'w19/rows.json': _sha(B20 / 'w19' / 'rows.json')},
            'caution': 'which timing difference caused which proof is not asserted'}


def review_03():
    rows = _load(B20 / 'w19' / 'rows.json')
    lean = _load(B20 / 'lean' / 'replays.json')
    reported = sum(r['successor_proved'] for r in rows)
    reported_fl_201 = sum(r['successor_proved'] for r in rows if r['seed'] == EVAL_SEEDS[0]
                          and r['policy'] in ('fixed', 'learned'))
    checked = sum(r['status'] == 'THEOREM_CHECKED' for r in lean)
    statuses = {}
    for r in lean:
        statuses[r['status']] = statuses.get(r['status'], 0) + 1
    scope = sorted({(r['system'], r['policy']) for r in lean})
    return {'finding': 'B20-REVIEW-03', 'title': 'Lean replay covers a subset of reported successor scores',
            'status': 'REPRODUCED' if checked < reported else 'NOT_REPRODUCED',
            'matches_review_statement': len(lean) == 68 and checked == 67,
            'replay_attempts': len(lean), 'replay_statuses': statuses,
            'replayed_scope': {'seed': EVAL_SEEDS[0], 'system_policy': [list(x) for x in scope],
                               'targets': 'successful target proofs that used at least one library lemma'},
            'reported_successes_all_runs': reported,
            'reported_successes_fixed_learned_seed_201': reported_fl_201,
            'checked_fraction_of_all_reported': round(checked / reported, 4),
            'not_covered': ['proofs from axioms only (no library lemma)', 'random, heuristic and bandit policies',
                            'evaluation seeds 202-204', 'empty-library baselines', 'W18/W20 arms and follow-ups'],
            'persistence_gap': 'proof objects of scored targets are not stored in the evidence (w19/rows.json keeps '
                               'counts only), so the uncovered scores cannot be replayed retroactively',
            'sources': {'w19/rows.json': _sha(B20 / 'w19' / 'rows.json'),
                        'lean/replays.json': _sha(B20 / 'lean' / 'replays.json')}}


def review_04():
    ev = _load(B19 / 'obstruction' / 'evaluation.json')
    rows = ev['rows']
    methods = {}
    missing = []
    for r in rows:
        j = r['joint']
        methods[j['upper_method']] = methods.get(j['upper_method'], 0) + 1
        absent = [k for k in ('witness', 'certificate', 'upper_certificate', 'cnf_sha256', 'proof_sha256')
                  if k not in j]
        missing.append({'task_id': r['task_id'], 'status': j['status'], 'lower': j['lower'], 'upper': j['upper'],
                        'upper_method': j['upper_method'], 'lp_certificate_recheck': j.get('lp_certificate_recheck'),
                        'fields_absent': absent})
    closed = sum(r['joint']['status'] == 'OPTIMALITY_CHECKED' for r in rows)
    lp = sum(r['joint']['upper_method'] == 'LP_DUAL_EXACT' for r in rows)
    no_witness = sum('witness' not in r['joint'] for r in rows)
    no_cert = sum('certificate' not in r['joint'] for r in rows)
    return {'finding': 'B20-REVIEW-04', 'title': 'B19 joint bounds exported without witness or exact LP certificate',
            'status': 'REPRODUCED' if no_witness or no_cert else 'NOT_REPRODUCED',
            'matches_review_statement': len(rows) == 12 and lp == 12 and closed == 11,
            'rows': len(rows), 'upper_methods': methods, 'optimality_checked': closed,
            'rows_without_witness': no_witness, 'rows_without_certificate': no_cert, 'per_row': missing,
            'source_defect': ['discovery/obstruction.py::certify returns the certificate in memory only; '
                              'scripts/b19_discovery.py::phase_obstruction exports bounds and verdict summaries',
                              'the SAT fallback discards the CNF and DRAT bytes returned by certify_upper '
                              '(cert, rec, _, _ = ...); it did not supply any of these 12 upper bounds'],
            'consequence': 'OPTIMALITY_CHECKED in this file cannot be replayed from artifacts; the recorded '
                           'observation stays as history and a custody-complete re-run is a new execution',
            'sources': {'obstruction/evaluation.json': _sha(B19 / 'obstruction' / 'evaluation.json')}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=Path(__file__).with_name('findings.json'))
    a = ap.parse_args(argv)
    findings = [review_01(), review_02(), review_03(), review_04()]
    report = {'schema': 'genesis-review-reproduction-v1', 'baseline_commit': '97fb23336a0a6c940193625bcc0091888b413cf2',
              'baseline_archive_sha256': '44bbbbeb1b8781203af8b3489b7c1a396d7694806232193dce9e7fee46f12091',
              'method': 'read-only inspection of stored evidence; no prover invoked', 'findings': findings}
    a.out.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    for f in findings:
        print(f"{f['finding']}: {f['status']} (matches review: {f['matches_review_statement']})")
    return 0 if all(f['status'] == 'REPRODUCED' for f in findings) else 1


if __name__ == '__main__':
    sys.exit(main())
