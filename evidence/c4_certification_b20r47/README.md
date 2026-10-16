# B20_R47 evidence: certification coverage on C4 hosts with the transferred, Lean-checked C4 rows (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no evaluator.
- **Script:** `scripts/b20r47_c4_certification.py`. It was committed before running in `73ecc52`,
  together with the checker (`verification/lp_dual_rows_c4.py`) and the route
  (`discovery/generated_certify_c4.py`). Their SHA-256s were sent to the user beforehand. The code
  identity the summary records (`f8c400ed…`) is that of the setup commit.
- **Registry:** B20_R46's package `7a081e4a…`, 34 CHECKED patterns.
- **Log:** `run.log`.
- **The run was interrupted once.**
  - **What happened.** After 25 of 40 hosts it reached the builder's 30-minute background-task time
    limit and was killed while host 26 was running.
  - **The resume.** The script is resumable by design. It reloaded the 40 saved hosts from
    `hosts.json`, kept the 25 recorded rows, and re-ran host 26 from the start. Nothing else changed.
  - **The exposure count.** The resumed run's exposure scan counts 2,756 identities rather than
    2,716. By then this run's own `hosts.json` was on disk and was scanned as named hosts. The hosts
    were generated and checked against the original 2,716 (first lines of `run.log`).
  - **The second core.** It was busy with other work for the whole run: the B20_R44 checkpoint
    rehearsal, then the diagnostics below. Both routes ran back to back on the pinned core in
    alternating order, so this affects them alike.
- **Files:**
  - `hosts.json`: the 40 hosts;
  - `rows.jsonl`: one row per host;
  - `certificates/`: LP certificates of hosts certified by route b only (there are none);
  - `summary.json`.

## Result (preregistered)

| | a: evaluator (4-cycle LP, then SAT/DRAT) | b: C4 rows route (rows LP, rounding, then SAT/DRAT) |
|---|---|---|
| Certified within the budget | **22/40** | **22/40** |
| … erdos n30 p0.2 (mean 85.9 edges) | 15/20 | 15/20 |
| … erdos n36 p0.17 (mean 108.1 edges) | 7/20 | 7/20 |
| Discordant hosts | 0 | 0 |
| Certified by the LP bound alone | 0 | **10** |
| Mean LP bound | 74.98 | **71.43** |
| Total wall time | 1,583.5 s | 1,494.1 s |

| Test | Result | Passes |
|---|---|---|
| Soundness | every LP certificate VALID; no value disagrees | yes |
| Coverage b ≥ a | 22 = 22 | yes |
| McNemar (one-sided) | no discordant host, p = 1.0 | **no** |
| Wall saving a − b | **+2.24 s per host**, 90% interval [+0.23, +4.74] | yes |

**Verdict: NO_CERTIFICATION_UTILITY.** The rows make certification faster where it already succeeds,
but they do not certify any host the evaluator cannot.

**Secondary diagnostic (preregistered, decides nothing).** On the 22 hosts with a certified optimum:
- the rows closed **80% of the LP gap** on average (75% at n30, 90% at n36);
- the rows' LP bound alone met the optimum on 10 hosts; the 4-cycle LP did on none.

The 60 s budget limits the SAT solver's run, and the DRAT check that follows is not counted in it. So four
hosts overran 60 s wall (66–111 s), under both routes. This is the evaluator's behaviour, and the same
for both routes.

## Diagnostics after the run (not preregistered; disclosed; they change nothing above)

They were run on the hosts left open, to find out why. They all used `hosts.json` and `rows.jsonl`
only, after the corresponding rows were recorded. Scripts are in the builder's scratch space;
B20_R48 commits the route the third one led to.

1. **True optima.** For the 8 open hosts recorded by then, HiGHS's MILP was run over the same rows
   (a float producer, diagnostic only). The seed witness was optimal on 6 of them, and one edge short
   on 2. HiGHS proved its optimum in 0.9–13 s on 7 hosts and in 298 s on one.
   **The open gap is in the upper bound, not the witness.**
2. **Failure-driven rows.** From each open host's LP solution, small vertex sets were searched whose
   induced support subgraph violates its own bound, on up to 8 vertices. A candidate was kept when
   rank-1 rounding (the proof method) can prove it. Over 4 rounds this kept 19 new patterns, and the
   LP bounds moved by at most 0.4. **The remaining gap is global: local rows on a few vertices cannot
   close it.**
3. **Branch and bound over the same rows.** The prototype has exact LP-dual certificates at every
   leaf. At 60 s it certified **10 of the 13 open hosts** recorded by then, and its values agree with
   the MILP optima above. This becomes B20_R48: a tree certificate with an exact checker, and then a
   preregistered study on fresh hosts.

## What it means

This is the first prospective test of a transferred component's utility in the new domain:
- **Procedure:** transferred (B20_R46).
- **The rows:** much stronger than the evaluator's (80% of the LP gap closed), and faster where
  certification succeeds.
- **Coverage:** no gain. The C4 hosts the evaluator cannot certify need branching.

In the roadmap's terms (E5), C4-free and triangle-free are near domains. This is near-domain evidence,
and GV6 still needs a structurally different formal domain (B20R46-OPEN-1).

## Tests

`tests_genesis/test_lp_dual_rows_c4.py` (7):
- the registry is bound to the checked package and its definitions;
- the parser is strict;
- K6's bound is 7 against 11 for the 4-cycle LP;
- every tampering is rejected;
- the route certifies K6 without SAT.

`tests_genesis/test_c4_certification.py` (5):
- the preregistered constants;
- the tally and the gap closure;
- the verdict recomputes from the rows, McNemar and the passes included;
- kept certificates re-check (none here);
- the hosts are fresh and in the exposure addenda.
