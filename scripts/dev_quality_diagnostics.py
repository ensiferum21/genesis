#!/usr/bin/env python3
"""Statement-only DEV quality triage; never used to tune sealed outcomes.

These are descriptive heuristics, not an independent novelty or difficulty judge.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

from gap_engine.adapters.induction.conjecture import known_by_rewriting
from gap_engine.adapters.induction.extended import EXTENDED_DEFS, extended_theory
from gap_engine.adapters.induction.terms import size, symbols, variables
from gap_engine.adapters.induction.theory import Equation


def diagnose(freshness: Path, *, rewriting_check: bool = True) -> dict:
    tasks = json.loads(freshness.read_text())['fresh_tasks']
    th = extended_theory()
    parser = th.parser()
    buckets = Counter()
    classes = Counter()
    entries = []
    for s in tasks:
        eq = Equation(*parser.parse_eq(s))
        syms = set(symbols(eq.lhs)) | set(symbols(eq.rhs))
        new = sorted(syms & set(EXTENDED_DEFS))
        nvars = len(eq.vars())
        nodes = size(eq.lhs) + size(eq.rhs)
        by_rewriting = known_by_rewriting(th, {}, eq) if rewriting_check else None
        if not new:
            classes['NO_EXTENDED_SYMBOL'] += 1
        if nvars == 0:
            classes['GROUND'] += 1
        if len(new) >= 2:
            classes['MULTI_EXTENDED_SYMBOL'] += 1
        if by_rewriting:
            classes['DEFINITION_REWRITING_ONLY'] += 1
        for f in new:
            buckets[f] += 1
        entries.append({'statement': s, 'extended_symbols': new,
                        'variables': nvars, 'term_nodes': nodes,
                        'definition_rewriting_only': by_rewriting})
    return {
        'status': 'DEV_DIAGNOSTIC_NOT_PROMOTION_EVIDENCE',
        'statement_fresh_count': len(tasks), 'extended_symbol_counts': dict(sorted(buckets.items())),
        'quality_flags': dict(sorted(classes.items())),
        'independence_established': False, 'lean_verified': False,
        'entries': entries,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('freshness', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--skip-rewriting', action='store_true')
    args = ap.parse_args()
    report = diagnose(args.freshness, rewriting_check=not args.skip_rewriting)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k!='entries'},indent=2))

if __name__=='__main__':
    main()
