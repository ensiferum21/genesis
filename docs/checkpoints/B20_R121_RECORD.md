# B20_R121 record: the active procedure, version 2 (engineering); setup of B20_R122

- **Built by:** the builder, on 24 Oct 2026, developed on B20_R120's 40 instances. Those were already looked at,
  so every development number below is optimistic. B20_R122 measures the result once, on fresh instances.
- **Why:** B20_R120 (NOT_SHOWN) found two faults after the fact: a suspicion signal that barely separated confounded
  pairs, and a decision rule that read ancestry under intervention as direct causation.

## What was built: `src/genesis/causal/active2.py`

Version 1 (`active.py`) is unchanged. Version 2 with `rule='v1', signal='v1'` reproduces it exactly; a test checks
this.
1. **Signal: LiNGAM residuals.**
   - Fit DirectLiNGAM. Within each environment, regress every variable on its LiNGAM parents.
   - Test whether the residual depends on each parent, using nine non-linear correlations, Bonferroni-corrected.
   - A hidden common cause leaves the residual uncorrelated with the parent but dependent on it.
   - This is the principle of LiNGAM with hidden variables (Hoyer et al. 2008) and of RCD (Maeda and Shimizu 2020),
     used here as the signal for choosing experiments.
2. **Rule: direct causation under intervention.**
   - Under do(X_t), a neighbour j that depends on X_t is regressed on X_t and on t's descendants adjacent to j.
   - A significant coefficient means t → j.
   - Otherwise t is an ancestor of j but not a direct cause, and their FCI adjacency is explained by a hidden common
     cause (↔).
3. **Flagging.**
   - Pairs whose signal is significant (p < 0.01) are marked ↔ from observational data alone. This is the
     observational baseline any use of experiments must beat.
   - An experiment can refute a flag, by finding a direct cause, but cannot erase it by finding nothing.

## Development looks on B20_R120's instances (mean hidden-cause F1)

- **Signal.** The pairwise residual signal tried first had AUC 0.54 for confounded pairs. The LiNGAM-residual
  signal has AUC 0.83 and was adopted.
- **Without flags.** Suspicion scored 0.28 at budget 2 and 0.49 at budget 4. Random scored 0.20 and 0.26, and the
  oracle 0.29 and 0.49. The rule alone moved the oracle at budget 4 from 0.47 to 0.49.
- **Flags.** Flagging alone scored 0.46; FCI alone scored 0.19. When experiments could overwrite flags, every arm
  went down, so the rule was changed to "refute, not erase".
- **The B20_R122 arms:**

  | Arm | Hidden-cause F1 |
  |---|---|
  | FCI | 0.19 |
  | flag | 0.46 |
  | random, 2 | 0.46 |
  | degree, 2 | 0.45 |
  | suspicion, 2 | 0.43 |
  | oracle, 2 | 0.45 |
  | random, 4 | 0.49 |
  | degree, 4 | 0.46 |
  | suspicion, 4 | 0.50 |
  | oracle, 4 | 0.52 |

  Directed F1 rises from 0.27 (flag) to 0.59–0.69 at budget 4.

**What the development already says.** The observational signal, a prior-art principle, does most of the work in
marking hidden causes. Experiments mostly help orient direct causes, and Genesis's choice of experiments does not
clearly beat random ones.

## Tests

`tests_genesis/test_causal_active2.py` (8):
- version 1 reproduced;
- the residual signal on a direct cause and on a hidden cause;
- the signal's scale and keys;
- direct, indirect and none under intervention on a hand-built model, including the case version 1 got wrong;
- the decision rule;
- flags refuted but never erased;
- refusals.

## B20_R122 (preregistered here)

`scripts/b20r122_hidden_causes_v2.py` (SHA-256 `1c5dac80…9adc`), design tests in
`tests_genesis/test_hidden_causes_v2.py`. It runs 40 fresh instances with B20_R120's settings and 10 arms.
- **Test 1 (primary):** suspicion at budget 4 against FCI on hidden-cause F1. The verdict is HIDDEN_CAUSES_MARKED or
  NOT_SHOWN.
- **Test 2:** do experiments add to the flag (hidden-cause and directed F1)?
- **Test 3:** does Genesis's choice beat random, at budgets 2 and 4?
