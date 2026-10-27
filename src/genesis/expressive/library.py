"""Library learning over Λ1 (X2, B20_R154; `docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §5): Genesis abstracts named
statements from its own engines.

**What it does.** Given a corpus of programs in Λ1 + library_k (Genesis's engines, with weights), it proposes new
named statements and rewrites the corpus with them, choosing by minimum description length. Prior art, none claimed:
anti-unification (Plotkin 1970; Reynolds 1970), library learning by compression (DreamCoder, Ellis et al. 2021;
Stitch, Bowers et al. 2023; babble, Cao et al. 2023).

  1. **Fragments.** Every run of 1 to MAX_RUN adjacent items of any list of any program (the program, a block's
     items, a repeat's body) that can become ONE item without changing its meaning: a run of two or more items is
     not governed by a guard before it (a call would put the whole run under the guard) and does not end in a guard
     (its guard would then govern nothing); a single item can always be named (a single guard becomes a named
     condition). Runs inside an abstraction's body are fragments too, so later statements can be made of earlier ones.
  2. **Skeletons and anti-unification.** A fragment's skeleton is the fragment with every number replaced by a hole.
     Fragments with the same skeleton are anti-unified: a number equal in every occurrence stays; positions whose
     values differ become parameters, positions whose value tuples are equal sharing one parameter (Plotkin's rule).
     A skeleton needs at least MIN_USES occurrences in at least two programs.
  3. **Rewriting.** Each occurrence (left to right, outermost first, non-overlapping) is replaced by a call with its
     arguments. **Every rewritten program must expand to exactly the program it was** (`lambda1.expand`, canonical):
     the meaning is checked, not assumed; a candidate that changes any program is refused.
  4. **Score.** The gain in description length of corpus and library together, in bits (`lambda1.bits`,
     `lambda1.library_bits`), weighted by the corpus weights: compression = before - after. The best candidate with
     positive compression is added; the corpus is rewritten with it; repeat, up to `k` statements. Ties by skeleton
     text, so the result is deterministic.
Names are `g<generation><letter>` (g1a, g1b, ...). Each new definition records its provenance (the generation, the
skeleton, its uses, the programs it was found in, the compression).
"""
import json

from ..candidate_kinds import mcx3 as K
from . import lambda1 as L1

MAX_RUN = 4
MIN_USES = 2


# ------------------------------------------------------------------------------------------------------ fragments

def _runs(xs, guard_calls):
    """(start, end) of every run of xs that can be one item."""
    out = []
    for i in range(len(xs)):
        governed = i > 0 and K._guardlike(xs[i - 1], guard_calls)
        for j in range(i + 1, min(len(xs), i + MAX_RUN) + 1):
            if j - i == 1:
                out.append((i, j))
            elif not governed and not K._guardlike(xs[j - 1], guard_calls):
                out.append((i, j))
    return out


def fragments(prog, guard_calls):
    """Every abstractable fragment of a program: tuples of items."""
    out = []

    def lst(xs):
        for i, j in _runs(xs, guard_calls):
            out.append(tuple(xs[i:j]))
        for x in xs:
            item(x)

    def item(x):
        if x[0] == '[':
            lst(x[1])
        elif x[0] == '*':
            out.append((x[2],))
            item(x[2])
    lst(prog)
    return out


def _skeleton(x):
    """The item with its numbers replaced by None, and the numbers in order."""
    k = x[0]
    if k == 'op':
        return ('op', x[1], None if x[2] is None else '#', x[3]), [] if x[2] is None else [x[2]]
    if k in ('S', 'P'):
        return (k, '#'), [x[1]]
    if k == '?':
        return ('?', x[1], x[2], '#'), [x[3]]
    if k == '*':
        s, n = _skeleton(x[2])
        return ('*', '#', s), [x[1]] + n
    if k == '[':
        parts = [_skeleton(y) for y in x[1]]
        return ('[', tuple(s for s, _ in parts)), [v for _, n in parts for v in n]
    if k == 'call':
        return ('call', x[1], ('#',) * len(x[2])), list(x[2])
    raise ValueError(f'not an item: {x!r}')


def skeleton(frag):
    parts = [_skeleton(x) for x in frag]
    return tuple(s for s, _ in parts), [v for _, n in parts for v in n]


def _fill(skel, values):
    """The fragment of a skeleton with its holes filled from `values` (consumed in order)."""
    it = iter(values)

    def item(s):
        k = s[0]
        if k == 'op':
            return ('op', s[1], None if s[2] is None else next(it), s[3])
        if k in ('S', 'P'):
            return (k, next(it))
        if k == '?':
            return ('?', s[1], s[2], next(it))
        if k == '*':
            n = next(it)
            return ('*', n, item(s[2]))
        if k == '[':
            return ('[', tuple(item(y) for y in s[1]))
        return ('call', s[1], tuple(next(it) for _ in s[2]))
    out = tuple(item(s) for s in skel)
    return out


def anti_unify(occurrences):
    """The body (numbers or '$i'), its parameters' positions, from the number lists of a skeleton's occurrences."""
    cols = list(zip(*occurrences))
    body, params = [], {}
    for col in cols:
        if len(set(col)) == 1:
            body.append(col[0])
        else:
            params.setdefault(col, f'${len(params) + 1}')
            body.append(params[col])
    return body, list(params)


# ---------------------------------------------------------------------------------------------------- rewriting

def _match(frag_skel, frag_vals, skel, body):
    """The arguments of a call matching the fragment, or None."""
    if frag_skel != skel:
        return None
    args = {}
    for v, b in zip(frag_vals, body):
        if isinstance(b, str):
            if args.setdefault(b, v) != v:
                return None
        elif b != v:
            return None
    return [args[f'${i}'] for i in range(1, len(args) + 1)]


def rewrite(prog, name, skel, body, guard_calls):
    """The program with every occurrence of the skeleton (with consistent arguments) replaced by a call."""
    def lst(xs):
        xs = [item(x) for x in xs]
        out, i = [], 0
        runs = {}
        for a, b in _runs(xs, guard_calls):
            runs.setdefault(a, []).append(b)
        while i < len(xs):
            done = False
            for j in sorted(runs.get(i, []), reverse=True):          # the longest run first
                s, v = skeleton(xs[i:j])
                args = _match(s, v, skel, body)
                if args is not None:
                    out.append(('call', name, tuple(args)))
                    i, done = j, True
                    break
            if not done:
                out.append(xs[i])
                i += 1
        return tuple(out)

    def item(x):
        if x[0] == '[':
            return ('[', lst(x[1]))
        if x[0] == '*':
            body_ = item(x[2])
            s, v = skeleton((body_,))
            args = _match(s, v, skel, body)
            return ('*', x[1], ('call', name, tuple(args)) if args is not None else body_)
        return x
    return lst(prog)


def _body_text(skel, body):
    return K.render(_fill(skel, body))


# ------------------------------------------------------------------------------------------------------ learning

def corpus_bits(progs, weights, library):
    return sum(w * L1.bits(p, library) for p, w in zip(progs, weights)) + L1.library_bits(library)


def candidates(progs, library):
    """{skeleton: (body, params, uses, programs)} of the corpus's recurring skeletons."""
    gc = library.guard_calls()
    found = {}
    for pi, p in enumerate(progs):
        for f in fragments(p, gc):
            s, v = skeleton(f)
            found.setdefault(s, []).append((pi, v))
    out = {}
    for s, occ in found.items():
        if len(occ) < MIN_USES or len({pi for pi, _ in occ}) < 2:
            continue
        body, params = anti_unify([v for _, v in occ])
        out[s] = (body, params, len(occ), sorted({pi for pi, _ in occ}))
    return out


def learn(corpus, library=L1.EMPTY, k=3, generation=1, weights=None, exclude=(), first=0):
    """Up to k new named statements from the corpus (genomes or program texts in Λ1 + library). `exclude`: bodies
    not to propose (refused before); `first`: the letter of the first name (g<generation>a is 0).
    Returns (new library, rewritten program texts, steps)."""
    texts = [c['prog'] if isinstance(c, dict) else c for c in corpus]
    weights = list(weights or [1.0] * len(texts))
    progs = [L1.surface(t, library) for t in texts]
    meaning = [L1.expand(p, library) for p in progs]
    steps = []
    for step in range(k):
        before = corpus_bits(progs, weights, library)
        best = None
        for s, (body, params, uses, where) in sorted(candidates(progs, library).items(), key=lambda kv: repr(kv[0])):
            name = f'g{generation}{chr(ord("a") + first + step)}'
            if _body_text(s, body) in exclude:
                continue
            try:
                lib2 = library.extend(name, _body_text(s, body),
                                      provenance={'generation': generation, 'uses': uses, 'programs': where})
            except ValueError:
                continue
            gc = lib2.guard_calls()
            new = [K.canonical(rewrite(p, name, s, body, gc), gc) for p in progs]
            if new == progs:
                continue
            try:
                if any(L1.expand(q, lib2) != m for q, m in zip(new, meaning)):
                    continue                                     # the meaning changed: refused
            except ValueError:
                continue
            gain = before - corpus_bits(new, weights, lib2)
            if gain > 0 and (best is None or gain > best[0]):
                best = (gain, name, s, body, lib2, new, uses, where)
        if best is None:
            break
        gain, name, s, body, lib2, new, uses, where = best
        d = dict(lib2.get(name))
        d['provenance'] = dict(d['provenance'], compression_bits=round(gain, 3), skeleton=repr(s))
        library = L1.Library(lib2.defs[:-1] + (d,), parent=lib2.parent)
        progs = new
        steps.append({'name': name, 'body': d['body'], 'params': d['params'], 'uses': uses, 'programs': where,
                      'compression_bits': gain, 'length_after': sum(L1.length(p) for p in progs),
                      'version': library.version})
    return library, [K.render(p) for p in progs], steps


def describe(library):
    return json.dumps(library.to_json(), indent=1, sort_keys=True)
