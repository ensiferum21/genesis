# Next actions (continuation after B20)

- **Branch / parents:** `continuation-b20-repairs`; B20 commit `97fb233` (archive `44bbbbeb…2091`);
  checkpoint B20_R1 (commit `972dbb6`, archive `b8e99c16…bbf4`). See `batch_state.json` →
  `continuation_b20_r1`, and `docs/checkpoints/B20_R1_RECORD.md`, `B20_R2_RECORD.md`.
- **Completed:** H01; repairs A–D (B20-REVIEW-01..04) and B20R-NEW-01; custody-complete joint-certification
  re-run; CRPD-1 (soundness modes), CRPD-2a (Lean-checked codegree, first EQ abstraction), CRPD-3
  (orbit probe: NOT_DETECTED); H02 exit run (`evidence/e3_fresh_b20r/`: learned vs fixed 0W/2T/6L,
  all runs within cap, zero custody problems); H08 part (lineage validator, campaign-export audit);
  H05 part (trusted candidate runner).
- **Resume:**

      git clone genesis/source-history.bundle genesis-work && cd genesis-work
      git checkout continuation-b20-repairs
      GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # ~30 min from pinned sources
      export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
      python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json

- **Next, in order:**
  1. Decide CRPD-2b (B20R-OPEN-3): a reviewed workspace pin revision adding Finset big operators, then
     Lean-check the C4 pair-count bound. Needs Daniel's decision.
  2. Campaign export carrying lineage records (selection scores, attempt-bound candidates, per-run
     accounts); then wire `lineage.lineage_problems` into custodian request checking (B14-OPEN-3,
     B20R-OPEN-2). Keep both sealed kinds refused until then.
  3. Reviewed schema extension for candidate descriptors; wire `candidates.run` into the custodian
     (B19-OPEN-3, B20R-OPEN-4).
  4. A redesigned research policy (cheap features, per-attempt cost model) in a NEW frozen study
     (B20R-OPEN-1), on a family with headroom (Sheffer 6–9 nodes showed empty 2–8/25 vs fixed 2–9).
  5. CRPD-4 aliasing-pair refinement once such a family is chosen.
- **Needs external resources (BLOCKED_ENVIRONMENT here, re-checked 2026-10-12):** PyPI and the Docker
  registry are unreachable from this workspace (R-04 wheel hashes, image digest); second machine and
  operator; external time anchor; independent reviewer and custodian (GV0, GV1).
- **Claim ceiling:** engineering repairs and DEV diagnostics; better-improver UNESTABLISHED.
