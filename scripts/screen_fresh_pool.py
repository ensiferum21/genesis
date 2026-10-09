#!/usr/bin/env python3
"""Research-visible freshness screen; never consumes prior outcome data.

Checks exact/shingle overlap and equational subsumption (both equality orientations).
The latter detects variable renamings and instances such as f(g(x))=x vs
f(g(h(y)))=h(y), which token Jaccard alone can miss. This is a *necessary*
hygiene check, not evidence of independence or mathematical novelty.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from gap_engine.adapters.induction.tasks import PROPERTIES, TEXTBOOK
from gap_engine.adapters.induction.terms import match, symbols
from gap_engine.adapters.induction.theory import Theory
from gap_engine.kernel.sealed import jaccard, shingles


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parsed(text: str, parser):
    try:
        a, b = parser.parse_eq(text)
        return a, b
    except (SyntaxError, ValueError, IndexError, KeyError, RecursionError, TypeError):
        return None


def _instance_of(general: tuple, specific: tuple) -> bool:
    """True when a *single* substitution maps both sides of general to specific.

    Equality is symmetric. Matching both sides with a shared substitution is
    essential: separate substitutions would create false positives.
    """
    a, b = general
    x, y = specific
    for left, right in ((x, y), (y, x)):
        subst = match(a, left)
        if subst is not None and match(b, right, subst) is not None:
            return True
    return False


def _same_family(a: tuple | None, b: tuple | None) -> bool:
    """Conservative exclusion: either theorem is a substitution instance of the other."""
    return a is not None and b is not None and (_instance_of(a, b) or _instance_of(b, a))


def _candidate_equation(text: str, parser, theory: Theory):
    """Typed, non-reflexive equation with a known defined function.

    This is syntactic hygiene only: it does NOT establish theorem truth,
    proof correctness, novelty, or scientific independence.
    """
    if not isinstance(text, str) or len(text) > 8192:
        return None
    eq = _parsed(text, parser)
    if eq is None or eq[0] == eq[1]:
        return None
    try:
        if theory.sort_of(eq[0], {}) != theory.sort_of(eq[1], {}):
            return None
        if not ((set(symbols(eq[0])) | set(symbols(eq[1]))) & set(theory.funs)):
            return None
    except (TypeError, ValueError, KeyError, IndexError, RecursionError):
        return None
    return eq


def screen(candidate: Path, history: list[Path], *, threshold: float = 0.8,
           minimum: int = 300, theory: Theory | None = None) -> dict:
    """DEV-only structural freshness screen, never an authorization to preregister."""
    th = theory or Theory.default()
    fresh = json.loads(candidate.read_text())['tasks']
    old = [t for p in history for t in json.loads(p.read_text())['tasks']]
    if not isinstance(fresh, list) or not isinstance(old, list):
        raise ValueError('task collections must be lists')
    if any(not isinstance(t, str) for t in old) or any(not isinstance(t, str) for t in fresh):
        raise ValueError('task statements must be strings')
    if not (0 < threshold <= 1) or type(minimum) is not int or minimum < 1:
        raise ValueError('invalid screening threshold/minimum')
    parser = th.parser()
    handwritten = list(PROPERTIES) + list(TEXTBOOK)
    handwritten_sh = [shingles(t) for t in handwritten]
    handwritten_eq = [_parsed(t, parser) for t in handwritten]
    after_hand, hand, invalid = [], [], []
    for task in fresh:
        eq = _candidate_equation(task, parser, th)
        if eq is None:
            invalid.append(task)
            continue
        sh = shingles(task)
        if any(jaccard(sh, h) >= threshold for h in handwritten_sh) or any(_same_family(eq, h) for h in handwritten_eq):
            hand.append(task)
        else:
            after_hand.append(task)
    old_sh = [shingles(t) for t in old]
    old_eq = [_parsed(t, parser) for t in old]
    retained, rejected_old, rejected_internal, rejected_structural = [], [], [], []
    keep_sh, keep_eq = [], []
    for task in after_hand:
        sh = shingles(task)
        eq = _parsed(task, parser)
        if any(jaccard(sh, x) >= threshold for x in old_sh):
            rejected_old.append(task)
        elif any(_same_family(eq, x) for x in old_eq):
            rejected_structural.append(task)
        elif any(jaccard(sh, x) >= threshold for x in keep_sh):
            rejected_internal.append(task)
        elif any(_same_family(eq, x) for x in keep_eq):
            rejected_internal.append(task)
        else:
            retained.append(task)
            keep_sh.append(sh)
            keep_eq.append(eq)
    return {
        'status': 'DEV_FRESHNESS_THRESHOLD_MET_UNVERIFIED' if len(retained) >= minimum else 'INSUFFICIENT_FRESH_TASKS',
        'preregistration_allowed': False, 'promotion_allowed': False,
        'proofs_independently_replayed': False, 'semantic_family_independence_proven': False,
        'candidate': str(candidate), 'candidate_sha256': sha256(candidate),
        'historical_pool_sha256': {str(p): sha256(p) for p in history},
        'threshold': threshold, 'minimum': minimum,
        'candidate_count': len(fresh), 'invalid_or_trivial_rejected': len(invalid), 'handwritten_rejected': len(hand),
        'prior_pool_rejected': len(rejected_old), 'structural_prior_rejected': len(rejected_structural),
        'internal_rejected': len(rejected_internal),
        'fresh_count': len(retained), 'fresh_tasks': retained,
        'note': 'DEV ONLY. No sealed outcomes used. Typed syntax and structural freshness do not prove theorem truth, independent proof replay, novelty, or independence. A separate frozen preregistration gate must verify all required evidence.',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate', type=Path)
    ap.add_argument('--history', nargs='+', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--minimum', type=int, default=300)
    args = ap.parse_args()
    result = screen(args.candidate, args.history, minimum=args.minimum)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'fresh_tasks'}, indent=2))
    if not result['preregistration_allowed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
