# B20_R133 evidence: the Problem Compiler against the specialists: BEHIND_SPECIALISTS_ON coloring, mis

Builder-run on DEV (Genesis Ω, engine 1; Daniel, 24 Oct 2026: "a solver of anything verifiable"). It licenses
nothing.
- **Script:** `scripts/b20r133_problem_compiler.py`, preregistered at `e8bc181`.
- **Run:** alone on CPU 0, 24 Oct 2026, 19:33:37–20:32:49 SGT (3,552 s), from a clean worktree of `8bdebad`. That is
  the preregistration plus later code this study does not use.
- **Code identity:** `130db5cc…`, the tree of `8bdebad`.
- **The other core.** During the run the builder used CPU 1 for documents, unit tests and the representation
  language's fixtures. No solver ran there.

| File | What |
|---|---|
| `runs.jsonl` | 640 runs (80 instances x 2 budgets x 4 arms): the raw assignment of every answer, its verified score, the back-end's notes, CPU and wall time |
| `summary.json` | The tests, Holm, the verdict, means, secondary tests, failure rates |
| `run.log` | The run |

## What this study tests, and what it does not

R133 tests **the execution of existing reductions**. Every reduction used here was written by the builder:
- the textbook penalised QUBO forms of `compiler.families.compile` (e.g. Lucas 2014);
- the reduction to max-cut of `compiler.bqp.to_maxcut`;
- the natural MaxSAT encodings of `compiler.families.wcnf`.

Genesis's engine (REX, never tuned for these families) solves the compiled forms. **Nothing in R133 is an invented
reduction.** Reductions Genesis synthesises itself are B20_R135's subject (part C, from predicates only;
preregistered `7040a3c` before this study ran).

## Result: BEHIND_SPECIALISTS_ON coloring, mis

**Primary tests** (10 s; Genesis against PASMaxSAT-c, the MaxSAT Evaluation 2026 entrant; two-sided sign test over
the family's 20 instances; Holm over the three):

| Family | Wins–losses–ties | p | Label | Holm |
|---|---|---|---|---|
| Independent set (maximise) | 0–10–10 | 0.002 | **SPECIALIST_BETTER** | rejected |
| 4-colouring (conflicts, minimise) | 0–19–1 | 3.8 x 10^-6 | **SPECIALIST_BETTER** | rejected |
| Max-2-SAT (satisfied, maximise) | 2–0–18 | 0.50 | NOT_DISTINGUISHABLE | not rejected |

**Mean verified scores at 10 s** (by size, small and large):

| Family | Genesis | PASMaxSAT-c | NuWLS-c-2026 | HiGHS (MILP) |
|---|---|---|---|---|
| Independent set, n 500 / 2,000 | 219.0 / 874.3 | 219.0 / 877.0 | 219.0 / 876.8 | 204.7 / 547.8 |
| 4-colouring conflicts, n 150 / 500 | 5.3 / 31.9 | 3.4 / 10.4 | 3.7 / 11.8 | 21.4 / 146.9 |
| Max-2-SAT, n 500 / 2,000 | 2,070.0 / 8,292.7 | 2,070.0 / 8,292.5 | 2,044.8 / 8,291.2 | 1,898.8 / 6,772.3 |
| Max-cut (control), n 500 / 2,000 | 1,193.6 / 4,780.7 | 1,193.6 / 4,775.7 | 1,193.6 / 4,781.6 | 1,025.3 / 124.0 |

**Secondary (uncorrected):**
- **At 1 s:**
  - Max-2-SAT: Genesis is better than both MaxSAT entrants (7–0 and 15–0).
  - Independent set: Genesis is behind (0–11).
  - Colouring: Genesis is behind (1–18).
- **Control (max-cut):** Genesis beats PASMaxSAT-c (10–0 at 10 s, 11–0 at 1 s) and ties NuWLS-c-2026 (3–7, p = 0.34).
- **Against HiGHS:** Genesis is better on every family at both budgets (20–0).
- **Failures:** none, in any arm.
- **Repair:** none of Genesis's answers needed repair; the penalised QUBO's answers were feasible as returned.
- **Budgets** were matched in wall time, and each arm ran alone on one core: medians 1.00–1.05 s and 10.01–10.14 s
  for every arm. The recorded `cpu_s` is the parent process's and does not include the solvers' own CPU.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| Colouring SPECIALIST_BETTER (one-hot penalties make a rugged QUBO) | Yes, by far: 18.6 against 6.9 conflicts on average |
| Independent set NOT_DISTINGUISHABLE at 10 s | **No**: SPECIALIST_BETTER. The gap is small (546.7 against 548.0 on average, 0.25%) but consistent on the large instances (10 losses, no win) |
| Max-2-SAT NOT_DISTINGUISHABLE | Yes (2–0–18), and Genesis is better at 1 s |
| HiGHS far behind on every family | Yes |
| The control a tie | Genesis ties NuWLS and beats PASMaxSAT on max-cut |
| Verdict BEHIND_SPECIALISTS_ON coloring | BEHIND_SPECIALISTS_ON coloring, mis |

## What it means

- **Through builder-written reductions, Genesis's engine is a competitive general solver only where the reduction is
  natural.**
  - Max-2-SAT and max-cut are quadratic and unconstrained: there it ties or beats the specialists.
  - Hard constraints become penalties, and those penalties cost it: slightly on independent sets, heavily on
    colouring.
- **This is a representation result.** Colouring's one-hot penalties are the textbook encoding, and that is where
  Genesis loses most. B20_R135 (preregistered before this run) tests whether an encoding Genesis chooses does better
  through the same engine.
- **Limitations:**
  - one seed per (instance, arm, budget);
  - two sizes per family;
  - the engine's default configuration only;
  - PASMaxSAT-c and NuWLS-c-2026 run on their natural encodings, which encode the same problems differently from
    Genesis's QUBO.

## The record

`RecordB20R133` (in `tests_genesis/test_problem_compiler_study.py`):
- regenerates every instance from its seed;
- re-checks every answer twice:
  - by the family's verifier (`compiler.families.verify`);
  - by a second checker written apart from the compiler (numpy and networkx), which decodes the raw assignment
    itself;
- checks that the run set is complete;
- recomputes the analysis, the Holm family and the verdict;
- checks the code identity.
