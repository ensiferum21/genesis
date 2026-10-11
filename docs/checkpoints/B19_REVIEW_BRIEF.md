# B19 review brief: useful discovery (W13–W17, E1/E2 readiness)

The B19 exit is "prospective usefulness accepted or branch rejected". The builder cannot
accept anything. This brief maps what a reviewer has to decide. Every statement below
should be checked against the code and the evidence.

## Reproduce

```
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src PYTHONPYCACHEPREFIX=$(mktemp -d)
python3 -m unittest tests_formal.test_discovery tests_formal.test_ghost_census   # formal suite parts
python3 -m unittest tests_genesis.test_literature tests_genesis.test_readiness tests_genesis.test_analysis_v2
python3 scripts/b19_discovery.py /tmp/b19          # W13–W15, about 40 min on 2 cores
python3 scripts/b19_active_v2.py /tmp/b19          # W14 second evaluation
python3 scripts/b19_ghost_census.py /tmp/b19gc     # W16, about 80 min
python3 scripts/b19_literature.py /tmp/b19lit      # W17, about 2 min
python3 scripts/b19_readiness.py /tmp/b19r         # E1 pilot and E2 draft, about 25 min
```

## Decisions for the reviewer

| # | Decision | Evidence |
|---|---|---|
| 1 | Is the W13 relation between source and target checked? Feasibility needs the Lean inequality lemmas, the objective direction and weak duality. Is `check_certificate` independent of the LP producer? | `discovery/obstruction.py`; `obstruction/package.json`; `LPCertificates` tests (tampering) |
| 2 | Is the joint-vs-reference comparison fair? Same wall budget, fresh hosts, and each method uses its own construction. | `obstruction/evaluation.json`; README |
| 3 | W14: is it acceptable that KG* was added after EIG failed, given that it was then evaluated on fresh pools? Should a sealed comparison freeze KG* first? | `active/`, `active_v2/` |
| 4 | Are the identifiability rules right? Classes are declared by checked theorems or by identical per-task values, and are never separated by a tie-break. | `active.equivalence_classes`, `resolve` |
| 5 | W15: are the placebo, effort and conventional controls meaningful, and are they matched on CPU or heartbeats? | `catalysis/solver.json`, `catalysis/concept.json` |
| 6 | W16: does the diagnostic justify the decision for this scope? Run 1 has a harness defect; run 2 has the fix. Is replaying E proofs step by step in Lean a sound route to THEOREM_CHECKED? | `evidence/ghost_census_b19/`; `formal_research/fof_lean.py`; `LeanReplay` tests (tampered step, wrong goal) |
| 7 | W17: are the claims faithful to their sources? The quotes came through a summarising fetch tool. Answer ADJ-1 to ADJ-4. | `evidence/literature_b19/records/` |
| 8 | E1: accept or reject the centred-headroom power model. Is a 0.5-edge minimum useful effect meaningful? Is a single-family panel adequate? | `evidence/readiness_b19/e1/` |
| 9 | E2: is the design adequate, and who builds the sealed statement generator? | `evidence/readiness_b19/e2/design_DRAFT.json` |

## Known limits

- **DEV only.** Every comparison is DEV-only. No sealed task exists, and no claim is
  promoted.
- **W13.** Only the relaxation route is built. Symmetry reduction, decomposition, FPT,
  kernelization and continuation are not.
- **W16 replay.** Skolem functions with arguments are not replayed. A step that the
  tactic cascade cannot close leaves the result at E's PROVED.
- **W17.** The search record is small (4 web searches, 5 sources read). Absence of a hit
  proves nothing.
- **E1.** The custodian's evaluator cannot run the candidate yet (B19-OPEN-3).
