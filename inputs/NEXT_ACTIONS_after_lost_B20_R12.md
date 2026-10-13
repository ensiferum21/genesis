# Next actions (continuation after B20)

## Where things stand

- **Branch:** `continuation-b20-repairs`.
- **Parent checkpoints:**
  - B20: commit `97fb233`, archive `44bbbbeb…2091`.
  - B20_R1: commit `972dbb6`, archive `b8e99c16…bbf4`.
  - B20_R2: commit `3c1089e`, archive `d5056b57…b304`.
  - B20_R5: commit `0989a4f`, archive `60d5c307…4ddb`.
  - B20_R8: commit `ae50d74`, archive `9f34fec8…334f`.
  - B20_R11: commit `36954d6`.
- **State and records:** `batch_state.json` → `continuation_b20_r1`; `docs/checkpoints/B20_R1_RECORD.md` to `B20_R12_RECORD.md`.

## Completed

| Batches | Work |
|---|---|
| B20_R1–R2 | Review repairs A–D; CRPD-1, CRPD-2a and CRPD-3; the H02 exit run; first parts of H05 and H08 |
| B20_R3, R6, R9 | Three headroom pilots on the equational domain (lemma selection, prover strategy, library curation) and a new frozen policy study: no research-policy headroom on DEV (B20R9-OPEN-1) |
| B20_R4 | Native research-lineage records; generation requests checked by the custodian (H08) |
| B20_R5, R7 | The custodian runs real frozen candidates of three kinds in the OCI sandbox; sealed equational statement panels (H05 done on DEV) |
| B20_R8 | Replay contracts for exact, formal and DEV evidence (part of B14-OPEN-4) |
| B20_R10 | Custodian statement screen for research; checker CPU metering; checker logs keep error lines |
| B20_R11 | E1 readiness package (`handoff/e1/`). The effect replicates under equal sandbox metering, but the DRAFT cost rule fails |
| B20_R12 | E1 under the user's decisions of 13 Oct 2026 (time-matched baselines, custodian SELECT-panel comparator, centred power model). It is fair (CPU ratio 1.00), but the effect is +0.60 per task and the power model is INFEASIBLE. The rehearsal custodian refused registration (s14.4). Package v2 |

## Resume

    git clone genesis/source-history.bundle genesis-work && cd genesis-work
    git checkout continuation-b20-repairs
    GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # ~30 min from pinned sources
    export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
    python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json   # as root (runc)

## Decisions needed from Daniel or a reviewer

The user decided on 13 Oct 2026: time-matched baselines, the centred power model, graph construction as the GV4 domain, and Go on CRPD-2b (time-boxed, reverted with a record if it fails). These still need a reviewer:

1. **E1 design** (B20R12-OPEN-1, `handoff/e1/README.md`). Under the decided design E1 cannot be powered. The options are a harder host family calibrated on DEV (recommended), an independently justified design effect, or retiring E1.
2. **Statistician sign-off** of the centred power model (B19-OPEN-4).

## Next engineering, in order

1. B20_R13: the graph-construction headroom pilot for GV4 (`scripts/b20r13_graph_headroom_pilot.py`).
2. B14-OPEN-4, the remaining contracts: causal (ablation and placebo), internal replication and priority. Also a Lean-package route for THEOREM_CHECKED, and DEV rows bound to their execution evidence (B20R8-OPEN-1).
3. H08, the remaining work: recovery, rollback and retention (s20.6); paired research lineages for `sealed_improver_evaluation`, once a GV4 domain with headroom exists.
4. H06, W22/W23, W28 and the H11 release review.

## Needs external resources

These are BLOCKED_ENVIRONMENT here (re-checked 2026-10-12):

- PyPI and the Docker registry are unreachable from this workspace, so the R-04 wheel hashes and the image digest cannot be produced.
- A second machine and operator.
- An external time anchor.
- An independent reviewer and custodian (GV0, GV1, and every scientific gate).

## Claim ceiling

Engineering and DEV diagnostics only. No sealed task has been run on real panels. Better-improver remains UNESTABLISHED.
