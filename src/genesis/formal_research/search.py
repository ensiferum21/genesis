"""Proof search (roadmap W08: "separate proof search and proof acceptance").

Search is untrusted. It compiles its own context, tries candidate proofs and reports
which compiled. Nothing it produces is accepted here: a candidate becomes a library
lemma only after `checker.accept` has recompiled it from source in fresh sandboxes,
bound it to its trusted statement and audited it.

Candidates come from recipes. The recipes are builder-written, generic tactic programs
parameterised by the conjecture's binders, the definitions it mentions and the lemmas
already in the accepted library. Which recipe proves which conjecture, and which library
lemmas a proof uses, is found by running them. The receipts name the recipe of every
attempt, so a reviewer can see how much of a proof the search found and how much the
recipe supplied.

All candidates for one conjecture are elaborated in one sandbox run, each as its own
theorem. Lean reports errors with line numbers, so every candidate gets its own verdict.
Every attempt is charged, including the ones that fail.
"""
import re

from ..common import bytes_hash, digest
from . import checker as C


def _binders(conj):
    return [b['name'] for b in conj['binders']]


def _hyps(conj):
    return [b['name'] for b in conj['binders'] if b.get('hyp')]


def recipes(conj, library, unfold):
    """[(recipe id, tactic text)] for a conjecture. Tactic text is a tactic block whose
    lines are relative to the block's own column. `library` lists accepted lemmas as
    {'const': 'GTP3.proof', 'statement': id}; `unfold` lists definitions to unfold."""
    names = _binders(conj)
    intro = f'intro {" ".join(names)}' if names else 'skip'
    # `unfold` fails when a definition does not occur, so each one is tried in turn (outermost
    # first: unfolding a bound exposes the predicate inside it)
    unf = '\n'.join(f'try unfold {d} at *' for d in unfold) if unfold else 'skip'
    edges = [b['name'] for b in conj['binders'] if b.get('type') == 'GT.Edges']
    out = [('decide', ['decide']),
           ('decide-kernel', ['decide +kernel']),
           ('unfold-simp', [intro, f'simp_all [{", ".join(unfold)}]' if unfold else 'simp_all']),
           ('unfold-aesop', [intro, unf, 'aesop']),
           ('unfold-omega', [intro, unf, 'intros', 'omega']),
           ('unfold-solve', ['intros', unf, 'solve_by_elim [Finset.card_le_card, Finset.Subset.trans]'])]
    for h in _hyps(conj):
        out.append((f'apply-hyp:{h}', [intro, unf, 'intros', f'apply {h} <;> solve_by_elim']))
        # instantiate a universally quantified hypothesis at the goal's objects, then arithmetic
        out.append((f'specialize-omega:{h}', [intro, unf, 'intro S hS hT',
                                              f'have := {h} S (by solve_by_elim [Finset.Subset.trans]) hT',
                                              'omega']))
    for lem in library:
        c = lem['const']
        out.append((f'library-elim:{c}', [intro, f'solve_by_elim [{c}, Finset.inter_subset_left, '
                                                  'Finset.inter_subset_right, Finset.Subset.refl]']))
        # cover strategy: split a subset S of A ∪ B along the cover, bound each part with the
        # hypotheses, using a down-closure lemma from the library for the restricted parts
        hyps = _hyps(conj)
        if len(hyps) >= 2 and len(edges) >= 2:
            (ha, hb), (a, b) = hyps[:2], edges[:2]
            out.append((f'cover-split:{c}', [
                intro, unf, 'intro S hS hT',
                f'have h1 := {ha} (S ∩ {a}) Finset.inter_subset_right ({c} _ _ Finset.inter_subset_left hT)',
                f'have h2 := {hb} (S ∩ {b}) Finset.inter_subset_right ({c} _ _ Finset.inter_subset_left hT)',
                f'have h3 : S ⊆ S ∩ {a} ∪ S ∩ {b} := by',
                '  intro x hx; have := hS hx; simp only [Finset.mem_union, Finset.mem_inter] at this ⊢; tauto',
                'have h4 := (Finset.card_le_card h3).trans (Finset.card_union_le _ _)',
                'omega']))
    return [(rid, '\n'.join(lines)) for rid, lines in out]


def disproof_recipe(conj, counterexample):
    """The proof of `¬ conj` from a counterexample found by the Python model: instantiate
    every binder, discharge every hypothesis and refute the conclusion by evaluation."""
    args = ' '.join(f'({counterexample["values"][b["name"]]})' if not b.get('hyp') else '(by decide +kernel)'
                    for b in conj['binders'])
    return f'intro h\nexact absurd (h {args}) (by decide +kernel)'


OPTION_LINE = re.compile(r'^set_option maxHeartbeats (\d+) in$')


def split_options(text):
    """(declaration options, tactic): a recipe may begin with `set_option maxHeartbeats N in` on
    its own line (B20_R37); that line is placed before the theorem, where it governs the whole
    declaration. maxHeartbeats is an allowed option (checker.ALLOWED_OPTIONS)."""
    first, _, rest = text.partition('\n')
    if OPTION_LINE.match(first.strip()):
        return [first.strip()], rest
    return [], text


def candidate_module(name, target, unfold_first, imports, candidates):
    """One module holding every candidate as its own theorem; returns (source, line ranges)."""
    lines = [f'import {m}' for m in imports] + [f'namespace {name}']
    ranges = {}
    for j, (rid, text) in enumerate(candidates):
        start = len(lines) + 1
        opts, text = split_options(text)
        lines += opts
        lines.append(f'theorem cand_{j} : {target} := by')
        lines.append(f'  unfold {" ".join(unfold_first)}')
        lines += ['  ' + t for t in text.split('\n')]
        ranges[j] = (start, len(lines))
    lines.append(f'end {name}')
    return '\n'.join(lines) + '\n', ranges


def proof_module(name, target, unfold_first, imports, tactic):
    """The proof module submitted for acceptance: `theorem proof : target := by ...`."""
    opts, tactic = split_options(tactic)
    lines = [f'import {m}' for m in imports] + [f'namespace {name}'] + opts + [f'theorem proof : {target} := by',
                                                                         f'  unfold {" ".join(unfold_first)}']
    lines += ['  ' + t for t in tactic.split('\n')] + [f'end {name}']
    return '\n'.join(lines) + '\n'


def target_of(conj_const, counterexample):
    """The constant a proof must inhabit, and what to unfold first. A disproof proves the
    trusted negation constant `<conjecture>_negation`."""
    if counterexample:
        return conj_const + '_negation', [conj_const + '_negation', conj_const]
    return conj_const, [conj_const]


SEARCH_HEARTBEATS = 100000


def search(conj, *, conj_const, context, library, unfold, counterexample=None, env=None, policy=C.POLICY,
           extra=(), heartbeats=SEARCH_HEARTBEATS):
    """Try the recipes for `conj` (or its disproof) against compiled `context`
    ({'imports': [module names], 'artifacts': {file: bytes}}). Never accepts anything.
    `extra`: further (recipe id, tactic) candidates; for a disproof they replace the default."""
    env = env or C._env()
    target, unfold_first = target_of(conj_const, counterexample)
    if counterexample:
        tiers = [list(extra) or [('counterexample-evaluation', disproof_recipe(conj, counterexample))]]
    else:
        # specialised candidates first; the generic portfolio only if none of them compiles
        tiers = [t for t in (list(extra), recipes(conj, library, unfold)) if t]
    base = 'GTSearch' + digest({'c': conj_const, 'x': counterexample})[:8].upper()
    base = re.sub(r'[^A-Za-z0-9]', 'X', base)
    attempts, runs, found = [], [], None
    for tier, cands in enumerate(tiers):
        name = f'{base}T{tier}'
        source, ranges = candidate_module(name, target, unfold_first, context['imports'], cands)
        r = C.compile_module(name, source, context['artifacts'], env, policy, heartbeats=heartbeats)
        found_errors = [(int(m.group(2)), m.group(1))
                        for m in re.finditer(rf'(?m)^({name}\.lean:(\d+):\d+: error.*)$', r['log'])] \
            if r['result'] != 'COMPILED' else []
        errors = [n for n, _ in found_errors]
        whole_failed = r['result'] in ('TIMEOUT', 'RESOURCE_LIMIT', 'CHECKER_ERROR') or \
            (r['result'] != 'COMPILED' and not errors)
        sorry = re.search(r'declaration uses .sorry.', r['log']) is not None
        for j, (rid, text) in enumerate(cands):
            lo, hi = ranges[j]
            bad = whole_failed or sorry or any(lo <= n <= hi for n in errors)
            # handoff s15.1: every proposed tactic and its failed elaboration are preserved (bounded)
            mine = [line[:300] for n, line in found_errors if lo <= n <= hi][:5]
            attempts.append({'recipe': rid, 'tier': tier, 'tactic_sha256': bytes_hash(text.encode()),
                             'compiled': not bad, 'tactic': text[:4000],
                             'errors': mine if mine else ([f'whole module: {r["result"]}'] if whole_failed else []),
                             'sorry': sorry})
            if not bad and found is None:
                found = (rid, text)
        runs.append({'module_sha256': bytes_hash(source.encode()), 'result': r['result'], 'stats': r['stats']})
        if found is not None:
            break
    cpu = sum(x['stats'].get('cpu_ns') or 0 for x in runs)
    wall = sum(x['stats'].get('wall_ns') or 0 for x in runs)
    return {'target': target, 'runs': runs, 'result': runs[-1]['result'], 'stats': runs[-1]['stats'],
            'attempts': attempts, 'found': found,
            'charged': {'candidates': len(attempts), 'cpu_ns': cpu, 'wall_ns': wall}}


__all__ = ['recipes', 'disproof_recipe', 'search', 'proof_module', 'candidate_module', 'target_of']
