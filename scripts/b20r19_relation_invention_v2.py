#!/usr/bin/env python3
"""B20_R19 (s15.3, W10): the versioned k <= 4 expansion of the generated relational decoders.

    b20r19_relation_invention_v2.py OUT_DIR

B20_R17 generated relational decoders over k <= 3 classes. One was outside the menu (the oriented
3-cycle, rel3_011220), Lean-checked, with NO_UTILITY_AFTER_COST on DEV. This is the second attempt in
the same family, and both attempts count:
  * generator version v2 (invention.relations.VERSIONS['v2']): the class bound is lifted to 4, by
    version and with the reason recorded there, and class twins are merged before comparison, so a
    twin-split of a menu decoder is never called NEW;
  * candidates for this step: generated, not equal to a menu decoder, and not already evaluated
    (B20_R17's rel3_011220 is excluded here, whatever it would score);
  * Part A, unchanged from B20_R17: image and triangle-free soundness as Lean statements, screened,
    then proved with relations.recipes; the construction CPU is charged (the larger of getrusage and
    the checker's own report). None checked -> NO_NEW_CHECKED_REPRESENTATION;
  * Part B, the B20_R17 design unchanged except for fresh seeds: S2 (erdos n30 p0.3) and S3 (erdos
    n40 p0.2), SELECT 8 and EVAL 16 hosts per setting with generator seeds 20262201 + 10 i and
    20262202 + 10 i, excluding every triangle-free host named in the B20_R13..RX5 evidence, every E1
    host and every B20_R17 host; every arm 1.0 CPU s per host; arms new / menu (best SELECT total
    among cross_2, ordered_2, adjacent_2, adjacent_3) / conventional (best time-matched DSL program) /
    matched (the chosen menu decoder with 1.0 s + construction / 100 hosts); stratified bootstrap
    (4000 resamples, seed 20262299);
  * verdict: UTILITY_AFTER_COST iff every comparison has mean >= 0.5 edge per host and a 90% interval
    lower bound > 0; otherwise NO_UTILITY_AFTER_COST.
A DEV study: it licenses no claim, its hosts are exposed, and the family now has two attempts.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r17_relation_invention as R17  # noqa: E402
from genesis.common import code_identity  # noqa: E402
from genesis.discovery.construct import Budget  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.invention import relations as RL  # noqa: E402

VERSION, MAX_K = 'v2', 4
EVALUATED_BEFORE = ('rel3_011220',)         # B20_R17
SEEDS = (20262201, 20262202)
BOOT_SEED = 20262299


def part_a(out, log):
    budget = Budget(1e9)
    gen = RL.generate(MAX_K, VERSION)
    props = [RL.proposal(g['k'], g['relation'], VERSION) for g in gen]
    conjs = RL.conjectures(props)
    screened = {c['id']: 'COUNTEREXAMPLE' if L.screen(c)[0] is not None else 'NO_COUNTEREXAMPLE' for c in conjs}
    base = [R17.DEFS, {'name': RL.MODULE, 'source': RL.source(props), 'trusted': True}]
    unfold = ['GT.TriangleFree'] + [f'RL.{p["id"]}' for p in props]
    state = L.prove_all(conjs, base_modules=base, conj_name='RLConj', proof_prefix='RLP', unfold=unfold,
                        extra_recipes=RL.recipes(props), log=log)
    st = {s['id']: s for s in state['statements']}
    records = []
    for g, p in zip(gen, props):
        records.append(dict(R17.public(p), equals_menu=g['equals_menu'], enumerated_at_k=g['enumerated_at_k'],
                            evaluated_before=p['id'] in EVALUATED_BEFORE,
                            screen={k: screened[f'{p["id"]}_{k}'] for k in ('image', 'sound_tf')},
                            obligations={k: st.get(f'{p["id"]}_{k}', {}).get('status') for k in ('image', 'sound_tf')}))
    pkg, _ = L.assemble(state, name='relational decoders v2 (s15.3, generated)', domain=R17.TF,
                        scope=('Machine-generated oriented relational decoders over at most 4 classes (generator v2, '
                               'twins merged), their checked image and triangle-free soundness. Conservative '
                               'definitions only.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'statements quantify over all pair sets, loops and reversed pairs included'],
                        extra={'relations': records, 'generator_version': VERSION})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    new = [p for p, r in zip(props, records) if r['equals_menu'] is None and not r['evaluated_before']
           and r['obligations'] == {'image': 'CHECKED', 'sound_tf': 'CHECKED'}]
    R17.dump(out / 'package.json', pkg)
    summary = {'generator_version': VERSION,
               'generated': [{k: r[k] for k in ('id', 'k', 'relation', 'equals_menu', 'evaluated_before',
                                                'obligations', 'screen')} for r in records],
               'new_checked': [p['id'] for p in new], 'construction_cpu_s': round(construction, 3),
               'checker_cpu_s_reported': round(checker, 3),
               'verdict_a': 'NEW_CHECKED' if new else 'NO_NEW_CHECKED_REPRESENTATION'}
    R17.dump(out / 'part_a.json', summary)
    log(f'Part A (v2): {[(r["id"], r["equals_menu"] or ("evaluated before" if r["evaluated_before"] else "NEW"), r["obligations"]) for r in records]}; '
        f'construction {construction:.1f} CPU s -> {summary["verdict_a"]}')
    return new, max(construction, checker), summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    new, construction, a = part_a(out, log)
    b = None
    if new:
        # The B20_R17 Part B, unchanged except for its seeds and its exclusions (R17's hosts added).
        prior = json.loads((ROOT / 'evidence' / 'relation_invention_b20r17' / 'hosts.json').read_text())
        from genesis.models import GraphTask
        from genesis.common import canonical
        r17_hosts = [GraphTask.model_validate_json(canonical(t)) for v in prior.values() for k in v for t in v[k]]
        real_hosts, real_boot = R17.hosts, R17.BOOT_SEED

        def hosts(excluded):
            import b20r12_e1_redo as E
            excluded = set(excluded) | E.identities(r17_hosts)
            a_ = R17.ADAPTERS[R17.TF]
            out_ = {}
            for i, (sid, family, params) in enumerate(R17.SETTINGS):
                sel, seen, _ = a_.generate(SEEDS[0] + 10 * i, R17.SELECT_N, 'DEV', family, params, excluded=excluded)
                ev, seen, _ = a_.generate(SEEDS[1] + 10 * i, R17.EVAL_N, 'DEV', family, params, excluded=seen)
                excluded = set(seen)
                out_[sid] = {'select': sel, 'eval': ev}
            return out_
        R17.hosts, R17.BOOT_SEED = hosts, BOOT_SEED
        try:
            b = R17.part_b(out, log, new, construction)
        finally:
            R17.hosts, R17.BOOT_SEED = real_hosts, real_boot
    verdict = b['verdict'] if b else a['verdict_a']
    R17.dump(out / 'summary.json', {'schema': 'genesis-b20r19-relation-invention-v2', 'part_a': a, 'part_b': b,
                                    'verdict': verdict, 'attempts_in_family': ['B20_R17', 'B20_R19'],
                                    'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses no claim'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
