# B20_R54: does research beyond the pool reach Wolfram's ceiling? (design pilot, DEV)

- **Script:** `scripts/b20r54_wolfram_ceiling.py`, preregistered in commit `5eaf4e9`.
  SHA-256 `fa4a21a0a7a17dee1e14056cdd120f88c7fc78a00c91a071efa7d1d9bd3c0ff1`.
- **Run:** the builder, pinned to one core, 5,845 s.
- **Status:** a design diagnostic. It licenses no claim and adopts nothing.

## Question

B20_R53 found that choosing which pool lemmas to keep has at most 1 of 15 headroom on Wolfram's axiom. The limit
is the ceiling: targets that no library built from the pool proves.

This pilot asks whether a larger conjecture space reaches that ceiling. POOL6 holds the true equations of up to 6
operation nodes, 233 per seed, against POOL5's 88–90.

The evaluation targets avoid both pools and the development targets. The script dropped the 1–3 drawn targets
per seed that had a declared relation to any of them.

## Result: **NO_CEILING_HEADROOM**

Targets proved, of 15:

| Seed | EMPTY | EXHAUST5 | ORACLE5 | GAP5 | EXHAUST6 | ORACLE6 | GAP6 | REPEAT5 |
|---|---|---|---|---|---|---|---|---|
| 5401 | 0 | 9 | 9 | 8 | 8 | 9 | 8 | 9 |
| 5402 | 0 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| 5403 | 0 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| 5404 | 0 | 12 | 12 | 13 | 12 | 12 | 12 | 12 |

- **Ceiling headroom.** ORACLE6 − ORACLE5 is 0 on every seed. Evaluation noise is 0.
- **Conventional research over the larger pool.** EXHAUST6 − EXHAUST5 is −1, 0, 0, 0.
- **Cost.** EXHAUST6 proved 174–183 of the 233 true equations in 523–615 CPU-s. Each of the other 50–59 failed a
  10 s attempt. None of these lemmas proves a target that the 5-node library does not.
- **The keep rule (descriptive).**
  - GAP6 kept 1–5 lemmas and proved 8, 12, 11 and 12, the same as EXHAUST6, at 616–714 CPU-s.
  - GAP5 kept 1–3 lemmas and differs from EXHAUST5 by −1, 0, 0, +1.
  - On seed 5404, GAP5 with one lemma (13) beats both EXHAUST5 and ORACLE5 (12). Lemmas interfere, so the
    oracle is not an upper bound (B20_R6).

## Consequence

Across B20_R53 and R54, on eight seeds, no library-building research of any kind changes the successor on
Wolfram's axiom at these settings by more than 1 of 15. That covers:
- selection;
- keeping;
- larger conjecture spaces;
- the transferred keep rule.

The 3–8 unproved targets per seed need something other than more pool lemmas, for example longer evaluation
budgets or deeper proof search.

The equational target therefore offers neither GV4 headroom nor a GV6 transfer test at these scales.
B20R9-OPEN-1 is updated. The GV6 target question (B20R46-OPEN-1) moves to the other candidates in
`handoff/gv6/README.md`.

## Files

- `seed_<n>.json`: the material (both pools, development and evaluation targets, the dropped related targets; all
  now exposed), the research runs with every outcome, GAP trajectories, and every library's per-target statuses.
- `summary.json`: the verdict and the table.
- `run.log`: the log.

## Tests

`tests_genesis/test_wolfram_ceiling.py` has 7 tests. The design tests check:
- the rules, the seeds and the pools;
- that POOL5 is B20_R53's construction;
- that the targets are unrelated to all research material;
- the verdict rule.

The record tests check:
- the verdict recomputes from the seed files;
- the material is what the script derives;
- no run hit its cap;
- GAP's lemmas come from its pool.
