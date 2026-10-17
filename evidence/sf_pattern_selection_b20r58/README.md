# B20_R58: does choosing which invented sum-free patterns to use matter? (GV4 headroom pilot, DEV)

- **Script:** `scripts/b20r58_sf_pattern_selection.py`, preregistered in commit `641ff38`.
  SHA-256 `26535533…2cb4eb`.
- **Run:** the builder, pinned to one core, 2,495 s.
- **Code identity:** `08689a1a…`.
- **Status:** a design diagnostic. It licenses no claim.

## Question

GV4 needs a research decision that changes the successor. B20_R56/R57 suggested one: all 17 transferred patterns
help on hard sum-free hosts but cost time on easy ones. Could a chosen subset beat both "none" and "all"?

**The setup.**
- **Development hosts (16).** Each pattern was scored by the root-bound gain per separation row it adds alone.
  TOP-k is the k highest-scoring patterns. DEV-K is the smallest k within 0.5 of ALL's development root bound,
  else 8.
- **Evaluation hosts (16).** NONE, ALL, TOP-1, TOP-2, TOP-4 and TOP-8, each with the tree route at 30 s.

## Result: **NO_HEADROOM**

| Set | Certified (of 16) | Total wall |
|---|---|---|
| NONE (Schur rows only) | 10 | 283 s |
| **ALL (17 patterns)** | **13** | 322 s |
| TOP-1 | 9 | 300 s |
| TOP-2 | 10 | 285 s |
| TOP-4 | 10 | 277 s |
| TOP-8 (ORACLE-K, and DEV-K) | 11 | 269 s |

- **BASE is ALL.** H = ORACLE-K − BASE = −2, and the deployable DEV-K is also 2 below ALL.
- **Soundness.** Every certificate VALID, and values agree across sets.
- **Why selection fails.** Alone, each pattern barely moves the development root bound: gains of 0.1–0.6 from 1–5
  added rows. Together they move it 7 (115.9 → 108.9). TOP-8 reaches only 114.2. The patterns' value is joint,
  so no subset chosen by individual merit approaches ALL. The one that won here keeps every pattern.

## Consequence

For GV4 (B20R9-OPEN-1), this setting has no selection headroom either. Choosing which invented patterns to use
does not beat using all of them. The domains with no research-decision headroom now include:
- graph construction;
- the equational systems, including Wolfram at hard settings;
- larger C4 rows;
- sum-free pattern selection.

GV4's learned-versus-fixed comparison has no setting where it could show a difference. The roadmap's fallback
(report a useful solver without claiming a better improver) is now the builder's recommendation for the reviewer's
GV4 decision.

## Files and tests

- **Files.** `hosts.json` (with witnesses), `scores.json` (per-pattern development scores and ranking),
  `rows.jsonl` (every evaluation host × set), `summary.json`, `run.log`.
- **Tests.** `tests_genesis/test_sf_pattern_selection.py` (5): constants and fresh hosts; subsets and sets; the
  verdict rule; the record recomputes; the hosts are the script's.
