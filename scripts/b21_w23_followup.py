#!/usr/bin/env python3
"""B21 / W23 follow-up: a larger fault-injection sample and expert-budget sweep, DEV only.

  b21_w23_followup.py OUT_DIR               (writes OUT_DIR/w23_followup.json)

Written after the main run, where only 2 items qualified (lemmas whose library proof used
no earlier lemma), so each fault kind was injected twice. Rules fixed here before running:
  * items: true Sheffer equations (pool of size 4, seed 710) that E proves from the axioms
    alone in 1 s, shuffled with seed 710; the first 8. Each gets a false partner equation;
  * every item is checked clean (true, and its false partner) and with each injected fault
    (corrupted proof, another item's proof, the proof offered for a false claim, a flipped
    decider), through all four routes; false acceptance as in the main run: ACCEPTED for
    anything but a clean true claim or a true claim whose only fault is the decider;
  * expert sweep on Wolfram's axiom: 16 true + 8 false claims (seeds 711, 712), prover 1 s,
    countermodels up to size 2, decider withheld; SIMULATED experts with error rates 0.1
    and 0.3 (seeds 713, 714) under budgets of 0, 4, 8 and 16 questions. The expert is the
    decider flipped at the error rate: labelled SIMULATED, not evidence about real experts.
"""
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import faults as FT  # noqa: E402
from genesis.verification.eprover import prove  # noqa: E402

RULES = {'items_system': 'ba_sheffer', 'items_seed': 710, 'items': 8, 'item_prove_s': 1,
         'expert_system': 'ba_wolfram', 'true_claims': 16, 'false_claims': 8, 'claim_seeds': [711, 712],
         'expert_errors': {'0.1': 713, '0.3': 714}, 'budgets': [0, 4, 8, 16], 'prove_s': 1, 'model_size': 2,
         'model_s': 2}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    path = out / 'w23_followup.json'
    if path.exists():
        raise FileExistsError(path)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    rng = random.Random(RULES['items_seed'])
    sysname = RULES['items_system']
    ax = Q.axioms(sysname)
    pool = Q.true_equations(sysname, 4, per_bucket=4, seed=RULES['items_seed'])
    rng.shuffle(pool)
    items = []
    for eq in pool:
        r = prove(ax, Q.closed(eq), seconds=RULES['item_prove_s'])
        if r['status'] == 'THEOREM' and r['proof']:
            items.append({'eq': eq, 'text': Q.text(eq), 'proof': r['proof']})
        if len(items) == RULES['items']:
            break
    falses = Q.false_equations(sysname, 4, len(items), seed=RULES['items_seed'])
    for it, f in zip(items, falses):
        it['false_eq'] = f
        it['decider'] = Q.SYSTEMS[sysname]['decider']
    rows = []

    def record(kind, truth, eq, r):
        d = FT.diagnose(r)
        # the main run's definition: any acceptance except a clean true claim or a true claim
        # whose only fault is the decider counts as false acceptance
        rows.append({'kind': kind, 'truth': truth, 'claim': Q.text(eq),
                     'routes': {k: r[k] for k in ('decider', 'prover', 'kernel', 'countermodel')}, **d,
                     'false_acceptance': d['verdict'] == 'ACCEPTED' and not (truth and kind in
                                                                            ('clean_true', 'decider_flip'))})
    for it in items:
        record('clean_true', True, it['eq'], FT.routes(sysname, it['eq'], proof=it['proof']))
        record('clean_false', False, it['false_eq'], FT.routes(sysname, it['false_eq'], prove_s=1))
        for kind in ('corrupt_proof', 'swapped_proof', 'false_claim_with_proof', 'decider_flip'):
            eq, proof, dec, truth = FT.inject(kind, it, items, rng)
            if proof is None:
                rows.append({'kind': kind, 'truth': truth, 'claim': Q.text(eq), 'verdict': 'NOT_INJECTED',
                             'false_acceptance': False})
                continue
            record(kind, truth, eq, FT.routes(sysname, eq, proof=proof, decider=dec))
        log(f'item {it["text"][:48]}: {[r["verdict"] for r in rows[-6:]]}')
    by = {}
    for r in rows:
        b = by.setdefault(r['kind'], {'n': 0, 'false_acceptance': 0, 'verdicts': {}})
        b['n'] += 1
        b['false_acceptance'] += r['false_acceptance']
        b['verdicts'][r['verdict']] = b['verdicts'].get(r['verdict'], 0) + 1
    # ---------------- expert sweep
    esys = RULES['expert_system']
    s1, s2 = RULES['claim_seeds']
    claims = Q.sample_targets(esys, RULES['true_claims'], min_total=5, max_total=8, seed=s1) + \
        Q.false_equations(esys, 4, RULES['false_claims'], seed=s2)
    routed = []
    for eq in claims:
        r = FT.routes(esys, eq, prove_s=RULES['prove_s'], model_size=RULES['model_size'], model_s=RULES['model_s'],
                      decider=lambda e: True, kernel=False)          # decider withheld
        base = True if r['prover'] == 'THEOREM' else (False if r['countermodel'] == 'FOUND' else None)
        routed.append({'claim': Q.text(eq), 'eq': eq, 'truth': Q.holds(eq, Q.SYSTEMS[esys]['decider']),
                       'prover': r['prover'], 'countermodel': r['countermodel'], 'without_expert': base})
    log(f'expert claims routed: {sum(r["without_expert"] is None for r in routed)} of {len(routed)} undecided')
    sweep = []
    for err, seed in RULES['expert_errors'].items():
        for budget in RULES['budgets']:
            expert = FT.SimulatedExpert(esys, float(err), seed)
            spent, asked, correct, wrong_answers = 0.0, 0, 0, 0
            for r in routed:
                final = r['without_expert']
                if final is None and spent + 1.0 <= budget:
                    q = expert.answer(FT.question(r['claim'], 'prover gave up; no countermodel up to size 2'), r['eq'])
                    spent += q['cost']; asked += 1
                    final = q['answer']
                    wrong_answers += final != r['truth']
                correct += final == r['truth']
            sweep.append({'expert_error': float(err), 'budget': budget, 'questions': asked, 'cost': spent,
                          'correct': correct, 'claims': len(routed), 'wrong_expert_answers': wrong_answers})
            log(f'expert error {err} budget {budget}: {correct}/{len(routed)} correct, {asked} questions')
    record_ = {'rules': RULES, 'rows': rows, 'by_kind': by,
               'false_acceptances': sum(r['false_acceptance'] for r in rows),
               'expert': {'claims': [{k: v for k, v in r.items() if k != 'eq'} for r in routed], 'sweep': sweep,
                          'label': 'SIMULATED expert (the decider flipped at the error rate); '
                                   'not evidence about real experts'},
               'wall_seconds': round(time.monotonic() - t0, 1)}
    path.write_text(json.dumps(record_, indent=1, sort_keys=True, default=str) + '\n')
    log(f'wrote {path}: false acceptances {record_["false_acceptances"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
