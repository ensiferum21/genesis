# B20_R79 evidence: the system's program search finds its own solver, with a swap-like step

Builder-run on DEV. It licenses nothing. The program it froze is tested on fresh hosts in B20_R81.
- **Script:** `scripts/b20r79_program_search.py`, preregistered at `49d34ec` (SHA-256 `950a587d…eb3b`); amended
  before any output at `943cc6d` (the random-program generator could draw programs above the size limit; the new
  `solver_programs.py` is `6700866d…46e2`, sent to Daniel before the restart). Run 1 was stopped 6 minutes in, during
  its first population, with nothing frozen (`run1_stopped/run.log`); run 2 is the run. Alone, pinned to CPU 0,
  6,247 s; search CPU 6,160 s. `code_identity` `11626325…9776`, the committed tree at the run.
- **Training hosts:** 16 fresh DEV planted-cluster hosts (p_in 0.8, p_out 0.06) at n63 (`hosts.json`, drawn in run 1
  excluding 3,179 exposed identities and reloaded by run 2). The search saw only these.

## What it found

From 16 random programs (mean fitness 265.4 edges, best 279.9) to a frozen program with a final mean of 287.34 (at
0.25 and 1.0 s, 2 fresh seeds, all 16 hosts), after 149 generations, 1,497 evaluations of 1,201 distinct programs:

```
rep adjacent_2 (it decodes exactly as cross_2: the cut)
descent
split 10% / 90%:
  first 10%:  sweep drop sideways                      <- a swap-like edge step
              loop: split 10% / 90%: relabel 1000 random vertices with annealing acceptance | descent
  last 90%:   split 75% / 25%: relabel 1000 random vertices with annealing acceptance | descent
(the body repeats until the budget is spent)
```

That is iterated local search over cuts (perturb with annealing, then descend), with a sweep in the space of edge sets
that drops each chosen edge, refills its ends and keeps the result if it is no smaller. "Drop and refill, keep if
larger" is a (1,2)-swap; with "sideways" it also walks plateaus. **Anatomy:** swap-like step yes; kick (force) no; cut
search yes; phases (split) yes; restarts (init) no.

- The first swap-like program was the search's second draw; swap-like programs held the running best from evaluation
  36 on (with brief exceptions) and were 94% of the last 300 evaluations. Representations in the last 300: adjacent_2
  261, cross_2 20, ordered_2 13, adjacent_3 6.
- The four finalists are all of this shape (final means 287.31, **287.34**, 287.31, 287.25); two also use a "force"
  step (a kick), which the winner does not.

## Against the expectation

The builder expected an iterated local search over cuts like the two-minute development look's (no edge moves) and
put the chance of a swap-like edge step at about one in three. The search found both.

## What it does not show

Nothing here compares the program with anything on hosts it was not trained on. B20_R80 (random programs with the
same budget and choice) and B20_R81 (fresh hosts, against the builder's engine, dSB, BURER2002 and CP-SAT) do. The
fitness is in-process at 0.25 s; B20_R81 runs in the sandbox on the 0.05–2 s ladder.

## Tests

`tests_genesis/test_program_search_study.py`: Design (4); Record (4): the frozen program is in the language, its
descriptor rebuilds, and it is the finalist with the highest final mean; the history starts from random programs and
its counts match the summary; the anatomy recomputes; the training hosts are fresh and in the exposure addenda.
