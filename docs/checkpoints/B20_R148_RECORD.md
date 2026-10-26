# B20_R148 record: a portfolio of discovery processes is not distinguishable from Genesis's single inventor at 1,024 evaluations (NOT_SHOWN; DEV)

- **Run by:** the builder, on DEV; licenses nothing; changes no package, rule, comparator or default. Preregistered at
  `251c956` (`scripts/b20r148_harness_portfolio.py`, SHA-256 `d20a30d4728190e62ce6d24cc1f334a451a534c4a0bb875936c842035dbd3409`,
  sent to Daniel before it ran), unchanged. Design and adoption: `docs/OMEGA_META_ADAPTIVE.md`; the development looks
  behind the preregistration: `B20_R148_SETUP.md`.
- Alone on CPU 0, from a clean worktree of `13bd014` (no code change after `251c956`), 26 Oct 2026 17:38 to 27 Oct
  00:08 SGT, in four slices (6,625 s, 6,634 s and 6,677 s paused as designed; 3,368 s to the end). The `code_identity`
  is the same in all four (`5ed7b8e0…bc8`). Evidence `evidence/harness_portfolio_b20r148/`; recomputed
  independently from the rows with separate code (normalisation, AUDC, H1, task means, Holm, labels, verdict, and H*
  from the development rows): every value matches.

## Result

**Verdict NOT_SHOWN; G3_NOT_SHOWN.** On ten fresh tasks in three of Genesis's languages, at 1,024 evaluations each,
neither the adaptive portfolio (G2, successive halving across six discovery processes) nor its meta-tuned version
(G3) can be told apart from Genesis's current inventor's search (G0, steady-state evolution). G2 was not worse either.

Primary family: per-task mean AUDC over six seeds; two-sided Wilcoxon over the ten tasks; Holm across the three.

| Test | Mean AUDC difference | Tasks won–lost | p | p (Holm) | Label |
|---|---|---|---|---|---|
| T1: G2 − G0 | +0.0015 | 6–4 | 0.625 | 1.0 | NOT_DISTINGUISHABLE |
| T2: G2 − H* (H* = evolution = G0) | +0.0015 | 6–4 | 0.625 | 1.0 | NOT_DISTINGUISHABLE (the same comparison as T1, as preregistered) |
| T3: G3 − G2 | +0.0100 | 6–4 | 0.232 | 0.697 | NOT_DISTINGUISHABLE |

**By domain** (descriptive; mean of the per-task differences, wins–losses):

| Domain | T1 (G2 − G0) | T3 (G3 − G2) |
|---|---|---|
| acquisition rules (4 tasks) | +0.019 (3–1) | +0.003 (2–2) |
| planted formulas (4) | −0.038 (1–3) | +0.010 (3–1) |
| max-cut engine programs (2, a held-out domain) | +0.045 (2–0) | +0.023 (1–1) |

The portfolio gains where the best single process changes from task to task (max-cut, acquisition) and loses on the
formulas, where hill climbing and evolution are strongest and the portfolio spends part of its budget elsewhere. The
two cancel.

**H1, by its preregistered rule: UNIVERSAL_HARNESS** (unbeaten: anneal and evolution). A process is beaten on a task
when another single process has a higher AUDC on all six seeds. Map-Elites is beaten on 5 tasks, racing on 4, best-of-N
and hill climbing on 1 each. Annealing and evolution are never beaten in that sense. **This label does not mean one
process is best everywhere.** Five different processes have the best mean AUDC on some task: hill climbing on 4
(formula small, medium, large; acquisition shift), best-of-N on 3 (acquisition base, sparse; torus), and annealing
(acquisition large), evolution (formula mixed) and racing (erdos_pm1) on one each. The rule asks for dominance on every
seed, which six noisy seeds rarely give, so it is a weak test of the question it answers. The label stands as
preregistered. Reading it as "a universal discovery process exists" would be wrong. Reading it as "no process was
consistently dominated by another, except Map-Elites and racing" is accurate.

Mean AUDC on each test task (six seeds; the best single process in bold):

| Task | best-of-N | hill climb | anneal | evolution (G0) | Map-Elites | racing | uniform (G1) | halving (G2) | bandit | halving tuned (G3) |
|---|---|---|---|---|---|---|---|---|---|---|
| acquire base | **0.831** | 0.789 | 0.787 | 0.823 | 0.802 | 0.774 | 0.825 | 0.827 | 0.828 | 0.830 |
| acquire shift | 0.822 | **0.860** | 0.836 | 0.824 | 0.816 | 0.749 | 0.871 | 0.875 | 0.876 | 0.870 |
| acquire sparse | **0.818** | 0.803 | 0.764 | 0.804 | 0.788 | 0.745 | 0.823 | 0.826 | 0.825 | 0.822 |
| acquire large (held out) | 0.790 | 0.799 | **0.839** | 0.782 | 0.825 | 0.786 | 0.794 | 0.780 | 0.796 | 0.799 |
| formula small | 0.956 | **0.970** | 0.968 | 0.965 | 0.946 | 0.923 | 0.962 | 0.966 | 0.964 | 0.964 |
| formula medium | 0.683 | **0.720** | 0.661 | 0.702 | 0.613 | 0.594 | 0.701 | 0.701 | 0.701 | 0.709 |
| formula large | 0.690 | **0.724** | 0.700 | 0.711 | 0.671 | 0.633 | 0.652 | 0.646 | 0.649 | 0.654 |
| formula mixed (held out) | 0.669 | 0.784 | 0.752 | **0.815** | 0.713 | 0.705 | 0.723 | 0.729 | 0.738 | 0.755 |
| mcx2 torus (held out) | **0.755** | 0.685 | 0.725 | 0.690 | 0.720 | 0.750 | 0.786 | 0.735 | 0.721 | 0.725 |
| mcx2 erdos_pm1 (held out) | 0.737 | 0.592 | 0.602 | 0.693 | 0.732 | **0.756** | 0.765 | 0.738 | 0.752 | 0.795 |
| **mean over tasks** | 0.775 | 0.773 | 0.763 | 0.781 | 0.763 | 0.742 | 0.790 | 0.782 | 0.785 | **0.792** |

**The discovery curve.** Mean normalised quality q of each arm's validated answer at each checkpoint (over tasks and
seeds):

| Arm | 32 | 64 | 128 | 256 | 512 | 1,024 |
|---|---|---|---|---|---|---|
| evolution (G0) | 0.719 | 0.729 | 0.769 | 0.793 | 0.829 | 0.849 |
| hill climb | 0.665 | 0.729 | 0.754 | 0.794 | 0.829 | 0.849 |
| best-of-N | 0.726 | 0.740 | 0.759 | 0.796 | 0.809 | 0.816 |
| anneal | 0.680 | 0.702 | 0.750 | 0.775 | 0.813 | **0.874** |
| uniform (G1) | **0.732** | 0.760 | 0.782 | 0.806 | 0.819 | 0.837 |
| halving (G2) | 0.725 | 0.748 | 0.762 | **0.807** | 0.814 | 0.838 |
| bandit | 0.718 | 0.755 | 0.782 | 0.801 | 0.808 | 0.839 |
| halving tuned (G3) | 0.725 | **0.762** | **0.784** | 0.794 | 0.827 | 0.864 |

The portfolio arms lead from 32 to 256 evaluations. The single processes catch up by 512 and pass them at 1,024:
annealing ends highest (0.874), then G3 (0.864). **This is the opposite of the mechanism the expectation gave.** The
expectation said a portfolio's early checkpoints would follow its weakest starters. In fact, early on a portfolio is
the best of several processes' first answers, which is strong. What it loses is the late part of the curve: it never
gives one process the whole budget. AUDC weighs each doubling equally, so the early lead and the late deficit nearly
cancel.

**Secondary (uncorrected, labelled so by preregistration; none is a finding):**
- G1 (uniform) − G0: +0.009 (6–4, p 0.43). Uniform has the second-best mean AUDC (0.790), above G2.
- bandit − G2: +0.003 (7–3, p 0.38).
- G2 against each single process: best-of-N +0.007 (p 0.56), hill climb +0.010 (p 0.85), anneal +0.019 (p 0.43),
  evolution +0.002 (p 0.63), Map-Elites +0.020 (8–2, p 0.19), racing +0.041 (7–3, **p 0.049 uncorrected**).
- Final quality (q at 1,024): T1 −0.011 (4–5, p 0.82); **T3 +0.027 (7–2, one tie; p 0.039 uncorrected)**. G3's tuning
  may help the end of the curve more than its area. A study that wants to show that must make it primary.
- Held-out tasks only (acquisition large, formula mixed, torus, erdos_pm1): T1 +0.0005 (2–2, p 1.0); T3 +0.023 (3–1,
  p 0.25).

**The second currency.** Mean CPU per run is 30.1–31.7 s for every arm (within 5%), so matching evaluations also
matched CPU. The allocators' own logic costs nothing measurable next to the evaluations.

**Development** (written to `dev.json` before any test task existed in the output):
- H* = evolution (mean development AUDC 0.847, against anneal 0.829, hill climb 0.823, best-of-N 0.806, Map-Elites
  0.788, racing 0.757). H* is G0's process, so T2 duplicates T1, as the preregistration provided.
- G3's parameters differ from DEFAULTS for five processes:
  - hill climbing stall 100 (development AUDC 0.835 against 0.793 for the default);
  - Map-Elites with 16 initial programs and no crossover (0.849 against 0.808);
  - evolution with population 32, 8 children, tournament 3, crossover 0.25 and no leaders (0.835 against 0.829);
  - annealing with t_end 0.001 and probe 8 (0.818 against 0.815);
  - racing batch 32 (0.774 against 0.755).

  Best-of-N has no parameters. On the test tasks the tuning gained +0.010 AUDC, not distinguishable (T3).

**Validity.** All 600 rows present (10 tasks × 10 arms × 6 seeds). Every run's charged evaluations are within
[1022, 1024], and every curve has six checkpoints. Every max-cut cut was checked by both checkers with no
disagreement (the study would have stopped). The protected judge's digest was checked at every start (`2ff4a5ab…dd6`);
nothing here uses the judge.

## Against the expectation stated before running

| Expected | Found |
|---|---|
| H1 NO_UNIVERSAL_HARNESS likely; racing and best-of-N beaten on formulas, hill climbing on acquisition | **no**: UNIVERSAL_HARNESS (anneal and evolution never beaten on all six seeds). Racing beaten on three formula tasks and best-of-N on one (mixed), as expected; Map-Elites on four formula tasks and acquisition base; hill climbing only on erdos_pm1, not on acquisition |
| T1, T2 NOT_DISTINGUISHABLE; G2 worse than H* possible | NOT_DISTINGUISHABLE (+0.0015); not worse |
| the mechanism: a portfolio's early checkpoints follow its weakest starters | **reversed**: the portfolio arms lead early and fall behind at the full budget |
| T3 NOT_DISTINGUISHABLE | yes (+0.010, p_Holm 0.70) |

## Cost against the estimate (disclosed)

23,303 s (6.5 h) against "about 5 hours", 29% over.
- **Instance preparation and development:** 4,246 s (71 min) against about 75 min estimated. Within the estimate.
- **The 600 test runs:** about 5.3 h against 3.7 h.
  - Max-cut accounts for most of the overrun. Its runs took 73 s on torus and 124 s on erdos_pm1, against "about
    65 s": 3.3 h for the 120 runs, against 2.2 h.
  - Acquisition runs took 16–41 s (estimated 12–40 s), 1.8 h in all.
  - Formula runs took under 1 s, as estimated.

The setup document does not record how the 65 s figure was obtained, so the source of the error cannot be traced
from the record. The slices absorbed the overrun as designed.

## Limits

- DEV, builder-run, one machine. Ten tasks in three domains; the task is the unit, so the primary tests have n = 10.
  One budget (B = 1,024 evaluations); six seeds per task. No independent replication.
- **The processes are textbook versions** (all six are prior art) with small parameter spaces; nothing here is
  invented. G3 is parameter tuning, which ARA's rule says is never reported as invention.
- **Max-cut is noisy relative to its range.** The answers lie within about 1% of REX (low 0.990–0.992; high, the best
  any arm reached, 1.006–1.010), so normalisation stretches run noise: the development looks saw about 0.002 between
  checkpoints. The
  max-cut AUDC differences, where the portfolio gained most, are partly noise even with the mean of two measured runs.
- **The formulas are a positive control with a known optimum.** They reward steady local improvement, which favours
  hill climbing and evolution.
- **The acquisition tasks saturate early.** Many programs reach the best value, and the validated answer can be worse
  on T than on V. This was disclosed from the development looks and is the reason for the larger V and T.
- **H1's rule versus its question** (above): the rule is weak, and the label is not evidence that a universal process
  exists.
- The report's citations (the 30-harness comparison and others) remain unverified, `OMEGA_META_ADAPTIVE.md` §7.
  This study neither confirms nor refutes them. It tests their central claim in a small LLM-free setting and does not
  find it.

## What it decides

Nothing about packages, rules, comparators or defaults. **The study does not support making successive halving
across processes Genesis's default allocator at this budget.** Genesis's inventors keep their single process until a
separately preregistered study shows otherwise. The result is not that portfolios fail. A portfolio's advantage, here,
is at small budgets and on tasks where the best process varies. Its cost is at the full budget on tasks where one
process is clearly best. Directions this suggests, none preregistered:
- an allocator judged at several budgets;
- an allocator that hands the whole remaining budget to a leader earlier;
- the allocator across activities (`OMEGA_META_ADAPTIVE.md` §5.1), whose units differ more than these six processes do.

The queue's line `meta-adaptive` records this as a negative outcome (one of three before stagnation).

## Tests

`tests_genesis/test_harness_portfolio.py::RecordB20R148` (3), on the evidence:
- the preregistered script unchanged (its SHA-256);
- validity, and the verdict, G3, H1 and every primary label and Holm p-value recomputed by `analyse` from the saved
  rows;
- development used development rows only: the six development tasks × six processes × three seeds, H* and the tuned
  parameters from them.

The design tests (11) and `test_portfolio` (14) are unchanged.
