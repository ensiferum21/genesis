# B20_R188 record (WP-4): INVALID by a measurement defect; the verifier refused every mutant at its boundary check (DEV)

**Run by:** the builder, on DEV. A measurement of the verifier's mutation adequacy (blueprint WP-4, weakness C1).
Preregistered at `0c8aa79`; the script `scripts/b20r188_verifier_adequacy.py` (digest pinned in
`tests_genesis/test_verifier_adequacy_study.py`) ran unchanged from a clean worktree, alone on CPU 0, 31 Oct 2026,
22:52:29-22:53:48 SGT.
- **CPU 0 idle time (disclosed):** 14 min 52 s before it (from B20_R187's end, 22:37:37, while B20_R187 was recorded
  and this was prepared); after it, idle while the defect was diagnosed and B20_R189 prepared.

## Result: INVALID (defect B20R188-BOUNDARY)

All 437 mutants were classed "killed", a mutation score of 1.0. That is an artefact. The kernel's verifier judges a
*patch* against the job's current source, and its boundary check refuses a patch that changes no line. The script
built each job with the mutant itself and then offered the same mutant as the patch, so no line changed and the
boundary check refused every one. The rehearsal (the bag) showed the same artefact, and it was not noticed.

The rows still hold every other check's outcome, because the verifier runs them all. They are evidence only
descriptively:
- 23 mutants failed the boundary check alone (they passed the visible and hidden tests, the fresh workloads, the
  resource check and the resumed job);
- 4 failed the boundary and the hidden tests only;
- the rest failed one or more of the job, the fresh workloads and the hidden tests.

The repaired measurement, B20_R189, offers each mutant with one added comment line.

**The same defect elsewhere (disclosed).**
- The mutant catalogues' selection rule (`scripts/b20r185-187_make_mutant_catalogue.py`, "the verifier rejects it")
  was satisfied vacuously by the same boundary refusal. Every catalogue entry also interrupts every job of its draw,
  which the verifier's resumed-job check rejects, so no entry would change; the scripts are sealed and stay as they
  are.
- The design tests of B20_R185, R186 and R187 checked "the verifier tells right from wrong" on the wrong side
  vacuously. They now offer the defective source with one added comment line, as B20_R182's did, and pass.

**Evidence:** `evidence/verifier_adequacy_b20r188/` (`result.json`, `rows.jsonl`, `run.log`). Its record test is not
appended: the drafted test would check the invalid classification.
