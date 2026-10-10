"""Leak scanner and contamination firewall (spec §18.2, §35, §37.3).

    screen(candidate, sealed_index) ->
        BLOCK(EXACT_MATCH | STRUCTURAL_MATCH | ELABORATED_MATCH | NEAR_DUPLICATE)
        QUARANTINE_FOR_ADJUDICATION | ALLOW

Applied to tasks, generated lemmas, memorized examples, procedure libraries,
retrieved documents and curricula before they become research-visible. The
sealed index lives with the evaluator; only decisions leave it. Thresholds and
canonicalization rules are part of the scanner version, which is part of the
evaluator version.

Canonicalization (§35.1): comments, theorem names, attributes and
non-semantic whitespace removed; bound variables alpha-renamed in binding
order; commutative arguments are NOT reordered (no proof of equivalence is
available); both source-text and structural fingerprints are recorded. An
optional third layer uses Lean's elaborated expression structure, computed
in the sandbox by the evaluator and never shown to research workers.
"""
from dataclasses import dataclass, field
import hashlib
import re

from ..common import canonical, digest

HARD_THRESHOLD = 0.92     # shingle Jaccard at or above: block as near duplicate
REVIEW_THRESHOLD = 0.60   # at or above: quarantine for adjudication
SHINGLE = 3
RULES_VERSION = 'genesis-leakscan-rules-v1'

_COMMENT_BLOCK = re.compile(r'/-.*?-/', re.S)
_COMMENT_LINE = re.compile(r'--[^\n]*')
_ATTRIBUTE = re.compile(r'@\[[^\]]*\]')
_DECL_NAME = re.compile(r'\b(theorem|lemma|example|def|abbrev)\s+([^\s:({\[⦃]+)')
_TOKEN = re.compile(r"[A-Za-z_Ͱ-Ͽᴀ-ᶿ₀-ₜ][\w'Ͱ-Ͽ₀-ₜ.!?]*"
                    r"|\d+|:=|=>|->|<->|<=|>=|≠|≤|≥|→|↔|∀|∃!|∃|λ|Π|∧|∨|¬|\S")
_BINDER_OPENERS = {'∀', '∃', '∃!', 'fun', 'λ', 'Π'}
_GROUP = {'(': ')', '{': '}', '[': ']', '⦃': '⦄'}
_KEYWORDS = {'theorem', 'lemma', 'example', 'def', 'abbrev', 'fun', 'by', 'have', 'show', 'from', 'let', 'in',
             'if', 'then', 'else', 'match', 'with', 'Type', 'Prop', 'Sort', '_'}


def scanner_version():
    return digest({'rules': RULES_VERSION, 'hard': HARD_THRESHOLD, 'review': REVIEW_THRESHOLD,
                   'shingle': SHINGLE, 'token': _TOKEN.pattern})


def _sha(text):
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def canonical_statement(text):
    """Canonical token list for a Lean-like statement (see module docstring)."""
    text = _COMMENT_BLOCK.sub(' ', text)
    text = _COMMENT_LINE.sub(' ', text)
    text = _ATTRIBUTE.sub(' ', text)
    text = _DECL_NAME.sub(lambda m: m.group(1) + ' _', text)
    # Proof bodies are not part of the statement identity.
    head = re.split(r':=', text, maxsplit=1)[0]
    tokens = _TOKEN.findall(head)
    binders = {}

    def bind(name):
        if name not in binders and name not in _KEYWORDS and not name.isdigit():
            binders[name] = f'v{len(binders)}'

    i, depth, seen_colon = 0, 0, False
    while i < len(tokens):
        t = tokens[i]
        if t in _BINDER_OPENERS:
            j = i + 1
            while j < len(tokens) and tokens[j] not in (',', '=>', ':'):
                if tokens[j] in _GROUP:
                    k = j + 1
                    while k < len(tokens) and tokens[k] != ':' and tokens[k] != _GROUP[tokens[j]]:
                        bind(tokens[k]); k += 1
                    j = k
                    while j < len(tokens) and tokens[j] not in _GROUP.values():
                        j += 1
                else:
                    bind(tokens[j])
                j += 1
            i += 1
            continue
        if t in _GROUP and not seen_colon and depth == 0:
            k = i + 1
            names = []
            while k < len(tokens) and tokens[k] not in (':', _GROUP[t]):
                names.append(tokens[k]); k += 1
            if k < len(tokens) and tokens[k] == ':':
                for n in names:
                    bind(n)
        if t in _GROUP:
            depth += 1
        elif t in _GROUP.values():
            depth -= 1
        elif t == ':' and depth == 0:
            seen_colon = True
        i += 1
    def rename(t):
        if t in binders:
            return binders[t]
        head, dot, rest = t.partition('.')
        if dot and head in binders:   # generalized field notation: l.reverse -> v0.reverse
            return binders[head] + '.' + rest
        return t
    return [rename(t) for t in tokens]


def shingles(tokens, n=SHINGLE):
    return {tuple(tokens[i:i + n]) for i in range(max(1, len(tokens) - n + 1))}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a or b else 1.0


@dataclass
class SealedIndex:
    """Evaluator-side index. Never serialize its contents to research-visible storage."""
    exact: dict = field(default_factory=dict)          # sha(raw bytes) -> sealed id
    structural: dict = field(default_factory=dict)     # sha(canonical tokens) -> sealed id
    elaborated: dict = field(default_factory=dict)     # elaborated fingerprint -> sealed id
    shingle_sets: list = field(default_factory=list)   # (sealed id, shingle set)
    graphs: object = None                              # exposure.GraphIndex for graph tasks

    def add_statement(self, sealed_id, text, elaborated_fp=None):
        tokens = canonical_statement(text)
        self.exact[_sha(text)] = sealed_id
        self.structural[_sha(' '.join(tokens))] = sealed_id
        if elaborated_fp:
            self.elaborated[elaborated_fp] = sealed_id
        self.shingle_sets.append((sealed_id, shingles(tokens)))

    def add_graph(self, sealed_id, n, edges):
        from ..exposure import GraphIndex
        if self.graphs is None:
            self.graphs = GraphIndex()
        self.graphs.add(n, tuple(tuple(e) for e in edges), sealed_id)

    def digest(self):
        """Commitment to the index contents (for the evaluator ledger), not the contents themselves."""
        return digest({'exact': sorted(self.exact), 'structural': sorted(self.structural),
                       'elaborated': sorted(self.elaborated), 'graphs': self.graphs.count if self.graphs else 0,
                       'version': scanner_version()})


def _decision(decision, reason, **extra):
    return {'decision': decision, 'reason': reason, 'scanner_version': scanner_version(), **extra}


def screen_statement(text, index, elaborated_fp=None):
    if _sha(text) in index.exact:
        return _decision('BLOCK', 'EXACT_MATCH')
    tokens = canonical_statement(text)
    if _sha(' '.join(tokens)) in index.structural:
        return _decision('BLOCK', 'STRUCTURAL_MATCH')
    if elaborated_fp and elaborated_fp in index.elaborated:
        return _decision('BLOCK', 'ELABORATED_MATCH')
    mine = shingles(tokens)
    best = max((jaccard(mine, s) for _, s in index.shingle_sets), default=0.0)
    if best >= HARD_THRESHOLD:
        return _decision('BLOCK', 'NEAR_DUPLICATE', similarity=round(best, 4))
    if best >= REVIEW_THRESHOLD:
        return _decision('QUARANTINE_FOR_ADJUDICATION', 'SIMILAR', similarity=round(best, 4))
    return _decision('ALLOW', 'NO_MATCH', similarity=round(best, 4))


def screen_graph(n, edges, index):
    edges = tuple(tuple(e) for e in edges)
    key = _sha(canonical({'n': n, 'edges': sorted(map(list, edges))}))
    if key in index.exact:
        return _decision('BLOCK', 'EXACT_MATCH')
    if index.graphs is not None:
        if index.graphs.find(n, edges) is not None:
            return _decision('BLOCK', 'STRUCTURAL_MATCH')
        near = index.graphs.near(n, edges)
        if near:
            return _decision('QUARANTINE_FOR_ADJUDICATION', 'NEAR_DUPLICATE', neighbours=len(near))
    return _decision('ALLOW', 'NO_MATCH')


def screen(candidate, index, elaborated_fp=None):
    """candidate: {'kind': 'statement', 'text': ...} or {'kind': 'graph', 'n': ..., 'edges': ...}."""
    if candidate.get('kind') == 'graph':
        return screen_graph(candidate['n'], candidate['edges'], index)
    if candidate.get('kind') in ('statement', 'lemma', 'memory', 'document', 'curriculum', 'tool'):
        return screen_statement(candidate['text'], index, elaborated_fp)
    return _decision('BLOCK', 'UNSCREENABLE_KIND')   # fail closed


class OracleScreener:
    """Narrow evaluator-side screening interface handed to research code.

    Research receives only the decision (ALLOW / BLOCK / QUARANTINE_FOR_ADJUDICATION)
    and the scanner version. Reasons and similarities stay in the private ledger,
    and a query budget limits hill-climbing toward sealed content.
    """

    def __init__(self, index, *, query_budget=10_000, fingerprinter=None):
        self._index = index
        self._ledger = []
        self._budget = query_budget
        self._fingerprinter = fingerprinter   # e.g. Lean elaborated fingerprints for statements

    def __call__(self, candidate):
        if self._budget <= 0:
            return {'decision': 'BLOCK', 'scanner_version': scanner_version(), 'note': 'screening budget exhausted'}
        self._budget -= 1
        fp = None
        if self._fingerprinter and candidate.get('kind') != 'graph':
            fp = self._fingerprinter(candidate['text'])
        full = screen(candidate, self._index, fp)
        self._ledger.append({'candidate_sha256': digest(candidate), **full})
        return {'decision': full['decision'], 'scanner_version': full['scanner_version']}

    def private_ledger(self):
        return list(self._ledger)
