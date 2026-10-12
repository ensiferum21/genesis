# B20_R3 design pilot: does the E3 family leave room for a better research policy?

`scripts/b20r3_headroom_pilot.py`, DEV, builder-run. This is a design diagnostic, not a study: it runs
no candidate policy, licenses no claim, and its pools and targets count as exposure for every later
study (`b20r3_e3_costaware.py` scans this directory).

The question: before redesigning the learned research policy (B20R-OPEN-1), can *any* selection from
the research pool beat the fixed smallest-first policy under the calibrated cap? ORACLE is the
dependency closure of the lemmas that eligible proofs with the exhaustive library used, built from the
targets themselves. It is an optimistic reference, not an arm.

Rounds (each added after the previous one came back flat; all rounds are reported):

| Round | Mode | What changed |
|---|---|---|
| 1 | default | E3 configuration on six systems: pools of up to 4–5 nodes, targets as in E3 |
| 2 | `:t6` variants | larger targets (up to 6 nodes per side, 9–12 nodes in total) |
| 3 | `--scarcity` | caps of 2%, 5% and 10% of the exhaust CPU (Huntington t6) |
| 4 | `--mined` | research pool extended with true subterm equalities mined from 10 development targets |
| 5 | `--strategy` | empty library under E `--auto` at 1 s and 3 s and `--auto-schedule` at 1 s |

## Findings (12 targets per range; `summary.json`)

- **Selection headroom (ORACLE − FIXED@CAP): at most +1 target in 12 on every system and range.**
  - Sheffer: libraries barely matter (EMPTY 2–8, EXHAUST at most +1).
  - Huntington: libraries matter a lot (round 2, 10–12 nodes: EMPTY 5, EXHAUST 11, ORACLE 12), but
    FIXED@CAP already reaches 12.
  - grp_div, grp_std, dist_lattice: EMPTY at or near 12/12 (ceiling).
  - Wolfram: 0/12 under every library (floor; E proves no pool equation in 1 s).
- **Why Huntington has no room.** The smallest pool lemma, `plus(X,X) = X`, is the expensive key
  lemma: 0.26 s, against about 6 ms for each lemma after it. Smallest-first therefore *is* the oracle
  order.
- **Round 3.** Under 2–10% caps no library can be built at all: the first attempt alone needs about
  0.26 s. Fixed and oracle both stay at EMPTY.
- **Round 4.** Mined target-shaped lemmas are almost never used:
  - Huntington: 1 of 36–41 mined lemmas used, no gain.
  - Sheffer: 0–1 of 14–17 used, no gain.
- **Round 5.** E's strategy schedule and 3× time add at most one target (Huntington 10–12: 5 → 6).
  The unproved Sheffer targets are beyond 3 s.

**Consequence for B20R-OPEN-1.** On this family a better research policy *cannot* show up as better
successors. The fixed policy is at the oracle reference within one target in 12, so a redesigned
policy can at best tie.

- `b20r3_e3_costaware.py` is therefore registered as a repair and non-inferiority check of the redesign,
  with its own ORACLE diagnostic of discriminating power.
- The better-improver question needs a family where the useful lemmas are not the smallest ones and
  where libraries move the needle. See `docs/checkpoints/B20_R3_RECORD.md`.

## Not completed

- Round 2 `dist_lattice:t6`: stopped during term enumeration (over 10 min). It was at the ceiling in
  round 1.
- Round 3 for the round-1 Huntington configuration: stopped after its first range. Its result
  (EMPTY 9, FIXED 9, ORACLE 9) matches round 3 on t6.
