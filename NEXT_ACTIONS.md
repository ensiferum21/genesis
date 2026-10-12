# Next actions (continuation after B20)

- **Branch / parent:** `continuation-b20-repairs` from B20 commit `97fb233`
  (archive sha256 `44bbbbeb…2091`). See `batch_state.json` → `continuation_b20_r1`.
- **Completed:** H01 (reproductions in `audit/review_b20/`); repairs A–D for
  B20-REVIEW-01..04; B20R-NEW-01; custody-complete joint-certification re-run.
- **Active unit:** checkpoint `B20_R1`, then the adopted CRPD v3 subset (below), then H05/H08.
- **Resume:**

      git clone genesis/source-history.bundle genesis-work && cd genesis-work
      git checkout continuation-b20-repairs
      GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh     # ~30 min, pinned sources
      export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
      python3 -m unittest tests_formal.test_learning_partitions tests_genesis.test_research_resource_accounting \
          tests_formal.test_successor_proof_custody tests_certificates.test_obstruction_custody

- **Next, in order:**
  1. CRPD-1: one soundness-mode field (EQ / SUFF / NEC / BOUND / HEURISTIC) shared by
     representations, world transport, obstruction bounds and macros; HEURISTIC never admits proof.
  2. CRPD-2: Lean-check the C4 codegree equivalence and the pair-count bound so that
     `C4-pair-count-quadratic` stops being an unchecked THEOREM upper bound.
  3. CRPD-3: orbit-sensitivity probe of E proof cost (DEV diagnostic; also the noise
     estimate B20-OPEN-3 needs before sizing E3).
  4. A fresh frozen DEV E3 study on the repaired harness (partition + budget + custody).
  5. H05 candidate adapters; H08 lineage validator and DEV generation fixture.
- **Needs external resources (BLOCKED_ENVIRONMENT here):** second machine and operator
  (R-04), container registry digest, PyPI wheel hashes, external time anchor, independent
  reviewer/custodian (GV0, GV1).
- **Claim ceiling:** engineering repairs on DEV; better-improver UNESTABLISHED.
