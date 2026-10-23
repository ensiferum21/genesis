# B20_R118 record: causal calibration with hidden confounders (CONFOUNDING_MISLEADS), and the checkpoint it closes

- **Run by:** the builder, alone on CPU 0, 23 Oct 2026, 38 s. Setup commit `82e95c5`, run at `39f4f64`.
- **Evidence:** `evidence/causal_calibration_b20r118/` (README with the full tables).

## Result

- DirectLiNGAM connects 191 of 192 confounded non-adjacent pairs (0.99). PC connects 130 (0.68), and the oracle PC
  all of them. None of these methods can mark a hidden cause. Label: **CONFOUNDING_MISLEADS**.
- Hidden variables cut DirectLiNGAM's directed F1 from 0.98 to 0.77 (HIDDEN_HURTS). PC's directed F1 (0.66 → 0.63) is
  limited by Markov equivalence either way (NO_EFFECT).
- Pooling three environments naively changes little.
- Next: FCI as the hidden-variable baseline, and Genesis's active procedure, which proposes the interventions that
  resolve hidden causes (B20_R119–R120).

## The checkpoint this batch closes (B20_R114's slot)

`GENESIS_COMPLETION_CHECKPOINT_B20_R118` covers B20_R74–R118, since the last checkpoint (B20_R73):
- the state-of-the-art MaxSAT and max-cut tool chains;
- the large-graph engine and the autonomy layer;
- the knowledge map;
- the feedback contract (v1 and v2);
- the Gset track: Genesis's max-cut engine `mcx-v1`, 40 of 54 best known values matched, none exceeded;
- three invention tests, all NOT_DEMONSTRATED;
- the hidden-confounder causal benchmark.

The first build, at `1d473a1`, failed its release matrix on three record tests that read the live evidence corpus
(repaired in `39f4f64`). The other suites passed in that build: legacy 282 (one declared skip), sandbox 28,
certificates 43, formal 184.

## Tests

`tests_genesis/test_causal_calibration.py`: Design (7); Record (1). The record test re-scores all 640 answers from
the regenerated truth.
