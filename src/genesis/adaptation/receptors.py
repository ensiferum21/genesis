"""Receptors of the adaptation cell: each senses one kind of weakness in a time-to-solution study's evidence.

A study is read from its evidence directory (`summary.json`, `rows.jsonl`, `run.log`) through a profile that names its
focal arm (the system's method), its competitor arms and the published solvers they stand for. Rows have the shape
every TTS study here writes: `runs[arm][run time] = [{'value', 'run'}, ...]`, `target`, `target_certified`, `n`, and
optionally `long[arm]` (a long-budget run). Each receptor returns zero or more `Caveat` records; it never changes
anything. Thresholds are constants here, fixed in B20_R93 before the receptors were run on any study (they are the
ones the builder used when it noticed these weaknesses by hand, stated in the B20_R90 and B20_R92 records).
"""
from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path

FLOOR_SHARE = 0.5           # the focal arm sits at the shortest run time on at least half the hosts
SATURATION_SHARE = 0.9      # on at least 90% of hosts the focal arm and the best competitor end at the same value
UNCERTIFIED_SHARE = 0.2     # more than 20% of targets are best-known values, not certified optima
TTS_FAILURE = 'never'       # (documentation) a host the focal arm never reaches counts against nothing here

CAVEAT_TYPES = {
    'FLOOR_EFFECT': 'the focal method reaches its targets at the shortest run time tested on most hosts, so its '
                    'margin is censored: the ladder cannot show how much faster it is',
    'SATURATION': 'every strong method ends at the same value on (almost) every host, so the instances can only '
                  'separate methods by speed, never by solution quality',
    'UNCERTIFIED_TARGETS': 'many targets are best-known values rather than certified optima, so "reached the target" '
                           'may not mean "solved"',
    'UNRESOLVED_VERDICT': 'a preregistered comparison ended UNRESOLVED or MIXED: the study lacked the power or the '
                          'resolution to decide it',
    'COMPONENT_EFFECT_UNRESOLVED': 'removing a component of the method had no measurable (or no resolved) effect, so '
                                   'whether it matters is unknown',
    'INVALID_RUN': 'the study failed its own validity check; nothing it measured can be read',
    'INTERRUPTED': 'the run was interrupted and resumed; the resume must be disclosed and the design should expect it',
    'MISSING_BASELINE': 'a stronger published solver for this problem class was not among the competitors',
    'REGIME_GAP': "the study's longest budget is below the competitors' home regime (the budgets they were tuned for)",
    'SIZE_CAP': "the instances sit at the task model's maximum size, so the study cannot say what happens beyond it",
    'ARM_NOT_RESPONDING': 'a competitor ends at about the same value at every run time on most hosts, well short of '
                          'the target: either the budgets are outside its regime or its harness is wrong, and the '
                          'comparison with it means nothing until one of the two is known',
    'OUTPERFORMED': "a competitor reaches the targets more than twice as fast as the system's own method on a "
                    'quarter of the hosts or more: the method has a weakness there (or, if the competitor is one of '
                    "the system's earlier methods, a regression)",
    'STALE_KNOWLEDGE': "the cell's own knowledge of the field (its baseline catalog) predates the newest Evaluation, "
                       'so MISSING_BASELINE cannot be trusted until the catalog is refreshed',
}
SEVERITY = {'INVALID_RUN': 'high', 'MISSING_BASELINE': 'high', 'FLOOR_EFFECT': 'medium', 'SATURATION': 'medium',
            'SIZE_CAP': 'medium', 'REGIME_GAP': 'medium', 'UNCERTIFIED_TARGETS': 'medium',
            'UNRESOLVED_VERDICT': 'medium', 'COMPONENT_EFFECT_UNRESOLVED': 'low', 'INTERRUPTED': 'low',
            'ARM_NOT_RESPONDING': 'high', 'STALE_KNOWLEDGE': 'high', 'OUTPERFORMED': 'high'}
OUTPERFORMED_FACTOR = 2.0   # OUTPERFORMED: a competitor's TTS* is less than half the focal method's ...
OUTPERFORMED_SHARE = 0.25   # ... on at least a quarter of the hosts it ran on
NATIVE_ARMS = ('tfx', 'found', 'engine', 'system', 'candidate')   # names the system's own methods have had
IDENTITY_KEYS = {'config', 'binary_sha256', 'config_file_sha256', 'descriptor_id'}   # what makes a method itself
FLAT_SHARE = 0.5            # ARM_NOT_RESPONDING: on at least half the hosts the arm is flat ...
FLAT_RISE = 0.01            # ... (its median value rises by at most 1% of the target from the shortest run time to
FLAT_SHORT = 0.95           # the longest, ends below 95% of the target and never reaches it) ...
FLAT_SPAN = 10.0            # ... over a ladder spanning at least a factor of 10


@dataclass(frozen=True)
class Caveat:
    type: str
    study: str
    evidence: dict = field(default_factory=dict)

    @property
    def severity(self):
        return SEVERITY[self.type]

    @property
    def lineage(self):
        """The lineage this caveat belongs to: its type, and its subject when it has one (an arm that does not
        respond is a different weakness from another arm that does not)."""
        sub = self.evidence.get('subject')
        return f'{self.type}[{sub}]' if sub else self.type

    @property
    def key(self):
        return f'{self.lineage}@{self.study}'

    def record(self):
        return dict(asdict(self), severity=self.severity, meaning=CAVEAT_TYPES[self.type])


@dataclass(frozen=True)
class Profile:
    """How to read one study: its batch name, evidence directory, focal arm (the system's own method), the other arms,
    when it ran (YYYY-MM-DD: what was published by then counts as known) and its problem class in the baseline
    catalog. `discovery.discover` infers all of it from the evidence; nothing has to be declared by hand."""
    study: str
    evidence: str
    focal: str
    competitors: tuple
    date: str = ''
    problem_class: str = 'unweighted_partial_maxsat_anytime'
    kind: str = 'tts'              # 'tts': time to solution (B20_R70-R92); 'qet': quality at equal time (B20_R96 on)


@dataclass
class Study:
    profile: Profile
    summary: dict
    rows: list
    run_log: str

    @classmethod
    def load(cls, profile, root):
        d = Path(root) / profile.evidence
        rows = [json.loads(l) for l in (d / 'rows.jsonl').read_text().splitlines() if l.strip()]
        summary = json.loads((d / 'summary.json').read_text()) if (d / 'summary.json').exists() else {}
        log = (d / 'run.log').read_text() if (d / 'run.log').exists() else ''
        return cls(profile, summary, rows, log)

    # ---- helpers over the common row shape
    def ladder(self):
        if self.summary.get('ladder'):
            return tuple(float(t) for t in self.summary['ladder'])
        return tuple(sorted({float(t) for r in self.rows for t in r['runs'][self.profile.focal]}))

    def tts(self, row, arm):
        """TTS* over the ladder: min over run times of t * ceil(ln 0.01 / ln(1 - s))."""
        best = math.inf
        for t in self.ladder():
            runs = row['runs'][arm].get(str(t)) or row['runs'][arm].get(repr(t)) or []
            if not runs:
                continue
            s = sum(x.get('run') == 'SUCCESS' and x['value'] >= row['target'] for x in runs) / len(runs)
            if s >= 1:
                v = t
            elif s <= 0:
                v = math.inf
            else:
                v = t * math.ceil(math.log(0.01) / math.log(1 - s))
            best = min(best, v)
        return best

    def best_value(self, row, arm):
        vals = [x['value'] for xs in row['runs'].get(arm, {}).values() for x in xs if x.get('run') == 'SUCCESS']
        if arm in row.get('long', {}) and row['long'][arm].get('run') == 'SUCCESS':
            vals.append(row['long'][arm]['value'])
        return max(vals, default=None)

    def labels(self):
        lab = self.summary.get('labels')
        if isinstance(lab, dict):
            return dict(lab)
        if isinstance(self.summary.get('verdict'), str):
            return {'verdict': self.summary['verdict']}
        return {}

    def budgets(self):
        if self.profile.kind == 'qet':
            return [float(self.summary['design']['budget'])]
        out = list(self.ladder())
        if self.summary.get('long_seconds'):
            out.append(float(self.summary['long_seconds']))
        return out

    # ---- quality-at-equal-time rows: runs[arm][budget] = {'value', 'run', 'cpu_ns'}
    def qet_value(self, row, arm):
        b = f"{self.summary['design']['budget']:g}"
        x = row['runs'].get(arm, {}).get(b)
        return None if x is None else x.get('value')


def focal_identity(study):
    """A short digest naming the focal method as this study ran it: its arm name and whatever configuration the
    summary records for it (a re-tuned method has a new identity under the same name)."""
    import hashlib
    block = study.summary.get(study.profile.focal)
    if isinstance(block, dict) and set(block) & IDENTITY_KEYS:
        block = {k: block[k] for k in sorted(set(block) & IDENTITY_KEYS)}
    ident = json.dumps([study.profile.focal, block], sort_keys=True, default=str)
    return hashlib.sha256(ident.encode()).hexdigest()[:16]


# ------------------------------------------------------------------------------------------------ the receptors

def floor_effect(study, catalog=None, cap=None):
    rows, floor = study.rows, study.ladder()[0]
    at = sum(study.tts(r, study.profile.focal) == floor for r in rows)
    if rows and at / len(rows) >= FLOOR_SHARE:
        return [Caveat('FLOOR_EFFECT', study.profile.study, {'focal': study.profile.focal, 'floor_s': floor,
                                                             'hosts_at_floor': at, 'hosts': len(rows)})]
    return []


def saturation(study, catalog=None, cap=None):
    rows, focal = study.rows, study.profile.focal
    comps = [a for a in study.profile.competitors if any(a in r['runs'] for r in rows)]
    if not rows or not comps:
        return []
    same = 0
    for r in rows:
        f = study.best_value(r, focal)
        c = max((v for v in (study.best_value(r, a) for a in comps) if v is not None), default=None)
        same += f is not None and f == c
    if same / len(rows) >= SATURATION_SHARE:
        return [Caveat('SATURATION', study.profile.study, {'hosts_with_equal_best_values': same, 'hosts': len(rows),
                                                           'largest_n': max(r['n'] for r in rows)})]
    return []


def uncertified_targets(study, catalog=None, cap=None):
    rows = study.rows
    unc = sum(not r.get('target_certified') for r in rows)
    if rows and unc / len(rows) > UNCERTIFIED_SHARE:
        ref_s = max((r.get('reference', {}).get('wall_s') or 0 for r in rows), default=0)
        return [Caveat('UNCERTIFIED_TARGETS', study.profile.study, {'uncertified': unc, 'hosts': len(rows),
                                                                    'certification_s': round(ref_s)})]
    return []


def unresolved_verdicts(study, catalog=None, cap=None):
    bad = {k: v for k, v in study.labels().items()
           if not k.startswith('ablation_') and isinstance(v, str) and ('UNRESOLVED' in v or v == 'MIXED')}
    ev = {'labels': bad, 'hosts': len(study.rows), 'ladder_points': len(study.ladder())}
    return [Caveat('UNRESOLVED_VERDICT', study.profile.study, ev)] if bad else []


def null_ablations(study, catalog=None, cap=None):
    nul = {k.split('_', 1)[1]: v for k, v in study.labels().items()
           if k.startswith(('ablation_', 'extra_')) and v in ('NO_MEASURABLE_EFFECT', 'UNRESOLVED')}
    ablated = [r for r in study.rows if any(k in r['runs'] for k in nul)] or study.rows
    ev = {'components': nul, 'hosts': len(ablated), 'largest_n': max((r['n'] for r in ablated), default=0)}
    return [Caveat('COMPONENT_EFFECT_UNRESOLVED', study.profile.study, ev)] if nul else []


def invalid_run(study, catalog=None, cap=None):
    inv = sorted({v for v in study.labels().values() if isinstance(v, str) and v.startswith('INVALID')})
    return [Caveat('INVALID_RUN', study.profile.study, {'labels': inv, 'focal': study.profile.focal})] if inv else []


PLANNED_PAUSE = '): paused after '      # qet.main's line when a time slice ends on purpose (B20_R96)


def interruption(study, catalog=None, cap=None):
    """A study that started again without having paused on purpose. Each start after the first is an interruption
    unless a planned pause (a time slice that ended between hosts, `genesis.autonomy.qet`) came before it: pausing and
    resuming is the answer to INTERRUPTED, not a new case of it (B20_R97)."""
    starts = study.run_log.count('pinned to CPU')
    planned = study.run_log.count(PLANNED_PAUSE)
    if starts - 1 - planned > 0:
        ev = {'starts_in_run_log': starts}
        if planned:
            ev['planned_pauses'] = planned
        return [Caveat('INTERRUPTED', study.profile.study, ev)]
    return []


def included_solvers(study):
    """Solver keys whose pinned binaries the study recorded (its summary's 'champions'), or, for a study of quality at
    equal time, the solvers its design ran."""
    if study.profile.kind == 'qet':
        return {s for _, s in study.summary['design']['champions']}
    return set((study.summary.get('champions') or {}).keys())


def missing_baseline(study, catalog, cap=None):
    cls = (catalog or {}).get('problem_classes', {}).get(study.profile.problem_class)
    if not cls:
        return []
    present = included_solvers(study)
    gone = [e for e in cls['entries'] if e.get('leading') and e['solver_key'] not in present
            and e['published'] <= (study.profile.date or '9999')]
    if gone:
        return [Caveat('MISSING_BASELINE', study.profile.study, {'missing': [e['name'] for e in gone],
                                                                 'missing_keys': [e['solver_key'] for e in gone],
                                                                 'catalog': cls['source']})]
    return []


def regime_gap(study, catalog, cap=None):
    cls = (catalog or {}).get('problem_classes', {}).get(study.profile.problem_class)
    if not cls or not cls.get('home_budgets_s'):
        return []
    longest, home = max(study.budgets()), min(cls['home_budgets_s'])
    if longest < home:
        return [Caveat('REGIME_GAP', study.profile.study, {'longest_budget_s': longest,
                                                           'competitors_home_budgets_s': cls['home_budgets_s']})]
    return []


def domain_cap(study):
    """The size cap of the task model the study's domain uses: the large domain's for a study of it (B20_R94), else
    the n <= 63 model's (cell v2: v1 read only the latter)."""
    if study.profile.kind == 'qet' and study.summary.get('design', {}).get('domain') == 'triangle_free_large_v1':
        from ..models_large import LARGE_MAX_N
        return LARGE_MAX_N
    from ..models import GraphTask
    return next(m.le for m in GraphTask.model_fields['n'].metadata if hasattr(m, 'le'))


def size_cap(study, catalog=None, cap=None):
    if study.profile.kind == 'qet' or cap is None:
        cap = domain_cap(study)
    largest = max((r['n'] for r in study.rows), default=0)
    if largest >= cap:
        return [Caveat('SIZE_CAP', study.profile.study, {'largest_n': largest, 'model_cap': cap})]
    return []


def _median(xs):
    xs = sorted(xs)
    return None if not xs else (xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2)


def arm_not_responding(study, catalog=None, cap=None):
    """Competitor arms whose value does not respond to the run time (a dose-response check): no one told the cell
    which arms are broken; it compares each arm's values at the shortest and the longest run time. A study that
    probed an arm at its home budget records `probes[arm] = {'budget_s', 'value', 'run'}` in its rows: if the arm
    reaches 95% of the target there on at least half of the probed hosts, it responds, only later (its regime is
    longer than the ladder) and is not flagged; if not, the flag says the probe found no response, which points at
    its harness."""
    lad = study.ladder()
    if len(lad) < 2 or lad[-1] / lad[0] < FLAT_SPAN or not study.rows:
        return []
    ablations = {k[len('ablation_'):] for k in study.labels() if k.startswith('ablation_')}
    lo, hi = lad[0], lad[-1]

    def vals(row, arm, t):
        runs = row['runs'][arm].get(str(t)) or row['runs'][arm].get(repr(t)) or []
        return [x['value'] for x in runs if x.get('run') == 'SUCCESS' and isinstance(x.get('value'), (int, float))]
    flagged = {}
    for arm in study.profile.competitors:
        if arm in ablations:
            continue
        rows = [r for r in study.rows if arm in r['runs']]
        flat, shares = 0, []
        for r in rows:
            a, b = vals(r, arm, lo), vals(r, arm, hi)
            every = [x for t in lad for x in vals(r, arm, t)]
            if not a or not b or not r.get('target'):
                continue
            ma, mb = _median(a), _median(b)
            if mb - ma <= FLAT_RISE * r['target'] and mb < FLAT_SHORT * r['target'] and max(every) < r['target']:
                flat += 1
                shares.append(mb / r['target'])
        probed = [r for r in rows if (r.get('probes') or {}).get(arm)]
        responds = [r for r in probed if r['probes'][arm].get('run') == 'SUCCESS'
                    and r['probes'][arm].get('value', 0) >= FLAT_SHORT * r['target']]
        if probed and len(responds) / len(probed) >= 0.5:
            continue
        if rows and flat / len(rows) >= FLAT_SHARE:
            flagged[arm] = {'flat_hosts': flat, 'hosts': len(rows), 'median_share_of_target': round(_median(shares), 3),
                            'run_times_s': [lo, hi]}
            if probed:
                flagged[arm]['probe'] = f'no response at the home budget on {len(probed) - len(responds)} of ' \
                                        f'{len(probed)} probed hosts'
    return [Caveat('ARM_NOT_RESPONDING', study.profile.study, {'subject': a, 'arms': [a], 'detail': flagged[a]})
            for a in sorted(flagged)]


def outperformed(study, catalog=None, cap=None):
    """Where the system's own method lost, read from the rows (not from any label): which competitors were more
    than `OUTPERFORMED_FACTOR` times faster, on how many hosts, and on which families and sizes (a diagnosis the
    next design can aim at)."""
    focal = study.profile.focal
    ablations = {k[len('ablation_'):] for k in study.labels() if k.startswith('ablation_')}
    hit = {}
    for arm in study.profile.competitors:
        if arm in ablations:
            continue
        rows = [r for r in study.rows if arm in r['runs'] and focal in r['runs']]
        lost = [r for r in rows if study.tts(r, arm) < study.tts(r, focal) / OUTPERFORMED_FACTOR]
        if rows and len(lost) / len(rows) >= OUTPERFORMED_SHARE:
            fam, size = {}, {}
            for r in lost:
                fam[str(r.get('family', '?'))] = fam.get(str(r.get('family', '?')), 0) + 1
                size[str(r['n'])] = size.get(str(r['n']), 0) + 1
            hit[arm] = {'lost_hosts': len(lost), 'hosts': len(rows), 'native': arm in NATIVE_ARMS,
                        'families': fam, 'sizes': size}
    if hit:
        return [Caveat('OUTPERFORMED', study.profile.study, {'focal': focal, 'focal_identity': focal_identity(study),
                                                             'arms': hit,
                                                             'worst_share': round(max(v['lost_hosts'] / v['hosts']
                                                                                      for v in hit.values()), 4)})]
    return []


RECEPTORS = (floor_effect, saturation, uncertified_targets, unresolved_verdicts, null_ablations, invalid_run,
             interruption, missing_baseline, regime_gap, size_cap, arm_not_responding, outperformed)


def _next_refresh(as_of, refresh):
    """The first date after `as_of` on which the field's yearly results appear (`refresh`: month, day)."""
    import datetime
    d = datetime.date.fromisoformat(as_of)
    due = datetime.date(d.year, refresh['month'], refresh['day'])
    return due if due > d else datetime.date(d.year + 1, refresh['month'], refresh['day'])


def stale_knowledge(catalog, today):
    """An autoreceptor: it senses the cell itself, not a study. Each problem class's catalog states when it was
    last checked (`as_of`) and when the field publishes new results (`refresh`); once that date has passed, the
    catalog may be missing the newest leading solvers."""
    out = []
    for name, cls in sorted((catalog or {}).get('problem_classes', {}).items()):
        if not cls.get('as_of') or not cls.get('refresh'):
            out.append(Caveat('STALE_KNOWLEDGE', 'CELL', {'problem_class': name, 'as_of': cls.get('as_of', ''),
                                                          'due': '0000-00-00', 'reason': 'no as-of date'}))
            continue
        due = _next_refresh(cls['as_of'], cls['refresh']).isoformat()
        if str(today) >= due:
            out.append(Caveat('STALE_KNOWLEDGE', 'CELL', {'problem_class': name, 'as_of': cls['as_of'], 'due': due,
                                                          'event': cls['refresh'].get('event', '')}))
    return out


# ------------------------------------------------------------------ receptors for studies of quality at equal time

def qet_saturation(study, catalog=None, cap=None):
    """The focal method and the best champion end at the same value on (almost) every host: values do not separate
    the methods even here."""
    rows, focal = study.rows, study.profile.focal
    champs = [a for a, _ in study.summary['design']['champions']]
    same = 0
    for r in rows:
        f = study.qet_value(r, focal)
        c = max((v for v in (study.qet_value(r, a) for a in champs) if v is not None), default=None)
        same += f is not None and f == c
    if rows and same / len(rows) >= SATURATION_SHARE:
        return [Caveat('SATURATION', study.profile.study, {'hosts_with_equal_best_values': same, 'hosts': len(rows),
                                                           'largest_n': max(r['n'] for r in rows)})]
    return []


def qet_uncertified(study, catalog=None, cap=None):
    """Hosts whose best known value is below the certified bound: how far from optimal anything can still be."""
    rows = [r for r in study.rows if 'upper' in r]
    if not rows:
        rows = study.rows
        unc, gap = len(rows), 1.0
    else:
        unc = sum(r['best_value'] < r['upper']['value'] for r in rows)
        gap = sum((r['upper']['value'] - r['best_value']) / r['upper']['value'] for r in rows) / len(rows)
    if rows and unc / len(rows) > UNCERTIFIED_SHARE:
        return [Caveat('UNCERTIFIED_TARGETS', study.profile.study, {
            'uncertified': unc, 'hosts': len(rows), 'mean_bound_gap': round(gap, 5),
            'certification_s': study.summary['design'].get('bound_seconds', 0)})]
    return []


def qet_outperformed(study, catalog=None, cap=None):
    lab = study.labels()
    if lab.get('qet_champions') != 'A_CHAMPION_BETTER' and lab.get('qet_vbs') != 'VBS_BETTER':
        return []
    det = study.summary.get('detail', {})
    worse = {a: {'verdict': c['verdict'], 'mean_difference': c['mean_difference']}
             for a, c in det.get('champions', {}).items() if c['verdict'] == 'B_BETTER'}
    lost = sum(1 for r in study.rows if (study.qet_value(r, study.profile.focal) or -1) < max(
        (v for v in (study.qet_value(r, a) for a, _ in study.summary['design']['champions']) if v is not None),
        default=-1))
    return [Caveat('OUTPERFORMED', study.profile.study, {'focal': study.profile.focal,
                                                         'focal_identity': focal_identity(study),
                                                         'arms': {a: dict(v, native=False, families={}, sizes={})
                                                                  for a, v in worse.items()},
                                                         'worst_share': round(lost / max(1, len(study.rows)), 4)})]


def qet_probe(study, catalog=None, cap=None):
    out = []
    for k, v in sorted(study.labels().items()):
        if k.startswith('probe_') and v == 'NO_RESPONSE':
            arm = k[len('probe_'):]
            out.append(Caveat('ARM_NOT_RESPONDING', study.profile.study, {
                'subject': arm, 'arms': [arm],
                'detail': {'probe': 'no response at the home budget on at least half the probed hosts'}}))
    return out


QET_RECEPTORS = (qet_saturation, qet_uncertified, unresolved_verdicts, null_ablations, invalid_run, interruption,
                 missing_baseline, regime_gap, size_cap, qet_outperformed, qet_probe)


def sense(study, catalog=None, cap=None):
    """Every receptor for the study's kind, in receptor order."""
    out = []
    for r in (QET_RECEPTORS if study.profile.kind == 'qet' else RECEPTORS):
        out.extend(r(study, catalog, cap))
    return out


def magnitude(caveat):
    """How bad a caveat is, comparable between occurrences of the same type (larger is worse)."""
    e = caveat.evidence if isinstance(caveat, Caveat) else caveat['evidence']
    t = caveat.type if isinstance(caveat, Caveat) else caveat['type']
    return {'FLOOR_EFFECT': lambda: e['hosts_at_floor'] / e['hosts'] * e['floor_s'],      # the censoring level
            'SATURATION': lambda: e['hosts_with_equal_best_values'] / e['hosts'],
            'UNCERTIFIED_TARGETS': lambda: e['uncertified'] / e['hosts'],
            'UNRESOLVED_VERDICT': lambda: len(e['labels']),
            'COMPONENT_EFFECT_UNRESOLVED': lambda: len(e['components']),
            'INVALID_RUN': lambda: len(e['labels']),
            'INTERRUPTED': lambda: e['starts_in_run_log'],
            'MISSING_BASELINE': lambda: len(e['missing']),
            'REGIME_GAP': lambda: min(e['competitors_home_budgets_s']) / e['longest_budget_s'],
            'SIZE_CAP': lambda: 1.0,
            'ARM_NOT_RESPONDING': lambda: len(e['arms']),
            'STALE_KNOWLEDGE': lambda: 1.0,
            'OUTPERFORMED': lambda: e['worst_share']}[t]()
