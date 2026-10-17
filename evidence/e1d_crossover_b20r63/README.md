# B20_R63 evidence: how much CPU HiGHS needs to match E1d's 0.5 s candidate (DEV): **CROSSOVER_AT_8S**

Builder-run on DEV. Nothing here is independently reviewed, and it licenses nothing.
- **Script:** `scripts/b20r63_e1d_crossover.py`. It was committed before the run in `fca3c47`, with its design,
  verdict rule and expectation. SHA-256 `b9d49322…30cb`.
- **Log:** `run.log`, 1,227 s on one pinned core.
- **Development looks:** none.

## Design (fixed before running)

**Hosts.** 30 fresh DEV hosts, 10 in each E1d setting, which the B20_R43 calibration record selects:
| Stratum | Setting |
|---|---|
| `2269386b` | planted_cluster n38 (0.8, 0.07) |
| `9491bde8` | planted_cluster n40 (0.8, 0.06) |
| `6493e4fc` | planted_cluster n40 (0.7, 0.06) |

They exclude 2,957 exposure identities, which covers every host of B20_R41 and R43–R45.

**Arms.** All arms ran in runc:
- E1's frozen candidate, with 0.5 CPU s of search;
- HiGHS (`milp-highs-v1`, one core) at 2, 4, 8, 16 and 32 s, that is 4×–64× the candidate's budget. The 2 s arm
  is the E1d package's `milp_highs_4x` descriptor itself.

**Rule.** Per budget, the estimate is the mean of the stratum means of candidate − HiGHS, with a stratified
bootstrap 90% interval.
- **ADVANTAGE:** the lower end is above 0.5, the minimum useful effect.
- **Crossover budget:** the first budget without ADVANTAGE.

## Result: **CROSSOVER_AT_8S**

All 30 optima were certified, and no run failed.

| HiGHS budget (× candidate) | Candidate − HiGHS, 90% interval | W/T/L | HiGHS optimal | HiGHS CPU, median | Verdict |
|---|---|---|---|---|---|
| 2 s (4×) | **+10.30** [8.77, 11.83] | 23/7/0 | 7/30 | 2.20 s | ADVANTAGE |
| 4 s (8×) | **+6.37** [4.73, 8.00] | 20/10/0 | 10/30 | 4.16 s | ADVANTAGE |
| 8 s (16×) | +0.43 [0.03, 0.90] | 4/25/1 | 26/30 | 6.15 s | UNRESOLVED |
| 16 s (32×) | −0.03 [−0.10, 0.00] | 0/29/1 | 30/30 | 5.97 s | NO_MATERIAL_DIFFERENCE |
| 32 s (64×) | −0.03 [−0.10, 0.00] | 0/29/1 | 30/30 | 6.36 s | NO_MATERIAL_DIFFERENCE |

**The candidate** was optimal on 29 of 30 hosts, one edge short on the other.

**The HiGHS arms** never got worse as the budget rose. The reference certified each optimum in a median 13.9 s of
wall time.

## Reading

**The 4× result replicates.** This is the third fresh sample: +10.3 here, after +10.6 in B20_R41 and +9.80 in the
B20_R43 rehearsal.

**The advantage is speed, and it ends between 8× and 16×.** With enough time, HiGHS solves these hosts exactly:
- it proved the optimum on all 30 hosts at 16 s;
- its whole sandboxed run took about 6 CPU s per host (median).

The 0.5 s candidate reaches the same answers about ten times sooner.

**This corrects a builder reading.** The builder had read HiGHS's weakness as a relaxation problem ("a weak
relaxation on dense hosts", GV4 fallback draft). That reading was wrong: HiGHS is slow here, not unable.

**The stated expectation was wrong too.** The builder expected ADVANTAGE at least through 8 s (16×). At 8 s the
estimate is +0.43, with an interval reaching above 0.5 but not entirely above it.

**What it means for the claim.** E1d's claim ("beats HiGHS at 4× its budget") stands as stated, and it now has a
known edge. A reviewer choosing the comparator budget (B20R41-OPEN-1) should know:
- at 16× or more the candidate ties an exact MILP;
- an exact method (HiGHS, about 6 s; the generated-rows reference, about 14 s) solves every host.

The honest form of the claim is a speed advantage of about an order of magnitude at equal answers, not a quality
advantage at any budget.

## Tests

`tests_genesis/test_e1d_crossover.py`.
- **Design (4):** fresh seeds, the arms, the budget profiles and the rule.
- **Record (2):** the verdict recomputes from the rows, and the hosts are the script's.
