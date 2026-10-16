# B20_R34 evidence: probe for MIP-hard, certifiable triangle-free settings (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no rule or
package.
- **Script:** `scripts/b20r34_mip_hard_probe.py`. It was committed before running in `0aeea98`,
  and its SHA-256 was sent to the user beforehand.
- **Logs:** `run.log`. A container restart stopped the first run after 48 of 56 hosts, and the
  run was resumed: the second "pinned to CPU 0" line marks the resume. See the record repair below.

## Why

This is B20R33-OPEN-1, option 3. On the decided `e1b` family an exact MIP solver is always optimal
within 0.36 CPU s. Are there triangle-free settings inside the domain's family space (n ≤ 40) and
the evaluator's 200-edge certification bound where:
- the exact solver fails within the candidate's 2 s;
- the evaluator certifies within its 60 s limit;
- the DSL baselines leave headroom?

## Design (fixed before running)

**Settings.** Seven settings at 160–195 expected edges, 8 fresh DEV hosts each, all on one
pinned core:
- erdos n30 p0.42, n34 p0.33, n37 p0.27, n40 p0.23;
- planted_cluster n36 (0.6, 0.15), n40 (0.6, 0.12), n40 (0.8, 0.06).

**Per host:**
- an exact MIP at 2.0 s;
- the frozen E1b candidate and its three baselines, in runc;
- the joint reference at 60 s.

**Classification.** A setting is MIP_HARD_CERTIFIABLE iff all three hold:
- certified ≥ 0.9;
- MIP suboptimal on ≥ 25% of the certified hosts;
- baseline headroom ≥ 0.5.

## Result (`summary.json`, `rows.jsonl`, `hosts.json`)

| Setting | Mean edges | Certified ≤ 60 s | MIP proved optimal (2 s) | MIP below the optimum (certified hosts) | Mean gap to optimum, candidate | Mean gap to optimum, best baseline |
|---|---|---|---|---|---|---|
| erdos n30 p0.42 | 183 | **2/8** | 6/8 | 0 | 3.0 | 8.5 |
| erdos n34 p0.33 | 183 | 5/8 | 8/8 | 0 | 0.0 | 4.2 |
| erdos n37 p0.27 | 183 | 5/8 | 8/8 | 0 | 0.0 | 2.6 |
| erdos n40 p0.23 | 173 | **8/8** | 8/8 | 0 | 0.13 | 1.75 |
| planted n36 (0.6, 0.15) | 163 | 4/8 | 8/8 | 0 | 0.5 | 7.25 |
| planted n40 (0.6, 0.12) | 182 | 5/8 | 8/8 | 0 | 0.0 | 6.8 |
| planted n40 (0.8, 0.06) | 188 | **0/8** | **0/8** | — | — | — |

Three hosts exceeded 200 edges and have no reference.

**Verdict: NO_MIP_HARD_CERTIFIABLE_SETTING.** The two conditions pull against each other:
- Where the evaluator certifies at least 90% (erdos n40 p0.23), the MIP proves every optimum in
  under 0.16 CPU s.
- In five settings, the MIP proves optimality within 2 s on 38 of 40 hosts, yet the evaluator's
  60 s LP/SAT certification fails on 3 to 6 of each setting's 8. There, the evaluator, not the
  solver, is the bottleneck.
- Where the MIP fails (planted n40, 0.8/0.06: no proof on any host), the evaluator certifies
  nothing either. Its reference gap there is 8–11 edges at 60 s.

## Exploratory observation (not preregistered; not a test)

In the setting where the MIP never finished (planted n40, 0.8/0.06), the frozen E1b candidate's
2 s witness beat the MIP's 2 s incumbent on 7 of 8 hosts:
- candidate − MIP per host: −3, +2, +10, +8, +5, +13, +4, +12 (mean +6.4);
- candidate − best DSL baseline: mean +3.1.

These are checker-validated values on 8 hosts, with no certified optimum. A dense planted cluster
may therefore be a regime where an LP-guided method beats an exact solver at matched budget. But
the evaluator cannot certify there, and E1's analysis plan needs certified references (at most 5%
unsupported). Using such a regime would need one of:
- a stronger certification route, for example branch-and-bound certificates whose leaves are
  exact LP duals, possibly over generated rows;
- or a plan whose endpoint does not need certified optima.

Both are decisions for the reviewer. Any such regime would need its own preregistered calibration.

## Record repair (`record_repair.json`, `hosts_regenerated_on_resume.json`)

**The defect.** On resume, the script regenerated its hosts with the exposure exclusions. By
then, its own first `hosts.json` counted as a named host file, so the resumed run drew a new set
of 56 graphs with the same task ids. Then:
- the 48 completed rows were skipped by id;
- the last 8 rows (setting 7) ran on graphs of the new set;
- `hosts.json` was overwritten with the new set.

**The repair.** `scripts/b20r34_record_repair.py` was committed before it ran. It:
1. reconstructs the first-run hosts deterministically, from the 1,988 exclusions the first run
   logged;
2. checks every row against its graph by id, n and edge count: 48/48 first-run matches and 8/8
   new-set matches, with no cross-matches;
3. writes `hosts.json` as the 56 graphs actually run;
4. keeps the overwritten listing as `hosts_regenerated_on_resume.json`. Of its 56 graphs, 48 were
   never run.

The rows are unchanged, and the recomputed summary equals the original.

**Defect status.** The same latent resume defect is in the B20_R30, B20_R32 and B20_R33 scripts.
None of those runs was resumed. It is recorded as B20R34-OPEN-1.

Both listings are named here, and the handoff exposure addenda list all 104 graphs
(`handoff/e1*/exposure_hosts_addendum_b20r34.json`).
