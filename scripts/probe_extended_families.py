#!/usr/bin/env python3
"""DEV-only extension of inductive theorem families, no sealed access or promotion.

Tasks must have a new semantic function, fail the weak solver, and have an
independently replayed proof with the same verified lemma library available
to every future arm. Historical task *statements* are screened; outcomes aren't read.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from gap_engine.adapters.induction.checker import LemmaStore, CheckError, check_proof
from gap_engine.adapters.induction.conjecture import THEMES, generate
from gap_engine.adapters.induction.extended import EXTENDED_DEFS, EXTENDED_LEMMAS, EXTENDED_THEMES, extended_theory
from gap_engine.adapters.induction.prover import Prover
from gap_engine.adapters.induction.proof_codec import encode
from gap_engine.adapters.induction.suite import textbook_library
from gap_engine.adapters.induction.theory import Equation, counterexample
from gap_engine.adapters.induction.terms import symbols
from scripts.screen_fresh_pool import screen
import numpy as np


def build_dev_probe(out: Path, history: list[Path], *, max_size=7, max_terms=1800,
                    weak_fuel=150, strong_fuel=5000, seed=424246, themes: list[str] | None = None) -> dict:
    selected = list(EXTENDED_THEMES) if themes is None else list(themes)
    if not selected or len(selected) != len(set(selected)) or any(t not in EXTENDED_THEMES for t in selected):
        raise ValueError("themes must be a nonempty unique subset of EXTENDED_THEMES")
    th = extended_theory()
    old_themes = dict(THEMES)
    THEMES.update(EXTENDED_THEMES)
    try:
        # Kernel-verified library, not assumptions or randomized truth testing.
        verified = textbook_library(th)
        st = LemmaStore(th)
        for k, eq in verified.items():
            # This is already independently verified in textbook_library; do not
            # re-admit without the proof object. The store here only adds new lemmas.
            pass
        extended_verified = []
        pending = [Equation(*th.parser().parse_eq(s)) for s in EXTENDED_LEMMAS]
        for _ in range(3):
            rest = []
            for eq in pending:
                att = Prover(th, verified, fuel=12000, max_depth=2, seed=seed).prove(eq)
                if not att.proved:
                    rest.append(eq)
                    continue
                try:
                    check_proof(th, verified, eq, att.proof)
                except CheckError:
                    rest.append(eq)
                    continue
                verified['extended_' + hashlib.sha256(eq.text().encode()).hexdigest()[:16]] = eq
                extended_verified.append(eq.text())
            if len(rest) == len(pending):
                break
            pending = rest
        candidates, proofs, counts, proof_failures = [], {}, {}, 0
        for theme in selected:
            cs = generate(th, {}, themes=[theme], max_size=max_size, max_terms=max_terms,
                          seed=seed, prune=True)
            counts[theme] = {'generated': len(cs), 'new_symbol': 0, 'weak_failed': 0,
                             'checker_proved': 0}
            for c in cs:
                if not (set(symbols(c.eq.lhs)) | set(symbols(c.eq.rhs))) & set(EXTENDED_DEFS):
                    continue
                counts[theme]['new_symbol'] += 1
                if Prover(th, {}, fuel=weak_fuel, max_depth=2, seed=seed).prove(c.eq).proved:
                    continue
                counts[theme]['weak_failed'] += 1
                att = Prover(th, verified, fuel=strong_fuel, max_depth=2, seed=seed).prove(c.eq)
                if not att.proved:
                    continue
                try:
                    check_proof(th, verified, c.eq, att.proof)
                except CheckError:
                    proof_failures += 1
                    continue
                counts[theme]['checker_proved'] += 1
                candidates.append(c.eq.text())
                proofs.setdefault(c.eq.text(), encode(att.proof))
        unique = list(dict.fromkeys(candidates))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({'tasks': unique,
            'params': {'seed': seed, 'max_size': max_size, 'max_terms': max_terms,
                       'weak_fuel': weak_fuel, 'strong_fuel': strong_fuel,
                       'domain': th.name, 'themes': selected}, 'counts': counts,
            'extended_verified_lemmas': extended_verified,
            'proof_failures': proof_failures,
            'status': 'DEV_ONLY_NOT_SEALED'}, indent=2))
        proof_path = out.with_name(out.stem + '_proofs.json')
        proof_path.write_text(json.dumps({'theory': th.name, 'proofs': proofs}, indent=2))
        result = screen(out, history, theory=th, minimum=300)
        fresh_path = out.with_name(out.stem + '_freshness.json')
        fresh_path.write_text(json.dumps(result, indent=2))
        return {'generated_unique': len(unique), 'fresh': result['fresh_count'],
                'status': result['status'], 'extended_verified_lemmas': len(extended_verified),
                'unproved_extended_lemmas': [eq.text() for eq in pending],
                'proof_failures': proof_failures, 'counts': counts,
                'freshness_report': str(fresh_path), 'proof_report': str(proof_path)}
    finally:
        THEMES.clear()
        THEMES.update(old_themes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--history', nargs='+', type=Path, required=True)
    ap.add_argument('--max-size', type=int, default=7)
    ap.add_argument('--max-terms', type=int, default=1800)
    ap.add_argument('--seed', type=int, default=424246)
    ap.add_argument('--themes', nargs='+', choices=list(EXTENDED_THEMES))
    args = ap.parse_args()
    print(json.dumps(build_dev_probe(args.out, args.history, max_size=args.max_size,
                                     max_terms=args.max_terms, seed=args.seed, themes=args.themes), indent=2))


if __name__ == '__main__':
    main()
