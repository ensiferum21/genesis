# Next actions (continuation after B20)

## Where things stand

- **Branch:** `continuation-b20-repairs`.
- **Parents:**
  - B20: commit `97fb233`, archive `44bbbbeb…2091`.
  - Checkpoint B20_R1: commit `972dbb6`, archive `b8e99c16…bbf4`.
  - Checkpoint B20_R2: commit `3c1089e`, archive `d5056b57…b304`.
- **Records:** `batch_state.json` → `continuation_b20_r1`, and `docs/checkpoints/B20_R1_RECORD.md` through `B20_R5_RECORD.md`.

## Completed

| Batch | Work |
|---|---|
| B20_R1 | H01; repairs A–D |
| B20_R2 | CRPD-1/2a/3; the H02 exit run; first parts of H05 and H08 |
| B20_R3 | Headroom pilot. The redesigned cost-aware policy, run under a new frozen DEV study, was INFERIOR_DEV; the material was NOT_DISCRIMINATING. Finding: libraries are not monotone for E. |
| B20_R4 | Campaigns write native lineage records; the custodian checks generation requests against them. |
| B20_R5 | Request v4, receipt v4 and claim binding v2. The custodian rebuilds descriptors from the frozen export and runs every arm in the OCI sandbox. The judge re-checks every witness. |

## Resume

    git clone genesis/source-history.bundle genesis-work && cd genesis-work
    git checkout continuation-b20-repairs
    GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # ~30 min from pinned sources
    export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
    python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc)

## Next, in order

1. **H05, rest (B20R5-OPEN-1).** Build the sealed theorem generator for equational statements (handoff s13.3). Statements are generated on the custodian side and committed before any candidate has access; inclusion rules are preregistered; rejected and unsolved statements are accounted for; residual pretraining exposure is recorded. Add a third candidate kind for frozen formal-research successors, with Lean replay by the judge.
2. **B20R3-OPEN-1.** Run a DEV design pilot over further equational families to find one with selection headroom (ORACLE − fixed ≥ 2 of 12). Only after that, a new frozen study with a library-level objective (B20R3-OPEN-2), followed by CRPD-4.
3. **B14-OPEN-4.** Replay contracts for the remaining evidence kinds (s12.2): finite exact, formal theorem, causal, DEV utility, replication and priority.
4. **H06.** Formal discovery and representation gaps: a Mathlib history study and richer representations.
5. **CRPD-2b (B20R-OPEN-3).** Needs Daniel's decision on a reviewed revision of the workspace pin.
6. **Remaining handoff units.** H08 recovery, rollback and retention (s20.6); W22/W23; W28; H11 release review.

## Needs external resources

These are BLOCKED_ENVIRONMENT here (re-checked 2026-10-12):

- PyPI and the Docker registry are unreachable from this workspace, so the R-04 wheel hashes and image digest cannot be produced.
- A second machine and its operator.
- An external time anchor.
- An independent reviewer and custodian (GV0, GV1).

## Claim ceiling

Engineering and DEV diagnostics only. Better-improver remains UNESTABLISHED.
