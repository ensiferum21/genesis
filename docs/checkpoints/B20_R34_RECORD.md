# B20_R34 record: probe for MIP-hard, certifiable triangle-free settings (B20R33-OPEN-1)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No rule or package was changed.
- **Commits:**
  - `0aeea98` (setup): the script, committed before the run; its SHA-256 was sent to the user
    beforehand.
  - The record-repair script, committed before it ran.
  - The result commit.
- **Evidence:** `evidence/mip_hard_probe_b20r34/`.

## Why

B20_R33 found that, on the decided family, an exact MIP solver is always optimal, so no candidate
can be "beyond strong baselines" there. One option for the reviewer is a harder family. This probe
asks whether any triangle-free setting inside the family space (n ≤ 40) and the 200-edge
certification bound meets three conditions:
- the solver fails within 2 s;
- the evaluator certifies within 60 s;
- the baselines leave headroom.

## Result

Seven settings, 8 hosts each: **NO_MIP_HARD_CERTIFIABLE_SETTING**.
- **erdos n40 p0.23** is the only setting the evaluator certifies fully. There the MIP proves every
  optimum in under 0.16 CPU s.
- **Five settings** (erdos n30/n34/n37, planted n36/n40 at 0.6): the MIP proved optimality on
  38 of 40 hosts within 2 s, while the evaluator's 60 s certification failed on 3–6 of 8 per
  setting. The evaluator is the bottleneck there.
- **planted n40 (0.8, 0.06)**: the MIP proves nothing in 2 s, and the evaluator certifies nothing in
  60 s.

**Exploratory, not preregistered.** In that last setting, the frozen E1b candidate beat the MIP's
2 s incumbent on 7 of 8 hosts (mean +6.4 edges, checker-validated, no certified optimum).

## What it means

Within the domain's certifiable range, an exact solver is at least as strong as the evaluator's
certification. Wherever the evaluator can certify, the MIP is optimal. The only regime seen where
an LP-guided method beats the exact solver at matched budget is one the evaluator cannot certify.

For GV3 on this domain, the options left for the reviewer are:
1. accept the DSL-baseline scope;
2. build a stronger certification route and calibrate a dense regime under a new versioned rule.
   The route would be branch-and-bound certificates whose leaves are exact LP duals. That
   generalises B20_R32's checker and is engineering possible here;
3. change the analysis plan so that it does not need certified optima;
4. move GV3 to another domain.

## Record repair (B20R34-OPEN-1, found and repaired in this record)

**The defect.** A container restart stopped the run after 48 hosts. On resume, the script
regenerated its hosts while excluding its own first `hosts.json`. The last 8 rows therefore ran on
graphs from a new draw, under the old ids, and `hosts.json` was overwritten.

**The repair.** `scripts/b20r34_record_repair.py`:
- reconstructed the first-run hosts deterministically, from the 1,988 logged exclusions;
- matched all 56 rows to their graphs, by id, n and edge count, with no cross-matches;
- rewrote `hosts.json` as the graphs actually run;
- kept the overwritten listing.

The rows and the verdict are unchanged.

The B20_R30, B20_R32 and B20_R33 scripts share the latent defect, but were not resumed. Future
resumable scripts must load their own `hosts.json` on resume.

## Tests

`tests_genesis/test_mip_hard_probe.py` (5) checks:
- the settings and arms are the preregistered ones;
- the classification and verdict follow from the rows;
- no arm exceeds a certified optimum, and hosts over 200 edges are uncertified;
- the record repair matches every row;
- the hosts are in the addenda.

## Open

- B20R33-OPEN-1, updated with this map.
- B20R34-OPEN-1: the resume defect in the R30–R34 scripts; R34's record is repaired.
