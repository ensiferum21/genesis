# B14 internal red-team review

A fresh agent (same operator, no shared context beyond the repository and a
brief) attacked the R-01/R-02/R-03 repairs at commit `6302204`. This is useful
adversarial coverage but **not** external independence (roadmap §15).

- `REPORT_internal_redteam.md` — the reviewer's report, verbatim.
- `f*_*.py`, `_harness.py` — the reviewer's reproduction scripts (unchanged).
- `logs_before_fix/` — their output on `6302204` (attacks succeeded).
- `logs_after_fix/` — the same scripts on the repaired tree. Several now stop
  at schema validation (the scripts build pre-repair request shapes), so the
  attacks are re-expressed against current schemas in
  `tests_genesis/test_redteam_b14.py`, which is part of the release matrix.

| Finding | Severity | Repair | Regression |
|---|---|---|---|
| F1 bundle fields not compared; duplicate claim ids; report/statements unlinted; certificates/MANIFEST unchecked | CRITICAL | verifier regenerates every store-derived file and requires byte equality; whole-object CLAIMS comparison; duplicate ids rejected; report and claim statements linted; snapshot tables compared; LIMITATIONS checked; unsafe paths refused | `F1BundleWholeObject` |
| F2 re-registering a verifier name un-revokes it | CRITICAL | revoking any registration retires the identity; revoked identities cannot be registered | `test_f2_…` |
| F3 priority adjudication revocation ignored | CRITICAL | evaluation identity defined for every signed schema; priority branch checks revocations | `test_f3_…` |
| F4 MULTIGEN from a cyclic lineage of one program | CRITICAL | receipts sign `candidate_program_hash`; candidate ≠ baseline; each link's baseline is the predecessor's candidate; no repeated versions or programs | `test_f4_…` |
| F11 re-registering a claim until a lucky draw | HIGH | custodian allows one registration per claim slot (claim, kind, domain, generation); anchors carry the slot | `test_one_registration_per_claim_slot` |
| F8 statement written after the receipt | HIGH | requests, anchors and receipts commit `statement_hash` and `scope`; `create_claim` with a binding must use them; claim statements linted at export | `test_f8_…` |
| F5 OPTIMALITY_CHECKED on custody alone | HIGH | kernel replays the certificate (checker only, cached per bundle) before licensing; trivial bounds checked against the host | `test_f5_…` |
| F6 index/history/phase from mutable or raw records | HIGH | index evidence rows are the effective licensing nodes; history only from content-addressed decisions and labelled producer-recorded; campaign phase re-derived from the event history and verified envelopes | `test_f6_…` |
| F10 preflight/phases disagree with kernel | MEDIUM | `receipts.accept_receipt` (trusted role, schema, outcome, source eligibility) used by phases and preflight; phases use the role of the frozen request's evidence kind | `F10SharedAcceptance` |
| F9 optimality claim not bound to its problem | MEDIUM | claims carry `problem = {task_sha256, value}`; required for OPTIMALITY_CHECKED and matched against bound state, witness check and certificate | `test_f9_…` |
| F7 `verify-bundle` exits 0 on rejection | MEDIUM | exit status 1 when not ok | `test_cli_verify_bundle_exits_nonzero_on_rejection` |

Speculative items: trust-root ancestors now checked; key revocation compares
decoded keys; malformed revocation records no longer crash; bundle paths are
checked. **Still open:** the custodian does not yet verify a request's
`campaign_id`, `source_hash` and transfer source domain against the campaign
export it receives (it binds the export hash only). Recorded in
`docs/BLOCKING_DEFECTS.md`.
