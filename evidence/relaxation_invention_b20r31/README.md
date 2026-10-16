# B20_R31 evidence: generated valid inequalities (relaxation family, attempt 1; DEV)

Builder-run. Nothing here is independently reviewed, and it licenses no claim.
- **Script:** `scripts/b20r31_relaxation_invention.py`. It was committed before running in
  `c90f00f`, and its SHA-256 was sent to the user beforehand.
- **Family:** `src/genesis/invention/cuts.py`.
- **Log:** `run.log`, 500 s.

## Design (fixed before running; see the script's docstring)

**Generation.** The generator goes through every graph F on 4–6 vertices in the networkx atlas.
It keeps F when three conditions hold:
- F is connected;
- every edge of F lies in a triangle;
- F's LP under the triangle rows, plus the copies of the patterns kept before it, exceeds ex(F).

**Checking.** Lean checks the bound of every kept pattern before the bound is used.

**Utility (Part B).** The B20_R17 design on the decided `e1b` family:
- SELECT 24 hosts and EVAL 48 hosts, 16 per setting;
- 1.0 CPU s per arm;
- the existing LP component itself as the control.

**Certification diagnostic (Part C).** Run on B20_R30's 90 certified hosts.

## Part A: generation and checking (`part_a.json`, `package.json`)

| Step | Graphs |
|---|---|
| In range | 201 |
| Connected, every edge in a triangle | 40 |
| Implied by the triangle rows | 36 |
| Implied by earlier patterns: K6−e and K6, both by K5 | 2 |
| **Kept** | **2**: K5 (ex 6, triangle LP 20/3) and the 5-wheel W5 (ex 7, LP 15/2) |

**Obligations.** Each was screened by sampling, with no counterexample, then CHECKED by
`checker.accept`:

| Obligation | Statement | Recipe |
|---|---|---|
| `pc_adj_le_one` | 0/1 adjacency is at most 1 | `adj-split` |
| `pc_bridge` | adjacency sums to at most 2 on any vertex triple of a triangle-free edge set in host form | `adjacency-orientation-cases` |
| `pc_pat5_10_…` (K5) | at most 6 | `bridge-instances-omega`: the bridge on each triangle, ≤ 1 on each edge, then `omega` |
| `pc_pat6_10_…` (W5) | at most 7 | `bridge-instances-omega` |

**Construction cost.** 46.7 CPU s (the checker reported 28.1 s). The matched arm therefore gets
1.467 s.

## Part B: utility after cost (`part_b.json`, `part_b_rows.json`, `hosts.json`)

**SELECT.** It chose `cross_2` for the menu (2,169, tied with `adjacent_2` and `adjacent_3`;
ties are broken by name) and `low_cycle_tm` for the conventional arm (2,097).

| new − … | Mean per host | 90% interval | W / T / L | By setting (planted / erdos n26 / erdos n30) | Passes |
|---|---|---|---|---|---|
| control (`lp_greedy`, triangle LP) | +0.19 | [+0.06, +0.31] | 8 / 39 / 1 | +0.13 / +0.25 / +0.19 | no (below 0.5) |
| menu (`cross_2`) | +0.98 | [+0.81, +1.15] | 32 / 16 / 0 | +0.63 / +0.75 / +1.56 | yes |
| conventional (`low_cycle_tm`) | +3.21 | [+2.81, +3.58] | 47 / 1 / 0 | +4.13 / +2.88 / +2.63 | yes |
| matched (control at 1.467 s) | +0.19 | [+0.06, +0.31] | 8 / 39 / 1 | as control | no |

**Verdict: NO_UTILITY_AFTER_COST.**

**Separation.** All copies were found within the budget on every host. Per host, the median was
2.5 K5 copies and 441 W5 copies; the most W5 copies on one host was 6,571.

**The matched arm** scored exactly the control's value on all 48 hosts. Half a second more of
LP-perturbed restarts does not change what `lp_greedy` finds here.

## Part C: certification diagnostic (`part_c.json`, `part_c_rows.json`)

These are float LP values. They are a measurement, not a certificate.

| Setting | Certified hosts | floor(LP) = optimum, triangle rows | … with the generated rows | Newly met | Mean LP − optimum (triangle → generated) |
|---|---|---|---|---|---|
| planted_cluster | 30 | 20 | 26 | 6 | 0.73 → 0.36 |
| erdos n26 p0.35 | 30 | 26 | 28 | 2 | 0.44 → 0.30 |
| erdos n30 p0.3 | 30 | 26 | 28 | 2 | 0.47 → 0.30 |
| **pooled** | 90 | **72** | **82** | **10** | 0.55 → 0.32 |

**Comparison with how the evaluator certified these hosts (B20_R30):**
- The 72 hosts met by the triangle LP are exactly the 72 the evaluator certified with its LP dual.
- Of the 18 that needed SAT with a DRAT proof, the generated rows bring the LP floor down to the
  optimum on 10. Those 10 include two that took the evaluator 126 s and 334 s.
- Building and solving the strengthened LP took a median of 0.06 CPU s, and at most 0.99 s.

## What it means

**Construction.** The generated rows make the LP component's order slightly better (+0.19 per
host, interval above 0), but well short of the 0.5 minimum useful effect. As a construction
component, this is attempt 1 of the relaxation family, NO_UTILITY_AFTER_COST.

**Certification.** The same rows close more than half of the LP's integrality gap where it
matters. On this diagnostic, 10 of the 18 hosts the evaluator had to certify by SAT become
LP-certifiable in principle. Two conditions remain:
- An exact certificate would need the LP dual over the generated rows to be verified in rational
  arithmetic.
- The rows' validity would rest on the Lean lemmas above.

That route is not built yet. It is the natural next step (B20_R32). It would be the first
machine-generated component with a measured benefit, but in certification, not construction.

The 72 study hosts are in `hosts.json`, and the six development-look hosts are in
`development_look_hosts.json`. The handoff exposure addenda list all 78
(`handoff/e1*/exposure_hosts_addendum_b20r31.json`).
