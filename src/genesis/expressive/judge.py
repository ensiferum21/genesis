"""The language judge (X2, B20_R154; KERNEL SIDE; `docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §3): a named statement enters
the language only if the language with it does better, where Genesis cannot see.

**The question.** Does Λ_k + s let a search find better engines than Λ_k, on graphs no one has seen, at matched
compute? The research plane submits the parent library, the candidate library (the parent plus the named statements
it claims), the claim and the starting engines:
  * claim 'search': under the inventor's search (s makes good engines easier to find at the bound);
  * claim 'expressiveness': under the ceiling search (s lets the bound hold better engines; §2).
**What the judge does itself** (it takes no number from the submitter):
  1. correctness: both libraries rebuild from their JSON to their versions; the candidate is the parent plus exactly
     the statements claimed, in order; the claim is one of the two; the starting engines are valid in the parent;
  2. for an expressiveness claim, the structure: a statement whose expansion is a single item cannot raise the value
     reachable within the bound (a call to it is as long as what it expands to), so such a claim fails 'structural';
  3. the control: a statement with as many items as the largest claimed one, drawn by the judge from its own seed
     (random statements of Λ1), added to the parent. The candidate must beat it too, so that having one more
     statement to call is not what gets admitted;
  4. the searches: for each language (parent, candidate, control) and replicate r, the registered search (`SEARCHES`,
     closed) from the starting engines, on TRAINING graphs the judge draws from its seed, with the same seed in every
     language for replicate r, and the same runs wherever the languages evaluate the same engine (common random
     numbers);
  5. the truth: each search's winner on TRUTH graphs the judge draws from its seed: per graph, (value - reference) /
     reference, the reference the domain's reference engine (REX);
  6. for an expressiveness claim, saturation: the parent's ceiling search is run again stopped at half its budget (the
     same trajectory); if the full ceiling still beats the half one (one-sided Wilcoxon p < ALPHA and a mean of at
     least MATERIAL), the ceiling is not a ceiling there, a gain could be the search's, and the claim fails
     'not_saturated' (found while building: without this check a one-item statement, which can add nothing at the
     bound, was admitted as expressive because it made the pattern easier to find);
  7. the decision: per truth graph, the candidate's mean gain over the replicates minus the parent's, and minus the
     control's; ADMITTED if both one-sided Wilcoxon signed-rank tests give p < ALPHA and both mean differences are at
     least MATERIAL. Otherwise refused, failing 'sealed'.
The submitter receives {'admitted': bool, 'failed': None or the check that failed}; the numbers go to the ledger, for
the study. The research plane never sees the training or truth graphs; the judge never sees how a statement was
found. Each ledger entry records the digests of the code the judge executed (this module, `expressive.operators`,
`expressive.lambda1`, `candidate_kinds.mcx3`, the protected `autonomy.feedback`), which a study checks: the searches
use the research plane's operators, so a change there would change what the judge measures.

**Domains.** A domain gives `draw(seed, n, split)` (graphs), `run(config, graph, seed)` (an engine's value) and
`reference` (the reference engine's configuration); optionally `search_scale`, a factor on the registered budgets
(the fixture's searches are short), and `bound`, the description-length bound of the searches (default 32). `expressive.fixture.FixtureDomain` is the planted test domain; the max-cut domain
(mcx3 at a CPU budget) is for the studies.

Digest pinned (`tests_genesis/test_expressive_judge.py`); a change is a human-gated amendment.
"""
import hashlib
import json
from pathlib import Path
import random
import statistics

from ..candidate_kinds import mcx3 as K
from . import lambda1 as L1
from . import operators as O

MATERIAL = 0.0005
ALPHA = 0.05
SEARCHES = {'inventor': {'evals': 240, 'size': 4, 'process': None},
            'ceiling': {'evals': 480, 'size': 8, 'process': {'pop': 32, 'children': 16, 'leaders': 4,
                                                             'tournament': 3, 'p_cross': 0.25}}}
CODE = ('expressive/judge.py', 'expressive/operators.py', 'expressive/lambda1.py', 'candidate_kinds/mcx3.py',
        'autonomy/feedback.py')
_SRC = Path(__file__).resolve().parents[1]


def _h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12], 16)


def code_digests():
    return {p: hashlib.sha256((_SRC / p).read_bytes()).hexdigest() for p in CODE}


class LanguageJudge:
    def __init__(self, domain, sealed_seed, replicates=2, train=8, truth=24):
        self._domain, self._seed, self._replicates = domain, sealed_seed, replicates
        self._train = domain.draw(_h('train', sealed_seed), train, 'train')
        self._truth = domain.draw(_h('truth', sealed_seed), truth, 'truth')
        self._ledger, self._runs, self._n = [], {}, 0

    # ------------------------------------------------------------------------------------------------ runs
    def _run(self, cfg, graph, occ):
        k = (json.dumps(cfg, sort_keys=True), graph['id'], occ)
        if k not in self._runs:
            self._runs[k] = self._domain.run(cfg, graph, _h(self._seed, k))
        return self._runs[k]

    def _ref(self, graph):
        return self._run(self._domain.reference, graph, 'ref')

    def _search(self, library, name, starts, rep, fraction=1.0):
        from ..autonomy import feedback as FB
        from ..autonomy import selfimprove as SI
        spec = SEARCHES[name]
        evals = max(16, int(spec['evals'] * getattr(self._domain, 'search_scale', 1.0) * fraction))
        tasks = self._train[:spec['size']]
        occ = {}

        def ev(genome, split):
            cfg = L1.config(genome, library)
            k = json.dumps(cfg, sort_keys=True)
            n = occ.get(k, 0)
            occ[k] = n + 1
            return statistics.mean(self._run(cfg, t, n) / self._ref(t) for t in tasks)
        ops = SI.seeded_ops(O.ops('L1', library, bound=getattr(self._domain, 'bound', O.BOUND)),
                            [dict(s) for s in starts])
        seed = _h(self._seed, 'search', name, rep)
        if spec['process'] is None:
            winner, _ = FB.steady_state_search(ops, ev, evals, seed, contract=False)
        else:
            winner, _ = SI.search(dict(SI.ORIGINAL, **spec['process']), ops, ev, evals, seed, contract=False,
                                  calibrate='AB')
        return L1.config(winner, library)

    def _truth_gains(self, cfg):
        return [(self._run(cfg, t, 0) - self._ref(t)) / self._ref(t) for t in self._truth]

    def _control(self, parent, size):
        """A random statement of `size` items from the judge's seed, added to the parent."""
        rng = random.Random(_h(self._seed, 'control', parent.version, self._n))
        for _ in range(500):
            items = [O.random_stmt(rng, 'L1', guards=(i < size - 1)) for i in range(size)]
            try:
                body = K.render(K.canonical(tuple(O._freeze(x) for x in items), parent.guard_calls()))
                if L1.length(K.parse(body, calls=True)) != size:
                    continue
                return parent.extend(f'ctl{self._n}', body, provenance={'control': True})
            except ValueError:
                continue
        raise RuntimeError('no control statement')

    # ------------------------------------------------------------------------------------------------ the decision
    def submit(self, parent_json, candidate_json, names, claim='search', starts=None):
        self._n += 1
        rec = {'n': self._n, 'names': list(names), 'claim': claim, 'code': code_digests()}
        try:
            parent, cand = L1.Library.from_json(parent_json), L1.Library.from_json(candidate_json)
            starts = [dict(s) for s in (starts or [dict(K.DEFAULT)])]
            for s in starts:
                L1.config(s, parent)
        except (ValueError, KeyError, TypeError):
            return self._close(rec, False, 'correctness')
        added = cand.defs[len(parent.defs):]
        if (claim not in ('search', 'expressiveness') or not names or cand.defs[:len(parent.defs)] != parent.defs
                or [d['name'] for d in added] != list(names)):
            return self._close(rec, False, 'correctness')
        if claim == 'expressiveness':
            for d in added:
                call = d['name'] + (f'({",".join(str(lo) for lo, _ in d["ranges"])})' if d['params'] else '')
                if L1.length(L1.expand(K.parse(call + ' b1', calls=True), cand)) - 1 <= 1:
                    return self._close(rec, False, 'structural')
        size = max(L1.length(K.parse(d['body'], calls=True, params=True)) for d in added)
        control = self._control(parent, size)
        rec['control'] = control.defs[-1]['body']
        search = 'inventor' if claim == 'search' else 'ceiling'
        lanes = {}
        for lang, lib in (('parent', parent), ('candidate', cand), ('control', control)):
            winners = [self._search(lib, search, starts, r) for r in range(self._replicates)]
            lanes[lang] = [statistics.mean(x) for x in zip(*(self._truth_gains(w) for w in winners))]
            rec[f'{lang}_winners'] = [w['prog'] for w in winners]
        from scipy.stats import wilcoxon

        def greater(d):
            nz = [x for x in d if x != 0]
            return {'mean': statistics.mean(d), 'p': float(wilcoxon(nz, alternative='greater').pvalue) if nz else 1.0}
        if claim == 'expressiveness':
            half = [self._search(parent, search, starts, r, fraction=0.5) for r in range(self._replicates)]
            hl = [statistics.mean(x) for x in zip(*(self._truth_gains(w) for w in half))]
            sat = greater([a - b for a, b in zip(lanes['parent'], hl)])
            rec['saturation'] = sat
            if sat['p'] < ALPHA and sat['mean'] >= MATERIAL:
                return self._close(rec, False, 'not_saturated')
        tests = {}
        for other in ('parent', 'control'):
            tests[other] = greater([a - b for a, b in zip(lanes['candidate'], lanes[other])])
        rec['tests'] = tests
        rec['lanes'] = {k: statistics.mean(v) for k, v in lanes.items()}
        ok = all(t['p'] < ALPHA and t['mean'] >= MATERIAL for t in tests.values())
        return self._close(rec, ok, None if ok else 'sealed')

    def _close(self, rec, admitted, failed):
        rec.update(admitted=admitted, failed=failed)
        self._ledger.append(rec)
        return {'admitted': admitted, 'failed': failed}

    def ledger(self):
        """The study's view: every submission with its numbers."""
        return json.loads(json.dumps(self._ledger))
