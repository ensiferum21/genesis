# B20_R60 record: the GV4 fallback claim, DRAFT

- **Built by:** the builder. Documentation and a derived table; no run, no new evidence, nothing adopted.
- **Files:**
  - `handoff/gv4/FALLBACK_CLAIM_DRAFT.md`;
  - `handoff/gv4/attempt_family.json`;
  - `scripts/b20r60_gv4_fallback.py`;
  - `tests_genesis/test_gv4_fallback.py`.

## Why

The handover's GV4 step: if a reviewer names a new domain, pilot its headroom; otherwise write the roadmap's
fallback claim ("report a useful solver without claiming a better improver"). No probed domain has a research
decision with headroom (B20_R3 … R58), so the builder drafts the fallback for decision 6 of the review brief.

## What the draft proposes

- **Part A, a useful solver (GV3):** E1d. The frozen 0.5 s represent-and-repair solver beats the strongest of
  five baselines, including HiGHS at 4× budget, on dense planted hosts. So far: re-pilot +10.6 per host, and a
  same-operator rehearsal SUPPORTED at +9.80 [9.30, 10.35]. The draft also states:
  - the representation is classical;
  - the scoring reference is exact and solves these hosts in about 20 s;
  - the mechanism is the builder's reading, not measured.
- **Part B, causal attribution:** the registered ablation, +7.07 per host with a clean null control, rehearsed
  through custody at +6.64.
- **Part C, only if certification utility counts:** generated, Lean-checked inequalities certify optima the
  conventional relaxation leaves open on two motifs (B20_R35, B20_R48/R49). Sum-free contributes stronger
  certified bounds only, because B20_R57's coverage effect did not replicate (B20_R59).
- **Not claimed:**
  - a better improver (GV4);
  - compounding generations (GV5);
  - structural transfer (GV6);
  - independent replication (GV7);
  - novelty.

## The false-discovery table, now machine-derived

`attempt_family.json` derives Benjamini–Yekutieli at q = 0.1 from the evidence summaries. It covers all 13
preregistered component attempts. The six construction attempts were decided by interval rules and count at
p = 1, which is conservative for the others.

| Survivor | Survives up to |
|---|---|
| B20_R35 | any family size searched (10,000) |
| B20_R48 | 147 attempts |
| B20_R57 | 21 attempts (but not replicated) |

Until now this table had been computed by hand in the B20_R57 record.

## Tests

`tests_genesis/test_gv4_fallback.py` (6). It checks:
- every number in the draft renders from its cited file and key, and appears verbatim;
- the family file is the script's derivation;
- the BY step-up is correct;
- the draft's statements about survivors match the family;
- the draft is labelled DRAFT and claims no better improver.

## Open

B20R9-OPEN-1 is updated: the fallback is drafted, and accepting, narrowing or rejecting it is the reviewer's.
