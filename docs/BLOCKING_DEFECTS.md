# Blocking defects (registered at the start of B14)

Source: reviewer roadmap "Genesis: what remains to reach the grand vision"
(baseline `GENESIS_COMPLETION_CHECKPOINT_B13.zip`, commit `82aa557`, tag `b13-baseline`).
Scientific promotion is blocked until each is closed by an adversarial regression
test and independent review (gate GV0).

| ID | Defect | Reproduced on B13 here | Status |
|---|---|---|---|
| R-01 | Evidence kernel accepts a valid envelope without schema, role-to-kind authorization or claim binding; one envelope in three wrapper nodes counts as three generations | yes — `audit/reproductions/logs/b13_baseline_82aa557.log` (R-01a, R-01b ATTACK_SUCCEEDED) | REPAIRED IN B14, PENDING INDEPENDENT REVIEW |
| R-02 | Release bundle exports stored claim levels and ignores revocation; `verify_bundle` returns ok | yes — same log (R-02 ATTACK_SUCCEEDED, `verify_ok: true`) | REPAIRED IN B14, PENDING INDEPENDENT REVIEW |
| R-03 | World loop / IR drop the DRAT proof and full upper certificate; no checker-only replay | source inspection (not an exploit) | REPAIRED IN B14, PENDING INDEPENDENT REVIEW |
| R-04 | Deployment not reproducible: placeholder image digest, Python 3.12 lock vs 3.13 run, containment needs a supporting host | environment finding | OPEN (main work in B15) |

Reproduction command (run from the repo root against any tree):

    PYTHONPATH=src python3 audit/reproductions/r01_r02_b13.py

The script uses the B13 fixture hook (`kernel._load_roles = ...`) on purpose so the
original log stays meaningful. Post-repair regression tests live in
`tests_genesis/test_acceptance_regressions.py`.

## B14 outcome

- After the repair the original script reports every attack blocked
  (`audit/reproductions/logs/after_r01_r02_repair.log`).
- An internal red-team pass on the first repair found eleven further ways
  through (four critical); a second pass on the repaired tree found twelve more
  (two critical); a third pass found nine more (one critical). All are
  repaired with regression tests; see `audit/redteam_b14/README.md`,
  `audit/redteam_b14_round2/README.md` and `audit/redteam_b14_round3/README.md`. The
  reviewers were fresh agents under the same operator, so this is not the
  independent source review GV0 requires — and three rounds that each found
  critical issues are a reason to expect more.
- R-04 remains OPEN (main work in B15). B14 only fixed packaging consistency
  (networkx declared in `pyproject.toml`) and made undeclared test skips fail.

| ID | Item still open | Needs |
|---|---|---|
| R-04 | Supported deployment: pinned image digest, one Python version across lock and runtime, containment on a supporting host, second-machine matrix | registry access, a second machine |
| B14-OPEN-1 | ~~Custodian did not verify request facts against the campaign export~~ — CLOSED in B14 (round-2 C1): the custodian rebuilds the export and checks campaign, source and domain | — |
| B14-OPEN-2 | Selective reporting across different candidates or campaigns: one registration per candidate slot is enforced, but a custodian-published registration log with a multiplicity rule is not | W06/W07 |
| B14-OPEN-3 | `sealed_improver_evaluation` and `sealed_generation_evaluation` are refused by the custodian until a research-lineage protocol can be checked from the export | W21 |
| B14-OPEN-4 | FINITE_CERTIFIED, THEOREM_CHECKED, causal, internal-replication, DEV_ONLY and priority levels have no replay contract and are unreachable (fail closed) | W03/W05/W08 |
| B14-OPEN-5 | ~~Report prose linted against the bundle-wide ceiling~~ — CLOSED after the external review (F-01): report.md is derived from per-claim current wording; caller prose is checked at the floor. Still open: ladder/world-loop internal reports lint against fixed levels (they are not exported as claims) | W02 |
| F-01 (external review) | ~~A requested optimum exported as the claim's statement at WITNESS_VALID~~ — REPAIRED: requested vs established wording separated; see `audit/review_b14_external/` | pending re-review |
| GV0 | Independent source review of R-01..R-03 and the F1–F11 repairs | an auditor outside the research operator |
