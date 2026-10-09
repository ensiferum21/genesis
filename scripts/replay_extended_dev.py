#!/usr/bin/env python3
"""Replay saved DEV proof objects using an independent checker, not prover success flags."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from gap_engine.adapters.induction.checker import check_proof
from gap_engine.adapters.induction.extended import EXTENDED_LEMMAS, extended_theory
from gap_engine.adapters.induction.proof_codec import decode
from gap_engine.adapters.induction.prover import Prover
from gap_engine.adapters.induction.suite import textbook_library
from gap_engine.adapters.induction.theory import Equation


def replay(pool: Path, proof_path: Path) -> dict:
    th = extended_theory()
    parser = th.parser()
    tasks = json.loads(pool.read_text())['tasks']
    proofs = json.loads(proof_path.read_text())['proofs']
    lib = textbook_library(th)  # internally replay-verified
    pending = [Equation(*parser.parse_eq(s)) for s in EXTENDED_LEMMAS]
    for _ in range(3):
        nxt = []
        for eq in pending:
            attempt = Prover(th, lib, fuel=12000, max_depth=2, seed=424246).prove(eq)
            if not attempt.proved:
                nxt.append(eq)
                continue
            check_proof(th, lib, eq, attempt.proof)
            import hashlib
            lib['extended_' + hashlib.sha256(eq.text().encode()).hexdigest()[:16]] = eq
        if len(nxt) == len(pending):
            break
        pending = nxt
    checked = 0
    for task in tasks:
        if task not in proofs:
            raise AssertionError(f'missing proof for {task}')
        eq = Equation(*parser.parse_eq(task))
        if not check_proof(th, lib, eq, decode(proofs[task])):
            raise AssertionError(f'checker rejected {task}')
        checked += 1
    return {'status': 'DEV_PROOF_REPLAY_PASS', 'proofs_replayed': checked,
            'theory': th.name, 'unproved_extended_lemmas': [eq.text() for eq in pending]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pool', type=Path)
    ap.add_argument('proofs', type=Path)
    args = ap.parse_args()
    print(json.dumps(replay(args.pool, args.proofs), indent=2))

if __name__ == '__main__':
    main()
