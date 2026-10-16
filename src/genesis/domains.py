"""Domain contracts (roadmap W05).

A DomainAdapter is the single place that knows how a domain parses tasks, gives
them an exposure identity, checks and scores witnesses, states certificate
obligations, measures cost, generates task families and replays stored results.
It also separates what a candidate may see (`candidate_view`) from what only the
evaluator holds (task identity, family, split, reference optimum, certificates).

Anything an adapter cannot handle is an explicit UNSUPPORTED outcome with a
reason, never an exception that silently drops a task and never a guessed value.

The two graph domains conform, and so does the Lean statement domain
(genesis.formal_research.lean_domain, B17). The signed meaning of a sealed-evaluation
domain stays kernel.receipts.DOMAINS: each graph adapter's contract digest must equal
receipts.domain_contract_hash(name). The Lean domain is not listed there, so no sealed
receipt can name it yet.
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
            out = {'status': 'CHECKER_ERROR', 'reason': str(exc)}
            if getattr(exc, 'results', None) is not None:      # W23: kept for quarantine
                out['disagreement'] = {'question': exc.question, 'inputs': exc.inputs, 'results': exc.results}
            return out
        except (ValueError, TypeError) as exc:
            return {'status': 'INVALID', 'reason': str(exc)}
        return {'status': 'VALID', 'value': checked['value'], 'checkers': checked['checkers']}

    JOINT_REFERENCE = True          # B20_R24: the custodian asks v4 evaluations for the joint LP/SAT reference
    ROWS_REFERENCE = False          # B20_R42: only the triangle-free adapter offers the generated-rows reference

    def reference(self, task, *, evidence=None, seconds=600, joint=False, rows=None):
        """Evaluator-only certified optimum, or UNSUPPORTED with the reason.

        ``joint`` (B20_R24, used by the custodian for v4 evaluations): above the exact-search range, certify
        with ``obstruction.certify`` (exact LP dual certificate, then SAT/DRAT on the remaining gap with the whole
        remaining budget), seeded with the better of an 8-round DSL solution and 1 CPU s of LP-ordered greedy,
        and keep the certificate bundle v2 (witness, LP certificate, CNF/DRAT bytes) in ``evidence``. The SAT-only
        path below (the default, kept for existing callers) stops at the first SAT call that returns UNKNOWN
        within its 60 s limit; on B20_R24's rehearsal panels it left 4 of 30 and 2 of 30 hosts unsupported, of
        which the joint certification closed 5 of 6 within 120 s (evidence/repilots_b20r24)."""
        gate = self.supports(task, 'exact_reference')
        if gate:
            return gate
        if rows is not None:
            # B20_R42 (v5 requests, opt-in): the named generated-rows route above the exact-search range
            if not self.ROWS_REFERENCE:
                return Unsupported(f'{self.name} offers no generated-rows reference')
            if len(task.edges) > self.EXACT_MAX_EDGES:
                return self._rows_reference(task, evidence=evidence, rows=rows)
        if joint and len(task.edges) > self.EXACT_MAX_EDGES:
            return self._joint_reference(task, evidence=evidence, seconds=seconds)
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
            stop = ('; stopped when a SAT call returned UNKNOWN within its 60 s limit'
                    if bounds.get('calls') and bounds['calls'][-1]['status'] not in ('SAT', 'UNSAT') else '')
            return Unsupported(f'optimum not certified within {seconds}s (bounds {bounds.get("lower")}..'
                               f'{bounds.get("upper")}{stop})')
        out = {'status': 'FINITE_CERTIFIED', 'value': bounds['upper'], 'method': 'SAT_DRAT_UPPER+CHECKED_WITNESS',
               'witness': [list(e) for e in bounds['witness']]}
        if evidence is not None:
            from .verification.certificates import build, persist
            out['certificate_bundle'] = persist(evidence, *build(task, bounds))
        return out

    def _joint_reference(self, task, *, evidence, seconds):
        from .discovery import construct as K
        from .discovery import obstruction as O
        from .dsl import solve
        from .models import SolverProgram
        from .verification.tools import ToolUnavailable
        start = tuple(map(tuple, solve(task, SolverProgram(rounds=8), 100000, 0)['selected']))
        lp = tuple(map(tuple, K.lp_greedy(task, K.Budget(1.0), 0)['witness']))
        try:
            rec = O.certify(task, max((start, lp), key=len), seconds=seconds)
        except ToolUnavailable as exc:
            return Unsupported(f'certificate tools unavailable: {exc}')
        if rec['lower'] != rec['upper']:
            return Unsupported(f'optimum not certified within {seconds}s by the joint LP/SAT certification '
                               f'(bounds {rec["lower"]}..{rec["upper"]})')
        out = {'status': 'FINITE_CERTIFIED', 'value': rec['upper'], 'method': 'JOINT_' + rec['upper_evidence']['method'],
               'witness': [list(e) for e in rec['witness']], 'certificate_status': rec['status']}
        if evidence is not None:
            from .verification.certificates import persist
            out['certificate_bundle'] = persist(evidence, rec['bundle'], rec['objects'])
        return out

    def _rows_reference(self, task, *, evidence, rows):
        """generated_certify.reference_record over the request's package and limits; the custody bundle
        (a certificates_rows bundle for an LP certificate over generated rows, else a v2 bundle) goes into
        the evidence store."""
        from .discovery import generated_certify as GC
        from .verification.tools import ToolUnavailable
        try:
            package, _ = GC.known_package(rows['package_sha256'])
        except ValueError as exc:
            return Unsupported(f'generated-rows reference: {exc}')
        route = {k: rows[k] for k in ('separation_seconds', 'max_rows', 'max_total', 'order', 'lp_rounding_seconds')}
        route['enumerator'] = None if rows['enumerator'] == 'generic' else rows['enumerator']
        try:
            out, bundle, blobs = GC.reference_record(task, package, seconds=rows['seconds'], **route)
        except ToolUnavailable as exc:
            return Unsupported(f'certificate tools unavailable: {exc}')
        if bundle is None:
            return Unsupported(out['reason'])
        out = dict(out, witness=[list(e) for e in out['witness']], route=rows['route'],
                   package_sha256=rows['package_sha256'])
        if evidence is not None:
            from .verification.certificates import persist
            out['certificate_bundle'] = persist(evidence, bundle, blobs)
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
    ROWS_REFERENCE = True           # the generated rows are triangle-free pattern bounds (B20_R31/R37)


ADAPTERS = {a.name: a for a in (C4HostAdapter(), TriangleFreeHostAdapter())}


def adapter(name):
    """The adapter for `name`, or Unsupported (callers record it; they never guess)."""
    return ADAPTERS.get(name) or Unsupported(f'no domain adapter for {name!r}')
