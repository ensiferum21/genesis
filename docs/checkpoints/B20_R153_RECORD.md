# B20_R153 record: X1, the engine language Λ1 (mcx3, its front end and the inventor's operators) (engineering)

- **What this is.** The first batch of Daniel's direction of 27 Oct 2026, 14:33 (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`):
  "prioritize richer algorithm expressiveness, experimentally separated from improvements in search. They should
  improve on themselves as in expressiveness wise and richness". It is the queue's `expr-x1-build`, numbered
  B20_R153. It builds the language that B20_R151 measures and that X2 and B20_R152 let Genesis grow.
- **No claims.**
  - Nothing here is a result, and no engine was compared with another.
  - **The construct algebra is the builder's.** It is human-designed infrastructure: whatever it gains is a human
    LANGUAGE change (Λ0 → Λ1), never Genesis's invention.
  - Genesis's own claims can start only from Λ1 + the statements it defines (X2, B20_R152).
- **Built by** the builder on 27 Oct 2026, with no LLM. The protected judge `autonomy/feedback.py` is untouched.
  mcx2 (its source, binary and pin) is untouched.

## What was built

| Part | What it does |
|---|---|
| `candidate_kinds/native/mcx3.c` | mcx2's interpreter turned into a tree interpreter. Every line of mcx2.c from its includes to `relink`, and its option parser, is kept byte for byte (checked by diff); only the program representation, the parser and the main loop are new. **Items:** mcx2's operators, optionally with a **target** (`@c`, `@h`, `@a`, `@<levels>`); mcx2's guards S and P; **?-guards** over run-time observables (`f` the fraction of the budget spent, `d` the elite pool's diversity, `s` the spread of the replicas' cuts, `t` the attractors since the last new best); **repeats** `*k`; **blocks** `[ ... ]`. Up to 512 items, nesting 16. A test build (`-DMCX3_PROBE`) reports where each operator acts and what each observable is computed from |
| `candidate_kinds/mcx3.py` (kind `mcx3-v1`) | The language as data: `parse`, `render`, `check`, `canonical` (one text per meaning class), `is_lambda0` (mcx2's language), `size`/`walk`/`depth`; the configuration (mcx2's options and space, `prog` canonical without calls), the pinned binary, `solve`. Bounds 256 items, nesting 8 |
| `scripts/b20r153_build_mcx3.py` | The deterministic build (gcc 13.3, `-O3 -std=gnu11 -static`, mcx2's flags), install, `--check`; `build_test` for the counting-clock and probe builds. Pin `9449f8b6…dcbd24` |
| `tests_genesis/native/countclock.h` | Test builds only: a counting clock in place of the CPU clock, and a trace hash of every exp call's clock reading and argument |
| `expressive/lambda1.py` | Λ1 + library. **Named statements** with parameters `$1..$k` in numeric places, in immutable versioned **libraries** (each version names its parent; JSON rebuilds to the same version). A call is one item, so a guard before it governs the whole statement; a one-item body is that item, so a statement can be a named condition. **Expansion** to the kind's canonical programs. **Description length:** `length` (items: the bound N of E(Λ, N)) and `bits` (a prefix code, for the MDL scores of X2), with `library_bits` |
| `expressive/operators.py` | **The inventor's operators over Λ0 and Λ1, as one implementation with the language as a parameter.** Λ0: selfimprove's seven mutation kinds and a crossover, making only mcx2 programs. Λ1: those and `target`, `guard`, `block` and `repeat`, plus `call` with a library. Every output is valid and canonical in its language within the bound (default 32, mcx2's). `ops()` plugs into `feedback.steady_state_search` and `selfimprove.search` unchanged |
| `candidate_kinds/kinds.py` | `mcx3-v1` registered |

## The identity: every mcx2 program means the same in mcx3

The test builds replace the CPU clock with one that counts readings, so a run is a function of its input. mcx2's
unchanged source and mcx3's are built the same way, and their output and trace (every exp call, once per attractor
and per exchange attempt, with its clock reading and argument) are compared.

- **The battery** (`test_mcx3_kind.Identity`): 26 mcx2 programs (the 12 hand-written ones and 14 random Λ0
  programs) × 6 configurations (levels 1, 3, 4 and 8; all three perturbation modes; pools 4 to 16; two random
  configurations) × 2 seeds, on four graphs: **312 runs, all identical**, averaging more than 100 traced events per
  run.
- **The comparison sees a difference when there is one.** Two planted mutants of mcx3 are caught on more than a
  third of the runs where they apply:
  - one extra clock reading in L;
  - replica exchange visiting levels hottest first.
  This check exists because the first version of the test compared outputs only, and it missed the extra clock
  reading (the final best had already been found). The trace was added after that.
- **At study scale** (`evidence/mcx3_b20r153/overhead.json`): 800-vertex random graphs and 784-vertex tori, three
  programs including REX, 300,000 clock readings per run: **30 of 30 identical.**
- **The interpreter's cost.** On the same work, mcx3's CPU time is a median **1.02** times mcx2's:
  - per-program medians 0.99–1.03;
  - single runs 0.91–1.23, alternating order, on core 1, so the spread is timing noise.
  No material overhead was seen.

## The constructs mean what they say

- **Equivalences that hold clock reading for clock reading** (21 pairs, two graphs, two seeds):
  - a target equal to the default and the bare operator;
  - `B@c` / `B@0` and `b`;
  - `[ A B ]` and `P1 A B`;
  - `*2 A` and `P1 A A`;
  - `*3 [ A B ]` and its unrolling;
  - nested repeats;
  - guards that always or never hold (`?t`, `?d`, `?s`, `?f`) and their P1 paddings.
- **Probes:**
  - every operator acts on the levels its target names, at 1, 4 and 8 levels;
  - `d` and `s` are recomputed exactly from the printed elite pool and replica cuts;
  - `f` rises monotonically to the end of the budget;
  - the item after a ?-guard runs exactly when the guard holds. Both outcomes are seen for every observable, over
    three threshold settings.
- **The canonical form keeps the meaning.** 400 random Λ1 programs are their own canonical forms, and a random
  non-canonical rewriting of each canonicalises back to it. For 25 programs without `?f` guards (f reads the clock,
  which a rewriting shifts), a program and its rewriting run the same operators in the same observed states over
  their common runs (more than 500 probe lines compared).
- **Small optima:** six programs that use the constructs, at 1 and 3 levels, on four brute-forced graphs; and a
  run in the runc sandbox.

## Choices made while building (disclosed)

- **Repeats** (`*k`) are a construct the design document (§4) did not list. They are control, not search, and are
  added to §4.
- **mcx2's guard rule is kept, quirk included.** A guard that fails skips the next item whatever it is, so
  `S5 P2 C` runs C when S5 fails. Composing guards needs a block (`S5 [ P2 C ]`).
- **Named statements whose body is a guard.** The first canonical form spliced `late(900) [ M H ]` into
  `late(900) M H`, which changes the meaning once `late` expands to a guard. Found while building; fixed:
  - the kind's `canonical` treats a call as a guard unless told which statements are not guards;
  - a library knows which of its statements are guards;
  - a definition that repeats a guard is refused.
- **Bounds.**
  - **The canonical form does not depend on the run's number of levels.** `@0123` stays as written, even though it
    equals `@a` at four levels.
  - **Description lengths:** `length` counts items, and arguments are part of their tokens; `bits` is a simple
    prefix code. Both are definitions, fixed here, before any study uses them.
- **The Λ0 operators follow selfimprove's distribution, not its sequence of draws.** The same seed gives different
  engines than `selfimprove.engine_ops()`. B20_R151 therefore runs both languages through `expressive.operators`,
  so the search is the same code in each.

## What B20_R151 takes from this

1. **Run both languages on the mcx3 binary.** The identity makes Λ0 programs on mcx3 the same engines as on mcx2,
   and keeps a binary difference out of the language factor. The reference REX also runs on mcx3.
2. **The bound N = 32 items for both languages** (mcx2's limit), and the factor is the language: Λ0 or Λ1, with
   `operators.ops(lang)`.
3. **Still to be fixed at preregistration:**
   - the ceiling search (the same operators and algorithm at a much larger budget, with exact evaluation on more
     graphs and repeats);
   - the headroom gate on fresh graph classes.

## Not in X1 (X2, B20_R154)

- Library learning (anti-unification with parameters, MDL).
- The kernel-side language judge.
- The consolidator (capability records with contracts, the language registry in the vault).
- The engine-invention workflow cast as an Architecture Graph for ARA's ladder.

## Tests

- `test_mcx3_kind` (18): binary, identity, mutants, equivalences, probes, canonical form, kind, sandbox.
- `test_expressive_lambda1` (8): libraries, definitions, expansion, guard calls, configuration, lengths.
- `test_expressive_operators` (6): validity in each language, reach, mutation kinds, determinism, bound, the
  protected search and selfimprove's search running with the operators.
- `test_omega_boundary`: now also covers `genesis.expressive`.
