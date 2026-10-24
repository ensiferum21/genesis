# B20_R127 evidence: the system's own max-cut engines against human designs: NOT_SHOWN

Builder-run on DEV (Daniel, 24 Oct 2026: "invent to improve itself ... better than us"). It licenses nothing.
- **Script:** `scripts/b20r127_self_invented_engine.py`, preregistered at `70a590d` and amended before any run at
  `bc7e424` (per-class engines, three compounding generations, macros, analogy across classes, Gset at 60 s).
- **Run:** alone on CPU 0 from the main worktree, in two slices on 24 Oct 2026 SGT: 12:43:24–14:33:29 (the searches
  and the first judged runs; paused at the 6,600 s slice limit) and 14:45:37–16:20:17. B20_R129 ran in the pause
  between them from its own clean worktree.
- **Code identity:** `badf60cb…`, the tree of `8d7e402` (the preregistration plus the Gset table's dated sources).
- **The other core.** During the run the builder used CPU 1 for unit tests, numpy development looks and documents.
  No engine ran on CPU 1 during the judged 10 s and 60 s runs.

| File | What |
|---|---|
| `search.json` | The nine searches (3 classes x 3 generations): references, each search's engine and the judge's report, the learned macro libraries |
| `trace.jsonl` | Every evaluation the searches made (generation, order, split, value, engine) |
| `runs.jsonl` | The 420 judged runs in the runc sandbox: held-out (D) at 1 s and 10 s, generations 1 and 2 at 1 s, Gset at 10 s (4 engines), SYSTEM at 60 s; each with its partition (`side`), CPU and descriptor |
| `summary.json` | Tables, tests, the verdict, the engines, CPU, validity |
| `run.log` | Both slices |

## Result: NOT_SHOWN (as expected)

**The engines.** Per class, generation 3's engine (SYSTEM):

| Class | SYSTEM's program | A template of a human design? |
|---|---|---|
| random | `B1044 X` (breakout, then replica exchange) | no |
| planar | `P6 b24` (perturbation, then a small breakout) | no |
| toroidal | `P3 R I b9` (perturbation, restart, cluster moves, breakout) | no |

**Test 1 (primary): Gset G1–G54 at 10 s, SYSTEM against MCX** (B20_R105's builder-configured engine): 16 wins, 11
losses, 27 ties, sign test p = 0.44: **NOT_DISTINGUISHABLE**. Verdict **NOT_SHOWN**.

**Secondary (uncorrected):**

| Comparison | Wins–losses–ties | p | Label |
|---|---|---|---|
| Gset 10 s: SYSTEM vs REX | 9–18–27 | 0.12 | NOT_DISTINGUISHABLE (REX ahead) |
| Gset 10 s: SYSTEM vs BLS | 28–5–21 | 6.6 x 10^-5 | SYSTEM_BETTER |
| Held-out (15 graphs) at 1 s: vs MCX / REX / BLS | 6–2 / 7–2 / 6–5 | 0.29 / 0.18 / 1.0 | NOT_DISTINGUISHABLE |
| Held-out at 10 s: vs MCX / REX / BLS | 5–2 / 4–4 / 6–2 | 0.45 / 1.0 / 0.29 | NOT_DISTINGUISHABLE |
| Compounding: generation 3 vs 1 (held-out, 1 s) | 6–3–6 | 0.51 | NOT_DISTINGUISHABLE |
| Gset 60 s: SYSTEM vs B20_R110's MCX at 60 s | 19–8–27 | 0.052 | NOT_DISTINGUISHABLE |

By class on Gset at 10 s (net wins of SYSTEM): random (25 instances) −8 against MCX and −10 against REX; planar (20)
+12 and +2; toroidal (9) +1 and −1. Instances at their best known value at 10 s: SYSTEM 27, MCX 24, REX 31, BLS 21
of 54; mean fraction of the best known: SYSTEM 0.99911, REX 0.99879, MCX 0.99866, BLS 0.99708. SYSTEM at 60 s: 30
of 54 at the best known value; **no record candidate** (no value above a best known one), so no literature check is
owed.

**Against the expectation** (stated before running: Test 1 NOT_DISTINGUISHABLE; no compounding; no record candidate;
NOT_SHOWN): as expected on every point. Not expected: the planar engine's lead over MCX on Gset's planar instances
(+12 net), and REX's lead on the random class.

## Ω0: why nothing was released (the mechanism analysis, from `trace.jsonl`)

**The judge released nothing in any of the nine searches.** So SYSTEM is not a released improvement: each class's
engine is the judge's *starting* incumbent of generation 3, the best of that search's initial population (the
previous generation's engine, three of its mutations, the other classes' engines and random engines) on the
4-graph training split A alone. That is why the engines changed between generations without a release.

| Search | Evaluations / distinct engines / generations | Best A score (vs REX = 1) | Judge's tau | tau / best A gain | Submissions |
|---|---|---|---|---|---|
| planar 1 / 2 / 3 | 160 / 76–77 / 8 | 1.0023 / 1.0022 / 1.0022 | 0.92% / 1.54% / 1.66% | 4.0 / 7.0 / 7.6 | 5 / 5 / 4 |
| random 1 / 2 / 3 | 160 / 75–76 / 8 | 1.0014 / 1.0011 / 1.0014 | 1.74% / 2.45% / 0.75% | 12.8 / 22.4 / 5.4 | 6 / 5 / 6 |
| toroidal 1 / 2 / 3 | 160 / 76–78 / 8 | 1.0007 / 1.0007 / 1.0004 | 1.26% / 1.12% / 1.95% | 17.1 / 15.2 / 52.4 | 3 / 4 / 5 |

The best training gains over REX (+0.04% to +0.23%) were 4 to 52 times smaller than the release threshold. The
threshold comes from B − C differences of **random** engines (the contract version 2's calibration); about 60
children per search were proposed. Four explanations remain open: the judge's calibration, the evaluator's size
(4 graphs per split), the number of proposals, and the headroom REX leaves at 1 s. **B20_R132** separates them
(Daniel's directive of 24 Oct, 15:35, item 2).

**Mechanism table (Ω0's success criterion).** No mechanism can be credited: with no release, macros, analogy across
classes and compounding generations contributed nothing measurable, and none was ablated.

| Mechanism | Measured contribution |
|---|---|
| Learned macros (generations 2–3) | none measurable (no release) |
| Analogy across classes (seeds from other classes) | none measurable |
| Compounding generations | NOT_DISTINGUISHABLE (6–3–6) |
| The planar engine's lead over MCX on Gset planar | observed (+12 net), from an engine chosen on A without confirmation; not attributed to any mechanism |

## Validity and the record

- Valid: median metered CPU 1.21, 1.02 and 1.00 of the 1 s, 10 s and 60 s budgets; 0 of 420 runs failed.
- `RecordB20R127` (in `tests_genesis/test_self_invented_engine.py`):
  - re-checks every run's cut against its partition on the regenerated graph;
  - checks that the run set is complete;
  - checks that the summary's tables are the runs';
  - recomputes the analysis, the tests and the verdict against the best-known table as it stood at the run's end
    (`gset.best_known(as_of=…)`);
  - checks the engines are valid programs and that the judge released nothing;
  - checks the code identity.
- **Limitations:**
  - one seed per (instance, engine, budget);
  - the held-out set is 15 graphs;
  - SYSTEM's engines were selected on 4 training graphs;
  - the 60 s comparison is against another study's run (another seed).
