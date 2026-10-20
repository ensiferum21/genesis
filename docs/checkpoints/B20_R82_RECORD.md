# B20_R82 record (engineering) and the setup of B20_R83–R86: compounding generations (GV5)

- **Run by:** the builder, asked by Daniel to do the remaining batches. No claim, rule, comparator or package changes.

## Why

The roadmap's GV5 asks for gains across generations: three executable generations, each judged against the one
before on fresh panels, with causal evidence. In program search the natural way for one generation's result to carry
into the next is a library of abstractions (library learning; DreamCoder, Ellis et al., PLDI 2021): the next search
can call the earlier discovery, combine it and build around it.

## Engineering

- `invention/solver_library.py`: B20_R78's language (unchanged) plus `["macro", I]`, which runs library entry I as a
  sub-block; entries may call only earlier entries (no cycles); a macro counts as one statement. An empty library is
  exactly B20_R78's language (tested on 300 random programs). Its interpreter subclasses B20_R78's, so a macro inside a
  loop or split runs too.
- `invention/library_search.py`: B20_R78's search, the same algorithm and constants, over programs carrying a fixed
  library; only the body evolves. With an empty library it is the control.
- Kind `solver-library-v1`: runs such a program; refuses anything outside the grammar.
- Tests: `tests_genesis/test_solver_library.py` (9). The first of them found the generator defect recorded in the
  B20_R79 amendment (`B20_R78_RECORD.md`).

## Setup (preregistered before B20_R79 has finished)

- `scripts/b20r83_generation_search.py`: **B20_R83** generation 2 (library: generation 1's body; 16 fresh n63
  training hosts, seed 20268301; search seed 20268302); **B20_R84** its control (no library; B20_R83's hosts; search
  seed 20268402); **B20_R85** generation 3 (library: generations 1 and 2; fresh hosts, seed 20268501; search seed
  20268502). 6,000 CPU s each, alone and pinned.
- `scripts/b20r86_generations_eval.py`: **B20_R86** judges generations 1–3 and the control (and B20_R77's engine as a
  reference) on 24 fresh n63 hosts by the quantile statistic. Labels: transition 1→2, transition 2→3 (IMPROVES /
  WORSENS / NO_DIFFERENCE / UNRESOLVED), the library's effect (generation 2 against its control), and the headline:
  COMPOUNDS (both transitions improve and the library helps), PARTIAL (one improves, none worsens), NO_COMPOUNDING.
- **Expectation:** PARTIAL or NO_COMPOUNDING, PARTIAL slightly more likely; generation 2 can only show a gain if
  generation 1 leaves room at the shortest run times.
- Tests: `tests_genesis/test_generations.py` (7, design).

## B20_R83 result (generation 2)

Alone, pinned, 6,237 s (`evidence/generation2_b20r83/`). The search, with generation 1 callable, froze a 13-statement
program on cross_2 that calls generation 1 three times and adds a kick (force one edge, keep if improved), annealed
edge drops and relabels around it; final mean 291.59 on its own 16 training hosts (not comparable with B20_R79's
hosts). All 16 programs of its final population call generation 1. Judged against generation 1 and the control in
B20_R86. Record tests (2); exposure addenda (16 hosts).

## B20_R84 result (generation 2's control)

Alone, pinned, 6,241 s (`evidence/generation2_control_b20r84/`); light builder work on the other core in its last
~40 minutes, disclosed. With no library, on B20_R83's hosts and budget, the search froze an iterated local search over
cuts with an annealed edge sweep; final mean 291.61 against generation 2's 291.59. The library made no difference on
the training hosts. B20_R85 and B20_R86 are deferred, not withdrawn: Daniel asked for the comparison with the
strongest tuned solvers first (B20_R87 onward).
