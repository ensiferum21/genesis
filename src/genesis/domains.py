"""Domain contracts (roadmap W05).

A DomainAdapter is the single place that knows how a domain parses tasks, gives
them an exposure identity, checks and scores witnesses, states certificate
obligations, measures cost, generates task families and replays stored results.
It also separates what a candidate may see (`candidate_view`) from what only the
evaluator holds (task identity, family, split, reference optimum, certificates).

Anything an adapter cannot handle is an explicit UNSUPPORTED outcome with a
reason, never an exception that silently drops a task and never a guessed value.

The two graph domains conform; the Lean domain (W08) is to implement the same
interface. The signed meaning of a domain stays kernel.receipts.DOMAINS: each
adapter's contract digest must equal receipts.domain_contract_hash(name).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import combinations
import random

from .common import digest
from .graphs import SearchLimit, canonical_graph, certified_optimum, check_witness
from .kernel import receipts as R
from .models import CandidateGraph, GraphTask

INTERFACE = 'genesis-domain-adapter-v1'
PURPOSES = ('execute', 'exact_reference', 'certificate', 'exposure')
EVALUATOR_ONLY = ('task_id', 'family', 'split', 'optimum', 'reference', 'certificate')


@dataclass(frozen=True)
class Unsupported:
    reason: str
    status: str = 'UNSUPPORTED'

    def record(self):
        return {'status': self.status, 'reason': self.reason}


class DomainAdapter(ABC):
    name: str

    # -- contract ---------------------------------------------------------------------
    def contract(self):
        return {'schema': 'genesis-domain-contract-v1', 'domain': self.name, **R.DOMAINS[self.name]}

    def contract_hash(self):
        return digest(self.contract())

    # -- parsing and identity ------------------------------------------------------------
    @abstractmethod
    def parse(self, raw): ...

    @abstractmethod
    def supports(self, task, purpose): ...

    @abstractmethod
    def exposure_identity(self, task): ...

    # -- views -----------------------------------------------------------------------------
    @abstractmethod
    def candidate_view(self, task): ...

    def evaluator_view(self, task, reference=None):
        return {'task': task.model_dump(mode='json'), 'reference': reference}

    # -- validity, score, obligations, cost ------------------------------------------------
    @abstractmethod
    def validate(self, task, witness): ...

    def score(self, task, witness):
        checked = self.validate(task, witness)
        return checked['value'] if checked['status'] == 'VALID' else None

    @abstractmethod
    def reference(self, task, *, evidence=None, seconds=600): ...

    @abstractmethod
    def certificate_obligations(self, claim, value): ...

    def cost(self, receipt):
        """Normalized cost of one execution receipt (W07 accounting)."""
        result = receipt.get('result') or {}
        return {'status': receipt.get('status'), 'wall_ns': receipt.get('wall_ns'), 'cpu_ns': receipt.get('cpu_ns'),
                'peak_rss_bytes': receipt.get('peak_rss_bytes'), 'queries': result.get('queries'),
                'category': 'candidate-execution'}

    # -- families and replay ----------------------------------------------------------------
    @abstractmethod
    def families(self): ...

    @abstractmethod
    def generate(self, seed, count, split, family, params, excluded=()): ...

    def replay(self, record):
        """Re-check a stored witness record {'task', 'witness', 'value'} from its data alone."""
        task = self.parse(record.get('task'))
        if isinstance(task, Unsupported):
            return task.record()
        checked = self.validate(task, record.get('witness'))
        if checked['status'] != 'VALID':
            return checked
        if checked['value'] != record.get('value'):
            return {'status': 'INVALID', 'reason': 'stored value differs from the re-checked witness'}
        return {'status': 'REPLAYED', 'value': checked['value']}


class GraphHostAdapter(DomainAdapter):
    """Maximum forbidden-subgraph-free subgraph of a finite host graph."""
    MAX_N = 63
    EXACT_MAX_EDGES = 24
    CERTIFICATE_MAX_EDGES = 200          # SAT/DRAT encoding size kept bounded (W03 custody)

    def parse(self, raw):
        if isinstance(raw, GraphTask):
            raw = raw.model_dump(mode='json')
        if not isinstance(raw, dict):
            return Unsupported('task is not an object')
        if raw.get('domain') != self.name:
            return Unsupported(f'task domain {raw.get("domain")!r} is not {self.name}')
        try:
            from .common import canonical
            return GraphTask.model_validate_json(canonical(raw))
        except Exception as exc:                  # pydantic ValidationError and JSON errors alike
            return Unsupported(f'malformed task: {type(exc).__name__}')

    def supports(self, task, purpose):
        if purpose not in PURPOSES:
            return Unsupported(f'unknown purpose {purpose!r}')
        if not isinstance(task, GraphTask) or task.domain != self.name:
            return Unsupported('not a task of this domain')
        if purpose == 'exact_reference' and len(task.edges) > self.CERTIFICATE_MAX_EDGES:
            return Unsupported(f'more than {self.CERTIFICATE_MAX_EDGES} host edges: no certified reference')
        if purpose == 'certificate' and len(task.edges) > self.CERTIFICATE_MAX_EDGES:
            return Unsupported(f'more than {self.CERTIFICATE_MAX_EDGES} host edges: certificate obligations unsupported')
        return None

    def exposure_identity(self, task):
        try:
            return {'canonical': canonical_graph(task), 'method': 'color-refinement+bounded-permutation'}
        except SearchLimit as exc:
            return Unsupported(f'exposure identity needs external adjudication ({exc})')

    def candidate_view(self, task):
        return CandidateGraph(domain=task.domain, n=task.n, edges=task.edges)

    def validate(self, task, witness):
        try:
            edges = tuple(tuple(e) for e in witness)
            checked = check_witness(task, edges)
        except RuntimeError as exc:               # dual predicates disagree: never a verdict
            return {'status': 'CHECKER_ERROR', 'reason': str(exc)}
        except (ValueError, TypeError) as exc:
            return {'status': 'INVALID', 'reason': str(exc)}
        return {'status': 'VALID', 'value': checked['value'], 'checkers': checked['checkers']}

    def reference(self, task, *, evidence=None, seconds=600):
        """Evaluator-only certified optimum, or UNSUPPORTED with the reason."""
        gate = self.supports(task, 'exact_reference')
        if gate:
            return gate
        if len(task.edges) <= self.EXACT_MAX_EDGES:
            try:
                r = certified_optimum(task, self.EXACT_MAX_EDGES)
                return {'status': 'FINITE_CERTIFIED', 'value': r['value'], 'method': 'DUAL_EXACT_SEARCH'}
            except SearchLimit as exc:
                return Unsupported(f'exact search limit: {exc}')
        from .dsl import solve
        from .models import SolverProgram
        from .verification.sat import certified_bounds
        from .verification.tools import ToolUnavailable
        try:
            start = solve(task, SolverProgram(rounds=8), 100000, 0)['selected']
            bounds = certified_bounds(task, seconds=seconds, start_witness=start)
        except ToolUnavailable as exc:
            return Unsupported(f'certificate tools unavailable: {exc}')
        if bounds['status'] != 'OPTIMALITY_CHECKED':
            return Unsupported(f'optimum not certified within {seconds}s (bounds {bounds.get("lower")}..{bounds.get("upper")})')
        out = {'status': 'FINITE_CERTIFIED', 'value': bounds['upper'], 'method': 'SAT_DRAT_UPPER+CHECKED_WITNESS',
               'witness': [list(e) for e in bounds['witness']]}
        if evidence is not None:
            from .verification.certificates import build, persist
            out['certificate_bundle'] = persist(evidence, *build(task, bounds))
        return out

    def certificate_obligations(self, claim, value):
        lower = {'obligation': 'lower_bound', 'evidence': 'witness_check',
                 'checker': R.DOMAINS[self.name]['checker'], 'value': value}
        if claim == 'lower_bound':
            return [lower]
        if claim == 'optimum':
            return [lower, {'obligation': 'upper_bound', 'evidence': 'bound_state',
                            'certificate': 'SAT_DRAT (drat-trim) or HOST_EDGE_COUNT', 'value': value}]
        return [Unsupported(f'no certificate obligations for claim {claim!r}').record()]

    # Families: (generator, parameter space). 'v1-*' are the original small hosts.
    FAMILY_SPACE = {
        'erdos': {'n': (5, 40), 'p': (0.05, 0.95)},
        'bipartite': {'n': (4, 40), 'p': (0.05, 0.95)},
        'planted_cluster': {'n': (6, 40), 'p_in': (0.05, 0.98), 'p_out': (0.0, 0.9)},
    }

    def families(self):
        return {k: dict(v) for k, v in self.FAMILY_SPACE.items()}

    def _edges(self, rng, family, params):
        n = params['n']
        edges = []
        for u, v in combinations(range(n), 2):
            if family == 'erdos':
                p = params['p']
            elif family == 'bipartite':
                p = params['p'] if (u < n // 2) != (v < n // 2) else 0.0
            else:
                p = params['p_in'] if u < n // 2 and v < n // 2 else params['p_out']
            if rng.random() < p:
                edges.append((u, v))
        return tuple(edges)

    def generate(self, seed, count, split, family, params, excluded=()):
        """`count` structurally distinct tasks from one family setting; tasks whose exposure
        identity is unsupported are skipped and counted (never silently admitted)."""
        if family not in self.FAMILY_SPACE:
            raise ValueError(f'unknown family {family!r}')
        space = self.FAMILY_SPACE[family]
        if set(params) != set(space) or any(not lo <= params[k] <= hi for k, (lo, hi) in space.items()):
            raise ValueError(f'parameters {params} outside the family space {space}')
        rng = random.Random(digest({'seed': seed, 'family': family, 'params': params, 'domain': self.name}))
        seen, out, skipped, tries = set(excluded), [], 0, 0
        tag = digest({'family': family, 'params': params})[:8]
        while len(out) < count and tries < count * 200:
            tries += 1
            edges = self._edges(rng, family, params)
            if not edges:
                continue
            task = GraphTask(task_id=f'{split.lower()}-{family}-{tag}-{seed}-{len(out):04}', domain=self.name,
                             n=params['n'], edges=edges, family=f'{family}:{tag}', split=split)
            identity = self.exposure_identity(task)
            if isinstance(identity, Unsupported):
                skipped += 1
                continue
            if identity['canonical'] in seen:
                continue
            seen.add(identity['canonical'])
            out.append(task)
        if len(out) != count:
            raise RuntimeError(f'only {len(out)} of {count} distinct tasks within the generator budget')
        return out, seen, {'skipped_unsupported_identity': skipped, 'draws': tries}


class C4HostAdapter(GraphHostAdapter):
    name = 'c4_host_v2'


class TriangleFreeHostAdapter(GraphHostAdapter):
    name = 'triangle_free_host_v1'


ADAPTERS = {a.name: a for a in (C4HostAdapter(), TriangleFreeHostAdapter())}


def adapter(name):
    """The adapter for `name`, or Unsupported (callers record it; they never guess)."""
    return ADAPTERS.get(name) or Unsupported(f'no domain adapter for {name!r}')
