"""Command line: `gap-engine demo | prove | conjecture | verify-ledger`."""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gap-engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="run one v2 campaign on a cached lesion world")
    d.add_argument("--seed", type=int, default=0)
    d.add_argument("--budget", type=float, default=200.0)
    d.add_argument("--ledger", default=None, help="write the campaign ledger to this JSONL file")
    p = sub.add_parser("prove", help="prove an equation with optional lemmas and show the checked proof")
    p.add_argument("equation")
    p.add_argument("--lemma", action="append", default=[])
    p.add_argument("--fuel", type=int, default=6000)
    c = sub.add_parser("conjecture", help="enumerate and test conjectures for a theme")
    c.add_argument("--theme", default="rev")
    c.add_argument("--size", type=int, default=6)
    v = sub.add_parser("verify-ledger", help="verify a JSONL ledger's hash chain")
    v.add_argument("path")
    a = ap.parse_args(argv)

    if a.cmd == "prove":
        from .adapters.induction.checker import check_proof
        from .adapters.induction.prover import Prover
        from .adapters.induction.theory import Equation, Theory
        th = Theory.default()
        P = th.parser()
        lib = {f"L{i}": Equation(*P.parse_eq(s)) for i, s in enumerate(a.lemma)}
        goal = Equation(*P.parse_eq(a.equation))
        att = Prover(th, lib, fuel=a.fuel).prove(goal)
        ok = att.proved and check_proof(th, lib, goal, att.proof)
        print(json.dumps({"goal": goal.text(), "proved": att.proved, "checked": bool(ok), "cost": att.cost,
                          "trace": att.trace[:20], "stuck": [s.text() for s in att.stuck[:5]]}, indent=1))
        return 0 if ok else 1
    if a.cmd == "conjecture":
        from .adapters.induction.conjecture import generate
        from .adapters.induction.theory import Theory
        for cj in generate(Theory.default(), {}, themes=[a.theme], max_size=a.size):
            print(cj.text())
        return 0
    if a.cmd == "verify-ledger":
        from .kernel.ledger import Ledger
        Ledger(a.path).verify()
        print("ledger OK")
        return 0
    if a.cmd == "demo":
        from .adapters.induction.adapter import build_world, judge_sealed
        from .engine.loop import Campaign
        w = build_world(seed=a.seed, lesion=True, cache_dir="experiments/cache")
        base = judge_sealed(w, [], seed=a.seed, actor="baseline", unsafe_dev=True)["solved"]
        from .kernel.ledger import Ledger
        led = Ledger(a.ledger) if a.ledger else Ledger()
        res = Campaign(w, a.budget, a.seed, ledger=led).run()
        after = judge_sealed(w, [], seed=a.seed, actor="v2", unsafe_dev=True)["solved"]
        print(json.dumps({"sealed_before": base, "sealed_after": after, "n_sealed": w.sealed.size("SEALED"),
                          "accepted": [w.statement(i) for i in res.accepted], "spent": res.spent,
                          "steps": [(s["arm"], round(s["reward"], 2)) for s in res.steps]}, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
