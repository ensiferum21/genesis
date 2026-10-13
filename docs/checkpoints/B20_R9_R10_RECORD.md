# B20_R9 and B20_R10 record: library curation pilot; custodian statement screen, checker metering and logs

- **Parent:** checkpoint B20_R8 (commit `ae50d74`).
- **Run by:** the builder. DEV only. Nothing here has been independently reviewed.

## B20_R9: is there headroom in curating a lemma library? (B20R3-OPEN-1/2)

- **Problem.** B20_R3 and B20_R6 ruled out choosing *which lemmas to prove* on eight systems. They also found that true lemmas interfere, which raised a second question: does choosing *which lemmas to keep* have headroom?
- **Implementation.** `scripts/b20r9_curation_pilot.py`, committed as `63f7d8b` before running. The verdict rule was fixed in the script. Libraries compared on 12 evaluation targets per range:
  - EMPTY, FIXED@CAP and ALL;
  - DEV-CURATED: deployable; usage-ranked top-k, with k chosen on development targets;
  - EVAL-CURATED: an optimistic subset-search reference;
  - BEST-OF: a per-target ceiling.
- **Evidence** (`evidence/curation_pilot_b20r9/`). Every variant is NO_CURATION_HEADROOM:
  - **Huntington:** idempotence alone reaches the ceiling (k=1).
  - **Boolean rings:** DEV-CURATED beats the best fixed rule by at most 1 of 12, and so does the optimistic reference.
  - **Sheffer:** libraries barely matter.
- **Limitation.** One prover at 1 s, 12 targets per range, a usage-ranked curator only.
- **Consequence.**
  - Across B20_R3, R6 and R9, no research-policy dimension tried reaches 2 of 12 headroom on the equational families: selection, strategy and curation.
  - GV4 cannot be answered positively on this domain at these settings, and a frozen E3 study here would have no power (s14.4).
  - GV4 needs a different domain or setting; that choice is a design decision for review.
  - B20R3-OPEN-1 is answered on DEV: NO_HEADROOM on the equational domain. It is replaced by B20R9-OPEN-1, which requires choosing a domain for GV4.

## B20_R10: small open items (B20R7-OPEN-1, B20R7-OPEN-2, B20R3-OPEN-3)

Commit `16d649e`.

**Custodian statement screen for research (B20R7-OPEN-2)**

- `custodian.screen_statements_for_research` returns signed ALLOW/BLOCK decisions against every statement sealed at the custodian. It applies the partition relations: EXACT, ALPHA and INSTANCE are blocked; GENERALIZES is quarantined, and therefore blocked.
- The receipt carries a salted commitment to the sealed set and no reserved text. Matches go to a private ledger.
- On the research side, `partitions.CustodianStatementScreen` verifies the receipt and blocks on any failure. `partitions.both` combines screens.
- Test (`ResearchScreen`):
  - a sealed statement and an alpha-variant of it are blocked; an unrelated statement is allowed;
  - a wrong signer, a receipt for other items, and a transport failure all block;
  - a research run that would prove a sealed statement does not admit it.

**Checker CPU metering (B20R7-OPEN-1)**

- `fof_lean.replay` and `custody.replay_target` now report the checker sandboxes' cgroup CPU; cached modules count as 0.
- Statement replay attempts carry this CPU. The end-to-end statement test asserts `cpu_unknown == 0` for verification.

**Error lines kept in checker logs (B20R3-OPEN-3)**

- The stored module log puts error lines first, followed by the tail of the full log. Test: `KeptLog`.
- The checker's verdict logic is unchanged. The replay route's identity changes because the checker and translator files changed.
- Stored checks under the old identity now score as needing a recheck. That is the intended behaviour.

## Claim ceiling

DEV diagnostics and engineering. Better-improver UNESTABLISHED.
