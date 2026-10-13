"""Globally disjoint research and evaluation material (Repair A, finding B20-REVIEW-01).

B20 sampled each seed's evaluation targets with ``exclude = pool + dev`` *for that seed
only*. Training runs evaluated on their own development targets and derived usefulness
labels from them, so three evaluation statements that also appeared in training
development material (four evaluation slots) were visible to research. Fresh seeds did
not imply fresh content.

This module replaces that per-script filter with one reusable partition builder:

1. Every research-visible item is registered first, for the whole study (all research
   units: training and evaluation seeds alike, pools, development targets, accessible
   proofs, starting memory). The exposure set is frozen and committed to by a root hash.
2. Evaluation material is then generated against that *global* exposure set, unit by
   unit, under a frozen policy. A candidate is compared with every visible item of the
   same theory under declared relations:

       EXACT        identical statement text
       ALPHA        equal after variable renaming and orientation (``equational.canon``)
       INSTANCE     the candidate is a substitution instance of a visible item (the
                    visible item answers it in one step)
       GENERALIZES  a visible item is a substitution instance of the candidate
                    (research has seen a special case)

   The policy maps each relation to REJECT or QUARANTINE (both keep the candidate out;
   quarantine records it as ambiguous for adjudication). Theory-dependent equivalence
   (e.g. commutativity of an operation) is NOT normalized: no semantic deduplication is
   claimed beyond these syntactic relations, and the manifest says so.
3. If a unit cannot be filled with admissible items, the build fails with
   ``INSUFFICIENT_DISTINCT_MATERIAL``; it never weakens the policy or returns fewer
   items than requested.
4. The manifest freezes the algorithm version, policy (and its hash), RNG derivation,
   exposure root, per-unit accepted identities, rejection counts by relation and the
   quarantined items with reasons. Any change gives a new partition identity.

Insertion routes (lemmas admitted by research, macro steps, memory, curriculum items,
imports) are screened through :class:`InsertionScreen`, a narrow evaluator-side
interface: it answers only ALLOW or BLOCK, keeps relations and matched identities in a
private ledger, rate-limits queries, fails closed on unknown routes, and never puts
reserved statement text into responses or exceptions.

The equational domain is the first adapter (:class:`EquationalAdapter`). The core does
not depend on it: an adapter supplies the theory key, identities, relations and display
text for one domain.
"""
from dataclasses import dataclass, field
import hashlib
import hmac
import random

from ..common import canonical, digest
from . import equational as Q

ALGORITHM = 'genesis-material-partition-v1'
SCHEMA = 'genesis-material-partition-manifest-v1'
RELATIONS = ('EXACT', 'ALPHA', 'INSTANCE', 'GENERALIZES')
ACTIONS = ('REJECT', 'QUARANTINE', 'ALLOW')
ROUTES = ('pool', 'development', 'lemma', 'macro_step', 'memory', 'curriculum', 'import', 'proof', 'policy_feature',
          'sealed')   # 'sealed': statements already sealed or reserved at a custodian (B20_R7)

DEFAULT_POLICY = {'EXACT': 'REJECT', 'ALPHA': 'REJECT', 'INSTANCE': 'REJECT', 'GENERALIZES': 'QUARANTINE',
                  'cross_unit_distinct': True, 'max_draws_per_item': 4000}

RESIDUAL_LIMITS = (
    'relations are syntactic: exact text, alpha-renaming with orientation, and substitution instances in '
    'either direction; equivalence modulo theory laws (e.g. commutativity, associativity) is not detected',
    'a statement absent from the exposure set may still be known to a pretrained model or to the operator; '
    'only Genesis-visible material is screened',
    'false conjectures in research pools are screened like true ones (conservative); proofs are covered '
    'through the statements they prove',
)


class PartitionError(Exception):
    """Structured failure. ``code`` is stable; the message never contains reserved text."""

    def __init__(self, code, **detail):
        self.code, self.detail = code, detail
        super().__init__(f'{code}: ' + ', '.join(f'{k}={v}' for k, v in sorted(detail.items())))


def policy_identity(policy):
    for rel in RELATIONS:
        if policy.get(rel) not in ACTIONS:
            raise PartitionError('POLICY_INCOMPLETE', relation=rel)
    return digest({'algorithm': ALGORITHM, 'policy': policy})


# ---------------------------------------------------------------- equational adapter

def _match(p, t, s):
    if p[0] == 'var':
        if p[1] in s:
            return s if s[p[1]] == t else None
        return {**s, p[1]: t}
    if t[0] != 'fn' or p[1] != t[1] or len(p[2]) != len(t[2]):
        return None
    for a, b in zip(p[2], t[2]):
        s = _match(a, b, s)
        if s is None:
            return None
    return s


def instance_of(general, special):
    """Is ``special`` a substitution instance of ``general`` (either orientation)?"""
    for l, r in (general, (general[1], general[0])):
        s = _match(l, special[0], {})
        if s is not None and _match(r, special[1], s) is not None:
            return True
    return False


def _as_tuple(t):
    if t[0] == 'var':
        return ('var', t[1])
    return ('fn', t[1], tuple(_as_tuple(a) for a in t[2]))


class EquationalAdapter:
    """Material identity and relations for equations of ``learning.equational`` systems.

    The theory is the *variety and signature*, not the axiomatization: the same
    equation in Sheffer's basis and in Wolfram's single axiom is the same mathematical
    statement, so seeing it in one counts as exposure for the other. Different
    signatures (Huntington's + and n versus the Sheffer stroke) are different theories
    even when texts could coincide.
    """
    name = 'equational-v1'

    def theory(self, system):
        spec = Q.SYSTEMS[system]
        return digest({'variety': spec['variety'], 'ops': sorted(spec['ops'].items())})

    def normalize(self, item):
        return Q.canon((_as_tuple(item[0]), _as_tuple(item[1])))

    def raw_text(self, item):
        """The statement exactly as given (no renaming or orientation)."""
        return Q.text((_as_tuple(item[0]), _as_tuple(item[1])))

    def identity(self, system, item):
        eq = self.normalize(item)
        return {'theory': self.theory(system), 'axiomatization': system,
                'text_sha256': hashlib.sha256(self.raw_text(item).encode()).hexdigest(),
                'structural_sha256': digest(repr(eq)), 'size': Q.size(eq[0]) + Q.size(eq[1])}

    def text(self, item):
        return Q.text(self.normalize(item))

    def relation_normalized(self, c, v, c_text=None, v_text=None):
        """Relation between two already-normalized items (raw texts optional, for EXACT)."""
        if c_text is not None and c_text == v_text:
            return 'EXACT'
        if c == v:
            return 'ALPHA'
        if instance_of(v, c):
            return 'INSTANCE'
        if instance_of(c, v):
            return 'GENERALIZES'
        return None

    def relation(self, candidate, visible):
        """The most specific declared relation of ``candidate`` to ``visible``, or None."""
        return self.relation_normalized(self.normalize(candidate), self.normalize(visible),
                                        self.raw_text(candidate), self.raw_text(visible))


ADAPTERS = {'equational-v1': EquationalAdapter}


# ---------------------------------------------------------------- exposure set

@dataclass
class ExposureSet:
    """Every item research could see in a study, grouped by theory. Freeze before use."""
    adapter: object
    _by_theory: dict = field(default_factory=dict)      # theory -> {structural_sha256: [norm, identity, sources]}
    _texts: dict = field(default_factory=dict)          # theory -> {raw text sha256: structural_sha256}
    frozen: dict = None

    def add(self, system, item, *, unit, route):
        if self.frozen is not None:
            raise PartitionError('EXPOSURE_FROZEN')
        if route not in ROUTES:
            raise PartitionError('UNKNOWN_ROUTE', route=route)
        ident = self.adapter.identity(system, item)
        bucket = self._by_theory.setdefault(ident['theory'], {})
        rec = bucket.setdefault(ident['structural_sha256'], [self.adapter.normalize(item), ident, set()])
        rec[2].add((unit, route))
        self._texts.setdefault(ident['theory'], {})[ident['text_sha256']] = ident['structural_sha256']

    def freeze(self):
        keys = sorted((t, s) for t, b in self._by_theory.items() for s in b)
        texts = sorted((t, h) for t, b in self._texts.items() for h in b)
        routes = {}
        for b in self._by_theory.values():
            for _, _, srcs in b.values():
                for _, route in srcs:
                    routes[route] = routes.get(route, 0) + 1
        self.frozen = {'algorithm': ALGORITHM, 'adapter': self.adapter.name, 'items': len(keys),
                       'root': digest({'structural': keys, 'texts': texts}),
                       'route_counts': dict(sorted(routes.items())), 'theories': len(self._by_theory)}
        return self.frozen

    def items(self, theory):
        return self._by_theory.get(theory, {})

    def screen(self, system, candidate):
        """(relation, matched identity) for the most specific relation found, else (None, None)."""
        ident = self.adapter.identity(system, candidate)
        theory, bucket = ident['theory'], self.items(ident['theory'])
        hit = self._texts.get(theory, {}).get(ident['text_sha256'])
        if hit is not None:
            return 'EXACT', bucket[hit][1]
        if ident['structural_sha256'] in bucket:
            return 'ALPHA', bucket[ident['structural_sha256']][1]
        c = self.adapter.normalize(candidate)
        generalizes = None
        for norm, vid, _ in bucket.values():
            if instance_of(norm, c):
                return 'INSTANCE', vid
            if generalizes is None and instance_of(c, norm):
                generalizes = vid
        return ('GENERALIZES', generalizes) if generalizes is not None else (None, None)


# ---------------------------------------------------------------- partition builder

def derive_rng(study_seed, unit):
    """Deterministic per-unit RNG, recorded in the manifest as a derivation rule."""
    return random.Random(int(digest({'study_seed': study_seed, 'unit': unit})[:16], 16))


def build_partition(*, study, study_seed, visible, units, sampler, count, policy=None, adapter=None):
    """Freeze a global exposure set and draw evaluation material against it.

    visible: iterable of (system, item, unit, route) for EVERY research-visible item of the
             study, generated before any evaluation material.
    units:   ordered list of (unit_label, system) needing evaluation material.
    sampler: sampler(unit_label, system, rng) -> iterator of candidate items.
    count:   items required per unit.
    Returns the manifest (DEV: includes statement text). Raises PartitionError on
    insufficient distinct material; never returns fewer items than requested.
    """
    policy = dict(DEFAULT_POLICY if policy is None else policy)
    adapter = adapter or EquationalAdapter()
    pid = policy_identity(policy)
    exposure = ExposureSet(adapter)
    for system, item, unit, route in visible:
        exposure.add(system, item, unit=unit, route=route)
    frozen = exposure.freeze()
    accepted_all = {}          # theory -> list of normalized items already reserved (cross-unit)
    out_units = {}
    for unit, system in units:
        rng = derive_rng(study_seed, unit)
        theory = adapter.theory(system)
        accepted, rejected, quarantined, seen = [], {}, [], set()
        draws, limit = 0, policy['max_draws_per_item'] * count
        it = iter(sampler(unit, system, rng))
        while len(accepted) < count:
            if draws >= limit:
                raise PartitionError('INSUFFICIENT_DISTINCT_MATERIAL', unit=unit, accepted=len(accepted),
                                     requested=count, draws=draws)
            try:
                cand = next(it)
            except StopIteration:
                raise PartitionError('INSUFFICIENT_DISTINCT_MATERIAL', unit=unit, accepted=len(accepted),
                                     requested=count, draws=draws) from None
            draws += 1
            norm = adapter.normalize(cand)
            key = digest(repr(norm))
            if key in seen:
                rejected['DUPLICATE_IN_UNIT'] = rejected.get('DUPLICATE_IN_UNIT', 0) + 1
                continue
            seen.add(key)
            rel, ident = exposure.screen(system, cand)
            action = policy[rel] if rel else 'ALLOW'
            if action == 'REJECT':
                rejected[rel] = rejected.get(rel, 0) + 1
                continue
            if action == 'QUARANTINE':
                quarantined.append({'text': adapter.text(cand), 'relation': rel,
                                    'against_structural_sha256': ident['structural_sha256']})
                continue
            if policy['cross_unit_distinct']:
                clash = None
                for other in accepted_all.get(theory, []):
                    clash = adapter.relation(cand, other)
                    if clash in RELATIONS:
                        break
                    clash = None
                if clash:
                    rejected[f'CROSS_UNIT_{clash}'] = rejected.get(f'CROSS_UNIT_{clash}', 0) + 1
                    continue
            accepted.append(norm)
            accepted_all.setdefault(theory, []).append(norm)
        out_units[unit] = {'system': system, 'theory': theory, 'requested': count, 'draws': draws,
                           'accepted': [dict(adapter.identity(system, a), text=adapter.text(a)) for a in accepted],
                           'rejected_counts': dict(sorted(rejected.items())), 'quarantined': quarantined}
    body = {'schema': SCHEMA, 'algorithm': ALGORITHM, 'study': study, 'adapter': adapter.name,
            'policy': policy, 'policy_sha256': pid,
            'rng_derivation': "random.Random(int(digest({'study_seed': S, 'unit': U})[:16], 16))",
            'study_seed': study_seed, 'exposure': frozen, 'units': out_units,
            'residual_limits': list(RESIDUAL_LIMITS)}
    body['partition_id'] = digest(body)
    return body


def equational_sampler(*, min_total, max_total, max_term, max_invalid=20_000):
    """Candidate stream of true equations (the B20 target distribution: random pairs of
    terms with equal term functions, min_total <= nodes <= max_total). Every candidate is a
    draw for the builder; the stream ends after ``max_invalid`` consecutive unusable pairs."""
    def sample(unit, system, rng):
        buckets = Q._buckets(system, max_term)
        keys = sorted(buckets, key=repr)
        invalid = 0
        while invalid < max_invalid:
            b = buckets[keys[rng.randrange(len(keys))]]
            a, c = rng.choice(b), rng.choice(b)
            n = Q.size(a) + Q.size(c)
            if a == c or not (min_total <= n <= max_total) or (a[0] == 'var' and c[0] == 'var'):
                invalid += 1
                continue
            e = Q.canon((a, c))
            if e[0] == e[1]:
                invalid += 1
                continue
            invalid = 0
            yield e
    return sample


def accepted_items(manifest, unit):
    """The evaluation items of ``unit`` as equation tuples (DEV manifests carry text)."""
    from ..fol import parse
    out = []
    for a in manifest['units'][unit]['accepted']:
        f = parse(a['text'])
        while f[0] == 'all':
            f = f[2]
        out.append(Q.canon((f[1], f[2])))
    return out


def partition_problems(manifest, visible, *, adapter=None):
    """Pure validator. Recomputes the exposure root and screens every accepted item.

    Returns a list of {'code', ...} dicts with stable codes; empty means no problem found.
    It never mutates anything and never trusts the manifest's own verdicts.
    """
    problems = []
    adapter = adapter or ADAPTERS.get(manifest.get('adapter'), EquationalAdapter)()
    if manifest.get('schema') != SCHEMA or manifest.get('algorithm') != ALGORITHM:
        return [{'code': 'UNKNOWN_MANIFEST'}]
    body = {k: v for k, v in manifest.items() if k != 'partition_id'}
    if digest(body) != manifest.get('partition_id'):
        problems.append({'code': 'PARTITION_ID_MISMATCH'})
    try:
        if policy_identity(manifest['policy']) != manifest['policy_sha256']:
            problems.append({'code': 'POLICY_MISMATCH'})
    except PartitionError as exc:
        problems.append({'code': exc.code})
        return problems
    exposure = ExposureSet(adapter)
    for system, item, unit, route in visible:
        exposure.add(system, item, unit=unit, route=route)
    frozen = exposure.freeze()
    if frozen['root'] != manifest['exposure']['root']:
        problems.append({'code': 'EXPOSURE_ROOT_MISMATCH', 'recorded': manifest['exposure']['root'],
                         'recomputed': frozen['root']})
    policy = manifest['policy']
    reserved = {}
    for unit, u in sorted(manifest['units'].items()):
        if len(u['accepted']) != u['requested']:
            problems.append({'code': 'COUNT_MISMATCH', 'unit': unit})
        items = accepted_items(manifest, unit)
        for idx, item in enumerate(items):
            ident = adapter.identity(u['system'], item)
            if ident['structural_sha256'] != u['accepted'][idx]['structural_sha256']:
                problems.append({'code': 'IDENTITY_MISMATCH', 'unit': unit, 'index': idx})
            rel, _ = exposure.screen(u['system'], item)
            if rel and policy[rel] != 'ALLOW':
                problems.append({'code': 'VISIBLE_COLLISION', 'unit': unit, 'index': idx, 'relation': rel})
            if policy.get('cross_unit_distinct'):
                for (ounit, oidx), other in reserved.get(ident['theory'], {}).items():
                    if ounit != unit:
                        rel2 = adapter.relation(item, other)
                        if rel2:
                            problems.append({'code': 'CROSS_UNIT_COLLISION', 'unit': unit, 'index': idx,
                                             'other_unit': ounit, 'relation': rel2})
            reserved.setdefault(ident['theory'], {})[(unit, idx)] = item
    return problems


# ---------------------------------------------------------------- insertion screening

class InsertionScreen:
    """Evaluator-side screen for every route that inserts material into research.

    Research code receives only ``{'decision': 'ALLOW' | 'BLOCK'}``. Relations, matched
    identities and the queried item's digest stay in the private ledger. Reserved items
    are held in memory only; the public commitment uses a salted HMAC so that hashes of
    a small enumerable statement space cannot be inverted. Queries are rate-limited
    (``query_budget``); an exhausted budget, an unknown route or a malformed item BLOCKs.
    """

    def __init__(self, reserved, *, salt, adapter=None, policy=None, query_budget=100_000):
        """reserved: iterable of (system, item) evaluation material to protect."""
        if not isinstance(salt, (bytes, bytearray)) or len(salt) < 16:
            raise PartitionError('WEAK_SALT')
        self._adapter = adapter or EquationalAdapter()
        self._policy = dict(DEFAULT_POLICY if policy is None else policy)
        self._salt = bytes(salt)
        self._reserved = {}
        for system, item in reserved:
            self._reserved.setdefault(self._adapter.theory(system), []).append(self._adapter.normalize(item))
        self._ledger = []
        self._budget = query_budget

    def commitment(self):
        """Salted commitment to the reserved set (safe to publish); no statement text."""
        leaves = sorted(hmac.new(self._salt, canonical([t, repr(i)]), 'sha256').hexdigest()
                        for t, items in self._reserved.items() for i in items)
        return {'algorithm': ALGORITHM, 'scheme': 'hmac-sha256(salt, [theory, structural repr])',
                'items': len(leaves), 'root': digest(leaves)}

    def __call__(self, route, system, item):
        if self._budget <= 0:
            self._ledger.append({'route': route, 'decision': 'BLOCK', 'reason': 'QUERY_BUDGET_EXHAUSTED'})
            return {'decision': 'BLOCK'}
        self._budget -= 1
        if route not in ROUTES or route == 'sealed':      # 'sealed' is an exposure source, not an insertion route
            self._ledger.append({'route': route, 'decision': 'BLOCK', 'reason': 'UNKNOWN_ROUTE'})
            return {'decision': 'BLOCK'}
        try:
            theory = self._adapter.theory(system)
            norm = self._adapter.normalize(item)
        except Exception as exc:      # malformed item: fail closed, no text in the ledger
            self._ledger.append({'route': route, 'decision': 'BLOCK', 'reason': f'MALFORMED:{type(exc).__name__}'})
            return {'decision': 'BLOCK'}
        rank = {r: i for i, r in enumerate(RELATIONS)}
        best = None
        for idx, res in enumerate(self._reserved.get(theory, [])):
            # the inserted item is "visible"; the reserved item is the candidate being protected
            rel = self._adapter.relation_normalized(res, norm)
            if rel is not None and (best is None or rank[rel] < rank[best[0]]):
                best = (rel, idx)
        decision = 'ALLOW' if best is None or self._policy[best[0]] == 'ALLOW' else 'BLOCK'
        self._ledger.append({'route': route, 'system': system, 'item_sha256': digest(repr(norm)),
                             'decision': decision, 'relation': best[0] if best else None,
                             'reserved_index': best[1] if best else None})
        return {'decision': decision}

    def private_ledger(self):
        return [dict(x) for x in self._ledger]

    def summary(self):
        """Coarse public summary: counts by route and decision, no identities."""
        out = {}
        for x in self._ledger:
            k = f"{x['route']}:{x['decision']}"
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))


class CustodianStatementScreen:
    """Research-side client of the custodian's signed statement screen (B20R7-OPEN-2).

    ``query(items)`` sends ``[{'route', 'system', 'statement'}]`` to the custodian (for example
    ``custodian.screen_statements_for_research``) and returns its signed envelope; ``verify`` and
    the custodian's public key check it. Any failure (transport, signature, a receipt for other
    items, a malformed decision) BLOCKs: research never inserts on an unverifiable answer."""

    def __init__(self, query, custodian_public_key, *, verify):
        self._query, self._key, self._verify = query, custodian_public_key, verify
        self._log = []

    def __call__(self, route, system, item):
        try:
            items = [{'route': route, 'system': system, 'statement': Q.text((_as_tuple(item[0]), _as_tuple(item[1])))}]
            payload = self._verify(self._query(items), self._key)
            ok = payload.get('schema') == 'genesis-statement-screening-receipt-v1' and \
                payload.get('items_sha256') == digest(items) and payload.get('decisions') in (['ALLOW'], ['BLOCK'])
            decision = payload['decisions'][0] if ok else 'BLOCK'
            reason = None if ok else 'RECEIPT_MISMATCH'
        except Exception as exc:
            decision, reason = 'BLOCK', f'UNVERIFIABLE:{type(exc).__name__}'
        self._log.append({'route': route, 'decision': decision, 'reason': reason})
        return {'decision': decision}

    def log(self):
        return [dict(x) for x in self._log]


def both(*screens):
    """A screen that ALLOWs only when every given screen ALLOWs (e.g. the study's own insertion
    screen and the custodian's)."""
    def screen(route, system, item):
        for s in screens:
            if s(route, system, item)['decision'] != 'ALLOW':
                return {'decision': 'BLOCK'}
        return {'decision': 'ALLOW'}
    return screen


def allow_all(route, system, item):
    """Explicit no-screen marker for DEV code paths that have nothing reserved."""
    return {'decision': 'ALLOW'}


# ---------------------------------------------------------------- contamination bookkeeping

def contamination_label(manifest, exposure_events):
    """Panels consumed by new exposure. exposure_events: iterable of (unit, structural_sha256, route).
    Returns {unit: {'status': 'CONTAMINATED'|'CLEAN', 'items': [...]}}; affected units are retired
    for the affected claim; nothing is deleted."""
    out = {u: {'status': 'CLEAN', 'items': []} for u in manifest['units']}
    index = {(u, a['structural_sha256']) for u, d in manifest['units'].items() for a in d['accepted']}
    for unit, sha, route in exposure_events:
        if (unit, sha) in index:
            out[unit]['status'] = 'CONTAMINATED'
            out[unit]['items'].append({'structural_sha256': sha, 'route': route})
    return out


__all__ = ['ALGORITHM', 'SCHEMA', 'RELATIONS', 'DEFAULT_POLICY', 'PartitionError', 'EquationalAdapter',
           'ExposureSet', 'build_partition', 'equational_sampler', 'accepted_items', 'partition_problems',
           'InsertionScreen', 'allow_all', 'contamination_label', 'policy_identity', 'instance_of', 'derive_rng']
