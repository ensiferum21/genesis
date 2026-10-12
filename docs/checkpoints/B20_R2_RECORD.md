# B20_R2 checkpoint record — adopted CRPD subset, the H02 exit run, first parts of H05 and H08

Parent: `GENESIS_COMPLETION_CHECKPOINT_B20_R1.zip`
(sha256 `b8e99c16e01c6ab93cbd0032b28f130be0e96f31372b5b8442416c22d265bbf4`, commit `972dbb6`).
Builder-run, DEV only; nothing here is independently reviewed.

Format per change: problem, implementation, evidence executed, limitation, consequence.

## CRPD-1: soundness modes (from the CRPD v3 proposal, mapped onto handoff s15.3/s16.2)

- **Problem.** Abstractions, transports and bounds had no shared statement of what they license; a
  heuristic and an exact equivalence were not distinguished by type.
- **Implementation.** `invention/soundness.py`: EQ / SUFF / NEC / BOUND / HEURISTIC / REJECTED, derived
  from checked obligations (never from the proposer), requested vs established kept apart, licences per
  use, optimum only from matching checked bounds, aliasing refutation. Wired into world judgements,
  obstruction evidence and research guidance.
- **Evidence.** `tests_formal/test_soundness_modes.py` (13); `evidence/soundness_b20r/modes.json`:
  1 EQ, 5 SUFF, 13 REJECTED, 6 HEURISTIC, 12 BOUND (12 optima licensed).
- **Limitation.** The kernel's promotion rules do not yet consume mode records directly.

## CRPD-2a: codegree characterisation of C4-freeness, Lean-checked

- **Implementation.** `invention/codegree.py`, `scripts/b20r_codegree.py`; trusted definitions over the
  repository's own `GT.Edges`/`G4` and a builder-written proof (known result).
- **Evidence.** `evidence/codegree_b20r/`: CHECKED with the allowed axioms only, package REPLAYED;
  `tests_formal/test_codegree.py` (6). The first EQ abstraction in Genesis.
- **Limitation.** CRPD-2b, the pair-count bound, needs a workspace pin revision (B20R-OPEN-3).

## CRPD-3: orbit-sensitivity probe of E (DEV diagnostic)

- **Evidence.** `evidence/orbit_probe_b20r/`: 50 fresh targets, six equivalent presentations plus two
  repeats each; zero mixed outcomes; NOT_DETECTED on all three systems (decision rule fixed in advance).
- **Consequence.** CRPD s4.1 has no measured headroom on these families. Fixed-limit E outcomes were
  deterministic on a quiet host (context for B20-OPEN-3).

## H02 exit: fresh frozen DEV E3 study on the repaired harness

- **Design.** `scripts/b20r_e3_fresh.py`, committed before running (commit `e4e431b`): fresh seeds;
  global exposure from all prior DEV evidence (3,253 statements, B20 pools regenerated and hash-checked);
  calibration and evaluation drawn by `learning.partitions`; budgets OUTER_SUPERVISED re-measured under
  the repaired account (caps 1.848 s Sheffer, 0.648 s Huntington); learned policy retrained and frozen
  before evaluation; custody for every scored target; declared charging (primary comparison at equal
  research caps, training reported, not charged).
- **Results (prover-reported, eligible).** Learned vs fixed 0W/2T/6L (mean −2.375). Mean eligible per 25:
  fixed 16.125, heuristic 16.0, bandit 15.875, random 15.25, learned 13.75, empty 13.375. All 40 runs within
  cap; zero custody problems; screen blocks: none expected, see `screen_summary.json`.
- **Checked coverage.** 338 Lean replays from custody: 269 CHECKED, 69 CHECK_FAILED, all in Huntington 602/603
  and traced to one lemma step the tactic cascade cannot close (B19-OPEN-5); not falsity. On the checked metric
  fixed loses credit for that library while learned (empty library) does not: checked counts here measure
  translator coverage, which is why the prover-level endpoint was declared primary.
- **Findings.** With preparation charged, the learned policy's feature computation uses ~0.6 s of the
  0.65 s Huntington cap (library 0 in every Huntington run); on Sheffer it builds 66–76 lemmas without
  gain. Training CPU 75.3 s. B20R-OPEN-1.
- **Consequence.** The repaired harness runs E3 end to end. The learned policy does not beat fixed rules on
  this DEV study; better-improver remains UNESTABLISHED. A redesign needs a new frozen study.

## H08 (part): research lineage

- `src/genesis/lineage.py`, `tests_genesis/test_generation_lineage.py` (21): records, a pure validator with
  every s20.7 attack, a DEV fixture chain (not GV5 evidence), and an adapter for campaign exports.
- `audit/lineage_b20r/report.json`: the stored three-generation DEV campaign export yields no qualifying
  chain (selection scores not exported, candidates not bound to attempts, no per-run account, declared vs
  actual change mismatch). Both sealed kinds stay refused (B14-OPEN-3, B20R-OPEN-2).

## H05 (part): trusted candidate runner

- `src/genesis/candidates.py`, `tests_genesis/test_candidate_adapters.py` (12): closed kind registry,
  rebuilt descriptors, soundness-licensed representations only, candidate-view-only child under the
  metered budget, strict decoding and domain re-check. Not wired into the custodian (B20R-OPEN-4).

## Environment re-check

PyPI does not resolve and the Docker registry is refused by the egress proxy from this workspace:
R-04 wheel hashes and the image digest stay BLOCKED_ENVIRONMENT.

## Claim ceiling

Engineering checkpoint and DEV diagnostics. No sealed task, no promoted scientific claim, no
better-improver claim.
