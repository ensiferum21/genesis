# B20_R79 record: the system's own program search finds an iterated local search with a swap-like step

- **Run by:** the builder. DEV only. Asked for by Daniel: let the system find its solver itself.
- **Setup:** `49d34ec`; amended before any output at `943cc6d` (the generator fix; run 1 stopped at 6 minutes, nothing
  frozen; see `B20_R78_RECORD.md`). Alone, pinned, 6,247 s. **Evidence:** `evidence/program_search_b20r79/`.

## Result

From random programs only, the search (149 generations, 1,497 evaluations, 1,201 distinct programs, 6,160 CPU s on
16 fresh n63 training hosts) froze a 10-statement program on adjacent_2 (the cut): descent, then a phase with one
**swap-like sweep** (drop each chosen edge, refill its ends, keep if no smaller) and an annealed-perturbation-plus-
descent loop, then more perturbation and descent. Fitness went from 265.4 (random population mean; best 279.9) to
287.34. Swap-like programs held the lead from the 37th evaluation on and were 94% of the last 300.

**Against the expectation:** the builder expected an iterated local search over cuts and gave a swap-like step about
one chance in three. The search found both. No kick step was kept (two finalists had one).

**What this does and does not show.** It shows that the system, given low-level parts and no assembly, builds the
two ideas of B20_R77's repair stage that matter here (perturb-and-descend over cuts, and the (1,2)-swap on edge sets)
on its own. It does not yet show that the program is good on hosts it has not seen; that is B20_R81's question, with
B20_R80's random-program control.

## Tests

`tests_genesis/test_program_search_study.py`: Design (4); Record (4). Exposure addenda: 16 training hosts.
