# Genesis: every known weakness, what can and cannot be removed, and the blueprint to remove what can (31 Oct 2026, 22:03 SGT)

> Identify all the exhaustive weaknesses and solve it. Overall I want a system that's extremely powerful, recursively
> improves itself, has no weakness other than physical limitation, even that itself can overcome too. Push the full
> implementation idea for any agent to be able to understand. (Daniel, 31 Oct 2026, 22:03)

This document is written for any agent that picks up this repository. It has four parts:
1. what "no weakness" can mean, and what it cannot (§1);
2. the register of every weakness found so far, each with its evidence, its remedy and the test that would show the
   remedy works (§2);
3. the architecture that removes the removable ones, recursively (§3);
4. the implementation plan in order, with files, interfaces and acceptance tests (§4-§6).

It promises nothing it cannot measure. Each remedy is **not done** until its acceptance test is recorded.

## 1. What "no weakness" can mean

No system, natural or built, can be free of every weakness. The limits below are theorems or laws, not engineering
gaps. A system that claims to have overcome them is mistaken, or is measuring something else. What a system *can*
do is: know its limits, measure how close it is to them, and keep closing every gap that is not one of them. That is
the target here.

| Limit | What it says | What Genesis does about it |
|---|---|---|
| No free lunch (Wolpert and Macready 1997) | No search or invention method beats any other averaged over all problems | Improve on the *distribution of problems that matters*; measure on fresh draws from it; keep a portfolio (B20_R148 found no single best process) |
| Rice's theorem, the halting problem | No program decides every semantic property of programs | Verification is by certificates, tests and checkers: sound where they apply, never complete. Report what was checked, not "correct" |
| Gödel, and Löb's theorem | A system cannot prove its own soundness, and a system that trusts its own proofs unconditionally becomes inconsistent | **Genesis may not certify itself.** Its judge and verifier are fixed from outside (the circle, `docs/OMEGA_YIN_YANG.md`). Trust in a new part comes from an external check and a track record on fresh problems |
| Goodhart's law | A measure optimised hard stops measuring what it meant | Score only on problems drawn by fixed random rules after a contribution is sealed; several independent checks; audits of the checks themselves (§2, C) |
| Statistics | Finite samples; regression to the mean; many comparisons | Preregistration; effect sizes with intervals; multiplicity control; independent replication (B20_R186 replicated B20_R185) |
| Complexity | Search spaces grow exponentially with the size of what is searched for; NP-hard problems stay hard in the worst case | Compression (libraries, abstraction), priors (the LLM as proposer), anytime search. No escape for the worst case |
| Physics | Landauer: kT ln 2 per erased bit. Bremermann: about 1.36 x 10^50 bit/s per kg. Light speed; energy; money | Nothing overcomes these. Genesis can (a) measure and reduce compute per verified gain, (b) approach the limits by efficiency, (c) **ask humans** for more resources. It never acquires resources on its own: no spending, deployment or external action without authorisation (the standing brief) |
| Safety | An unbounded self-modifier with no fixed reference can optimise away its own checks | The circle is outside every loop; every self-change is a candidate admitted by a check it cannot alter |

**The honest target.** A system that improves itself at every level it can reach (object, inventor, meta-inventor,
process). Every improvement is verified by a circle it cannot change, on problems it did not choose. The improvement
compounds across generations and is measured per unit of compute. Its remaining limits are the ones in the table
above. That is achievable, step by step. "No weakness at all" is not, and an agent that promises it should not be
believed.

## 2. The weakness register (as of B20_R186; B20_R187 running)

Each entry gives:
- **evidence**: a record that shows the weakness;
- **remedy**: what removes it;
- **test**: what would show the remedy works;
- **status**.

Status is `open` unless stated; nothing in this section is marked solved unless a record shows it.

### A. Invention: Genesis's own building blocks

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| A1 | The substitution kinds, edits, grammar productions and derivation operators are the builder's | B20_R182-R186 records; `docs/OMEGA_RULE_INVENTION.md` §5 | **Invent the building blocks.** (a) Productions and substitution kinds as data in a typed meta-language (§3, L3), searched by Genesis. (b) LLM offers as candidates (`OMEGA_YIN_YANG.md` loop 1). Both are admitted only through verified transfer | A building block Genesis or an offer introduced repairs held-out draws that no builder-written block reaches (preregistered, fresh draw) |
| A2 | Genesis's lifted transformations alone never beat the builder's rules | B20_R185 P1 1-1, B20_R186 P1 3-0 (n.s.) | More and better lifting sources: every verified repair (not only version 3's and the dream's), multi-statement repairs, compound statements (today skipped) | P1 significant on a fresh draw |
| A3 | Compositions were never admitted | B20_R185, R186: compose [1, 1] | Composition at the *edit* level (a two-statement patch), not only substitution tuples; admission by a two-site repair | A composed transformation admitted and used held-out |
| A4 | About a third of every random draw is beyond every arm | 11 of 24 (B20_R185), 11 of 36 (B20_R186) | The failure atlas (`OMEGA_YIN_YANG.md` loop 2): diagnose each miss after recording (which substitution was missing), feed it to the inventor's and the LLM's next proposals | The beyond-every-arm fraction falls on fresh draws across cycles |
| A5 | Genesis's space has not beaten the builder's grammar | B20_R185 P3 0-0; B20_R186 P3 12-3, p_Holm 0.070 | Merge: let the grammar's productions be lifted and admitted as transformations, so the library subsumes the grammar; then the comparison becomes "library vs library plus offers" | P3 significant, or the grammar retired because the library covers it |
| A6 | The learned order over productions did not invent faster | B20_R183 step 6, 2-6 | Order by value of information (expected verified repairs per evaluation), learned across studies, not per study | Earlier first-solutions on a fresh draw |
| A7 | Admission on one verified repair of another family is weak evidence | B20_R182 design | Sequential admission: admit after a Beta lower bound on transfer success exceeds a threshold; retire below it; report each rule's track record | False admissions (rules that never help again) fall, with reach unchanged |
| A8 | Candidate rules whose patches fail the visible tests are never counted as failures | B20_R182 record | Count every tried candidate in the posterior (successes against attempts) | Posteriors calibrated (predicted against observed transfer rates) |
| A9 | Representation invention did not happen in the proving tests | PT-1 INADEQUACY_GATE_FAILED; PT-2 NOT_PROVED_OUT | Apply the repair line's lesson: lift, admit and derive *representations* the way transformations are; random fresh problem draws; the same circle | PT-3 part 1 passes |
| A10 | Invention in the engine line releases little: what is reached is too small to see | B20_R132 EXPRESSIVENESS; B20_R151, R152, R174 | Bigger, compositional engine languages with the same lift, admit and derive cycle; a finer, judge-approved measure (never a weaker one) | A released engine gain at the judge's material size on fresh graphs, replicated |

### B. Diagnosis: knowing what is missing

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| B1 | The loop does not tell an exhausted repertoire from a spent budget | B20_R182 record | Record per episode: candidates generated, candidates evaluated, and whether the search stopped on budget or on exhaustion | Field present; the invention trigger uses it |
| B2 | False repairs are sent to invention as if a rule were missing | B20_R182 record | Route by cause: a false repair means weak evidence, so add trials and strengthen the visible checks; it is not a missing rule | Fewer repeated false repairs (R2, W1 and D1 recur in every run) |
| B3 | The diagnosis is the suspected *methods*, not the missing *capability* | `OMEGA_RULE_INVENTION.md` §2 | The failure atlas: compute the minimal missing substitution against donors; classify the miss (no donor, wrong edit, missing kind, budget) | The atlas predicts which offer or derivation will repair a miss better than chance |
| B4 | The diagnosis-led search once lost to unfocused search | B20_R178 | Keep widening (version 2+); learn the focus width from outcomes | Never worse than nolocal on fresh draws |

### C. The circle: the checks themselves

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| C1 | The verifier's hidden tests are the builder's, and their strength is unmeasured | `repairkernel/verify.py` | **Mutation-adequacy of the verifier.** Run the mutant generator on every component; every mutant the hidden tests do not reject is a verifier gap. Strengthen the checks *monotonically* (add checks, never remove; each addition passes the correct sources) | Verifier mutation score reported; it only rises; no correct source rejected |
| C2 | Q02's deletion was proposed by every arm and rejected only by the verifier | B20_R185 | Also from C1: the visible checks miss what the verifier catches; promote verifier-caught failure patterns into visible regression tests (from recorded studies only) | Fewer false repairs per study |
| C3 | Isolation holes found late | B20R183-CATALOGUES | The isolation probe derived from a list of everything the kernel owns (`foundry.CATALOGUES` pattern), not hand-listed; a test that every kernel file is in a probe | A planted new kernel file is caught by the test |
| C4 | Security rules broken unseen for eight batches | B20R184-PICKLE | Before every commit, run the repository-wide rule tests (`test_no_llm`, `test_gi6_legacy_paths`, every study's digest pin, lint) as well as the changed modules' tests; the full integration suite (over three hours) stays at checkpoints | No rule violation survives a commit |
| C5 | The judge is fixed, so it cannot become sharper | B20_R132: its power to see +1% was at most 6% | A finer judge version, *added* beside the old one, only by preregistered calibration; never replace or weaken (contract) | A new judge version with measured power, adopted by Daniel's decision |

### D. Evidence and statistics

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| D1 | Obstacles of the same defect (three jobs) are not independent | B20_R185, R186 | Report the defect-level test beside the obstacle-level one; preregister the defect as the unit when claiming generality | Both reported in every new record |
| D2 | Effective samples are small (2-4 defects carry an effect) | B20_R185 P2 | Larger draws (cheap: random mutants), more seeds; replications by default | P2 holds at the defect level on a draw of 60 or more |
| D3 | One testbed, one builder | all repair studies | External replication: a second machine (`deployment/reproduce.sh`), and an independent reviewer | A second-machine reproduction of B20_R186 |

### E. Realism and generality

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| E1 | Fifteen small components, single-point mutants | `targets.py`, `defects5-7.py` | Real code: larger components written with tests (`OMEGA_YIN_YANG.md` YY-3), then real projects' historical bugs (a Defects4J- or BugsInPy-like corpus, imported only as data with its own tests) | The cycle's gain holds on a real-bug corpus |
| E2 | Multi-location and semantic bugs are absent | catalogues | Mutants with two or more points; deletions of compound statements; API misuse | Reach measured per bug order |
| E3 | Knowledge does not cross lines (repair, conjecture, engines) | separate libraries | One typed library of transformations over programs, statements and representations; one admission and credit system (§3) | A transformation admitted in one line helps another |

### F. Process and operations

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| F1 | CPU 0 idles when the session stalls (6 h 36 min, 1 h 7 min, ...) | B20_R177, B20_R183 records | A queue runner that is not the agent session: a persistent daemon (systemd or cron) that pops `research_queue.json` and runs `scripts/ops/run_slice.sh`; the agent only preregisters and records | CPU 0 idle under 1% over a week |
| F2 | A watcher started a study early | B20_R186 | Fixed in `scripts/ops/README.md` (match only new lines); better, the daemon of F1 holds a lock per CPU | Two jobs can never share CPU 0 |
| F3 | A failing test was committed | B20_R187 preregistration | A pre-commit hook that runs the commit profile and refuses on failure | The hook blocks a planted failure |
| F4 | The full suite takes 3+ hours and grows | B20_R184: 11,448 s for integration | Shards in parallel when cores allow; heavy record tests marked and run at checkpoints only | Checkpoint wall time flat as the suite grows |
| F5 | One writer, one session; handoff by documents | `docs/HANDOVER.md` | Keep `docs/HANDOVER.md` §0 current at every record; `wip/<study>` snapshots (done) | A new agent resumes a running study from `wip/` |

### G. Compute and efficiency

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| G1 | No standard measure of verified gain per unit of compute across lines | records report CPU s ad hoc | One metric: verified held-out gain per CPU-hour (and per joule, where measurable), in every record | Present in every record from now on |
| G2 | Invention's cost is not amortised in the comparisons | B20_R182: 829 CPU s of invention reported apart | Report break-even: after how many obstacles invention pays for itself | Break-even stated per study |
| G3 | Two cores | the container | Ask Daniel for more cores when a study's power needs them; never acquire resources autonomously | Requests with the power analysis attached |

### H. Governance and safety

| # | Weakness | Evidence | Remedy | Test |
|---|---|---|---|---|
| H1 | The builder (an LLM) both builds and evaluates | the protocol | Independent reviewers (a fresh session or a human) for records with positive claims; the circle's checks are code, not opinions | Reviews attached to positive records |
| H2 | LLM coupling could leak held-out problems | `OMEGA_YIN_YANG.md` §6 | Sealing, provenance and fresh sessions (the design) | Leak tests in YY-1 |
| H3 | Self-improvement could reach the circle | the contract | `capture.PROTECTED`, the no-LLM test, the protected judge's digest; extend PROTECTED to every circle file (verifier, catalogues, mutant rules, judge, preregistration tooling) | A planted self-change to any circle file is refused |

## 3. The architecture that removes the removable weaknesses: four levels inside one circle

**L0, the circle (fixed; owned by no level).** It holds:
- the kernel's verifier and the protected judge;
- the isolation;
- the catalogues and the rules that draw random problems;
- preregistration and records.

It changes only by *adding* checks (C1, C5), by Daniel's decision, and never from inside a loop.

**L1, object level.** It solves problems: repairs, engines, conjectures, representations. Its artifacts are patches,
programs and certificates.

**L2, the inventor.** It makes L1's tools:
- transformations;
- grammar productions;
- representation operations.

Every L2 artifact is data, carries its provenance (`genesis`, `builder` or `llm:<session>`), and is admitted only by
a verified repair, solution or refutation of a problem from a family it did not come from.

**L3, the meta-inventor.** It makes L2's tools:
- derivation operators (today: inverse, transfer, composition, generalisation, all builder-written);
- substitution kinds;
- grammar templates.

These too become *data in a typed meta-language*: a derivation operator is a rewrite rule over substitution tuples,
and a substitution kind is a typed relation between leaves. Genesis searches that language and admits an L3
artifact only when the L2 artifacts it produces are admitted and help on fresh draws. This removes A1. The ladder
stops at L3 because the measurement cost grows with each level and the gain must be shown first. A level L4 is
added only if L3's improvement is shown and compounds.

**P, the process level.** It runs alongside, not above. It tunes how the loops run:
- the budgets;
- what a brief contains;
- the admission thresholds;
- the split between Genesis's search and LLM offers.

It works through a meta-ledger and adopts a change only by preregistered tests (`OMEGA_YIN_YANG.md` loop 3).

**The LLM may offer at L1, L2, L3 or P**, always as data, never in the runtime, always through the same gates.
**Genesis briefs the LLM** at every level with the failure atlas (B3), the verified library, the refutations and the
credit.

**Recursion, measured.** Each level's improvement is tested as B20_R185 tested L3's derivations: generation k+1
against generation k, on a fresh random draw, preregistered, with defect-level statistics (D1). Recursive
self-improvement is *shown* when the gain of generation k+1 over k stays positive as k grows, at the same compute.
B20_R187 is the first such test, for k = 2.

## 4. Implementation plan, in order

Each work package (WP) gives: what to build, where, its interface, its tests, and its acceptance. The protocol for
every study is unchanged: preregister (script, design tests, record-test draft, rehearsal), run alone on CPU 0
(`scripts/ops/run_slice.sh`), record, push.

1. **WP-1, hygiene first (F3, C4, C3, H3).**
   - What: a pre-commit hook running the repository-wide rule tests (`test_no_llm`, `test_gi6_legacy_paths`, the
     design tests' digest pins, `ruff --select F,E9`) and the changed modules' tests. The integration suite takes
     over three hours, so it stays at checkpoints. Also: isolation probes generated from the kernel's file list, and
     `capture.PROTECTED` extended to every circle file.
   - Acceptance: planted failures are blocked.
2. **WP-2, the queue daemon (F1, F2).**
   - What: `scripts/ops/queue_daemon.py`. A loop that holds a CPU 0 lock file and starts the next preregistered study
     slice from `research_queue.json` (status `queued`, `preregistered` set) via `run_slice.sh`; on exit 3 it re-runs
     the slice; on exit 0 it marks the study `ran` (recording stays the agent's). It is run by systemd or cron, not by
     the agent.
   - Acceptance: a week with under 1% CPU 0 idle while the queue is non-empty.
3. **WP-3, the failure atlas and the evidence fields (B1, B2, B3, A4, A8).**
   - What: `src/genesis/repair/atlas.py` (research side, reads only recorded studies). For each unrepaired obstacle it
     gives the nearest donors, the closest admitted transformations and why they failed, and, once the defect is
     public, the minimal missing substitution. The loop records generated against evaluated candidates and the stop
     reason; every tried candidate counts in its rule's posterior.
   - Acceptance: tests on B20_R185/R186 evidence; the atlas's miss classes are reproducible.
4. **WP-4, the verifier's mutation adequacy (C1, C2).**
   - What: `scripts/b20rNNN_verifier_adequacy.py`. All mutants of all components against the hidden tests; every
     survivor is a verifier gap; checks are added only if every correct source still passes.
   - Acceptance: the score is recorded, and it only rises across versions.
5. **WP-5, sequential admission and retirement (A7).**
   - What: `Transforms`/`Library`. Admit when the Beta lower bound on transfer exceeds a threshold, retire below,
     report track records.
   - Acceptance: a preregistered comparison on a fresh draw against single-repair admission (reach equal or better,
     false admissions fewer).
6. **WP-6, offers and briefs (`OMEGA_YIN_YANG.md` YY-0).**
   - What: `src/genesis/repair/offers.py`, which validates offers as typed data and imports them as candidates with
     provenance; `scripts/ops/make_brief.py`, which writes the atlas, library, refutations and credit as
     `docs/yinyang/briefs/<study>.md` and `.json`.
   - Acceptance: an offer cannot bypass admission; a brief is a pure function of recorded evidence.
7. **WP-7, the typed meta-language for L3 (A1, A3).**
   - What: `src/genesis/repair/meta.py`. Derivation operators as rewrite rules over substitution tuples, and
     substitution kinds as leaf relations, both as data, with a small enumerator. Genesis searches it in the probes'
     place. Edit-level composition for two-site repairs.
   - Acceptance: a study (SR-3) where an L3 artifact Genesis found produces admitted L2 transformations that repair
     held-out draws no builder-written operator reaches.
8. **WP-8, larger draws and defect-level statistics (D1, D2).**
   - What: catalogues of 60 or more mutants; defect-level sign tests preregistered beside obstacle-level ones.
   - Acceptance: present in the next study.
9. **WP-9, real code (E1, E2).**
   - What: (a) YY-3, LLM-written larger components with tests, mutation-tested by Genesis, then held out. (b) Two-point
     mutants. (c) A real-bug corpus imported as data with its own tests.
   - Acceptance: the cycle's gains replicate there.
10. **WP-10, one library across lines (E3, A9, A10).**
    - What: the transformation language over programs, statements and representations, shared by the repair,
      conjecture and engine lines, with one credit system.
    - Acceptance: a cross-line transfer, preregistered.
11. **WP-11, LLM coupling (`OMEGA_YIN_YANG.md` YY-1, YY-2, YY-4).**
    - Requires Daniel's go-ahead for fresh LLM sessions.
    - Acceptance: the 2 x 2 interaction is positive and compounds over three cycles.
12. **WP-12, efficiency (G1, G2, G3).**
    - What: one metric in every record (verified held-out gain per CPU-hour) and break-even reporting; requests for
      resources with power analyses.
    - Acceptance: in every record.

Order rationale:
- WP-1 to WP-4 make the evidence trustworthy and the machine never idle.
- WP-5 to WP-8 make Genesis's own recursion stronger and its claims sharper.
- WP-9 and WP-10 take it out of the toy world.
- WP-11 adds the yang.

Each WP is small enough for one agent session, plus one CPU 0 study where a claim is made.

## 5. How any agent works here (read before touching anything)

1. Read `docs/HANDOVER.md` §0 (what is running, how to resume), then this file, then `docs/OMEGA_RULE_INVENTION.md`
   and `docs/OMEGA_YIN_YANG.md`.
2. Only one session writes `continuation-b20-rx`. Check `git log github/continuation-b20-rx` and the `wip/*` branches
   first.
3. Never modify the circle:
   - `src/genesis/autonomy/feedback.py` (SHA-256 `2ff4a5ab…dd6`);
   - the verifier's checks (add only, by decision);
   - sealed catalogues;
   - preregistered scripts after their commit.
4. Every claim is a preregistered study:
   - a script with its SHA-256 pinned in a design test;
   - a record test drafted in `docs/handoff/RECORD_TEST_DRAFTS.md` and dry-run on a rehearsal;
   - run alone on CPU 0 with `scripts/ops/run_slice.sh`, from a clean worktree of the preregistration commit;
   - recorded with the record test appended unchanged, `docs/checkpoints/B20_R<n>_RECORD.md` (disclose idle gaps,
     overlaps, development looks), and the bookkeeping (BATCHES, NEXT_ACTIONS, batch_state, the ledgers, TEST_MATRIX,
     HANDOVER, the queue);
   - committed and pushed.
5. Held-out problems are drawn by fixed random rules *after* the code they test is sealed (`scripts/b20r18[5-7]_make_mutant_catalogue.py`).
6. No LLM in the runtime (`tests_genesis/test_no_llm.py`); LLM help enters only as offers (§3).
7. Never report a planned capability as implemented: the register's status column changes only with a record.

## 6. Status of the register (31 Oct 2026, 22:10 SGT)

| Group | Items | Done | In progress | Open |
|---|---|---|---|---|
| A invention | 10 | none | A2-A4 partly addressed by SR-2c's design (shown on this testbed: derived transformations add reach) | all ten |
| B diagnosis | 4 | none | | 4 |
| C circle | 5 | C3 in part (B20R183-CATALOGUES repaired), C4 in part (B20R184-PICKLE repaired) | | 5 |
| D evidence | 3 | D3 in part (B20_R186 replicated B20_R185 on this host) | | 3 |
| E realism | 3 | | | 3 |
| F process | 5 | F2 in part (watcher rule), F5 in part (`wip/` snapshots, `scripts/ops/`) | | 5 |
| G efficiency | 3 | | | 3 |
| H governance | 3 | | | 3 |

The system is not free of weaknesses, and this document does not claim it is. It lists them, says which can be
removed and how, and says which cannot and why.
