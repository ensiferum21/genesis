# Genesis Ω: roadmap status and stage gates (master implementation contract §15, §18)

The contract's stages Ω0–Ω12 and the plan's stages (`docs/GENESIS_OMEGA_PLAN.md` §5) side by side, with each gate's
state. A stage is complete only when its acceptance test passes **and** it has shown behaviour on real runs. A file
existing is not enough.

Gate states:

| State | Meaning |
|---|---|
| **OPEN** | Not started |
| **BUILDING** | In progress |
| **GATE PASSED** | Acceptance test passes |
| **EVIDENCE PENDING** | Built; its study has not run or is not recorded |
| **BLOCKED** | Cannot proceed |

| Contract stage | Plan stage | What exists | Acceptance (contract §16) | State (24 Oct 2026, 14:45) |
|---|---|---|---|---|
| Ω0 Audit and baseline | Ω0 | `OMEGA_GAP_MATRIX.md`, `OMEGA_INTEGRATION_MAP.md`, `OMEGA_NO_LLM_AUDIT.md` + `test_no_llm` (one defect found and fixed). The baseline is the release matrix of the B20_R118 checkpoint (1,948 tests) | §16.1 clean bootstrap; §16.10 no LLM | **GATE PASSED** for §16.10. §16.1 rests on the B20_R118 checkpoint, and a fresh checkpoint is owed. The HSR v3 PDF is not available here (**BLOCKED** for the line-by-line check) |
| Ω1 Artifact substrate | Ω5 (part) | `vault.py` on `store.Store`; `genesis discovery list/show/export/verify`; `test_vault` (7 tests: exact bytes across a restart, identity, tampering, transitions, evidence-gated promotion, edges, lineage, CLI round trip) | §16.5 archived exactly, survives restart, retrievable | **GATE PASSED** for storage and retrieval. Replay through registered replayers is still OPEN |
| Ω2 Process IR | Ω3 | `ir.py`, `dsl.py`, `primitives.py` (registry with contracts), `science/acquire.py` (typed expressions, interpreter, search operators, feature sets), `causal/instruments.py` (instrument programs) | §16.2 sandboxed, metered, checked, replayable; §16.3 a primitive synthesised, registered, reused, rolled back | BUILDING. §16.2 holds for mcx2 programs (runc sandbox in judged runs). **§16.3 GATE PASSED on fixtures** (`science/library.py`, `test_primitive_library`): a primitive synthesised from recurring structure, registered in a new immutable version with its contract (type, range, purity, lineage), reused by the search and evaluated exactly as its expansion, rolled back (refused against the earlier version). Its value on fresh tasks is untested |
| Ω3 Inventor ecology | Ω4 | Evolutionary and MAP-Elites (`selfimprove`), the contract searches, exhaustive instrument search, Bayesian experiment design | Inventors compared at matched budget on held-out tasks | EVIDENCE PENDING (B20_R127, R128, R129, R130) |
| Ω4 World invention | Ω7 | `invention/worlds.py`, `representations.py`, renormalisation in mcx2; the Problem Compiler's exact reductions | §16.4 a transformation keeps its contract or is rejected | BUILDING. The compiler's forms are brute-force checked exact (`test_compiler`); a broken-decoder rejection test is OPEN |
| Ω5 Vault and capability graph | Ω5 | `vault.py` edges, queries, statuses | Query and retrieval; integrity | **GATE PASSED** (tests) |
| Ω6 Cascade / reactivation | Ω5–Ω6 | `vault.opportunities`, `reactivate`, `cascade` (fuel, seen set, depth; null-trigger and cycle tests) | §16.6 selective reactivation without runaway | **GATE PASSED** on fixtures. The real test is **B20_R131** (dormant acquisition rules against B20_R130's global interpretation; against fresh search, random retrieval and a null trigger): EVIDENCE PENDING |
| Ω7 Interpretation | — | `interpret.py`: exact simplification under declared feature ranges (B20_R129's invented rule reduces to `max decall * pf^2` and behaves identically), behavioural fingerprints, conjectures tested against counterexamples, ablation; Lean and the wording gate | §16.7 a conjecture rejected by a counterexample, the original untouched | **GATE PASSED** on fixtures (`test_interpret`). Not yet run over a real archive (B20_R131's vault next) |
| Ω8 Bottleneck scientist | Ω1–Ω2 | `science/design.py` (domain-independent), causal adapter, instruments, joint and global interpretation; Difficulty Cartographer development looks | Discriminating interventions, preregistered, matched budgets | **EVIDENCE**: B20_R129 ADAPTIVE_SCIENTIST (the experimental scientist beats random choice; an invented rule beats the established ones). B20_R130 preregistered `f812701`. Instrument invention is OPEN |
| Ω9 Process meta-invention | Ω6, Ω9 | `selfimprove` process genomes | §16.8 a process improver transformed; limits hold | EVIDENCE PENDING (B20_R128) |
| Ω10 Allocator | Ω4 | `adaptation/metabolism.py`, `autonomy/loop.py` | Regret against baselines | OPEN |
| Ω11 Cross-domain transfer | Ω5 | The Problem Compiler (independent set, colouring, Max-2-SAT, max-cut on Genesis's engine, with MaxSAT and MILP back-ends; development looks only) | Verified transfer with minimal special casing | BUILDING. A preregistered compiler study is next |
| Ω12 Longitudinal autonomy | Ω9 | Resumable studies, checkpoints, the research loop | Several prospective generations | OPEN |

**The protected boundary** (§16.9): `test_omega_boundary` (the research plane imports no kernel, judge, custody or
release module; a planted import is detected) and `test_vault` (promotion needs recorded evidence) pass. Rejection of
tampered evidence by the judge is the kernel's existing suite (`test_acceptance_regressions`, `test_redteam_b15`,
`test_redteam_b16`).

**Next smallest high-value actions:**
1. Record B20_R129.
2. Run B20_R127's second slice, then B20_R130, then B20_R128.
3. Preregister B20_R131 (the cascade on a real case) after R130's record.
4. Preregister the Problem Compiler's study.
