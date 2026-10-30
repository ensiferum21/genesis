"""The causal obstacle model (research plane; the Foundry directive's item 2, `docs/OMEGA_SELF_REPAIR.md` §2.3).

An obstacle is recorded as: the problem, the observed failure, the competing causes (hypotheses, each with a
posterior), the missing capability (the class of what is missing), the proposed intervention, its predicted effect,
its cost, the uncertainty, and the experimental evidence. Causes stay hypotheses until experiments discriminate them.

**Hypotheses.** One per executable line of the repairable file ("the fault is at line l"), and one for the causes no
local repair reaches ("elsewhere": the checker, the data, an infeasible objective). Priors are uniform over lines, with
ELSEWHERE_PRIOR for the last.

**Experiments** are trials: workloads of the experimenter's own choosing (a fresh seed and a length), run on the
current source, observed through the probe (coverage, conservation laws). Under "line l", a trial that executes l
fails with probability THETA and one that does not with EPSILON; under "elsewhere", with the failure rate seen so far.
After each trial the posterior is updated by Bayes' rule.

Short trials matter: a defect that shows within a few operations of any long run is often absent from very short
ones, and the contrast between short runs that pass and those that fail is what separates the causes (as probing a
system at lower energy shows which mode breaks first).

**Choosing the next experiment** is the expected information gain about the cause per unit cost, the quantity a
physicist maximises when choosing a measurement: for each candidate trial (a fresh seed at each of LENGTHS), the
probability that it covers each line is predicted from the trials of that length so far (Laplace-smoothed), the
outcome's predictive distribution under each hypothesis follows, and the gain is the mutual information between the
outcome and the cause. The cost is the trial's length in operations.

**Rising energy.** A length at which QUIET trials have all passed is quiet: the failure mode is not excited at that
energy (a defect in eviction needs more operations than the capacity). The next experiment is chosen among the lengths
that are not quiet, so probing moves to longer trials until the mode shows.

**Stopping.** Causes stay hypotheses until a discriminating experiment supports them: the model stops when the
posterior's entropy is below STOP_BITS *and* a fresh trial (not only the reproducer) has failed, or when the trials are
spent. (Without that rule, short passing trials alone concentrate belief on whatever they never reach.)

A conserved law broken first in some method (`probe.first_break`) multiplies the lines of that method by LAW_BOOST: a
second, independent line of evidence."""
import math

THETA, EPSILON = 0.6, 0.02
ELSEWHERE_PRIOR = 0.05
LENGTHS = (4, 12, 40, 120, 400)
LAW_BOOST = 4.0
STOP_BITS = 2.0
QUIET = 3


def entropy(ps):
    return -sum(p * math.log2(p) for p in ps if p > 0)


def bernoulli_h(p):
    return entropy([p, 1 - p])


class ObstacleModel:
    def __init__(self, problem, failure, lines, method_of_line):
        self.record = {'problem': problem, 'observed_failure': failure, 'competing_causes': None,
                       'missing_capability': None, 'intervention': None, 'predicted_effect': None, 'cost': 0,
                       'uncertainty_bits': None, 'evidence': []}
        self.lines = sorted(lines)
        self.method_of = dict(method_of_line)
        n = len(self.lines)
        self.post = {ln: (1 - ELSEWHERE_PRIOR) / n for ln in self.lines}
        self.post['elsewhere'] = ELSEWHERE_PRIOR
        self.trials = []            # (length, covered lines, failed)

    # ---------------------------------------------------------------------------------------------- inference
    def _fail_rate(self):
        if not self.trials:
            return 0.5
        return (sum(1 for t in self.trials if t[2]) + 1) / (len(self.trials) + 2)

    def update(self, length, covered, failed, label='', cost=None):
        """One trial of `length` (the requested workload size, the key of the per-length statistics) that cost `cost`
        operations (default: length)."""
        self.trials.append((length, set(covered), failed))
        fr = self._fail_rate()
        for h in self.post:
            if h == 'elsewhere':
                p = fr
            else:
                p = THETA if h in covered else EPSILON
            self.post[h] *= p if failed else 1 - p
        self._normalise()
        self.record['evidence'].append({'trial': label, 'length': length, 'failed': failed,
                                        'covered': len(covered)})
        self.record['cost'] += length if cost is None else cost

    def boost_method(self, method, why):
        for ln in self.lines:
            if self.method_of.get(ln) == method:
                self.post[ln] *= LAW_BOOST
        self._normalise()
        self.record['evidence'].append({'law_break': why, 'method': method})

    def _normalise(self):
        z = sum(self.post.values()) or 1.0
        for h in self.post:
            self.post[h] /= z

    def entropy(self):
        return entropy(list(self.post.values()))

    # ---------------------------------------------------------------------------------------------- design
    def _cover_prob(self, length):
        same = [t for t in self.trials if t[0] == length]
        return {ln: (sum(1 for t in same if ln in t[1]) + 1) / (len(same) + 2) for ln in self.lines}

    def gain(self, length):
        """Expected information (bits) about the cause from one fresh trial of this length."""
        cov = self._cover_prob(length)
        fr = self._fail_rate()
        pf = {h: (fr if h == 'elsewhere' else cov[h] * THETA + (1 - cov[h]) * EPSILON) for h in self.post}
        p_fail = sum(self.post[h] * pf[h] for h in self.post)
        return bernoulli_h(p_fail) - sum(self.post[h] * bernoulli_h(pf[h]) for h in self.post)

    def quiet(self, length):
        same = [t for t in self.trials if t[0] == length]
        return len(same) >= QUIET and not any(t[2] for t in same)

    def next_length(self):
        """Among the lengths that are not quiet, the one with the most expected information per operation."""
        live = [n for n in LENGTHS if not self.quiet(n)] or [max(LENGTHS)]
        return max(live, key=lambda n: (self.gain(n) / n, -n))

    def supported(self):
        """A fresh trial has failed (the first trial recorded is the reproducer)."""
        return any(t[2] for t in self.trials[1:])

    def done(self):
        return self.entropy() < STOP_BITS and self.supported()

    # ---------------------------------------------------------------------------------------------- reading
    def ranked_lines(self):
        return sorted((h for h in self.post if h != 'elsewhere'), key=lambda h: (-self.post[h], h))

    def ranked_methods(self):
        mass = {}
        for ln in self.lines:
            m = self.method_of.get(ln)
            if m:
                mass[m] = mass.get(m, 0.0) + self.post[ln]
        return sorted(mass, key=lambda m: -mass[m]), mass

    def summary(self, k=6):
        methods, mass = self.ranked_methods()
        self.record['competing_causes'] = ([{'cause': f'line {ln} ({self.method_of.get(ln)})',
                                             'posterior': round(self.post[ln], 4)} for ln in self.ranked_lines()[:k]]
                                           + [{'cause': 'elsewhere (not locally repairable)',
                                               'posterior': round(self.post['elsewhere'], 4)}])
        self.record['uncertainty_bits'] = round(self.entropy(), 3)
        self.record['methods'] = {m: round(mass[m], 4) for m in methods}
        return self.record
