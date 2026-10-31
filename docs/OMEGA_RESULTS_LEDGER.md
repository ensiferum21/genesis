# Genesis Ω: results ledger (master implementation contract §18)

Results are kept apart by status:
- **verified** (a recorded, preregistered study whose record test recomputes it; DEV scope, internal, not
  independently replicated);
- **exploratory** (development looks, disclosed in the next preregistration);
- **failures and negative results**;
- **unrun plans**.

Nothing here is an independent or sealed result.

## Verified (preregistered, recorded; DEV, internal)

| Batch | Result |
|---|---|
| B20_R102–R123 | Gset max-cut: 45 of 54 best-known values matched over all runs, none beaten; a "record" on G38 was a known 2013 max-bisection value |
| B20_R103, R107 | The feedback contract stops on zero-signal problems; version 2 keeps 63–93% of real gains |
| B20_R113 | Renormalisation, chosen by the system's selection, carries to Gset's planar instances (13–2 at 60 s) |
| B20_R118 | Hidden confounders mislead the established methods (CONFOUNDING_MISLEADS) |
| B20_R122 | On non-Gaussian data the observational residual flag marks hidden causes: F1 0.47 against FCI's 0.21 |
| B20_R124 | With Gaussian data only experiments find hidden causes (EXPERIMENTS_NEEDED); the oracle's 4 equal random's 8 |
| B20_R133 (positive parts) | Genesis's engine beats both MaxSAT 2026 entrants on Max-2-SAT at 1 s (7-0, 15-0) and PASMaxSAT-c on max-cut (10-0 at 10 s); it beats HiGHS on every family (20-0); every answer checked by two independent checkers |
| B20_R130 | **CHOICE**: Genesis's scientist (B20_R129's choice, decfall) beats random under the global estimator by 0.165 hidden-cause F1 (p 7.5e-26; transfer p 1.9e-9); with every experiment the global estimator reaches 0.69 against the per-pair framework's 0.61 |
| B20_R135 | **INVENTED_REPRESENTATION_BETTER**: encodings Genesis chose by its own search and pilot beat one-hot through the same pipeline on fresh colouring graphs at 10 s: k = 3 (binary code) 8.5 against 21.6 conflicts (18-0-2), k = 4 (a 3-bit table) 30.6 against 47.7 (20-0-0), both after Holm; k = 5 kept one-hot. Known kinds of encoding; no novelty claimed. PASMaxSAT-c still far ahead (1.6, 14.4, 17.9). Gadgets it synthesised reactivated exactly the four parked families (null 0); Genesis better than MaxSAT on 1-in-3 SAT (16-2-2) |
| B20_R129 | **ADAPTIVE_SCIENTIST**: Genesis's scientist needs 4.49 experiments against random's 6.81 (p 1e-27). Adapting is worth 0.70. Its own rule `inv1` beats every established acquisition (4.34 against eig's 4.98, preregistered; the others exploratory, Holm) and ties the builder's `decfall` (p 0.16), which Genesis chose on validation (4.42 against 4.59). `inv1` was a random initial program, not released by the judge. Exploratory: `inv1` has the higher F1 after 4 experiments (+0.054 test, +0.077 transfer, Holm p 0.008); reconciliation `evidence/r129_reconciliation/`. Four as good as eight holds on the shifted family only. Information gained does not predict accuracy gained |
| B20_R178 | **MILESTONE_DEMONSTRATED** (SR-1a, testbed only, CPU 1): on 24 of 39 held-out planted state-management obstacles the obstacle loop, isolated from its kernel by the operating system, repaired the defect, passed the independent verifier (hidden tests, fresh kernel workloads, the resumed job), was promoted by the Supervisor's policy, resumed the interrupted job and retained the repair; **REUSE_SHOWN**: retained hunks repaired 20 of 26 recurrences against 12 |
| B20_R180 | **MILESTONE_DEMONSTRATED** again (SR-1a2, testbed only, CPU 1): the version-2 loop repaired 12 of 36 held-out obstacles in larger components end to end, with the verifier's resource check required; isolation and 18 controls held |
| B20_R181 | **An invented operator reached what nothing else did** (SR-1a3, testbed only): the vestigial-call operator (a private method nothing calls gets its call restored) repaired E2 in all three jobs, in a component it was not developed on; no other arm reached E2. MILESTONE_DEMONSTRATED (12 of 36); LOOP_BEATS_RANDOM (6-0, p 0.031); no false repair in any arm |
| B20_R182 | **Genesis invented a repair rule with no human step** (SR-2a, testbed only, CPU 0): of 16 development obstacles the builder's rules could not solve, its dream repaired 6 (verified), lifted them into 17 rules, and admitted one, symmetry completion (after `self.A[x].m(y)`, add `self.A[y].m(x)`), lifted from its own repair of N2 and verified on N1, another family; the builder's own operator had missed both. RULES_INVENTED; no false repair in any probe or test arm; isolation and 30 controls held |
| B20_R183 | **The invented rule replicates** (SR-2b, fresh seeds, testbed only): Genesis again invented and admitted symmetry completion from its own repair of N2, verified on N1; RULES_INVENTED; isolation and the 30 controls held |
| B20_R185 | **The inventor improved how it invents** (SR-2c, testbed only, CPU 0; preregistered P2, narrowly): Genesis lifted repair transformations from its own verified repairs (11 admitted on other families), derived new ones from those by transfer, generalisation and inverse without any new repair (7 admitted), and on 24 random mutants nobody chose the derived generation repaired 34 of 72 obstacles against its lifted generation's 27 (7-0, p_Holm 0.047): two mutants, in all three jobs each, that neither its lifted transformations nor the builder's rules reached. SPACE_INVENTED; it equalled the builder's grammar (34) |
| B20_R186 | **Replicated, decisively** (SR-2c', fresh seeds, a fresh draw of 36 random mutants, testbed only): the inventor's derived transformations repaired 68 of 108 obstacles against its lifted ones' 56 (P2 12-0, p_Holm 0.0015), four mutants in all three jobs each, two of them wrong-attribute mutants that nothing had reached; against version 3 15-0; every B20_R185 verdict replicated |

## Failures and negative results (recorded)

| Batch | Result |
|---|---|
| B20_R111, R112, R115 | Autonomous invention of a better algorithm: NOT_DEMONSTRATED |
| B20_R86 | Generations do not compound in the earlier language: NO_COMPOUNDING |
| B20_R178 | **The loop's diagnosis-led search lost to unfocused search** on the testbed: nolocal 35, random 36, enum 33 repaired against the loop's 24 (sign tests p 0.001, 0.0005, 0.004); by SR-1's own falsification rule (beat random patches) it is falsified there. Laws mined from the defective component encode the defect; mislocalisation; components too small for focus to pay. The verifier accepted a storage-leaking repair in 9 comparator episodes (no resource check) |
| B20_R180 | The repaired loop **did not beat** unfocused search either (12 against nolocal 9, random 11, enum 8, retrieval 15; no difference significant), nor its predecessor (10); REUSE_NOT_SHOWN (11 against 10); five of twelve defects beyond every arm |
| B20_R181 | The loop version 3 **did not significantly beat** its predecessor, nolocal or enum (12 against 9 each; 3-0, p 0.25); symmetry completion missed both of its defects (the defect had erased the symmetry it looks for); seven defects beyond every arm |
| B20_R182 | **Genesis's library added nothing on held-out defects**: version 4 (with it) and version 3 (without) repaired the same 21 of 36; the admitted rule matched no held-out defect. **Searching the grammar directly beat the library** (30 against 21, 11-2, p 0.022), at a quarter of the CPU, though it lost 2 obstacles version 3 reaches; the grammar is the builder's. Step 6 (the inventor improving) not tested |
| B20_R183 | With fresh seeds **the library again added nothing** (version 4 22 = version 3 22); **the grammar's lead did not replicate** (28 against 22, 11-5, p 0.21); **step 6 not shown**: the inventor's learned order over its grammar productions invented no faster (earlier 2, later 6 of 28, p 0.29); two false repairs, caught |
| B20_R185 | Genesis's **lifted transformations added nothing** to the builder's rules on the random mutants (27 = 27, P1); its derived generation **did not beat the builder's grammar** (34 = 34, the same obstacles, P3); P2 rests on two mutants and would not pass Holm without the one discordant obstacle that was not a transformation's; 11 of 24 mutants (all four wrong-attribute ones) beyond every arm; no composition admitted |
| B20_R186 | Again **the lifted transformations alone did not significantly beat the builder's rules** (56 against 53, 3-0), and **Genesis's space did not significantly beat the builder's grammar** (68 against 59, 12-3, p 0.035, p_Holm 0.070); 11 of 36 mutants beyond every arm; no composition admitted; its first 17 min not alone on CPU 0 |
| B20_R177 | **PT-2: NOT_PROVED_OUT** (valid). The gate held bound by bound (A' = {30}: the predecessor missed bound 30 in three runs); Genesis refuted bound 30 (part 2), but in its starting representation (part 1 failed), with no procedure to extract (part 3), and no gain on B (5 against 6) or C (18 against 18) (parts 4, 5) |
| B20_R133 | The Problem Compiler through builder-written reductions: BEHIND_SPECIALISTS_ON coloring (0-19), mis (0-10-10, 0.25%); Max-2-SAT NOT_DISTINGUISHABLE (2-0-18); executed reductions only |
| B20_R130 | The global interpretation against the per-pair one at the preregistered measure (F1 averaged over 2-8 experiments): NO_DIFFERENCE (p 0.52), directed F1 worse; it helps only from 6 experiments. The invented instrument ties. Four as good as eight NOT_SHOWN (needs 6) |
| B20_R127 | The system's own engines against human designs: NOT_SHOWN (Gset 10 s: 16–11 against MCX, p 0.44; 9–18 against REX; 28–5 against BLS). The judge released nothing in nine searches: training gains +0.04–0.23% against tau 0.75–2.45%; no compounding; no mechanism credited |
| B20_R120, R122, R124 | Genesis's choice of experiments no better than random (four times; these chose from fixed observational scores; B20_R129's adaptive scientist then beat random) |
| B20_R72, R92, R97 | Physics move rules show no measurable effect in the invention engine |
| B20_R128 | Improving the inventor's process: NOT_SHOWN (NO_DIFFERENCE, EVOLVED − ORIGINAL +0.00023, 5–3, p 0.55); no release in any of 30 inner searches, so the meta-search selected first incumbents, not inventions |
| B20_R132 | The four bottlenecks of invention: NOT_SHOWN; diagnosis EXPRESSIVENESS in every class. No release by the protected judge or the candidate v3 in 9 trajectories; headroom +0.055% / +0.232% / +0.073% (REX 10 s over 1 s); no engine of 112-117 per class confirmed on fresh graphs (planar +0.288%, p 0.26); V2's power at +1% at most 6%, v3's delta50 0.2-1.0%; S1 holds (0/60); V2 3/60 zero-signal releases in the pool world |
| B20_R148 | The portfolio of discovery processes (Ω²): NOT_SHOWN; G3_NOT_SHOWN. G2 (halving across six processes) − G0 (the inventor's evolution) +0.0015 AUDC (6–4, p_Holm 1); G3 − G2 +0.010 (p_Holm 0.70); H1 UNIVERSAL_HARNESS by its rule (anneal and evolution never beaten on all six seeds), though five processes are each best on some task. Secondary, uncorrected: G3 − G2 in final quality +0.027 (7–2, p 0.039) |
| B20_R131 | The cascade on a real case: NO_VERIFIED_TRIGGER by protocol (R130 did not verify the global interpretation), so no reactivation was measured; comparators at 24 evaluations: fresh 0.496, random retrieval 0.502, null 0.496, eig 0.450; archive overhead 158.9 s CPU |

| B20_R165 | **REPLICATED_WITH_SINGLE_ENGINE**: the 18 engines Genesis's searches found in B20_R151 beat REX at 1 s on 48 fresh planar 2,000-vertex graphs by +0.582% (C0_1 +0.661%), all of it on ±1-weighted graphs (+1.16%, 24 of 24); unweighted ties, tori and random graphs lose. Not a release. (Note, 30 Oct: random L0 engines also beat REX on ±1 planar graphs (B20_R173's calibration); search against random sampling is B20_R174's question) |
| B20_R156 | **FRONTIER_BETTER** (a calibration): the Frontier's allocation beats halving (+0.193), UCB1 (+0.108) and uniform (+0.317) on 24 sealed planted worlds, each p_Holm < 0.001; with abstraction and branching out 2.3 times the reference. Its forecast intervals covered 0.66 at a nominal 0.90 (overconfident) |
| B20_R173 | **RELEASED**: the protected judge (contract v2, unchanged) released C0_1, an engine from Genesis's own search (B20_R151, over the builder's L0 language), over the builder-configured REX on ±1-weighted planar 2,000-vertex graphs at 1 s: B gain +1.220% against tau 0.782%; on 24 fresh truth graphs +1.122%, 24 of 24 (p 6 × 10⁻⁸). The first such release; one family only; not against published solvers; and REX is weak there: 7 of 47 random L0 engines would also have been released, so not evidence that the search beats random sampling |
| B20_R167 | **ARA_CALIBRATED** (a calibration): on 95 fresh sealed zoo environments ARA localised 42 of 50 planted limitations (chance 1/4, p 3 × 10⁻¹⁸), said NONE on 30 of 30 null controls, beat tuning alone in four of five classes (not SEARCH_WEAK), beat blind rewriting at two tries by +0.408 of the range (p_Holm 2.7 × 10⁻⁶), and released nothing on 45 controls. FUSION_NEEDED is its weak class. The zoo is planted by the builder |

## Exploratory (development looks, 24 Oct 2026; disclosed in B20_R129 and R130)

| Look | Result |
|---|---|
| Adaptive choice of experiments, R129's framework (confirmed by B20_R129's test above) | Experiments needed: random 7.5, eig 4.5, decfall 4.0, oracle 3.0. One dev search found its own rule (3.96) |
| Interpretation is the limit | Per-pair framework ceiling 0.51; joint re-analysis 0.59; the established LLC estimator 0.71–0.77; multi-regime ML 0.69. Under ML at 8 experiments, the scientist's choice 0.65 against random 0.49 |
| Instruments | Richer per-pair tests do not move the ceiling (0.49–0.53) |
| Question set | A third of hidden causes are never asked about, because FCI separates them on near-unfaithful partial correlations (median 0.03) |
| Problem Compiler at 2 s | Genesis's engine ties the MaxSAT 2026 champion on independent set, Max-2-SAT and max-cut; loses on colouring (15–19 against 7–10 conflicts); HiGHS behind everywhere |
| Difficulty probes | Planted coupling answered by renormalisation (+16 against +4); natural Gset classes give weak probe signals |
| B20_R151 | The builder's richer language Λ1 against Λ0, apart from search: NOT_SHOWN (NO_LANGUAGE_EFFECT on planar2000, the only class past the headroom gate; Λ1's ceiling winners 0.115% below Λ0's) |
| B20_R152 | Self-extension of the engine language on real engines: NOTHING_ADMITTED (the judge refused both of generation 1's statements; the line ended) |
| B20_R172 | Foundry G4, a state feature found by replaying the engine's own decisions: NOT_SHOWN (−0.022 against the defaults given C_search; a tie at equal budget, +0.048), but the distinction generalised (S7 0.768 against 0.702, p 0.001) |
| B20_R170 | Foundry G2, a forecast-update rule invented by meta-search: NOT_SHOWN (coverage 0.655 → 0.737, p 3 × 10⁻⁷, but below the band; value −0.180 against the fixed forecaster given C_meta, a tie at equal budget) |
| B20_R163 | F6, the Frontier searching its own configuration: NOT_SHOWN (P − D −0.221, p 0.99; P − D0 a tie; the meta-search's compute as extra budget pays +0.148) |
| B20_R158 | F5, Genesis's own conjectures over generations, FULL against PLAIN: NOT_SHOWN (9 posed in generation 1; FULL 6, PLAIN 5 refuted, McNemar 1–0; the generator posed nothing new afterwards; one unlabelled survivor, a candidate only) |
| B20_R157 | F4, the Frontier against prior-art searches on the sealed Laplacian bounds: PARTIAL (beats NRPA only; GBFS 19 of 33 refuted, the Frontier 14; the allocation no better than UCB or uniform; descriptively the engine reaches 25–26 with Γ-built graphs above the preregistered check's 40 vertices) |
| B20_R144 | ARA applied to its own settings (milestone 2): NOTHING_ADOPTED (the meta-ladder located nothing; six one-step candidates changed no released gain; the variants and the ranking were never tried, by the alphabetical fall-back) |
| B20_R136 | Experiment A, a synthesised sense choosing the engine per graph: NOT_SHOWN (SENSE − always-C0_1 +0.087%, p_Holm 0.0009 but below the material 0.1%; SENSE − the builder's degree CV −0.054%) |
| B20_R141 | ARA's calibration on the zoo: INVALID, by a defect in the script's freshness clause (False in every registered run). Descriptively every experiment would have passed; re-run as B20_R167 |

## Running or preregistered (no result yet)

As of 30 Oct 2026; the order on CPU 0 is in `docs/OMEGA_FRONTIER.md` §12 and `research_queue.json`.

| Batch | State |
|---|---|
| B20_R174 | Genesis's search against random sampling of the same language on ±1-weighted planar graphs (the control B20_R173 lacks): NOT_SHOWN, RANDOM_MATCHES_SEARCH (search winners +1.092% over REX, random winners +1.097%; the best random winner beat the released C0_1 by 0.27%) |
| B20_R175 | F6b, F6 repeated with the meta-search repaired (B20R163-META): NOT_SHOWN, NOTHING_PROMOTED (the guard kept the defaults: survivor 1.939 against 1.952 on the training worlds); F6's procedure's configuration −0.456 against the defaults on held-out worlds (p 0.002) |
| B20_R159 | PT-1, the proving test: INADEQUACY_GATE_FAILED (the predecessor refuted bound 40 of family A; Genesis refuted 40 and 21 from derived graph products; parts 1 and 3-5 not run; not proved out) |

## Unrun plans

| Batch | Plan |
|---|---|
| B20_R134 | The Difficulty Cartographer, redesigned |
| Ω7 | The interpretation engine |
| Ω10 | The allocator |
| Ω12 | Longitudinal autonomy |
