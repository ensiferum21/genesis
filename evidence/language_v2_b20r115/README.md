# B20_R115 evidence: a search in language v2, held to the invention test: NOT_DEMONSTRATED

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r115_language_v2.py` with `src/genesis/invention/solver_programs_v2.py`, preregistered at
  `9180a5c` (committed through the index while B20_R113 ran, before any run of this study).
- **Run:** alone on CPU 0, 3,712 s, on 23 Oct 2026 (19:17–20:19 SGT), in one slice.
- **Code identity:** `ddec2a16…`, the committed tree `9180a5c`. B20_R116's files were kept out of the working tree.
- **The other core.** While it ran, the builder recorded B20_R113 (documents, a 4 s record-test run, one worktree
  identity hash), added documentation rows, and listed the Gset instances not yet reached (about 2 s).

| File | What |
|---|---|
| `hosts.json` | 36 fresh large hosts, 9 per cell: 4 for the search, 8 for tuning, 24 held out |
| `search.json` | The search's report (generations, evaluations, distinct programs, its claimed score), the program it chose, and tfxw's 2 s reference value on each search host |
| `trace.jsonl` | All 816 search evaluations: normalised score and program digest |
| `runs.jsonl` | Every tuning and held-out run (84 template variants on 8 hosts; 10 tuned templates, the candidate, tfxw and hybrid-swap on 24) |
| `summary.json` | Tuning scores, the tuned variants, the champion, Test 1, T9's and T10's standing against T4, held-out values and means, the verdict, validity |
| `run.log` | The run |

## Result: NOT_DEMONSTRATED

**The search.**
- 79 generations, 816 evaluations (800 plus 16 for the four finalists), 644 distinct programs.
- Training score (the mean fraction of tfxw's 2 s value at 0.5 s): from 0.884 for the first program to 0.9959
  within the first 100 evaluations, 0.9983 at best. The final choice re-scored 0.9962 on fresh evaluations.
- **The program chosen:** on the `adjacent_2` representation, `[descent, relabel(random, anneal, 1000),
  repeat(1, [agree])]`, repeated until the budget ends.
- **It uses a pool statement only in name.** `agree` acts only when the pool holds two elite edge sets, and nothing
  in the program offers one (`elite` never runs). So `agree` does nothing. The preregistered syntactic check reports
  `uses pool: True`, but in effect the program is descent followed by annealing, repeated: annealing with the
  descent of T4 and T5. Had it beaten prior art, Test 2's deletion search would have removed the idle statement
  before judging the core.

**Prior art, tuned on 8 hosts.** The champion is again **T4** (annealing then descent; `adjacent_2`, half the budget
annealing), mean gap 0.11% below the best variant on each host. The two new memetic templates rank behind five of
the eight old ones: T9 (consensus recombination) 0.76%, T10 (cluster recombination) 0.76%.

**Test 1** (24 held-out hosts, 2 s, against T4): **7–10 (7 ties), p = 0.63: NOT_DISTINGUISHABLE.** No core test
ran.

**The new primitives in their textbook use:** T9 and T10 lose to T4 on **all 24** held-out hosts (0–24 each).

**Held-out means** (edges kept, 24 hosts):

| Arm | Mean |
|---|---|
| the builder's tfxw (reference) | 4,235.0 |
| **the candidate** | **4,229.4** |
| T2 iterated local search; T4 annealing then descent (champion) | 4,228.0; 4,228.0 |
| T3 annealing | 4,227.6 |
| the builder's hybrid-swap (reference) | 4,226.8 |
| T5 restarted annealing | 4,219.8 |
| T1 multistart descent | 4,215.8 |
| T9 memetic, consensus | 4,206.6 |
| T10 memetic, cluster exchange | 4,199.0 |
| T8, T6, T7 | 4,195.6; 4,183.6; 4,181.1 |

**Validity:** median CPU 1.00 of the budget for every program arm; 1.10 for tfxw (runc start-up metered); no
invalid edge set.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| NOT_DEMONSTRATED | NOT_DEMONSTRATED |
| T4 remains the champion; T9 and T10 trail it at 2 s | Yes; they trail it on every held-out host |
| The search finds a program that uses a pool primitive, NOT_DISTINGUISHABLE from T4 | NOT_DISTINGUISHABLE, with the highest held-out mean of any program (by 1.4 edges). It contains a pool statement, but one that never acts |
| The new primitives may need longer budgets or a different problem to matter | Consistent with what was seen: at 2 s on these hosts, recombining elites costs more time than it returns |

## What it means

- **The richer language did not produce an invention.** The search's program is a known recipe, descent and
  annealing, and does not beat the tuned champion of the same family.
- **The population moves that help on max-cut do not help here, at this budget.** Used as a memetic algorithm
  would, both new moves lose to annealing-then-descent on every held-out host. On max-cut they are restarts inside
  a fast native engine running for seconds to minutes; here, in the interpreted language at 2 s, rebuilding an edge
  set from elites costs more time than it returns.
- **The search can now get close to the best of prior art by itself:** its program has the highest held-out mean
  of all programs, though not significantly. As in B20_R80, most of the training gain came within the first hundred
  evaluations.
- **The invention test did its job twice over.** It caught that the candidate is no better than prior art. And its
  design (signature, deletion search, statement kinds) would have caught the idle pool statement had it been.
- **Three preregistered attempts (B20_R111, R112, R115) leave the claim NOT_DEMONSTRATED.** In this problem and
  language, program differences are about 0.1%, near the hosts' noise. A future attempt needs a setting where
  methods differ by more: larger hosts, longer budgets, or the max-cut engine's own move set.
