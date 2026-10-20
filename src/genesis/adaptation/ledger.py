"""Immune memory of the adaptation cell: the caveat ledger, rebuilt from the evidence.

Studies are read in batch order. For each caveat type the ledger keeps one lineage: where it first appeared, every
later study that showed it again, every attempt to answer it, and the studies where it was quiet. Nobody declares
which study answered what. The cell reads each study's design from its evidence (`design.design_of`) and, like a
bacterium sensing a gradient, compares it with the past rather than reading it in isolation: an attempt is a change
of a response's progress (`responses.Response.progress`) between the design of the study where the caveat was last
seen and the design of the later study. A state that was already there when the caveat fired is not an answer to it.

Outcomes of an attempt:
  * RESOLVED: the receptor no longer fires on the later study;
  * IMPROVING: it fires, but the caveat's magnitude fell below `NOISE_DROP` of the last one (keep going: the next
    design gives the same response at the dose the new evidence calls for);
  * PERSISTENT: a full dose and nothing improved; after `RETIRE_AFTER` such outcomes the response is retired for
    this lineage (apoptosis) and the next one in the library is proposed (a state such as 'upper bounds on' cannot be
    given twice, so the composer moves past it at once);
  * UNDERDOSED: a partial dose and nothing improved: the response is kept, at full dose next time.
Without an attempt:
  * CHRONIC: the caveat recurred in two or more later studies that did not try to answer it (its severity rises one
    level, once: an unanswered weakness that keeps coming back is worse than a new one);
  * quiet: the receptor did not fire, but nothing was done about it either. Absence of evidence is not resolution,
    so the lineage stays open; but a lineage quiet in `QUIET_CLEARS` consecutive studies that could have shown it
    (for a caveat about one arm: studies that ran that arm) is CLEARED: evidence of absence, with no response
    credited for it.
RELAPSE: it fires again after it was resolved; the response that resolved it is charged with the relapse.
Like a CAPA's verification of effectiveness (21 CFR 820.100: the action is effective and does not adversely affect the
product), every attempt records the weaknesses that first appeared in the same study (`new_alongside`): suspected
side effects, reported, not scored (co-occurrence is not cause).

Response memory: across lineages the ledger counts each response's outcomes and ranks the live responses by a
Laplace-smoothed success rate (`ranked_responses`), ties in the library's order. `events` is the cell's own account
of what it inferred, in order.
"""
import json
from pathlib import Path

from .design import design_of
from .receptors import SEVERITY, Study, magnitude, sense
from .responses import RESPONSES

NOISE_DROP = 0.9            # a magnitude must fall below 90% of the last one to count as an improvement
RETIRE_AFTER = 2            # a response is retired for a lineage after this many full doses without improvement
QUIET_CLEARS = 2            # quiet in this many consecutive studies that could have shown it: CLEARED
_UP = {'low': 'medium', 'medium': 'high', 'high': 'high'}
_OUTCOMES = ('RESOLVED', 'IMPROVING', 'PERSISTENT', 'UNDERDOSED', 'RELAPSED')


def _could_show(lineage, design):
    """Whether a study with this design could have shown the caveat again: a caveat about one arm needs that arm in
    the comparison; the others can show on any study."""
    arms = lineage['occurrences'][-1]['evidence'].get('arms')
    if lineage['type'] == 'ARM_NOT_RESPONDING' and arms:
        return all(a in design.get('arm_names', ()) for a in arms)
    return True


class Ledger:
    def __init__(self):
        self.lineages = {}          # type -> lineage
        self.outcomes = {}          # response -> {outcome: n}
        self.designs = {}           # study -> design read from its evidence
        self.studies = []           # in the order observed
        self.events = []            # the cell's account of what it inferred

    def _count(self, response, outcome):
        self.outcomes.setdefault(response, dict.fromkeys(_OUTCOMES, 0))[outcome] += 1

    def _say(self, study, text):
        self.events.append(f'{study}: {text}')

    # ---- reading one study
    def observe(self, study, caveats, design=None):
        design = design or design_of(study)
        name = study.profile.study
        fired = {c.lineage: c for c in caveats}
        for t, lin in self.lineages.items():
            last = lin['occurrences'][-1]
            prev = self.designs[last['study']]
            gains = []
            for i, r in enumerate(RESPONSES[lin['type']]):
                if r.name in lin['retired']:
                    continue
                new, old = r.progress(design, last['evidence']), r.progress(prev, last['evidence'])
                if new > old:
                    gains.append((new >= 1.0, new - old, -i, r.name, new))
            attempt = max(gains) if gains else None
            if lin['status'] in ('RESOLVED', 'CLEARED'):
                if t in fired:
                    lin['status'] = 'RELAPSE'
                    lin['occurrences'].append(self._occ(name, fired[t]))
                    lin['unanswered_recurrences'] = 0
                    if lin.get('resolved_by'):
                        self._count(lin['resolved_by'], 'RELAPSED')
                    self._say(name, f'{t} relapsed (it had been resolved by {lin.get("resolved_by")})'
                              if lin.get('resolved_by') else f'{t} relapsed (it had cleared without an answer)')
                continue
            if attempt:
                full, _, _, rname, dose = attempt
                if t not in fired:
                    outcome = 'RESOLVED'
                    lin['resolved_by'] = rname
                elif magnitude(fired[t]) < NOISE_DROP * last['magnitude']:
                    outcome = 'IMPROVING'
                elif full:
                    outcome = 'PERSISTENT'
                    lin.setdefault('failures', {})[rname] = lin.get('failures', {}).get(rname, 0) + 1
                    if lin['failures'][rname] >= RETIRE_AFTER:
                        lin['retired'].append(rname)
                else:
                    outcome = 'UNDERDOSED'
                lin['attempts'].append({'study': name, 'response': rname, 'dose': round(dose, 3), 'outcome': outcome})
                self._count(rname, outcome)
                lin['status'] = outcome
                lin['unanswered_recurrences'] = 0
                after = f'magnitude {last["magnitude"]} -> {round(magnitude(fired[t]), 6)}' if t in fired \
                    else 'no longer fires'
                self._say(name, f'{t}: {rname} at dose {round(dose, 3)} ({after}): {outcome}'
                          + (f'; {rname} retired for this lineage' if rname in lin['retired'] else ''))
                if t in fired:
                    lin['occurrences'].append(self._occ(name, fired[t]))
            elif t in fired:
                lin['occurrences'].append(self._occ(name, fired[t]))
                lin['quiet_streak'] = 0
                lin['unanswered_recurrences'] += 1
                if lin['unanswered_recurrences'] >= 2 and lin['status'] != 'CHRONIC':
                    lin['severity'] = _UP[lin['severity']] if not lin.get('escalated') else lin['severity']
                    lin['escalated'] = True
                    lin['status'] = 'CHRONIC'
                    self._say(name, f'{t} recurred unanswered {lin["unanswered_recurrences"]} times: CHRONIC '
                              f'(severity {lin["severity"]})')
            else:
                lin.setdefault('quiet', []).append(name)
                if _could_show(lin, design):
                    lin['quiet_streak'] = lin.get('quiet_streak', 0) + 1
                    if lin['quiet_streak'] >= QUIET_CLEARS:
                        lin['status'] = 'CLEARED'
                        self._say(name, f'{t} quiet in {QUIET_CLEARS} studies that could have shown it: CLEARED '
                                  '(no response is credited)')
        born = [t for t in fired if t not in self.lineages]
        for t, c in fired.items():
            if t not in self.lineages:
                self.lineages[t] = {'type': c.type, 'first_seen': name, 'severity': SEVERITY[c.type], 'status': 'OPEN',
                                    'occurrences': [self._occ(name, c)], 'attempts': [], 'retired': [],
                                    'unanswered_recurrences': 0}
                self._say(name, f'{t} first seen')
        if born:            # CAPA: an action must not cause new problems; note what first appeared alongside it
            for lin in self.lineages.values():
                for a in lin['attempts']:
                    if a['study'] == name:
                        a['new_alongside'] = sorted(born)
        self.designs[name] = design
        self.studies.append(name)

    @staticmethod
    def _occ(study, c):
        return {'study': study, 'evidence': c.evidence, 'magnitude': round(magnitude(c), 6)}

    # ---- queries
    def open(self):
        """Open lineages, keyed TYPE@FIRST_SEEN, with the latest occurrence's evidence."""
        out = {}
        for t, lin in self.lineages.items():
            if lin['status'] in ('RESOLVED', 'CLEARED'):
                continue
            last = lin['occurrences'][-1]
            age = len(self.studies) - self.studies.index(lin['first_seen']) if lin['first_seen'] in self.studies else 0
            out[f"{t}@{lin['first_seen']}"] = {'type': lin['type'], 'study': last['study'], 'status': lin['status'],
                                               'severity': lin['severity'], 'evidence': last['evidence'],
                                               'retired': list(lin['retired']), 'age': age,
                                               'attempts': list(lin['attempts'])}
        return out

    def score(self, name):
        o = self.outcomes.get(name, {})
        n = o.get('RESOLVED', 0) + o.get('IMPROVING', 0) + o.get('PERSISTENT', 0)
        good = o.get('RESOLVED', 0) + 0.5 * o.get('IMPROVING', 0) - 0.5 * o.get('RELAPSED', 0)
        return (good + 1) / (n + 2)                       # Laplace-smoothed success rate

    def ranked_responses(self, entry):
        """Live responses, best record first; a last-resort response (one that makes the observation go away, such
        as leaving an arm out) comes after every other however well it has scored: diagnose before excising."""
        lib = [r for r in RESPONSES[entry['type']] if r.name not in entry['retired']]
        names = [r.name for r in lib]
        last = {r.name for r in lib if r.last_resort}
        return sorted(names, key=lambda nm: (nm in last, -self.score(nm), names.index(nm)))

    def best_response(self, entry):
        ranked = self.ranked_responses(entry)
        return ranked[0] if ranked else None

    def record(self):
        return {'schema': 'genesis-caveat-ledger-v3', 'studies': list(self.studies), 'lineages': self.lineages,
                'response_outcomes': self.outcomes, 'designs': self.designs, 'events': list(self.events)}

    def save(self, path):
        Path(path).write_text(json.dumps(self.record(), indent=1, sort_keys=True) + '\n')


def rebuild(profiles, root, catalog, cap=None):
    """Sense every study in order and build the ledger; also returns each study's caveats and design, and the loaded
    studies."""
    led, seen, studies = Ledger(), {}, []
    for prof in profiles:
        st = Study.load(prof, root)
        cav = sense(st, catalog, cap)
        d = design_of(st)
        seen[prof.study] = {'caveats': cav, 'design': d}
        led.observe(st, cav, d)
        studies.append(st)
    return led, seen, studies
