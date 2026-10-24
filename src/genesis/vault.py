"""The discovery vault (Genesis Ω; master contract §3, §7, §8): exact artifacts, their lineage and statuses, the
capability graph, and a bounded reactivation queue, on the existing store (`store.Store`: single-writer SQLite
journal, immutable content-addressed objects, hash-chained events, verification, snapshots, recoverable export).

**Artifacts are immutable.** An artifact is a record {schema, type, content, domain, creator, parents, seeds,
contracts, costs, environment, replay, created}; its ID is the SHA-256 of its canonical bytes, so the same record
is stored once and an ID always returns exactly the bytes that were stored. `created` is empty unless the caller
pins it (the time of storing is in the first annotation), so identical content has one ID. TYPES are the contract's (ProblemSpec,
WorldSpec, ObservableSpec, ProgramSpec, ProcessSpec, ExperimentSpec, EvidenceRecord, DiscoveryRecord,
CapabilityRecord, ResearchOpportunity).

**Everything said about an artifact is appended, never edited** (annotations and edges are immutable entities too,
numbered per artifact). An annotation may set:
  * the STATUS (generated, exploratory, reproducible, verified, promoted, rejected, dormant, superseded), only along
    TRANSITIONS; `verified` and `promoted` need EvidenceRecord artifacts naming a recorded study and its record test
    (the vault proposes; only recorded, independently recomputed evidence promotes);
  * the EXPLANATION status (unknown, conjectural, empirical, established), separate from the status: a discovery may
    be promoted for a verified use while its explanation stays unknown;
  * the FAILURE kind (incorrect, too_expensive, context_limited, missing_prerequisite, unexplained, promising);
  * the NOVELTY rung (syntactic, behavioral, mechanistic, verified_useful, transferred, literature_checked,
    reviewed).
**Edges** of the capability graph (requires, enables, improves, explains, contradicts, equivalent_to, generalizes,
transfers_to, combines_with, failed_due_to, reactivated_by) carry their evidence, confidence, scope and provenance.
Some edges are inferred rather than shown; their confidence says so, and they are never treated as proven.

**Reactivation** (`opportunities`, `reactivate`). A trigger is a CapabilityRecord that declares what it `unlocks`
(tags). The candidates are dormant artifacts with a `failed_due_to` edge to a prerequisite tag the trigger unlocks.
They are ranked by the score stored on the edge (ties by ID), with at most `fuel` per trigger. An artifact already
reactivated by the same trigger is never retried (an unchanged retry). A reactivation records a `reactivated_by` edge
and returns the artifact to `exploratory`; what the re-test finds is annotated by the caller. `cascade` runs
triggers from a queue with a depth limit and a seen set, so cycles and fan-out stay bounded.
"""
import json

from .common import canonical, digest, utcnow
from .store import Store

SCHEMA = 'genesis-vault-artifact-v1'
TYPES = ('ProblemSpec', 'WorldSpec', 'ObservableSpec', 'ProgramSpec', 'ProcessSpec', 'ExperimentSpec',
         'EvidenceRecord', 'DiscoveryRecord', 'CapabilityRecord', 'ResearchOpportunity')
STATUSES = ('generated', 'exploratory', 'reproducible', 'verified', 'promoted', 'rejected', 'dormant', 'superseded')
TRANSITIONS = {'generated': {'exploratory', 'rejected', 'dormant'},
               'exploratory': {'reproducible', 'dormant', 'rejected'},
               'reproducible': {'verified', 'dormant', 'rejected', 'exploratory'},
               'verified': {'promoted', 'dormant', 'superseded', 'rejected'},
               'promoted': {'superseded', 'rejected'},
               'dormant': {'exploratory', 'rejected', 'superseded'},
               'rejected': set(), 'superseded': set()}
NEEDS_EVIDENCE = {'verified', 'promoted'}
EXPLANATIONS = ('unknown', 'conjectural', 'empirical', 'established')
FAILURES = ('incorrect', 'too_expensive', 'context_limited', 'missing_prerequisite', 'unexplained', 'promising')
NOVELTY = ('syntactic', 'behavioral', 'mechanistic', 'verified_useful', 'transferred', 'literature_checked',
           'reviewed')
EDGES = ('requires', 'enables', 'improves', 'explains', 'contradicts', 'equivalent_to', 'generalizes',
         'transfers_to', 'combines_with', 'failed_due_to', 'reactivated_by')


class VaultError(ValueError):
    pass


class Vault:
    def __init__(self, root):
        self.store = Store(root)

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # ------------------------------------------------------------------------------------------------ artifacts
    @staticmethod
    def record(type, content, *, domain, creator, parents=(), seeds=None, contracts=None, costs=None,
               environment=None, replay=None, created=None):
        if type not in TYPES:
            raise VaultError(f'artifact types are {TYPES}')
        rec = {'schema': SCHEMA, 'type': type, 'content': content, 'domain': domain, 'creator': creator,
               'parents': sorted(parents), 'seeds': seeds, 'contracts': contracts, 'costs': costs,
               'environment': environment, 'replay': replay, 'created': created}
        canonical(rec)                                   # JSON-representable, or a loud failure
        return rec

    def put(self, rec, status='generated', actor='genesis'):
        """Store an artifact record (from `record`) with its first status; returns its ID. Storing the same record
        again returns the same ID and appends nothing."""
        return self.put_many([rec], status, actor)[0]

    def put_many(self, recs, status='generated', actor='genesis'):
        if status in NEEDS_EVIDENCE:
            raise VaultError(f'an artifact enters as {status} only through evidence')
        ids, ents = [], []
        for rec in recs:
            if rec.get('schema') != SCHEMA or rec.get('type') not in TYPES:
                raise VaultError('not a vault record')
            for p in rec['parents']:
                if p not in ids and not self.exists(p):
                    raise VaultError(f'unknown parent {p}')
            aid = digest(rec)
            if aid not in ids and not self.exists(aid):
                ents.append(('artifact', aid, rec))
                ents.append(('annotation', f'{aid}:000000', {'artifact': aid, 'n': 0, 'status': status,
                                                             'explanation': 'unknown', 'failure': None,
                                                             'novelty': None, 'evidence': [], 'reason': 'created',
                                                             'actor': actor, 'time': utcnow()}))
            ids.append(aid)
        if ents:
            self.store.commit_batch(ents)
        return ids

    def exists(self, aid):
        return self.store.db.execute("SELECT 1 FROM entities WHERE kind='artifact' AND id=?", (aid,)).fetchone() \
            is not None

    def raw(self, aid):
        """The exact stored bytes of an artifact."""
        row = self.store.db.execute("SELECT object_hash FROM entities WHERE kind='artifact' AND id=?",
                                    (aid,)).fetchone()
        if not row:
            raise KeyError(aid)
        data = self.store.get_bytes(row[0])
        if digest(json.loads(data)) != aid:
            raise VaultError('artifact identity does not match its bytes')
        return data

    def get(self, aid):
        return json.loads(self.raw(aid))

    def ids(self, kind='artifact'):
        return [r[0] for r in self.store.db.execute('SELECT id FROM entities WHERE kind=? ORDER BY id', (kind,))]

    # ------------------------------------------------------------------------------------------------ annotations
    def history(self, aid):
        rows = self.store.db.execute("SELECT id, object_hash FROM entities WHERE kind='annotation' AND id LIKE ? "
                                     "ORDER BY id", (aid + ':%',)).fetchall()
        return [self.store.get(h) for _, h in rows]

    def status(self, aid):
        """The current {status, explanation, failure, novelty} (the latest value of each)."""
        cur = {'status': None, 'explanation': 'unknown', 'failure': None, 'novelty': None}
        for a in self.history(aid):
            for k in cur:
                if a.get(k) is not None:
                    cur[k] = a[k]
        return cur

    def annotate(self, aid, *, status=None, explanation=None, failure=None, novelty=None, evidence=(), reason,
                 actor='genesis'):
        if not self.exists(aid):
            raise KeyError(aid)
        cur = self.status(aid)
        if status is not None:
            if status not in STATUSES:
                raise VaultError(f'statuses are {STATUSES}')
            if status != cur['status'] and status not in TRANSITIONS[cur['status']]:
                raise VaultError(f'{cur["status"]} -> {status} is not allowed')
            if status in NEEDS_EVIDENCE:
                if not evidence:
                    raise VaultError(f'{status} needs evidence')
                for e in evidence:
                    rec = self.get(e)
                    c = rec['content']
                    if rec['type'] != 'EvidenceRecord' or not c.get('study') or not c.get('record_test'):
                        raise VaultError('evidence must be an EvidenceRecord naming a study and its record test')
        for v, allowed, name in ((explanation, EXPLANATIONS, 'explanation'), (failure, FAILURES, 'failure'),
                                 (novelty, NOVELTY, 'novelty')):
            if v is not None and v not in allowed:
                raise VaultError(f'{name}: one of {allowed}')
        for e in evidence:
            if not self.exists(e):
                raise KeyError(e)
        n = len(self.history(aid))
        body = {'artifact': aid, 'n': n, 'status': status, 'explanation': explanation, 'failure': failure,
                'novelty': novelty, 'evidence': sorted(evidence), 'reason': reason, 'actor': actor, 'time': utcnow()}
        self.store.save('annotation', f'{aid}:{n:06d}', body)
        return f'{aid}:{n:06d}'

    # ------------------------------------------------------------------------------------------------ edges
    def edge(self, kind, src, dst, *, evidence=(), confidence, scope, provenance, score=None):
        """dst is an artifact ID or a tag (a prerequisite or capability name, prefixed 'tag:')."""
        if kind not in EDGES:
            raise VaultError(f'edge kinds are {EDGES}')
        if not self.exists(src):
            raise KeyError(src)
        if not (dst.startswith('tag:') or self.exists(dst)):
            raise KeyError(dst)
        if not 0.0 <= confidence <= 1.0:
            raise VaultError('confidence in [0, 1]')
        body = {'kind': kind, 'src': src, 'dst': dst, 'evidence': sorted(evidence), 'confidence': confidence,
                'scope': scope, 'provenance': provenance, 'score': score, 'time': utcnow()}
        key = digest({k: body[k] for k in ('kind', 'src', 'dst', 'evidence', 'scope', 'provenance')})
        self.store.save('edge', key, body)
        return key

    def edges(self, kind=None, src=None, dst=None):
        out = []
        for _, h in self.store.db.execute("SELECT id, object_hash FROM entities WHERE kind='edge' ORDER BY id"):
            e = self.store.get(h)
            if (kind is None or e['kind'] == kind) and (src is None or e['src'] == src) and \
                    (dst is None or e['dst'] == dst):
                out.append(e)
        return out

    # ------------------------------------------------------------------------------------------------ queries
    def query(self, type=None, status=None, domain=None, failure=None, where=None):
        out = []
        for aid in self.ids():
            rec = self.get(aid)
            if type and rec['type'] != type or domain and rec['domain'] != domain:
                continue
            st = self.status(aid)
            if status and st['status'] != status or failure and st['failure'] != failure:
                continue
            if where and not where(rec, st):
                continue
            out.append(aid)
        return out

    def ancestors(self, aid):
        seen, stack = [], list(self.get(aid)['parents'])
        while stack:
            p = stack.pop()
            if p not in seen:
                seen.append(p)
                stack += self.get(p)['parents']
        return sorted(seen)

    def descendants(self, aid):
        kids = {}
        for x in self.ids():
            for p in self.get(x)['parents']:
                kids.setdefault(p, []).append(x)
        seen, stack = [], list(kids.get(aid, []))
        while stack:
            c = stack.pop()
            if c not in seen:
                seen.append(c)
                stack += kids.get(c, [])
        return sorted(seen)

    def verify(self):
        """The store's integrity check, then every artifact's identity against its bytes."""
        rep = self.store.verify()
        for aid in self.ids():
            self.raw(aid)
        rep['artifacts'] = len(self.ids())
        return rep

    # ------------------------------------------------------------------------------------------------ reactivation
    def opportunities(self, trigger, fuel):
        """Dormant artifacts a trigger (a CapabilityRecord artifact) may unlock, best first, at most `fuel`."""
        rec = self.get(trigger)
        if rec['type'] != 'CapabilityRecord':
            raise VaultError('a trigger is a CapabilityRecord')
        tags = {'tag:' + t for t in rec['content'].get('unlocks', [])}
        done = {e['src'] for e in self.edges(kind='reactivated_by', dst=trigger)}
        cands = {}
        for e in self.edges(kind='failed_due_to'):
            if e['dst'] in tags and e['src'] not in done and self.status(e['src'])['status'] == 'dormant':
                s = e['score'] if e['score'] is not None else float('-inf')
                cands[e['src']] = max(cands.get(e['src'], float('-inf')), s)
        ranked = sorted(cands, key=lambda a: (-cands[a], a))
        return ranked[:max(0, int(fuel))]

    def reactivate(self, aid, trigger, *, reason, actor='genesis'):
        if any(e['src'] == aid for e in self.edges(kind='reactivated_by', dst=trigger)):
            raise VaultError('already reactivated by this trigger (an unchanged retry)')
        self.annotate(aid, status='exploratory', reason=f'reactivated: {reason}', actor=actor)
        return self.edge('reactivated_by', aid, trigger, confidence=1.0, scope='reactivation',
                         provenance={'actor': actor, 'reason': reason})

    def cascade(self, triggers, retest, fuel, depth):
        """Run triggers breadth-first. retest(aid, trigger) -> list of new CapabilityRecord IDs it produced (each a
        further trigger). At most `fuel` artifacts per trigger and `depth` levels; a trigger runs once. Returns
        the log [(level, trigger, artifact)]."""
        log, seen, frontier = [], set(), list(triggers)
        for level in range(depth):
            nxt = []
            for t in frontier:
                if t in seen:
                    continue
                seen.add(t)
                for aid in self.opportunities(t, fuel):
                    self.reactivate(aid, t, reason=f'cascade level {level}')
                    log.append((level, t, aid))
                    nxt += [x for x in retest(aid, t) if x not in seen]
            frontier = nxt
            if not frontier:
                break
        return log
