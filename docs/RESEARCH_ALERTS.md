# Research alerts and what Genesis does with them

Each alert is Daniel's, recorded with the decision it led to and the batch that carries it. The papers are taken as
the alert describes them. If a paper could not be located independently, that is said.

## 22 October 2026 ("Genesis Distinction Engine — Research Alert")

### 1. Preventing an autonomous agent from fooling its own judge (priority: high)

**The alert.** *An Explicit Feedback Contract for Iterative ML-Agent Harnesses* (preprint, submitted 20 Oct 2026).
Iterative agents manufacture apparent gains by optimising repeatedly against the same validation data. In a setting
with no possible improvement:
- unrestricted feedback produced a reported gain of 0.0157;
- a restricted-feedback protocol reduced it to 0.0033.

The protocol has four parts:
- it releases validation scores only when an improvement exceeds a noise-dependent threshold;
- it restricts access to validation artifacts;
- it fixes stopping conditions;
- it keeps a separate test set for the final evaluation.

The formal guarantee covers a fixed-threshold variant. A web search on 23 Oct 2026 did not locate the preprint, so it
is used as the alert describes it.

**Where Genesis stands.** Three of the four parts are already enforced at the level of claims:
- every claim is preregistered and judged on fresh hosts drawn after the design was fixed (a separate test set);
- `judge.py` recomputes sealed evaluations from raw receipts;
- stopping rules are part of each preregistration (B20_R97's looks).

The gap is one level down, inside the improvers:
- The program search (B20_R79 onwards) and the configuration races (B20_R89, R95) select on repeated fitness
  feedback from the same training hosts. Their reported training numbers ("290.00 on its own hosts") are optimistic
  by construction, which is why they are never used as claims.
- The research loop sees full study results.

Neither has a contract that bounds how much noise it can mistake for progress. Neither has been tested on a problem
with no signal, where the right answer is to stop.

**Decision: B20_R103, strengthen the judge; no redesign.**
- **Engineering, `autonomy/feedback.py`.** A feedback contract with a *fixed* threshold, set from a calibration of the
  evaluation noise before the search starts (the variant the guarantee covers). A research worker (a search, or the
  loop) receives an improvement only when it exceeds the threshold *and* a fresh confirmation evaluation agrees.
  Otherwise it receives "not better" and no number. The judge keeps the detailed scores. A worker stops after a
  fixed number of consecutive rejections. Final numbers come only from held-out hosts the worker never saw.
- **Study (preregistered), the zero-signal battery:**
  - *L1, no signal:* Genesis's program search, with its real language and selection, on an oracle whose value is
    noise independent of the program. Measured: the reported gain, unrestricted against under the contract, over many
    replicate searches. The search must learn to stop.
  - *L1, signal present:* the same, with a planted real effect. The contract must not stop real progress.
  - *L2, no signal:* the research loop's preregistered analyses (`autonomy.qet`, the quantile-ratio labels) on
    synthetic studies whose arms are identical. Their false "better" rate must stay within the nominal level.
- An adaptive threshold would need its own statistical validation before adoption; it is not part of B20_R103.

**Result (23 Oct 2026; `evidence/zero_signal_b20r103/`).** The alert's effect is real in Genesis's own program search:
with no signal, the open protocol's reported number overstates the truth by 0.5, 3.4 and 6.6 sigma_e as the quirks of
the evaluation data grow (up to about one edge). Under the contract every no-signal search stopped at about a third
of its budget, released noise once in 180, and its held-out final numbers are unbiased. It keeps 69% and 51% of the
open protocol's real gain at small quirks and 13% at the largest (TOO_STRICT, as forecast). The research loop's
analyses never called identical arms different (0 of 800; CALIBRATED). The preregistered headline reads
CONTRACT_LEAKS: its ratio rule compares the contract with a quarter of the open protocol's claimed gain, which is
negative at quirk 0, and the one false release fails it. The rule is mis-specified for a negative reference; the
measured leak is 0.07 sigma_e of claimed gain and none in the final numbers. Next: compare with the truth, not a
ratio; larger confirmation data to recover power.

**Version 2 (B20_R107, `evidence/contract_v2_b20r107/`): V2_FIXES_POWER.** The judge sets its threshold from its own
two confirmation splits (each the mean of 4 hosts, charged to the budget) rather than from the worker's training
differences. The threshold halves; the contract keeps 93%, 77% and 63% of the open protocol's real gain (version 1:
59%, 40%, 17%), releases noise in 1 of 180 searches, and its held-out numbers stay unbiased. Version 2 is the
contract to use.

### 2. Causal discovery with hidden variables (priority: medium-high)

**The alert.** *Causal Discovery for Linear Models with Latent Confounding via Multi-domain Identifiable
Representation Learning* (LinADMG; preprint, submitted 20 Oct 2026). It uses several environments to identify the
noise variables when unobserved variables confound several observed ones, with conditions under which direct causal
edges, and possibly the whole graph, are recoverable. It assumes linear models and specific identifiability
conditions, and does not invent unknown variables. A web search on 23 Oct 2026 did not locate it.

**Why it matters to Genesis.** The roadmap's missing-variable question: can the system tell when its measurements
cannot explain what it sees, and propose the measurement or intervention that would? Genesis has a first, narrow
version of "knowing what it does not know": the knowledge map's uncertainty and surprises (B20_R100). It has nothing
for hidden causes.

**Decision: a later checkpoint, not now.** It is added to `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md`'s build order
as a benchmark:
- multi-environment linear systems with planted hidden confounders;
- Genesis against LinADMG (if its code is released) and established baselines;
- scored on causal-edge recovery, and on whether Genesis proposes the extra measurement or intervention that resolves
  a confounder.

It needs a new domain (causal models, with a checker for graph recovery) and comes after the feedback contract and the
Gset track.

**Started (23 Oct 2026).** B20_R117 built the benchmark (`src/genesis/causal`: planted multi-environment linear
models with hidden confounders, exact scoring, PC, an oracle PC and DirectLiNGAM written from their papers).
B20_R118's calibration: CONFOUNDING_MISLEADS. DirectLiNGAM connects 99% of the confounded pairs and PC 68%, and
neither can mark a hidden cause (`evidence/causal_calibration_b20r118/`). LinADMG's code was not found; FCI is
the established comparator for the next step, Genesis proposing the interventions that resolve hidden causes.

**B20_R119-R120 (24 Oct 2026): NOT_SHOWN.** FCI (written from the papers) plus a budget of interventions chosen by
Genesis's suspicion of hidden causes did no better than random targets. An oracle's targets show the headroom:
hidden-cause F1 0.47 against FCI's 0.19 at 4 interventions. Post hoc, the observational suspicion barely separates
confounded pairs, and the decision rule reads ancestral dependence as direct causation. Next: fix both, on fresh
instances (`evidence/propose_interventions_b20r120/`).

**B20_R121-R122 (24 Oct 2026): HIDDEN_CAUSES_MARKED.** With a LiNGAM-residual signal (Hoyer et al. 2008; RCD) and a
rule that tests direct causation under intervention, Genesis marks hidden causes on fresh instances with F1 0.47
against FCI's 0.21; the share of confounded pairs reported as causal falls from 0.44 to 0.14. Experiments add
direction (directed F1 0.25 to 0.64), not detection, and Genesis's choice of experiments still ties random: the
second half of the alert (proposing the experiment) remains NOT_SHOWN (`evidence/hidden_causes_v2_b20r122/`).

**B20_R124 (24 Oct 2026): EXPERIMENTS_NEEDED.** With Gaussian noise the observational flag sees nothing beyond FCI,
as theory predicts; random experiments add hidden-cause marks, and an oracle's choice of four equals random eight.
Genesis's choice ties random: proposing the right experiment needs a sequential design that uses what experiments
reveal (`evidence/gaussian_hidden_causes_b20r124/`).

## Overall

The Explorer–Judge–Consolidator shape stays. The urgent part is item 1: it decides whether any future claim of
recursive improvement can be trusted, and it is where B20_R103 goes.
