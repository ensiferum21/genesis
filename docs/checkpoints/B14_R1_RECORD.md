# B14_R1 checkpoint record (roadmap §14.1)

**Parent:** `GENESIS_COMPLETION_CHECKPOINT_B14.zip`
(SHA-256 `add37fcd26dc44405a7c86f1773a246115e6608ce5c89bef0eba13ce3eaeed4e`,
commit `30a61fc`). B14 itself is unchanged.

**What changed:** repairs F-01 from the external B14 review and closes
B14-OPEN-5 (see `audit/review_b14_external/README.md`). The reproduction's
before and after logs are kept.

**Tests:** see `test_report` in `CHECKPOINT_RECORD.json`. The suites are the
same as B14 plus `test_external_review_b14`.

**Migration:**
- CLAIMS.json renames `statement` to `requested_statement` and adds
  `current_statement`, `conjecture` and `statement_contract`.
- `report.md` is now derived from the claims; free prose moves to
  `operator_notes.md`.
- Mathematical claims require scope `this finite host only`.
- Bundles exported by B14 do not verify under B14_R1 (their CLAIMS.json and
  report.md differ). Re-export them; the evidence stores themselves are
  unchanged.

**Rollback:** check out `30a61fc`.

**Claim ceiling:** engineering only, as in B14. GV0 stays open until an
independent re-review.

**Next:**
1. Independent re-review of F-01 and the B14 repairs.
2. B15: a pinned environment and a second machine (R-04).
3. B14-OPEN-2 to OPEN-4.
