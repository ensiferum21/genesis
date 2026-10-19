# B20_R78 record (engineering): a solver language and a program search, so the system can find its own solver

- **Run by:** the builder. Asked for by Daniel (19 Oct 2026), after B20_R77: "we actually handheld it to
  bifurcation? We should let it find itself."
- **No claim, rule, comparator or package changes.**

## What was hand-held in B20_R77, stated plainly

The system's own contribution to B20_R77's engine is the representation it builds on: B18's representation search
found `cross_2`, the bipartite cut (the max-cut reduction), in a grammar the builder wrote. Everything else was the
builder's: simulated bifurcation (B20_R69, from Goto et al., at Daniel's request for physics ideas), and in B20_R77 the
portfolio and the (1,2)-swap search, chosen after the builder's diagnosis. When physics move rules were put inside
the system's own search engine (B20_R72) they did not help. So B20_R77 shows that the system's tool box, assembled by
the builder, beats the tools tested; it does not show that the system found how to. For GV4 (component invention) it
does not count.

## The parts: `invention/solver_programs.py`

A closed language of low-level search steps over an encoding (one of B18's licensed representations: cross_2,
ordered_2, adjacent_2, adjacent_3) and a triangle-free edge set: random encoding, descent (B18's engine), relabels
(random or best, judged by improve / sideways / always / anneal), edge moves (drop an edge and refill its ends; force
an edge in by removing one edge per blocker, then refill), sweeps of either move over all edges, repeat-until-stall,
loop, split of the time, and return to the best. No continuous dynamics (so no simulated bifurcation), no swap move as
such, no portfolio. A program is data checked against the grammar (at most 6 statements per block, depth 3, 30
statements); the interpreter checks the clock at every step, keeps the edge set triangle-free by construction, and
the domain checker re-checks every witness.

What the language can express, shown only by hand-written programs in the tests (none is given to the search): B18's
engine (`init, descent`, repeated) and a swap search (cut search for 75% of the time, then force one edge and sweep
drops with improve acceptance). Note that "drop an edge and refill its ends, keep if larger" is a (1,2)-swap: the
search can build it from two parts, but nothing tells it to.

## The search: `invention/solver_search.py`

A steady-state evolutionary search over programs (genetic programming, Koza 1992; generation hyper-heuristics, Burke
et al. 2010): 16 random programs; 8 children per generation by mutation (parameter, replace, insert, delete, wrap in
a control statement, unwrap, representation) or crossover of tournament winners; the 2 leaders re-evaluated each
generation (fitness is the mean of all their evaluations, so a lucky run is diluted); keep the 16 best; ties to the
smaller program. Fitness: mean best size over the training hosts at 0.25 CPU s. Final choice among 4 finalists by
fresh runs at 0.25 and 1.0 s.

**The kind:** `solver-program-v1` (`candidate_kinds/solver_program.py`), parameters `{program, cpu_seconds}`,
refuses any program outside the grammar or with an unlicensed representation.

## Development looks, disclosed (B20_R76's hosts only)

- At 0.5 s on B20_R76's 12 hosts (2 seeds): B18's engine written as a program reached 12 of 24 targets; the
  hand-written swap search 16 of 24; three random programs 0, 3 and 0. (B20_R77's engine: 20 of 24 at 0.5 s.)
- A two-minute search on 4 of those hosts (fitness at 0.1 s) went from a random population averaging 274.1 edges
  (best 287.3) to 289.3 and returned `[relabel random anneal 100, descent]` on cross_2: perturb a hundred vertices with
  annealing acceptance, then descend, repeated. That is iterated local search over cuts, found from random programs.
  It did not use edge moves.

## Tests

`tests_genesis/test_solver_programs.py` (11): licensed representations are B18's; the grammar accepts and refuses;
generation, mutation and crossover stay in the language (900 children); results triangle-free within budget on 40
random programs; known optima; drop with improve is a (1,2)-swap and undo restores; force keeps the set valid; the
search starts from random programs and returns a valid one; the kind is registered, bound to its files, closed, and
runs in runc with a checked witness. `tests_genesis/test_program_search_study.py` (4): B20_R79's design.

# B20_R79 setup: the system searches for its own solver (preregistered)

`scripts/b20r79_program_search.py`: 16 fresh n63 training hosts (seed 20267901), the search above for 6,000 CPU s
(seed 20267902), alone and pinned, in process; the frozen program, its descriptor, the full history and the program's
anatomy. **Expectation:** an iterated local search over cuts like the development look's, better than B20_R76's
system engine; about one chance in three that it also uses a swap-like edge step. B20_R80 will test the frozen program
on fresh hosts against B20_R77's engine, simulated bifurcation, BURER2002 and CP-SAT.

# B20_R80 and B20_R81 setup (preregistered before B20_R79 has run)

- **B20_R80, a control** (`scripts/b20r80_random_program_control.py`): random programs from the same language for the
  same 6,000 CPU s on B20_R79's training hosts, chosen as the search chooses (Bergstra and Bengio 2012: random search
  is the standard control). Expectation: weaker than the search's program.
- **B20_R81, the test** (`scripts/b20r81_self_found_solver.py`): the two frozen programs, read from B20_R79's and
  B20_R80's evidence (their SHA-256 recorded), against B20_R77's engine, dSB, the system's B20_R76 engine, BURER2002
  and CP-SAT on 24 fresh n63 hosts, by B20_R77's quantile statistic. Three labels: the GV4 headline (self-found
  against the builder's engine), whether the search does the work (against random), and against the state of the
  art; plus a replication of B20_R77. Expectation: the found program beats the B20_R76 engine and random search,
  loses to the builder's engine, and is MIXED against the state of the art; the engine replicates B20_R77.
- Tests: `tests_genesis/test_self_found_solver.py` (7, design).

# B20_R79 amendment before any output: the random-program generator could draw programs outside the language

A test written for B20_R82's library language (`test_solver_library.py`, 300 random B20_R78 programs) found that
`solver_programs.random_program` could draw a program with more than 30 statements (`MAX_NODES`), about 1 in 300
drafts: nested blocks were not counted while drawing. Mutation and crossover only return programs in the language,
but such a program could have entered the search's first population, and if it had won, B20_R79 would have refused
its own result. **B20_R79's first run was stopped 6 minutes in** (16:12 to 16:18 UTC, during its first population,
before any generation was logged or anything frozen; its log is kept as `run1_stopped/run.log`). The generator now
draws again until the program is in the language (the same fix in `solver_library`), and the test draws 3,000
programs (`tests_genesis/test_solver_programs.py`). B20_R79's script, constants, hosts (reloaded from the same
`hosts.json`) and seeds are unchanged; it was restarted with the fix. B20_R80 and B20_R81 are unchanged.
