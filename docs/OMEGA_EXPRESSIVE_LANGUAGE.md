# Richer algorithm expressiveness, separated from search, and a language that extends itself (adopted 27 Oct 2026)

**Status.** This is Daniel's direction of 27 Oct 2026, 14:33 SGT, adopted as the next priority. It answers the
question B20_R132 left open: what answers EXPRESSIVENESS. The directive, verbatim:

> ARA diagnoses the obstacle → Genesis invents a structural repair → the independent Judge verifies it → the
> Consolidator preserves it → Genesis resumes research with the improved workflow.
> prioritize richer algorithm expressiveness, experimentally separated from improvements in search.
> They should improve on themselves as in expressiveness wise and richness

Every part below is marked BUILT, PREREGISTERED or PLANNED. Nothing here is a result.

**Progress.** X1 is BUILT (B20_R153, `docs/checkpoints/B20_R153_RECORD.md`): `mcx3` and its pinned binary, with
every mcx2 program identical; the Λ1 front end; the inventor's operators over Λ0 and Λ1. X2 (B20_R154) is next.

## 1. Reading

- **The obstacle** is B20_R132's: engine invention reaches nothing that a fresh graph set confirms beats REX, and the
  diagnosis by its preregistered rule is EXPRESSIVENESS in every class. B20_R128 adds that a better inventor process
  has nothing to select on. ARA's ladder (B20_R150) generalises that diagnosis to any workflow graph.
- **The repair is structural and Genesis's**: a richer engine language, grown by Genesis from its own engines and
  verified before it is kept. A parameter change does not count, and nor does a human choosing the decisive
  mechanism (the milestone rules of `docs/OMEGA_ARCHITECTURE_INVENTION.md` §14).
- **Separated from search**: every claim says whether it is about what the language can express or about how well a
  search finds it, with an experiment that tells the two apart. A gain that a stronger search alone would have given
  is a search gain, whatever produced it.
- **"They should improve on themselves"**: the language's own richness grows by Genesis's inventions, generation
  after generation. Each generation's language is the base for the next, and each step is judged.

## 2. Definitions that make the separation measurable

Fix a domain (max-cut engines at a CPU budget), a graph distribution and a **description-length bound** N (tokens
per program).
- **The expressiveness of a language Λ at N**, E(Λ, N): the value, on fresh graphs, of the best program of length at
  most N that a **ceiling search** finds. The ceiling search is fixed, long and exactly evaluated, and the same for
  every language. Its value is estimated by B20_R132's instruments (T1 selection, T2 confirmation, power).
- **The search effectiveness of a search procedure s in Λ**, A(s, Λ, N): the value of what s itself finds, at its own
  budget, in programs of length at most N.
- **The two gaps:**
  - expressiveness gain = E(Λ', N) − E(Λ, N);
  - search gain = A(s', Λ, N) − A(s, Λ, N).
  Each is measured with the other factor held fixed.
- **The factorial**: language {Λ, Λ'} × search {s, s'} at matched compute. It gives both main effects and their
  interaction. A language gain that appears only under the weak search, and vanishes under the ceiling search, is a
  search effect: the richer language made good programs easier to find, not newly expressible.
- **Why a bound N**: a named statement that expands to many primitive statements lets a program of length N express
  behaviour that needs more than N primitive tokens. At a fixed bound, then, library growth is a real expressiveness
  increase, not only a search aid. Both readings are reported: at the bound, and with abstractions expanded.

## 3. The pipeline, mapped to Genesis

| Step | What does it | State |
|---|---|---|
| ARA diagnoses the obstacle | `architecture/diagnose.py`'s ladder on the engine-invention workflow cast as an AG (the language is a node; its ceiling stand-in is the ceiling search), with B20_R132's instruments for an expensive real domain | ARA-1 BUILT on the zoo (B20_R150); the real-workflow cast PLANNED (X2) |
| Genesis invents a structural repair | **Language growth**: new named statements Genesis abstracts from its own best engines (library learning by anti-unification of recurring subprograms with parameters, generalising `selfimprove.learn_macros`), written in a construct algebra (§4) | the language, named statements and operators BUILT (X1, B20_R153); library learning PLANNED (X2) |
| The independent Judge verifies it | A kernel-side **language judge**: a candidate language element is admitted only if, on sealed fresh graphs, the language with it beats the language without it at matched compute under the same search (and under the ceiling search, for an expressiveness claim), and beats a tuning-only control. The protected `autonomy/feedback.py` stays unchanged | PLANNED (X2) |
| The Consolidator preserves it | The vault: each admitted element as a capability record with its contract (expansion semantics), implementation, property tests (parse, expansion and execution identity), verification evidence (the judge's decision), cost profile, failure envelope (classes where it did not help) and provenance. A versioned language registry names its parent | vault BUILT; records with contracts PLANNED (X2, `OMEGA_META_ADAPTIVE.md` §5.3) |
| Genesis resumes research | The next generation of engine invention starts from the promoted language and its best engines (`selfimprove.seeded_ops`), and the cycle repeats on the next obstacle | PLANNED (B20_R152) |

## 4. The construct algebra (human-designed infrastructure, labelled as such)

The present engine language (`mcx2`) is a flat loop of physics operators with two guards (S, P). To give Genesis
something to grow, the builder provides once a **generic** construct algebra in a new engine kind (`mcx3`). Its
constructs are control and addressing, not search operators:
- **blocks** `[ ... ]`, so that a guard governs several statements;
- **guards over run-time observables** beyond stall and period: diversity of the elite pool, the spread of replica
  cuts, the fraction of the budget spent;
- **targets**: which replicas an operator acts on (coldest, hottest, a level, all);
- **phases** by fraction of the budget (built as ?-guards on `f`, the fraction of the budget spent);
- **repeats** `*k`, so that an item or a block runs k times (added while building, B20_R153; control, not search);
- **named statements**, which the front end expands, so they need no change to the native code.

BUILT (B20_R153): `candidate_kinds/native/mcx3.c` and `candidate_kinds/mcx3.py` (the grammar there), and
`expressive/lambda1.py` for named statements.

Every `mcx2` program means the same in `mcx3`, and gives the identical result under the same seed (a test). The
operators stay those of `mcx2`, all prior art.

The algebra is the builder's, and so is its gain. That gain is measured and reported as a human LANGUAGE change (Λ0 →
Λ1), never as Genesis's invention. **Genesis's** claims start from Λ1: the statements it defines, admits and reuses
(Λ1 → Λ1 + library_k).

## 5. Self-extension, generation by generation

A generation has five steps:
1. invent engines in Λ_k (the inventor and its judge, as in B20_R127);
2. abstract recurring parameterised subprograms from the best of them into candidate named statements, with a
   minimum-description-length score (as in DreamCoder, Ellis et al. 2021; Stitch, Bowers et al. 2023; prior art,
   none claimed);
3. admit them through the language judge;
4. consolidate them;
5. Λ_k+1 = Λ_k + the admitted statements.

Later statements may use earlier ones, so richness compounds: a statement of generation 2 can be a composition of
generation-1 statements. The measure each generation is E(Λ_k, N) and A(s, Λ_k, N), the factorial's two readings.
A generation that admits nothing stops the line (the queue's stagnation rule). A language element that never
helps is kept dormant with its failure, not deleted.

**Where the headroom is.** B20_R132 measured little headroom at 1 s on 800-vertex generated graphs: +0.055%,
+0.23% and +0.073% from ten times the time. Expressiveness can only show where something is attainable. Every
study therefore first measures headroom on its graph classes, by B20_R132's instrument, and runs only where it is
material. Larger planar and toroidal graphs at short budgets, where REX is furthest from its own longer runs, are
the first candidates.

## 6. Batches (dependency-ordered; each study preregistered before it runs)

| Batch | What | State |
|---|---|---|
| X1 (engineering) | `mcx3`: the construct algebra in the native interpreter (a new pinned binary; `mcx2` untouched), the Λ1 front end (parser, canonical form, expansion of named statements, the description-length measure), search operators over Λ1 for the inventor, the identity test against `mcx2` | BUILT (B20_R153): 312 of 312 identity runs identical, 30 of 30 at study scale, interpreter cost about 1.02 |
| X2 (engineering, B20_R154) | Library learning over Λ1 (anti-unification with parameters, MDL scoring); the language judge (kernel side, sealed graphs, digest pinned); the consolidator (capability records with contracts in the vault, a versioned language registry); the engine-invention workflow cast as an AG for ARA's ladder | PLANNED, next |
| B20_R151 (study) | **Expressiveness separated from search.** PREREGISTERED (`scripts/b20r151_expressiveness.py`); run alone on CPU 0 while X2 is built on CPU 1, because it needs only X1. The design as registered: candidate classes planar, toroidal and random at 2,000 vertices; gate 0.2% at p < 0.05; at most two classes; inventor 240 x 4 graphs, ceiling 480 x 8 graphs; 3 inventor and 3 ceiling replicates per language; 24 truth graphs, two runs each; P1 needs the per-graph test and the replicate permutation test. AMENDED before any search finished (the 2-replicate per-graph rule could take search luck for a language; found by X2's judge on its fixture; disclosed in the script). Gate: planar2000 PASS (0.572%), toroidal2000 and random2000 fail; one class studied. Headroom gate first. Factorial language {Λ0, Λ1} × search {the inventor at B20_R132's budget, the ceiling search} at matched compute, on fresh graph classes with headroom. Primary: the expressiveness gain under the ceiling search; the search gain within Λ0; their interaction | PLANNED |
| B20_R152 (study) | **Self-extension.** Generations k = 1–3 of Λ1 + library_k, each admitted by the language judge; per generation E and A, the admitted statements' reuse, and whether value on fresh graphs rises (Page's trend test). Every gain is labelled with the factor that carries it | PLANNED |

The zoo study B20_R141 (ARA's calibration, experiments A–D) moves after B20_R151. ARA-1 is used in X2 as the
diagnoser of the real workflow, and the zoo still calibrates it.

## 7. What does not count

- The builder's construct algebra presented as Genesis's invention.
- A library statement that only shortens programs, presented as an expressiveness gain, when the ceiling search
  without it reaches the same value.
- Any gain on development graphs.
- Any result in which a human chose the statement that carried the gain.
