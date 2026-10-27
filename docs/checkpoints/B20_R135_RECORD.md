# B20_R135 record: encodings Genesis chose beat one-hot on colouring (INVENTED_REPRESENTATION_BETTER; DEV), still far behind MaxSAT

- **Run by:** the builder, on DEV; licenses nothing. Preregistered at `7040a3c` (`scripts/b20r135_invented_representations.py`,
  SHA-256 `4b23e1a0de225450e00def7f95dc71356b7f76186ad16423227e5094295cc5bd`), before B20_R133's colouring results
  were seen. Unchanged.
- **Code since `7040a3c`.** The only later change in the packages it uses is a new file,
  `representation/processes.py` (`c8dc893`), which it does not import.
- **Before the run.** The queue's build step for the representation language was marked done: stages A–C and the
  process layer, with 38 fixture tests passing.
- **The run.** Alone on CPU 0, from a clean worktree of `f37e792`, 27 Oct 2026, 09:42–11:10 SGT, in one segment
  (5,232 s against about 1.5 h). `code_identity` `6196cd71…0fa0`.
- **Evidence.** `evidence/invented_representations_b20r135/`; the vault is packed as `vault.tar.xz`. Recomputed
  independently: every colouring's conflicts and every family assignment's satisfied constraints were recounted on
  the regenerated instances, and every value matches.

## Result

**Verdict INVENTED_REPRESENTATION_BETTER.** For 3 and 4 colours, the encoding Genesis chose by itself gives far fewer
conflicts than one-hot, the textbook encoding, through the same pipeline and the same engine at 10 s. For 5 colours it
kept one-hot. Both comparisons survive Holm. **Genesis's engine is still far behind PASMaxSAT-c**, a MaxSAT solver on
the natural encoding, at every k.

**Part B (primary): graph colouring.** G(n, d/n) near the k-colourability threshold; 20 fresh graphs per k (10 each
at n = 300 and 1,000); one seed per graph and arm; 10 s each.

| k (degree) | Genesis's choice (code table) | chosen | one-hot | compiler (B20_R133's path) | MaxSAT (PASMaxSAT-c) |
|---|---|---|---|---|---|
| 3 (4.5) | 2 bits: {00, 01, 10} | **8.5** | 21.6 | 20.1 | 1.6 |
| 4 (9) | 3 bits: {000, 001, 010, 100} | **30.6** | 47.7 | 48.0 | 14.4 |
| 5 (13.5) | one-hot (5 bits) | 59.0 | 59.0 | 58.4 | 17.9 |

The table gives mean conflicts (lower is better), counted by the family's checker and again independently, always in
agreement.

| k | chosen vs one-hot (sign test, wins–losses–ties) | Holm | chosen vs compiler | chosen vs MaxSAT |
|---|---|---|---|---|
| 3 | **18–0–2, p 7.6e-6: INVENTED_BETTER** | rejected | 20–0–0 (p 1.9e-6) | 0–19–1 (p 3.8e-6) |
| 4 | **20–0–0, p 1.9e-6: INVENTED_BETTER** | rejected | 19–0–1 (p 3.8e-6) | 0–20–0 (p 1.9e-6) |
| 5 | (one-hot chosen: no test) | — | 8–12–0 (p 0.50) | 0–20–0 (p 1.9e-6) |

**How Genesis chose** (on 4 training graphs of n = 300, 2 s pilots):
- The encoding search planned every code table in b and b + 1 bits, up to colour renaming: 4 tables for k = 3, 7 for
  k = 4, and 30 for k = 5, of which 3 were feasible.
- It took the 3 cheapest feasible tables other than one-hot, plus one-hot.
- Pilot conflicts (the candidate lists are in `choices.json`):

  | k | Chosen table | Its pilot conflicts | One-hot | Other candidates |
  |---|---|---|---|---|
  | 3 | {00, 01, 10} | 2.5 | 6.5 | 3.0 and 6.5 |
  | 4 | {000, 001, 010, 100} | 10.5 | 18.2 | 13.5 and 23.8 |
  | 5 | one-hot (kept) | 21.5 | — | 3-bit tables 69–245; they need an ancilla per edge |

**Novelty: none claimed.**
- The k = 3 table is the binary (log) encoding with one word unused. Finite-domain encodings of this kind are prior art
  named in the preregistration (Tamura et al. 2009; Chancellor 2019). A 2026 paper also reports a log encoding beating one-hot for graph colouring on a quantum
  annealer ([arXiv 2604.21123](https://www.alphaxiv.org/abs/2604.21123)).
- The k = 4 table is one-hot on three bits plus the all-zero word (k − 1 bits). It is not the domain-wall encoding,
  which for k = 4 would be 000, 100, 110, 111 (Chancellor 2019; [arXiv 2102.12224](https://arxiv.org/pdf/2102.12224)).
  A short search found no name for it. A proper literature check is owed before anything is said beyond the result.
- What the study shows is that Genesis's own search and pilot, without being told, moved away from the textbook
  encoding where it helps, and kept it where it did not (k = 5).
- The pipeline's validity weight and repair rule are human knowledge, declared in the preregistration.

**Part C (secondary): families whose reductions Genesis synthesised, reactivated through the vault.**
- **The cascade was exact.** The four families were parked dormant, each lacking its relation. The four gadgets were
  then synthesised (0.002–0.11 s of CPU each), admitted, archived and announced.
- The cascade (fuel 4, depth 1) reactivated exactly the four families, and the null trigger reactivated nothing.
  Total overhead was 0.34 s of CPU. The vault restores and verifies: 13 artifacts, 58 events.
- Results at 10 s, 20 instances per family (n = 500 and 2,000), satisfied constraints:

| Family | Genesis (synthesised Max-CSP BQP through the engine) | MaxSAT | wins–losses–ties | label |
|---|---|---|---|---|
| 1-in-3 SAT | 719.5 | 638.5 | 16–2–2 (p 0.0013) | GENESIS_BETTER |
| NAE-3SAT | 2,621.8 | 2,620.4 | 9–3–8 (p 0.15) | NOT_DISTINGUISHABLE |
| XOR-3SAT | 1,101.8 | 1,070.5 | 1–18–1 (p 7.6e-5) | MAXSAT_BETTER |
| Max-3-SAT | 5,212.7 | 5,247.2 | 0–20–0 (p 1.9e-6) | MAXSAT_BETTER |

**Disclosed: in 4 of the 80 MaxSAT runs, PASMaxSAT-c returned no model within 10 s.**
- The runs were 1-in-3 SAT at seeds 20581353, 20581456 and 20581457, and XOR-3SAT at seed 20583454. The solver used
  its full CPU time (9.88–9.91 s), but no model was parsed. The back-end then scores the all-zero assignment
  (`compiler/backends.maxsat`), so those four rows are far below the others (113, 460, 434 and 898 satisfied).
- They are valid assignments under the preregistered rule and stay in the table. But they inflate the MaxSAT
  deficit in the 1-in-3 SAT and XOR-3SAT means.
- With those four instances left out (a sensitivity check, not preregistered), the labels are unchanged:
  - 1-in-3 SAT: Genesis 13–2–2 (p 0.0074);
  - XOR-3SAT: 0–18–1 (p 7.6e-6).
- Why PASMaxSAT-c gave no model on those instances is not known. B20_R98's harness check covered other solvers.
- Every colouring run of PASMaxSAT-c returned a model.

**Part A (secondary): synthesis.** The MILP synthesiser against the local-search baseline, given the same CPU time.
The MILP finished in at most 0.57 s, so the search was given the 0.5 s floor in most cases; the comparison is
matched as preregistered, but short.

| Relation set | MILP | Local search | Discordant (MILP only / search only) | McNemar p | Uniform (Max-CSP exact) gadgets |
|---|---|---|---|---|---|
| 20 arity-3 orbits | 20 (16 with 0 ancillas, 4 with 1) | 15 (all with 0 ancillas) | 5 / 0 | 0.063 | 20 |
| 40 random arity-4 relations | 40 (10 with 0, 30 with 1) | 1 | 39 / 0 | 3.6e-12 | 40 |

Every admitted gadget is exact under both checkers.

**Validity.**
- Every colouring and assignment was checked by the family's checker and independently, always in agreement.
- Every gadget is exact under both checkers.
- The engine's median CPU was 0.9998 of the budget.
- The cascade reactivated exactly the parked families, and the null trigger reactivated none.

## Against the expectation stated before running

| Expected | Found |
|---|---|
| the pilot keeps one-hot for k = 5 | yes |
| for k = 3 and 4 a denser code may win the pilot | yes |
| P_k NOT_DISTINGUISHABLE or INVENTED_WORSE (denser couplings make a harder max-cut instance) | **no: INVENTED_BETTER for both**, by large margins (61% and 36% fewer conflicts) |
| verdict NOT_SHOWN or INVENTED_REPRESENTATION_WORSE | **INVENTED_REPRESENTATION_BETTER** |
| `maxsat` best on colouring | yes, at every k |
| Part A: the MILP finds every arity-3 orbit and most arity-4 relations, the search fewer | yes; the MILP found all 40 arity-4 relations |
| Part C: the cascade reactivates the four families | yes, exactly |
| `maxsat` ahead on Max-3-SAT and 1-in-3 SAT | Max-3-SAT yes; **1-in-3 SAT no** (Genesis better, also without the four no-model runs) |
| ties on NAE-3SAT and XOR-3SAT possible | NAE-3SAT tie; XOR-3SAT MaxSAT better |

## What it means

This is the first preregistered study in which a representation Genesis chose by itself beat the textbook one on
fresh instances, through an identical pipeline:
- For 3 colours, the binary code cut conflicts from 21.6 to 8.5.
- For 4 colours, a 3-bit table cut them from 47.7 to 30.6.

It is a result about choosing among encodings, judged by a pilot. Encodings of this kind are prior art, so it is not
an invention of a new kind of representation.

It narrows the gap to the MaxSAT specialist on colouring, but does not close it: 8.5 against 1.6, and 30.6 against
14.4. B20_R133 found Genesis's compiler path far behind there, and this shows that the one-hot penalties were part of
the reason.

The queue's `representation` line records a positive outcome, and its tag `representation-language` is unlocked. No
dormant direction requires that tag, so nothing is reactivated. The queued direction `reduction-invention`,
which waited on this study, is now ready.

## Limits

- DEV, builder-run, one machine, one seed per graph and arm, 20 graphs per k at n ≤ 1,000, one budget (10 s).
- The comparison is within Genesis's pipeline. The validity weight W and the repair rule were fixed in advance and
  apply to every encoding, but they are human choices, and a different W could change one-hot's numbers.
- Part C's MaxSAT means include four runs without a model (above).
- Part A's matched time was short (the MILP finished in under 0.6 s).
- No independent replication.

## Tests

`tests_genesis/test_invented_representations.py::RecordB20R135` (5), on the evidence:
- the preregistered script unchanged;
- every colouring and every family assignment re-checked on its regenerated instance by the family's checker and the
  independent count;
- the pilot's choice;
- the analysis recomputed by `analyse` (verdict, Holm, families, synthesis, the primary labels) and validity;
- the vault restored from `vault.tar.xz` and verified, and the cascade exact.

The 8 design tests are unchanged.
