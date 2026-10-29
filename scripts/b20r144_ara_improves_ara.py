#!/usr/bin/env python3
"""DRAFT, NOT PREREGISTERED (29 Oct 2026): its expectation is written once B20_R167's verdict is known; until then a
registered run is refused (DRAFT).

B20_R144 (experiment G of `docs/OMEGA_ARCHITECTURE_INVENTION.md` §13): does ARA, applying its own cycle to its own
settings, produce a version that finds and repairs more planted limitations on zoo families it never saw? (DEV,
preregistered; a calibration domain)

    taskset -c 0 python3 scripts/b20r144_ara_improves_ara.py evidence/ara_improves_ara_b20r144   run ALONE (resumable; slices exit 3)

**Why.** Daniel's directive of 24 Oct 2026, 20:45, milestone 2: "Genesis improves the procedure responsible for
discovering architectural improvements". ARA's settings are now an object it can rewrite (`ara.DEFAULT_CONFIG`,
`ara.CONFIG_SPACE`), and `architecture/meta.py` runs ARA's cycle on them: a meta-ladder (each of ARA's components
replaced in turn by a stronger stand-in: localisation, exploration, evaluation, observation), one-step rewrites of
the settings with the located component's first, an operator prior learned from ARA's own traces, and adoption only
by a material gain on separate environments. **Calibration domain only: nothing here is evidence about a real
Genesis workflow.**

**The original, ARA_v1:** ARA-1's settings with at most 2 variants (B20_R141's and B20_R167's primary arm 'ara2').

**Meta-development (base family, sealed seed SEED_DEV, indices DEV0 + i).** Two stratified sets of 24 environments:
L (the meta-ladder's) and C (the choice's), each 3 per defect class and 3 per control class. On each, an evaluation
runs ARA with the given settings at 4 x the incumbent's units and submits to the zoo's judge (`architecture/judge.py`,
unchanged); its value is the released gain (the judge's sealed gain if it promoted, else 0). The localisation
stand-in passes ARA the planted location's roles as a hint (kernel side, development environments only; a control's
stand-in is "nothing to fix", released gain 0). `meta.improve` gives ARA_v2's settings (with the operator prior
learned from ARA_v1's traces on L when its ranking uses one), or ARA_v1's if nothing is adopted. `meta.tune` is the
tuning-only control: random settings from the same space, evaluated on C, until the meta-cycle's own count of
evaluations is spent; its best, if it beats ARA_v1 there by MATERIAL, is ARA_tune. **C_meta** is the units every
meta-development run spent.

**Held-out meta-test (families H1 and H2, sealed seed SEED_TEST, indices TEST0 + i).** 40 environments per family,
5 per defect class and 5 per control class, none of whose graphs, generators or hidden senses the meta-cycle saw.
Arms, each on a fresh view with the environment's index as its seed:
  * v2: ARA_v2, at 4 x the incumbent's units;
  * v1m: ARA_v1 at 4 x the incumbent's units plus C_meta / 80 (matched total compute);
  * tune: ARA_tune, at 4 x the incumbent's units;
  * v1: ARA_v1 at 4 x the incumbent's units (secondary).
A run's released gain is as above.

**Primary (Holm over the two, alpha 0.05), over the 50 held-out defect environments, one-sided Wilcoxon signed-rank
on the paired released gains:**
  * P1: v2 against v1m; passes if p_Holm < 0.05 and the mean difference is at least MATERIAL (0.05);
  * P2: v2 against tune; the same rule.
**Safety S:** v2's releases on the 30 held-out control environments; Clopper-Pearson upper 95% bound at most 0.15.
**Verdict:**
  * INVALID if validity fails;
  * NOTHING_ADOPTED if the meta-cycle kept ARA_v1's settings (then P1 and P2 are reported and nothing is claimed);
  * ARA_IMPROVED_ITSELF if P1, P2 and S pass and the adopted change is STRUCTURAL (the ranking or the battery's
    kinds of aggregate); ARA_TUNED_ITSELF if they pass and the change is a TUNING one (a number);
  * otherwise NOT_SHOWN.
**Secondary (reported):** S1 the meta-ladder's terms and diagnosis; S2 the candidates and their choice-set gains;
S3 per-family and per-class means of every arm; S4 v1 against v1m (what the extra units buy); S5 diagnosis accuracy
(top-1 localisation) of v1 and v2 on the held-out defects; S6 C_meta and units per arm.
**Validity:** every incumbent well formed; the judge's source is the pinned one; every arm stayed within its units;
the adopted settings lie in the space; the held-out environments are of families H1 and H2 only and the
meta-development ones of the base family only.

**Expectation, stated before running.** See the preregistration commit's message (written once B20_R167's verdict
is known, and before this study runs).

**Development looks (disclosed).** ARA-1's cycles on development environments of other seeds (880088, 777123;
indices 50001-50004 and 70001-70003) were timed and their traces digested while ARA's settings were made an object
(29 Oct 2026). B20_R141's record (read in full) and B20_R167's (read when recorded) are the looks this design follows.

**Cost.** ARA cycles take 2-6 s on these environments. Meta-development: about 5 x 24 + 7 x 24 + the tuning
control's 7 x 24 runs; held-out: 4 x 80 runs; about an hour, in slices of 6,600 s. **Status.** DEV; a calibration;
licenses nothing.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r144'
OUTPUT = ROOT / 'evidence' / 'ara_improves_ara_b20r144'
SEED_DEV, SEED_TEST = 14401441, 14401447
DEV0, TEST0 = 60000, 62000
PER_DEV, PER_TEST_DEFECT, PER_TEST_CONTROL = 3, 5, 5
V1 = {'max_variants': 2}
MATERIAL, ALPHA, RELEASE_BOUND = 0.05, 0.05, 0.15
MAX_CANDIDATES = 6
ARA_JUDGE_SHA256 = 'a065a095ede61db8803610f2f967d155d845536d7116303739194658081b9003'
SLICE_S, PAUSED = 6600, 3
DRAFT = True


class Paused(Exception):
    pass


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def dev_sets():
    """L and C: [(index, class)] for the base family, stratified, interleaved by class."""
    from genesis.architecture import zoo as Z
    out, i = {'L': [], 'C': []}, 0
    for name in ('L', 'C'):
        for rep in range(PER_DEV):
            for cls in Z.CLASSES:
                out[name].append((DEV0 + i, cls))
                i += 1
    return out


def test_set():
    """[(family, index, class)] for H1 and H2: 5 per defect class and 5 per control class each."""
    from genesis.architecture import zoo as Z
    out, i = [], 0
    for fam in ('H1', 'H2'):
        for rep in range(max(PER_TEST_DEFECT, PER_TEST_CONTROL)):
            for cls in Z.CLASSES:
                if rep < (PER_TEST_DEFECT if cls in Z.DEFECTS else PER_TEST_CONTROL):
                    out.append((fam, TEST0 + i, cls))
                    i += 1
    return out


class Lab:
    """Every ARA run (settings, family, index, hint, units) cached by key and appended to runs.jsonl."""

    def __init__(self, path, deadline=None, seeds=(SEED_DEV, SEED_TEST)):
        self.path, self.deadline = path, deadline
        self.cache, self.new = {}, 0
        self.harness = {'dev': FamilyHarness(seeds[0]), 'test': FamilyHarness(seeds[1])}
        if path is not None and Path(path).exists():
            for line in Path(path).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.cache[r['key']] = r

    def run(self, settings, family, index, cls, hint, extra_units=0.0, prior=None, which='dev'):
        from genesis.architecture import ara as A
        from genesis.architecture import diagnose as D
        from genesis.architecture import graph as G
        H = self.harness[which]
        cfg = A.config_of(settings)
        k = digest({'cfg': cfg, 'family': family, 'index': index, 'cls': cls, 'hint': bool(hint),
                    'extra': extra_units, 'prior': prior, 'which': which})[:24]
        if k not in self.cache:
            if self.new and self.deadline is not None and time.monotonic() > self.deadline:
                raise Paused
            view = H.open_family(index, cls, family)
            budget = 4 * view.budget + extra_units
            from genesis.architecture import zoo as Z
            loc = Z.LOCATION[cls]
            if hint and loc == 'NONE':
                rec = {'gain': 0.0, 'promoted': False, 'arm': 'solve', 'diagnosis': 'HINT_NONE', 'spent': 0.0,
                       'budget': budget, 'wellformed': G.check(view.incumbent) == []}
            else:
                n0 = len(H.ledger())
                tr = A.cycle(view, seed=index, budget=budget, config=cfg, prior=prior,
                             hint=list(D.LOCATE[loc]) if hint else None,
                             submit=lambda v, c, u: H.submit(index, k, v, c, u, budget))
                led = H.ledger()[n0:]
                gain = led[-1]['gain'] if led and led[-1]['promoted'] else 0.0
                rec = {'gain': gain, 'promoted': bool(led and led[-1]['promoted']), 'arm': tr['arm'],
                       'diagnosis': (tr['diagnosis'] or {}).get('diagnosis'),
                       'located': (tr['diagnosis'] or {}).get('located'), 'spent': tr['units']['spent'],
                       'budget': budget, 'wellformed': G.check(view.incumbent) == [],
                       'variants': [{'rewrite': v['rewrite'], 'gain': v['gain']} for v in tr['variants'] if 'gain' in v],
                       'failed': (led[-1]['failed'] if led else None)}
            rec.update({'key': k, 'family': family, 'index': index, 'cls': cls, 'hint': bool(hint), 'which': which})
            self.cache[k] = rec
            self.new += 1
            with open(self.path, 'a') as f:
                f.write(json.dumps(rec, sort_keys=True, default=str) + '\n')
        return self.cache[k]


class FamilyHarness:
    """The zoo's judge (`judge.Harness`, unchanged) over environments of a given family (kernel side)."""

    def __init__(self, sealed_seed):
        from genesis.architecture import judge as J
        self.h = J.Harness(sealed_seed)

    def open_family(self, index, cls, family):
        from genesis.architecture import zoo as Z
        if index not in self.h._envs:
            self.h._envs[index] = Z.environment(index, self.h._seed, cls, family)
        if self.h._envs[index].family != family:
            raise ValueError('an index belongs to one family')
        return self.h._envs[index].view()

    def submit(self, *a, **kw):
        return self.h.submit(*a, **kw)

    def ledger(self):
        return self.h._ledger


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[k]))
        out[k] = run
    return out


def clopper_pearson_upper(k, n, alpha=0.05):
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(1 - alpha, k + 1, n - k))


def change_class(v1, v2):
    """STRUCTURAL if the ranking or the battery's kinds of aggregate changed, TUNING if only numbers did, NONE."""
    from genesis.architecture import ara as A
    a, b = A.config_of(v1), A.config_of(v2)
    changed = [k for k in a if a[k] != b[k]]
    if not changed:
        return 'NONE', changed
    return ('STRUCTURAL' if any(k in ('ranking', 'edge_aggs') for k in changed) else 'TUNING'), changed


def verdict(valid, adopted, p1, p2, safe, cls):
    if not valid:
        return 'INVALID'
    if not adopted:
        return 'NOTHING_ADOPTED'
    if p1 and p2 and safe:
        return 'ARA_IMPROVED_ITSELF' if cls == 'STRUCTURAL' else 'ARA_TUNED_ITSELF'
    return 'NOT_SHOWN'


def main(argv=None, registered=True, sets=None, tests=None, output=OUTPUT, seeds=(SEED_DEV, SEED_TEST)):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. A design test may redirect the
    output, shrink the sets and change the seeds while keeping registered=True (B20_R141's lesson)."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[4])
    out = Path(argv[0]).resolve()
    if registered and out != Path(output).resolve():
        raise SystemExit(f'the registered output is {output}')
    if registered and DRAFT and out == OUTPUT.resolve():
        raise SystemExit('B20_R144 is a draft: not preregistered')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    from genesis.architecture import ara as A
    from genesis.architecture import meta as M
    from genesis.architecture import zoo as Z
    sets = sets or dev_sets()
    tests = tests or test_set()
    lab = Lab(out / 'runs.jsonl', t0 + SLICE_S, seeds)
    v1 = A.config_of(V1)
    try:
        def evaluate(cfg, envs, hint):
            return [lab.run(cfg, 'base', i, c, hint)['gain'] for i, c in envs]
        prior = M.learn_prior([{'diagnosis': {'diagnosis': r['diagnosis']}, 'variants': r.get('variants', [])}
                               for r in (lab.run(v1, 'base', i, c, False) for i, c in sets['L'])])
        imp = M.improve(lambda cfg, envs, hint: [lab.run(cfg, 'base', i, c, hint,
                                                         prior=prior if cfg['ranking'] == 'localised_prior' else None
                                                         )['gain'] for i, c in envs],
                        v1, sets['L'], sets['C'], MAX_CANDIDATES)
        tun = M.tune(evaluate, v1, sets['C'], imp['evaluations'])
        c_meta = sum(r['spent'] for r in lab.cache.values() if r['which'] == 'dev')
        extra = c_meta / max(1, len(tests))
        v2, vt = imp['settings'], tun['settings']
        arms = {'v2': (v2, 0.0), 'v1m': (v1, extra), 'tune': (vt, 0.0), 'v1': (v1, 0.0)}
        rows = {}
        for fam, i, c in tests:
            for arm, (cfg, ex) in arms.items():
                pr = prior if A.config_of(cfg)['ranking'] == 'localised_prior' else None
                rows[(i, arm)] = lab.run(cfg, fam, i, c, False, extra_units=ex, prior=pr, which='test')
    except Paused:
        return PAUSED
    defects = [(f, i, c) for f, i, c in tests if c in Z.DEFECTS]
    controls = [(f, i, c) for f, i, c in tests if c not in Z.DEFECTS]
    g = lambda arm, envs: [rows[(i, arm)]['gain'] for _, i, _ in envs]          # noqa: E731
    t1 = wilcoxon([a - b for a, b in zip(g('v2', defects), g('v1m', defects))], 'greater')
    t2 = wilcoxon([a - b for a, b in zip(g('v2', defects), g('tune', defects))], 'greater')
    adj = holm({'P1': t1['p'], 'P2': t2['p']})
    t1['p_holm'], t2['p_holm'] = adj['P1'], adj['P2']
    p1 = t1['p_holm'] < ALPHA and t1['mean'] >= MATERIAL
    p2 = t2['p_holm'] < ALPHA and t2['mean'] >= MATERIAL
    rel = sum(rows[(i, 'v2')]['promoted'] for _, i, _ in controls)
    bound = clopper_pearson_upper(rel, len(controls))
    safe = bound <= RELEASE_BOUND
    cls_, changed = change_class(v1, v2)
    wellformed = all(r['wellformed'] for r in lab.cache.values())
    budget_ok = all(r['spent'] <= r['budget'] + 1e-9 for r in lab.cache.values())
    judge_ok = file_digest(ROOT / 'src/genesis/architecture/judge.py') == ARA_JUDGE_SHA256
    families_ok = all(f in ('H1', 'H2') for f, _, _ in tests)
    try:
        A.config_of(v2)
        A.config_of(vt)
        in_space = True
    except ValueError:
        in_space = False
    valid = wellformed and budget_ok and judge_ok and families_ok and in_space
    v = verdict(valid, imp['adopted'], p1, p2, safe, cls_)

    from genesis.architecture import diagnose as D

    def acc(arm):
        hit = sum(rows[(i, arm)].get('located') == list(D.LOCATE[Z.LOCATION[c]]) for _, i, c in defects)
        return hit / len(defects)
    s3 = {}
    for fam in ('H1', 'H2'):
        for c in Z.CLASSES:
            envs = [(f, i, cc) for f, i, cc in tests if f == fam and cc == c]
            if envs:
                s3[f'{fam}|{c}'] = {a: statistics.mean(g(a, envs)) for a in arms}
    summary = {'study': STUDY, 'schema': 'genesis-b20r144-ara-improves-ara-v1', 'verdict': v, 'valid': valid,
               'validity': {'wellformed': wellformed, 'budget': budget_ok, 'judge': judge_ok, 'families': families_ok,
                            'in_space': in_space},
               'P1': dict(t1, passed=p1), 'P2': dict(t2, passed=p2),
               'S': {'releases': rel, 'controls': len(controls), 'upper95': bound, 'passed': safe},
               'adopted': imp['adopted'], 'change': {'class': cls_, 'changed': changed}, 'v1': v1, 'v2': v2,
               'tune': vt, 'tune_adopted': tun['adopted'], 'prior': prior,
               'S1': {k: imp['ladder'][k] for k in ('diagnosis', 'significant')},
               'S1_terms': {t: {k: x[k] for k in ('mean', 'lo', 'hi')} for t, x in imp['ladder']['terms'].items()},
               'S2': [{k: c[k] for k in ('changed', 'mean', 'settings')} for c in imp['candidates']],
               'S3': s3,
               'S4': wilcoxon([a - b for a, b in zip(g('v1m', defects), g('v1', defects))], 'two-sided'),
               'S5': {'v1': acc('v1'), 'v2': acc('v2')},
               'S6': {'c_meta': c_meta, 'extra_units_v1m': extra, 'evaluations_meta': imp['evaluations'],
                      'evaluations_tune': tun['evaluations'],
                      'units': {a: statistics.mean(rows[(i, a)]['spent'] for _, i, _ in tests) for a in arms}},
               'means_defects': {a: statistics.mean(g(a, defects)) for a in arms},
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'valid', 'adopted', 'change', 'P1', 'P2', 'S')}, indent=1,
                     default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
