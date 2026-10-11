"""Literature, priority and faithful formalization (roadmap W17).

Everything retrieved is untrusted input. It is stored as data with its provenance; it is
never interpreted as instructions and cannot change trust policy, evaluation or any
verdict computed here. An injection screen flags instruction-like text, and a flagged
source is quarantined: no claim may be extracted from it until a person adjudicates it.

Records (schema `genesis-literature-v1`):
  source     provenance (tool, request, time, locator), the text exactly as received, its
             SHA-256, and its fidelity: VERBATIM (read directly, e.g. a pinned Mathlib
             file) or TOOL_SUMMARIZED (returned by a fetch tool that may excerpt or
             paraphrase; quotes in it are unconfirmed against the original).
  claim      an exact quote, which must occur in the source text (checked, with its
             offsets), the claim in normalised words, its assumptions and the notation
             it relies on, resolved against `NOTATION`.
  link       claim ↔ Genesis/Lean statement with a kind (EXACT, SPECIALIZATION,
             GENERALIZATION, CONTEXT, UNRESOLVED) and the checks behind it: a Lean
             theorem accepted by `formal_research.checker`, and/or an executable
             agreement check on all small instances.
  ambiguity  competing readings of a phrase, evaluated on small instances; a
             distinguishing instance is recorded, and the reading actually used named.
  adjudication  questions only a person can settle. They stay PENDING_HUMAN; Genesis
             never answers them itself.
  novelty    for a Genesis result: the scoped search record (queries, tools, dates,
             sources read, library searches) and the prior art found. The conclusion is
             PRIOR_ART_FOUND or NO_PRIOR_ART_FOUND_IN_SCOPE, never "novel": absence of a
             hit does not show that nobody found it. Independent review stays PENDING.
"""
import hashlib
from pathlib import Path
import re

SCHEMA = 'genesis-literature-v1'
FIDELITY = ('VERBATIM', 'TOOL_SUMMARIZED')
LINK_KINDS = ('EXACT', 'SPECIALIZATION', 'GENERALIZATION', 'CONTEXT', 'UNRESOLVED')

INJECTION = [r'(?i)\bignore (all |any )?(previous|prior|above) (instructions|rules)',
             r'(?i)\b(system|assistant|developer)\s*(prompt|message)?\s*:',
             r'(?i)\byou (must|should) (now )?(mark|promote|approve|accept|treat)',
             r'(?i)\b(promote|approve|accept) (this|the) claim',
             r'(?i)\bmark (this|it) as (novel|verified|checked|accepted)',
             r'(?i)<\s*/?\s*(system|instructions?)\s*>', r'(?i)\bdisregard\b.{0,40}\b(policy|instructions)']


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def screen(text):
    """Instruction-like spans in retrieved text (data, never obeyed)."""
    return [m.group(0) for p in INJECTION for m in re.finditer(p, text)]


def source(source_id, *, kind, text, fidelity, provenance):
    if fidelity not in FIDELITY:
        raise ValueError(fidelity)
    flags = screen(text)
    return {'schema': SCHEMA, 'record': 'source', 'source_id': source_id, 'kind': kind, 'fidelity': fidelity,
            'provenance': provenance, 'text': text, 'text_sha256': sha(text), 'trust': 'UNTRUSTED_INPUT',
            'screen': {'flags': flags, 'quarantined': bool(flags)}}


def from_retrieval(record):
    """A source from a stored retrieval transcript (tool output kept exactly as received)."""
    return source(record['source_id'], kind='paper', text=record['response_text'], fidelity='TOOL_SUMMARIZED',
                  provenance={'tool': record['tool'], 'request': record['request'],
                              'retrieved_utc': record['retrieved_utc'],
                              'time_precision': 'minute; recorded by the builder at the tool call'})


def from_library(source_id, root, rel_path, first, last, *, revision, package='mathlib'):
    """A verbatim excerpt (lines first..last, 1-based, inclusive) of a pinned library file."""
    path = Path(root) / rel_path
    data = path.read_bytes()
    lines = data.decode().splitlines()
    text = '\n'.join(lines[first - 1:last])
    return source(source_id, kind='library', text=text, fidelity='VERBATIM',
                  provenance={'package': package, 'revision': revision, 'file': rel_path, 'lines': [first, last],
                              'file_sha256': hashlib.sha256(data).hexdigest()})


def claim(claim_id, src, quote, *, statement, assumptions=(), notation=()):
    """A claim backed by an exact quote. REJECTED if the quote is not in the source text or
    the source is quarantined; the quote stays unconfirmed for TOOL_SUMMARIZED sources."""
    base = {'schema': SCHEMA, 'record': 'claim', 'claim_id': claim_id, 'source_id': src['source_id'],
            'quote': quote, 'statement': statement, 'assumptions': list(assumptions)}
    if src['screen']['quarantined']:
        return dict(base, status='REJECTED', reason='source quarantined by the injection screen')
    at = src['text'].find(quote)
    if not quote or at < 0:
        return dict(base, status='REJECTED', reason='quote does not occur verbatim in the source text')
    unknown = [n for n in notation if n not in NOTATION]
    if unknown:
        return dict(base, status='REJECTED', reason=f'unresolved notation {unknown}')
    return dict(base, status='EXTRACTED', span=[at, at + len(quote)],
                quote_confirmed=src['fidelity'] == 'VERBATIM',
                notation={n: NOTATION[n] for n in notation})


# Natural-language terms used by the ingested claims, resolved to Genesis definitions.
# `differences` records where the Genesis object is not literally the same thing.
NOTATION = {
    'graph': {'genesis': 'GT.Edges (Finset (ℕ × ℕ)), read as a finite simple undirected graph',
              'differences': 'pairs are ordered in the type; Genesis tasks store each edge once as (u, v) with '
                             'u < v, and no loops'},
    'edges m': {'genesis': 'H.card', 'differences': None},
    'triangle': {'genesis': 'three edges (a,b), (b,c), (a,c) of the host', 'differences': None},
    'triangle-free': {'genesis': 'GT.TriangleFree', 'differences': None},
    'set of edges meeting all triangles': {'genesis': 'a triangle edge cover T ⊆ H; τ = min |T|',
                                           'differences': None},
    'edge-disjoint triangles': {'genesis': 'a triangle packing; ν = max size; ν* = LP relaxation',
                                'differences': None},
    'bipartite cut': {'genesis': 'the edges decoded by the B18 representation cross_2 (2 vertex classes, '
                                 'cross decoder)', 'differences': None},
    'monotone graph property': {
        'genesis': 'a predicate P on edge sets with RC.C0 P (closed under taking subsets)',
        'differences': 'a graph property is isomorphism-invariant and also closed under vertex removal; on '
                       'edge sets vertex removal is a special edge removal, but RC.C0 does not require '
                       'isomorphism invariance. Order-theoretic naming is reversed: Mathlib calls such a '
                       'predicate Antitone, while Monotone means order-preserving.'},
    'lower set': {'genesis': 'IsLowerSet (Mathlib.Order.Defs.Unbundled)', 'differences': None},
    'antitone': {'genesis': 'Antitone (Mathlib.Order.Monotone.Defs)', 'differences': None},
    'equational law': {'genesis': 'a universally quantified equation (genesis.fol)', 'differences': None},
}


def link(claim_rec, *, formal, kind, checks, note=''):
    if kind not in LINK_KINDS:
        raise ValueError(kind)
    ok = claim_rec['status'] == 'EXTRACTED' and all(c.get('verdict') in ('PASS', 'CHECKED') for c in checks)
    return {'schema': SCHEMA, 'record': 'link', 'claim_id': claim_rec['claim_id'], 'formal': formal, 'kind': kind,
            'checks': checks, 'status': 'LINKED' if ok and kind != 'UNRESOLVED' else 'NOT_LINKED', 'note': note}


def ambiguity(phrase, readings, instances, *, used, describe=repr):
    """`readings`: {name: predicate on an instance}. Each pair of readings is compared on
    every instance; the first distinguishing instance of each pair is recorded."""
    names = sorted(readings)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            witness = next((x for x in instances if bool(readings[a](x)) != bool(readings[b](x))), None)
            pairs.append({'readings': [a, b], 'distinguished': witness is not None,
                          'witness': None if witness is None else describe(witness)})
    material = any(p['distinguished'] for p in pairs)
    return {'schema': SCHEMA, 'record': 'ambiguity', 'phrase': phrase, 'readings': names,
            'instances_tested': len(instances), 'pairs': pairs, 'material_on_tested_range': material,
            'reading_used': used}


def adjudication(item_id, question, *, context, options):
    return {'schema': SCHEMA, 'record': 'adjudication', 'item_id': item_id, 'question': question,
            'context': context, 'options': list(options), 'status': 'PENDING_HUMAN', 'answer': None,
            'answered_by': None}


def novelty(result_id, *, description, searches, sources_read, library_searches, prior_art, scope):
    """`prior_art`: [{'source_id' or 'library', 'relation'}]. Never concludes 'novel'."""
    return {'schema': SCHEMA, 'record': 'novelty', 'result_id': result_id, 'description': description,
            'scope': scope, 'search_record': {'searches': searches, 'sources_read': sources_read,
                                              'library_searches': library_searches},
            'prior_art': prior_art,
            'conclusion': 'PRIOR_ART_FOUND' if prior_art else 'NO_PRIOR_ART_FOUND_IN_SCOPE',
            'absence_disclaimer': 'absence of a search hit does not show that nobody has found this',
            'independent_review': 'PENDING'}


def library_search(root, patterns, *, revision, subdir='Mathlib'):
    """Exact-text search of the pinned library sources: per pattern, the hits (file, line).
    Every file is read once."""
    root = Path(root)
    files = sorted((root / subdir).rglob('*.lean'))
    rxs = [re.compile(p) for p in patterns]
    hits = [[] for _ in patterns]
    for f in files:
        for i, line in enumerate(f.read_text(errors='replace').splitlines(), 1):
            for k, rx in enumerate(rxs):
                if rx.search(line):
                    hits[k].append({'file': str(f.relative_to(root)), 'line': i, 'text': line.strip()[:200]})
    return [{'pattern': p, 'revision': revision, 'files_searched': len(files), 'hits': h[:50], 'hit_count': len(h)}
            for p, h in zip(patterns, hits)]


__all__ = ['source', 'from_retrieval', 'from_library', 'claim', 'link', 'ambiguity', 'adjudication', 'novelty',
           'library_search', 'screen', 'NOTATION']
