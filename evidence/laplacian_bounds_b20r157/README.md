# B20_R157 (F4): the Frontier against prior-art searches on the sealed Laplacian bounds (PARTIAL; DEV)

- **What ran:** the amended preregistered script `scripts/b20r157_laplacian_bounds.py` (`ff9eada`, sha256
  `fb5dd07e…5785`), from the clean worktree `/home/claude/f4b-wt`, alone on CPU 0, in two slices on 30 Oct 2026,
  08:23–10:44 SGT. `code_identity` `d823bcbb…173a` (recomputed at recording; it matches). The killed first attempt is
  in `../laplacian_bounds_b20r157_attempt1/`, not used.
- **What is here:**
  - `rows.jsonl`: 168 single-search rows and the three joint arms' rows, with their artifacts;
  - `summary.json`: validity, the refuted sets, P1 and the verdict, the unconfirmed refutations, and the Frontier's
    sources;
  - `run.log`: the slice log;
  - `state_*.json.gz`: the joint arms' final engine states, gzipped. The SHA-256 of the originals:
    - FRONTIER `ab075e4c2c494cf4240fa2f11cec9efe86a131ecdabf035c4a5efb03bcd0f5e4`
    - UCB `6176b45a2a5c73aa3ad982d3939843e976b1ad2a3e94e3a63189d5cb5dc1d923`
    - UNIFORM `c207abcffee0cac4de601c19b4c189163afc2283ed6ca58b81d832cfe01d7eb4`
- **Verdict:** PARTIAL, valid. FRONTIER beats NRPA (p_Holm 0.032), and not GBFS, CEM, UCB or UNIFORM. Refuted with
  both checks, of 33 known-false bounds:
  - GBFS 19;
  - FRONTIER 14;
  - UCB 13;
  - UNIFORM 12;
  - CEM 9;
  - NRPA 4.

  Nothing was found against bounds 44 or 46, and nothing against a proved bound.
- **Unconfirmed:** 38 Γ-built refutations of 43–64 vertices were beyond the Sturm check's n ≤ 40. A descriptive
  matrix-form check confirms all of them. With them, the joint arms reach 25–26 of 33.
- **Record:** `docs/checkpoints/B20_R157_RECORD.md`. The record tests are `RecordB20R157` in
  `tests_genesis/test_laplacian_bounds_study.py`.
