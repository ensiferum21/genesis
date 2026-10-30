"""What a run shows (research plane; `docs/OMEGA_SELF_REPAIR.md` §2.2): line coverage of the repairable file, and
**conservation laws** mined from passing runs.

A run is observed through the job's probe (the kernel's `Observer`, asked for with observe='full'), which sees only the
component's own frames: the lines executed, and the component's state (its attributes, as plain builtins) at every
method return. Each state is checked against candidate laws, the counterparts of conserved quantities in physics:
what a correct component keeps true however it is driven.
  * pairing: two containers hold the same elements (set(A) == set(B)), or as many (len(A) == len(B));
  * coherence: a cached attribute is either unset or equal to a function of a container
    (X is None or X == f(Y), f in sum, max, min, len): the cache agrees with what it caches;
  * bound: a container never exceeds an integer attribute (len(A) <= self.c);
  * index: a dict of positions points into a list (sorted(D.values()) == list(range(len(L)))).
A law is kept if it was tested non-trivially (the cache set, the containers non-empty) at least MIN_TESTS times and
either held at every return of every passing run (exact), or held at all but a fraction SYMMETRY_BREAK of them with
every run's first break after **one and the same method** (broken by one interaction only, the way a conservation law
violated by a single process points at that process). The second kind matters because a defect often corrupts state
silently, in runs that still pass, long before anything visible fails. In a failing run, the first return at which a
kept law breaks names the method that broke it: evidence for localisation, and the target of law-restoring repairs
(`synth`)."""
import math

MIN_TESTS = 5
SYMMETRY_BREAK = 0.2
FUNCS = {'sum': sum, 'max': max, 'min': min, 'len': len}
CONTAINERS = (list, dict, set, tuple)


def _is_container(v):
    return isinstance(v, CONTAINERS) or type(v).__name__ == 'OrderedDict'


def coherence_laws(names, conts):
    out = []
    for x in names:
        for y in conts:
            for fname, f in FUNCS.items():
                def test(s, x=x, y=y, f=f):
                    if s.get(x) is None or not s.get(y):
                        return None
                    try:
                        return s[x] == f(s[y])
                    except (TypeError, ValueError):
                        return False
                out.append((f'{x} is None or {x} == {fname}({y})', test))
    return out


class Observation:
    """Coverage and states of one run, from a runner's result."""

    def __init__(self, result=None):
        result = result or {}
        obs = result.get('obs') or {}
        self.lines = set(obs.get('lines', ()))
        self.steps = result.get('steps', 0)        # line events: the run's work in the component
        self.returns = list(obs.get('returns', ()))   # (method, state)


def mine(observations):
    """The laws that held at every return of the given (passing) runs, tested at least MIN_TESTS times."""
    states = [s for ob in observations for _, s in ob.returns]
    if not states:
        return []
    keys = set(states[0])
    conts = sorted(k for k in keys if any(_is_container(s.get(k)) for s in states))
    cached = sorted(k for k in keys if any(s.get(k) is None for s in states) and
                    any(isinstance(s.get(k), (int, float)) and not isinstance(s.get(k), bool) for s in states))
    ints = sorted(k for k in keys if all(isinstance(s.get(k), int) and not isinstance(s.get(k), bool) for s in states))
    laws = []
    for i, x in enumerate(conts):
        for y in conts[i + 1:]:
            laws.append((f'set({x}) == set({y})', lambda s, x=x, y=y: set(s[x]) == set(s[y]) if s[x] or s[y] else None))
            laws.append((f'len({x}) == len({y})', lambda s, x=x, y=y: len(s[x]) == len(s[y]) if s[x] or s[y] else None))
            for d, l in ((x, y), (y, x)):
                laws.append((f'positions({d}) == range(len({l}))',
                             lambda s, d=d, l=l: (sorted(s[d].values()) == list(range(len(s[l])))
                                                  if isinstance(s[d], dict) and s[d] else None)))
    for c in conts:
        for b in ints:
            laws.append((f'len({c}) <= {b}', lambda s, c=c, b=b: len(s[c]) <= s[b] if s[c] else None))
    laws += coherence_laws(cached, conts)
    kept = []
    for name, test in laws:
        tested, broken, first = 0, 0, set()
        for ob in observations:
            run_broken = False
            for method, s in ob.returns:
                try:
                    r = test(s)
                except (KeyError, TypeError):
                    r = None
                if r is None:
                    continue
                tested += 1
                if not r:
                    broken += 1
                    if not run_broken:
                        first.add(method)
                        run_broken = True
        if tested < MIN_TESTS:
            continue
        if broken == 0 or (broken <= SYMMETRY_BREAK * tested and len(first) == 1):
            kept.append((name, test))
    return kept


def first_break(observation, laws):
    """(method, law name) of the first return at which a kept law fails in this run, or None."""
    for method, s in observation.returns:
        for name, test in laws:
            try:
                r = test(s)
            except (KeyError, TypeError):
                r = None
            if r is False:
                return method, name
    return None


def ochiai(failed_cov, passed_cov):
    """Suspiciousness of each line: failed(l) / sqrt(total_failed x (failed(l) + passed(l)))."""
    nf = len(failed_cov)
    lines = set().union(*failed_cov) if failed_cov else set()
    out = {}
    for ln in lines:
        f = sum(1 for c in failed_cov if ln in c)
        p = sum(1 for c in passed_cov if ln in c)
        out[ln] = f / math.sqrt(nf * (f + p)) if f else 0.0
    return out
