# Genesis Ω²: a portfolio of discovery processes that learns where compute goes (adopted 26 Oct 2026)

**Status.** This is the adopted design for stage Ω10 (the allocator) and for how Genesis's discovery processes are
compared from now on. It comes from Daniel's report "Beyond Genesis-Ω: What Could Actually Be 'Miles Better' for
Autonomous Discovery?" (dated 24 Oct 2026, received 26 Oct; the attachment's SHA-256 is
`5652b79ba6bf8930911ce8d3f33787e9ac6727a851d5b50d7ec11b4ce322daac`; the attachment itself is not committed) and his
decision of 26 Oct: adopt it first, as the allocator stage, preregister its study, then resume the queue.

Every part below is marked **BUILT** (code and a named test), **PREREGISTERED** (a study script with a commit) or
**PLANNED** (neither). Nothing here is claimed as achieved: a passing unit test shows that code works, not that
meta-adaptive discovery works; only a preregistered study on fresh tasks shows that.

## 1. What the report says

- The established skeleton is right: generator or search, an executable evaluator, an archive, more search. Genesis's
  independent judge is one of its strongest choices and must stay outside everything that adapts.
- The weakest part of a fixed implementation is a **fixed Explorer**. The report cites a 2026 comparison of 30
  budget-matched discovery harnesses in which no fixed harness was reliably best and adaptive allocation among
  several beat committing to one. Its first recommendation: Genesis should be **a system that learns which discovery
  process to use**, and meta-evolve those processes.
- The Consolidator should become a **capability compiler**: a stored capability is a semantic contract, an
  implementation, its assumptions, tests, evidence, a cost profile, a failure envelope and provenance. "Memory is not
  capability."
- Later layers: a POET-like challenge generator judged by external transfer, formal-symbolic verification where
  possible, conditional multi-agent organisation, sandboxed self-modification of non-privileged components.
- A stricter measurement standard:
  - budgets matched in more than one currency;
  - the whole discovery curve (verified quality against log compute; the area under it);
  - best-of-N and simple search as serious controls;
  - task families with held-out families;
  - Holm correction;
  - wins counted by family, not by instance.
- The decisive experiment: G0 (fixed Explorer) against G1 (portfolio, fixed allocation), G2 (adaptive portfolio) and
  G3 (adaptive portfolio with meta-evolved policies) on unseen families, at matched compute.

## 2. What Genesis already has (mapping)

| Report layer | In Genesis | State |
|---|---|---|
| Independent epistemic boundary | The protected judge (`autonomy/feedback.py`, contract v2), sealed splits, the kernel outside the research plane (`test_omega_boundary`), two independent checkers per domain | BUILT |
| Discovery portfolio | Several searches exist (steady-state evolution, MAP-Elites in `selfimprove`, the contract searches, exhaustive instrument search, Bayesian experiment design), but each study runs one of them | fragment; **this stage** |
| Meta-discovery | `selfimprove` level 2 (processes as data), `autonomy/process.py` (processes at any level under fuel), ARA (`docs/OMEGA_ARCHITECTURE_INVENTION.md`) | BUILT on fixtures; B20_R128 and B20_R141 onward PREREGISTERED or PLANNED |
| Capability compiler | The vault (`vault.py`) with CapabilityRecords, lineage, explanation ladder, evidence-gated promotion, bounded reactivation | BUILT; the "contract + tests + failure envelope" record is PLANNED (§5) |
| Challenge ecology | The adversary (`autonomy/adversary.py`, POET-style host search), the Difficulty Cartographer | BUILT (adversary); B20_R134 PLANNED |
| Cross-task allocator | `adaptation/metabolism.py` (the cell's cost model), the loop | fragment; **this stage** |

## 3. What is adopted, translated to an LLM-free Genesis

Daniel's directive of 24 Oct (item 10) keeps Genesis LLM-free. The report's Explorers are LLM harnesses; here they are
**Genesis's own discovery processes** searching its own languages. The report's token budgets become evaluation
budgets, and model identity is not a variable. Its replication criterion "with a different base model" has no
counterpart; replication here means fresh tasks and fresh seeds.

**3.1 A portfolio of discovery processes (BUILT: `src/genesis/autonomy/portfolio.py`, `tests_genesis/test_portfolio.py`).**
- **Harnesses.** Six discovery processes, each a resumable generator, so that an allocator can pause and resume them
  between any two evaluations:
  - `best_of_n` (random sampling, the control the report insists on);
  - `hill_climb`;
  - `anneal`;
  - `evolution` (Genesis's current inventor's steady-state search, its constants, without the judge);
  - `map_elites`;
  - `racing` (successive halving over random batches).

  All six are prior art; none is claimed new.
- **One interface for every domain.** A domain is a `Task`: `random`, `mutate`, `crossover`, `size`, `descriptor`, and
  `evaluate(program, split, repetition)` on splits A (search), V (validation) and T (the study's, never charged and
  never shown).

**3.2 Allocators (BUILT).** Each allocator is an arm that spends exactly B evaluations, A and V each costing one.
- `single:<h>`: one harness gets the whole budget; G0 is `single:evolution`.
- `uniform`: harnesses in turn (G1).
- `halving`: successive halving across harnesses (G2). Stages of equal budget are shared equally; after each stage
  the best third continue (6 → 2 → 1).
- `bandit`: UCB1 on validated quality, with every tenth round reserved for the least-used harness (the plan's
  metabolism rule of at least 10% exploration).
- `halving_tuned`: G2 with harness parameters chosen beforehand on development tasks (G3, §3.3).

Each arm's answer is its best *validated* program. Validation costs budget, the same for every arm.

**3.3 Meta-adaptation of the discovery processes (BUILT, first form).**
- `tune_params` chooses each harness's parameters from `PARAM_SPACE` on development tasks only. DEFAULTS win ties.
- Under ARA's rule ("tuning is never reported as invention"), G3 is a claim about **meta-adaptation that transfers**,
  not about invention.
- Later forms (PLANNED):
  - harness programs and allocator policies as processes in `autonomy/process.py`, improved by a level-2 search;
  - the campaign policy as data, as the report's FreeEvolve example.

**3.4 The measurement standard (adopted for every discovery comparison from B20_R148 on).**
- **Matched evaluations**; CPU (evaluation and logic) recorded as a second currency.
- **The discovery curve.** The measured quality of each arm's answer is taken at log-spaced checkpoints B/32, …, B.
  Quality is normalised per task, from the median random program (0) to the best any arm reached, or a stated
  reference (1). The **area under the discovery curve** (AUDC) gives each doubling of compute equal weight.
- Best-of-N and hill climbing are arms, not footnotes.
- **Units and tests.** Task families are the unit of the primary tests, with held-out families and a held-out domain;
  Holm across the primary family.
- ARA's quantity G_t ("verified discovery value on fresh tasks per unit of research compute") is this, with the
  research compute made explicit.

**3.5 Domains for the first study (BUILT: `src/genesis/autonomy/portfolio_tasks.py`).** Three of Genesis's languages,
each with its verifier:
- **acquisition rules** (B20_R129's language) on the hidden-cause causal benchmark: minus the experiments needed;
- **max-cut engine programs** (B20_R125's `mcx2` language, the pinned native binary) on generated graphs: the cut
  relative to REX at the same budget, every cut checked twice;
- **planted formulas** in the expression language, scored by rank correlation with a hidden target that the language
  contains. This is a positive control with a known optimum.

## 4. The first study: B20_R148 (PREREGISTERED; see its script)

The report's decisive experiment, translated and bounded (its §"start with one bounded experiment"). The script's
docstring is the preregistration and governs; this is a summary.
- **Question.** Is any of the six discovery processes best on every task family (H1)? Does an adaptive portfolio (G2)
  beat Genesis's current inventor's search (G0) and the best single process chosen on development tasks? Do
  parameters meta-tuned on development tasks (G3) add to G2 on fresh tasks? The held-out families and a whole held-out
  domain test transfer.
- **Design, verdict rule, costs, expectation and development looks:** in `scripts/b20r148_harness_portfolio.py`.

## 5. What comes after (PLANNED, in order)

1. **The allocator across activities**: solving, diagnosing, inventing, improving and transferring, learned from
   yield per CPU (Ω4's metabolism), with the same AUDC standard and reserved exploration.
2. **Meta-evolved processes.**
   - Harness programs and allocator policies become processes (`autonomy/process.py`), improved at level 2.
   - Each generation is judged on fresh families against the previous one (the report's G^(n+1) > G^(n) on new
     sealed tasks), under ARA's tuning-only and blind controls.
3. **Capability records with contracts.**
   - A vault CapabilityRecord gains the report's fields: semantic contract, implementation, assumptions, property
     tests, verification evidence, cost profile, failure envelope and provenance.
   - Promotion stays evidence-gated.
4. **More domains in the portfolio study**: the Problem Compiler's families, the representation language and engine
   configuration, so that the H1 question is asked across more kinds of landscape.
5. **POET-lite.** The adversary and the Cartographer generate families at the edge of competence. They are judged
   only by external transfer to a separately authored sealed suite, never by generated tasks.

## 6. The rule kept

The portfolio, its allocators and its tuning live in the research plane. None of them imports or changes the judge
(`autonomy/feedback.py`), the kernel, custody or release code (`test_omega_boundary`), and none uses an LLM
(`test_no_llm`). The standard by which an improvement is accepted is never something the adapting layer can change.

## 7. Caveats on the report

- **Unverified citations.** Several systems it cites (EvoX, FreeEvolve, AgentDiscover, CORAL, the 30-harness
  comparison, the 2026 agent-scaling study) are after the builder's knowledge. They are not verified here and are not
  cited as evidence in any record until checked.
- **Costs.** Its resource estimates are for LLM-based programmes and do not transfer.
- **Architecture.** Its description of "Genesis-Ω as specified" (Explorer → Judge → Consolidator) is simpler than what
  exists. The mapping in §2 is the accurate one.
