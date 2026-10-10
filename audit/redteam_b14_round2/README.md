# B14 internal red team, round 2 (commit `9c71dbe`)

A second fresh agent (same operator; not external independence) attacked the
tree after the round-1 repairs. Its scripts (`r*_*.py`, `_r2.py`) and their
original outputs (`logs_before_fix/`) are kept unchanged. `logs_after_fix/`
holds the same scripts on the repaired tree; most now stop at an earlier,
stricter check (a request without a verifiable campaign export, an
unreplayable witness check, a claim bound to another campaign), so each attack
is re-expressed against current schemas in
`tests_genesis/test_redteam_b14_round2.py` (plus the cases noted below).

| ID | Severity | Finding | Repair | Regression |
|---|---|---|---|---|
| C1 | CRITICAL | CONFIRMED_TRANSFER for a candidate that never saw the source domain; request campaign/source/domain never checked | custodian rebuilds the bound campaign export and requires campaign_id, source_hash and domain (transfer: source = campaign domain, target differs) to match; improver/generation kinds refused until a lineage protocol exists (W21); kernel requires the claim binding to name this store's campaign and source | `test_request_facts_must_match_the_campaign_export`, `C1KernelCampaignBinding` |
| C2 | CRITICAL | WITNESS_VALID, FINITE_CERTIFIED, THEOREM_CHECKED, causal and replication levels from producer-written verdicts | only kernel-replayable evidence licenses a level: witness checks are re-run (stored problem + witness, dual predicates), bound states replay their certificate, EXECUTABLE needs a stored attempt or IR program, signed kinds need the right role; every other kind has no replay contract and licenses nothing | `test_declared_verdicts_without_a_replay_contract_license_nothing` |
| H1 | HIGH | `verified_phase` skipped the binding checks; envelopes replayable into another campaign | `verified_phase` applies the same binding checks as `advance` against the replayed history; the frozen request must name this campaign and its export must be a prefix of this campaign's events; frozen request may not change after LEAK_SCAN_PASSED; key revocations applied; `campaign status` shows the verified phase | `H1PhaseChain` |
| H2 | HIGH | same candidate re-registered under a new claim id | registration slot = campaign + candidate program + kind + domain + generation position | `test_one_registration_per_claim_slot` |
| H3 | HIGH | duplicate JSON keys in CLAIMS.json | strict JSON (duplicates/NaN rejected) and byte equality with the canonical re-derived claims | `test_h3_duplicate_keys_in_claims` |
| M1 | MEDIUM | extra code under `analysis_code/` | shipped file set must equal the code identity; REPRODUCE.md says to verify with the reader's own trusted genesis | `test_m1_unidentified_shipped_code` |
| M2 | MEDIUM | wording-gate bypasses; LIMITATIONS/REPRODUCE unlinted | NFKC + invisible-character stripping; affirming idioms ("not surprisingly", "no doubt") do not negate; negation confined to the clause; code spans with prose and self-referential citations are linted; all prose files linted, REPRODUCE.md must be the standard text | `M2Wording`, `test_m2_…` |
| L1 | LOW | nested MANIFEST.json exempt; partial event tail dropped; entries outside `release_*` ignored | only the top-level MANIFEST is exempt; a partial tail fails; anything outside the release directory is refused | `test_l1_…` |
| L2 | LOW | revoking a receipt node did not follow the envelope | revoking a signed node also revokes its evaluation identity | `test_l2_…` |
| L3 | LOW | program identity by raw encoding | identity = hash of the validated canonical program | `test_l3_…` |
| L4 | LOW | aliased base64 role keys | role keys compared as decoded keys | `test_l4_…` |
| L5 | LOW | initialised campaigns showed UNVERIFIED | idempotent phase writes accepted | `test_initialised_campaign_is_consistent` |

Still open (recorded in `docs/BLOCKING_DEFECTS.md`): selection across *different*
candidates or campaigns needs a custodian-published registration log with a
multiplicity rule (W07); improver/generation evaluations need the lineage
protocol (W21); declared-verdict kinds need replay contracts (W03/W05/W08).
