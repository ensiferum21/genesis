# B20_R70 evidence: time-to-solution scaling of E1d's candidate against three domain heuristics: **E1D_SLOWER_THAN_SOME**

Builder-run on DEV. It licenses nothing, and no package, rule or comparator changes.
- **Script:** `scripts/b20r70_tts_scaling.py`, committed with its design, rule and expectation before any run
  (`e48c5e7`; SHA-256 `ba258a47…6a62`, sent to Daniel before the run).
- **Run:** alone on the machine, pinned to CPU 0, 3,424 s; 2,688 solver runs, all in runc, none failed.
  `code_identity` `9a4c5dba…066a`.
- **Development looks:** one, disclosed in the B20_R69 record (three B20_R66 hosts).

## Question

E1d's evidence fixes the candidate's budget at 0.5 s at every size. Rønnow et al. (Science 2014) showed that speed
must be compared by time-to-solution at the *optimal* run time for each size and instance, read at quantiles of
hardness. Measured that way, how does the candidate compare with tabu search and the two physics-inspired kinds,
and how does its time grow with host size?

## Design (fixed before running)

- **Hosts:** 8 fresh planted (0.8, 0.06) hosts at each of n40, n50, n60 (176–198, 276–312 and 404–444 edges),
  excluding all 3,087 hosts named in the evidence.
- **Arms**, in runc under E1's profile, at every rung of the ladder 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2 CPU s, 4 seeds
  each: the candidate (its frozen kind and parameters; at 0.5 s exactly the package's descriptor), `maxcut-tabu-v1`,
  `ising-dsb-v1`, `maxcut-eo-v1`.
- **Target:** the generated-rows reference's certified optimum (20 of 24 hosts), else the best known value (4 hosts,
  flagged); no run exceeded its target.
- **TTS99** = t · ⌈ln 0.01 / ln(1 − s)⌉ at each rung; TTS* the minimum over the ladder.
- **Primary:** per size and heuristic, the median over hosts of log2(TTS*_heuristic / TTS*_candidate) with a
  bootstrap 90% interval; 2× margins (CANDIDATE_FASTER above +1, HEURISTIC_FASTER below −1).

## Result

**Validity.** Median cgroup CPU at t = 0.5 s: candidate 0.682, tabu 0.676, dSB 0.696, EO 0.682 s. No failures.

**Median log2(TTS*_heuristic / TTS*_candidate)** (negative: the heuristic is faster; −3.32 is 10×):

| | n40 | n50 | n60 |
|---|---|---|---|
| tabu | **−2.06 [−3.32, −1.16] HEURISTIC_FASTER** | **−3.32 [−4.64, −2.98] HEURISTIC_FASTER** | −3.32 [−4.89, +0.24] UNRESOLVED |
| dSB | −0.74 [−1.38, +1.00] UNRESOLVED | **−2.32 [−2.32, −1.66] HEURISTIC_FASTER** | **−3.20 [−4.59, −2.56] HEURISTIC_FASTER** |
| EO | −0.94 [−1.40, +0.34] UNRESOLVED | −1.82 [−3.32, −0.66] UNRESOLVED | −1.32 [−4.23, +1.90] UNRESOLVED |

**Overall verdict (n60): E1D_SLOWER_THAN_SOME**, as the builder expected.

**TTS\*, median (nearest rank) and 75th percentile, in CPU s:**

| | n40 | n50 | n60 |
|---|---|---|---|
| candidate | 0.14 / 0.2 | 0.5 / 0.5 | 0.85 / 3.4 |
| tabu | 0.02 / 0.02 (6 floors) | 0.02 / 0.05 (4 floors) | 0.02 / 0.34 (4 floors; 1 host unsolved) |
| dSB | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| EO | 0.05 / 0.08 | 0.05 / 0.2 | 0.2 / 3.4 (1 host unsolved) |

**Scaling** (slope of log10 median TTS* per vertex): candidate 0.039 (its median time grows about 2.5× per 10
vertices), EO 0.030, tabu and dSB 0.0 (flat: their medians sit at their smallest effective run time).

## Reading

**Measured properly, the candidate is the slowest of the four methods, and the gap grows with size.** At n50 and
n60 tabu search and simulated bifurcation reach the best known value about 10 times faster in median, and the
candidate's median and upper-quartile times grow with n while theirs stay flat. This is a scaling statement in
Rønnow et al.'s sense, and it is the opposite of a speed advantage: against the best-known class of methods,
E1d's representation-and-repair candidate is not fast.

**No heuristic dominates on every host.** Tabu search, the fastest in median at n60, needed 7 s on one host and
never reached the target on another, which is why its n60 interval crosses zero; simulated bifurcation needed at most
0.5 s on every host. This matches Dunning et al.'s finding that no max-cut heuristic is best everywhere.

**Two biases, both against the heuristics, disclosed.**
- *Floors.* Tabu search is at the ladder's first rung (0.02 s) on 4–6 hosts per size, so its TTS* there is an upper
  bound: its true advantage is at least what is shown.
- *dSB's start-up.* `ising-dsb-v1` imports numpy inside its own budget (about 0.11 s of CPU in a fresh interpreter
  here, measured after the run). It reached the target in 1 of 96 runs at 0.02 s and 2 of 96 at 0.05 s, against
  90 of 96 at 0.1 s, so its TTS* of 0.1 s is mostly start-up, not search. Its advantage is also understated.
Neither bias can make the heuristics look faster than they are.

**What this changes.** E1d's claim about HiGHS (B20_R41–R66) stands as measured. But a speed claim also needs the
best-known methods (Rønnow et al.'s "potential" versus actual speedup). Against them the candidate is slower,
with a worse scaling slope. Together with B20_R68 this settles the strong-baseline question for E1d as far as DEV
evidence can: if domain heuristics count, E1d has no GV3 claim. What the system did achieve is to rediscover the
max-cut reduction on its own; what it lacks is a competitive search, which is where B20_R71–R72 go next.

## Tests

`tests_genesis/test_tts_scaling.py`.
- **Design (7):** fresh seeds; the arms and their shared profile (the 0.5 s candidate is the frozen descriptor);
  TTS99; the optimal-run-time rule and floors; log ratios and verdicts; the analysis and overall rule on synthetic
  rows, including validity; pinning.
- **Record (3):** the analysis, slopes, validity and verdict recompute from `rows.jsonl`; every run is as designed
  (rungs, repetitions, runc, never above its target) and the descriptors are the recorded ones; the 24 hosts are
  distinct, match the rows and are in the e1/e1b exposure addenda (`exposure_hosts_addendum_b20r70.json`).
