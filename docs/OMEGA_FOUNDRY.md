# The "Verified Cognitive Invention Foundry" proposal (v0.2): what Genesis takes from it

**Source.** Daniel attached it on 28 Oct 2026, 10:50 SGT, with the message "U can use this if it can help our
system become extremely powerful and revolutionary". It is an engineering proposal, *Genesis-Ω: Verified Cognitive
Invention Foundry*, version 0.2 of 28 Oct 2026, with no author named. Its own status line says that no part of it
has been built or tested. The builder read it in full.

**How it is used.** It is input, not a new directive. Daniel's directives stay in force:
- 27 Oct, 14:33: ARA → invention → judge → consolidator;
- 27 Oct, 19:55: the Frontier;
- 27 Oct, 20:22: PT-1;
- 28 Oct, 00:53: PT-1 part 1's mechanisms.

This document maps the proposal onto what Genesis already has, says what is not adopted and why, and turns the
real gaps into batches with tests that can fail. Nothing here claims that Genesis is "extremely powerful" or
"revolutionary". The proposal itself refuses such claims ("'Classified level' is not a technical performance
specification").

## 1. What Genesis already has

| The proposal | Genesis | State |
|---|---|---|
| §1 The evolving object; a separate evaluation service owns acceptance | ARA's Architecture Graph (`architecture/`); the protected judge (`autonomy/feedback.py`, digest pinned); the language judge (X2); kernel-side checkers in every study | built |
| §2 Fast and slow memory; consolidation | the vault (B20_R131); library learning and the consolidator (X2, B20_R154); PT-1's mechanism 1 | built; tested, nothing admitted on real engines (B20_R152) |
| §2 Internal rehearsal with a learned surrogate | the Frontier's curve forecasts (`frontier/curves.py`) | built; overconfident (coverage 0.66 at 0.90, B20_R156) |
| §3 Representations, operators, control graph | Γ with derivation (mechanism 4) and templates; the Frontier's directions and policies; mcx2 and mcx3 programs | built |
| §4 Authority boundaries; isolation; a metered broker | research plane against kernel side, with the audit and the no-handholding tests; the runc sandbox and its escape suite; the custodian | built; independent custody and second-machine reproduction still outstanding (R-04) |
| §5.1 Diagnosis by controlled intervention | ARA's loss ladder by oracle substitution | built; calibration B20_R141 INVALID by a script defect, re-run B20_R167 running |
| §5.2 A mechanism with explicit claims and contracts | candidate-kind manifests; the vault's statuses and evidence; procedures with provenance | partial: no single manifest carries preconditions, decoder and transfer test |
| §5.3 Joint proposals and factorial interaction | ARA-3, the synergy factorial (B20_R143), planned | not built |
| §5.4 Consolidation with retesting | the consolidator; the language judge's random-statement control | built |
| §6 Does an invention improve invention? | PT-1 part 5 (improved inventor against its predecessor at matched total compute); F5; B20_R130 and B20_R131 | designed; PT-1 drafted (B20_R159) |
| §6 Information-only and generic-implementation controls | none yet | **gap G1** |
| §7 First demonstration: MaxSAT | B20_R89 to R92 (the system's MaxSAT engine against the 2024 and 2026 champions) | done, at DEV |
| §8 Levels of evidence | the novelty ladder (`docs/OMEGA_EXPERIMENT_PROTOCOL.md` §8) | built |
| §9 Families held out; fresh cohorts; preregistration | the protocol, followed in every study | built |
| §11 A ledger row for every attempt | study ledgers; the research queue; `batch_state.json` | partial: no common row schema (gap G6) |
| §13.2 Mechanism M = (phi, O, pi, U, C) | phi: Γ, templates, derived reps; O: methods; pi: Frontier policies; C: manifests | U, a learned update rule, is **gap G2** |
| §13.3 Decision-relevant representations found through counterexamples | ARA's SENSE_BLIND class; abstraction from convergent counterexamples | not for the allocator's state: **gap G4** |
| §13.7 A falsifiable test: joint vs separate discovery | none | **gap G3** |
| §13.8 Diversity against leakage | families and generators held out | built |

## 2. What is not adopted, and why

- **A foundation model as the proposer, a metered model broker, token budgets.** Genesis is strictly LLM-free, by
  standing decision, with no paid APIs (`docs/OMEGA_NO_LLM_AUDIT.md`). Its inventors are program search, derivation
  and library learning. Every place the proposal uses a model to propose, Genesis uses its own search. The
  proposal itself allows this ("keep the foundation model fixed").
- **The 12-week implementation sequence.** Genesis works in preregistered batches. Most stages of the sequence
  already exist (§1).
- **MaxSAT decomposition as a first demonstration.** It is a known idea, and the proposal itself calls rediscovering
  it a sanity check. Genesis's MaxSAT track is done at DEV.
- **"Classified level", "extraordinary capabilities".** These are not measurable. The proposal agrees.

## 3. The gaps, as batches

Each gap gets a falsifiable test, in priority order. None of these runs before the queue on CPU 0 (B20_R167, then
B20_R157 again, the checkpoint, B20_R158, B20_R163 and PT-1) unless it is stated otherwise.

**G1: the information-only and generic-implementation controls (§6), folded into PT-1 now.** When the improved
inventor beats its predecessor, the gain may come from what the procedure *knows*, not from what it *does*. Two
LLM-free controls separate these:
- **the notebook control:** the predecessor with the facts of the discovery. Every certified counterexample from
  family A is checked on every task first, at a charged cost, and then it runs as usual. This is the
  "memory-accumulation baseline" of §9;
- **the given-representation control:** the predecessor whose domain starts with the representation the procedure
  would build (the derived operation set or the template), without the procedure. This is the
  "generic-implementation" control.

They are arms of parts 4 and 5, preregistered with the test, each with the same two statistics as the primary
comparison.
- **Part 5 must beat both controls as well as the predecessor.** Daniel delegated the choice on 28 Oct 2026, 10:58
  SGT, and the builder chose the harder test. It is an intersection-union test, with no added error rate.
- In part 4 the comparisons are reported labels, OPERATIONAL_OVER_FACTS and PROCEDURE_OVER_REPRESENTATION.
- Built in the PT-1 draft (`scripts/b20r159_proving_test.py`).

**G2: an invented update rule for the Frontier's forecast calibration (§13.4, B20_R170).** F3 found the forecasts
overconfident and biased low, and a textbook correction failed (`docs/checkpoints/B20_R156_RECORD.md`).
- Instead of a builder's patch, Genesis searches a small grammar of update rules U. Each rule maps the engine's own
  resolved forecasts, as branches reach their horizons, to an adjustment of its intervals. The grammar has bounded
  shapes and declared state, and ACI-style rules are among its points.
- Each rule is scored by fresh engines on fresh planted worlds: allocation value and coverage, the search's compute
  charged.
- Falsified if the best rule does not beat the fixed forecaster on held-out worlds at matched total compute.
- Its prior art is adaptive conformal inference (Gibbs and Candès 2021) and learned optimizers (DiscoRL, ref. 7).
- **State (29 Oct 2026): BUILT and PREREGISTERED.** The grammar is `frontier/calibrate.py` (`8b29d0f`; 144 points, 81
  distinct behaviours: signal none/resolved/hindcast, form, sides, conditioning, adaptive-conformal or quantile updates,
  rate). B20_R170 (`scripts/b20r170_forecast_calibration.py`) is preregistered with two primaries under Holm: P1, the
  promoted rule against the fixed forecaster given the meta-search's compute (matched total, value); P2, coverage of
  the promoted rule's forecasts above the fixed forecaster's and inside [0.80, 0.97]. It runs after B20_R163.

**G3: joint against separate discovery (§13.7, B20_R171).** The proposal's own test of its central hypothesis,
here on the Frontier. There are four arms at the same total budget:
- fixed: the engine's defaults;
- operator discovery only: methods and parameters searched;
- separate stages: representations (derivation), then operators, then the policy (F6's meta-search), in turn;
- joint: bundles searched together, with interactions estimated by §5.3's formula on the screened pairs.

It runs on planted worlds and conjecture families held out of PT-1. Falsified if joint does not beat separate
after its extra cost. F6 (B20_R163) is the policy-only point of this design, and its result comes first.
- **30 Oct 2026: F6 is NOT_SHOWN** (`docs/checkpoints/B20_R163_RECORD.md`): the policy-only search lost to the
  defaults given its compute (−0.221) and tied them at equal budget. A diagnosis after recording found that its
  meta-search did not compare configurations at equal spend and promoted the first one it opened (B20R163-META), so
  the policy stage is not yet measured. B20_R175 (F6b) measures it with the repair (several training worlds, one
  successive-halving bracket, a guard against the defaults); G3 waits for it. B20_R170 (G2) inherits the defect.

**G4: decision-relevant state abstraction by counterexamples (§13.3, B20_R172).** For the allocator: the states
where its features look alike but a matched replay shows different best actions become a proposed new feature.
That feature is kept only if it improves held-out allocation after its computation is charged. This is ARA's
SENSE_BLIND class turned on the engine's own controller. It is engineering first, then a study.
- **State (29 Oct 2026): the engineering is BUILT** (`frontier/statefeat.py`; `tests_genesis/test_frontier_statefeat.py`).
  - The policy logs its two leading candidates at each exploitation decision (`log_decisions`), with 17 primitives of
    each branch's own history and forecast.
  - `replay_gain` advances each candidate alone by k quanta through the domain's public `step` (pure in the planted
    world) and returns the compute it used, for a study to charge.
  - `propose` searches 697 feature expressions (primitives, and differences, products and ratios of two). The whole
    search is cross-validated (search on one fold, score on the other), and a feature is proposed only if its
    held-out agreement with the replays beats the index alone by 0.02 with a one-sided z of at least 1.645.
    On noise it proposes nothing (tested); it recovers a planted distinction (tested).
  - The feature enters the index as `state_feature` = {'expr', 'weight'}. The defaults and decision logging leave
    runs unchanged (identical events).
  - A development look (disclosed for B20_R172): on three planted worlds of seeds 887021-887023 (budget 12,000), the
    index already agreed with replays on 0.82-0.92 of weighted pairs; two of three proposed a feature (held-out
    0.90 and 0.92). The replays cost 80,000 evaluations for 200 pairs (k = 20), several times a world's budget, so
    the study must amortise one search over many held-out worlds, as F6 and B20_R170 do.
- **B20_R172 is PREREGISTERED** (29 Oct 2026; `scripts/b20r172_state_features.py`): one counterexample search on two
  sealed training worlds (120 replayed decisions each, k = 10), its compute charged; the proposed feature against the
  defaults on 24 held-out worlds at matched total compute (P1, value), with S7 asking whether the distinction holds
  in new worlds' decisions. It runs after B20_R170.

**G5: interaction estimates for joint proposals (§5.3).** The formula goes into ARA-3's synergy factorial
(B20_R143, already planned) and G3.

**G6: one ledger row schema for every attempt (§11).** This is engineering, low priority. The study ledgers gain
the proposal's fields where they are missing: lineage, parent hash, candidate hash, the evidence level, and the
release decision.

## 4. Prior art in the proposal, checked on 28 Oct 2026

Found:
- AlphaEvolve (arXiv 2506.13131);
- the Darwin Gödel Machine (arXiv 2505.22954);
- DiscoRL (Oh et al., *Nature* 2025);
- RSIAgent (arXiv 2609.15364);
- AIDE² (Srikanth et al., "Recursive self-improvement of AI research agents", arXiv 2609.26457, a narrow,
  self-reported result);
- DiscoGen (Goldie et al., arXiv 2603.17863; ICML 2026);
- TTT-Discover (Yuksekgonul et al., arXiv 2601.16175; ICML 2026);
- Rep2Skill (arXiv 2609.39149v1, 30 Sep 2026).

Not found in two searches: "EvoCUE: The Right Lesson at the Right Step" (cited as arXiv 2609.34988). It is treated
as unverified.

For Genesis, the closest of these to PT-1 are:
- AIDE² and the Darwin Gödel Machine, which improve an agent by evaluating its own edits;
- DiscoRL, which invents learning rules.

None of them is LLM-free, and none tests the transfer of a procedure extracted from a mathematical discovery, as
PT-1 does. Whether that difference matters is what PT-1 measures. It is not claimed here.
