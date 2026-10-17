# B20_R65 record: why rehearsal hosts were unsupported (statistician's brief, finding 5)

- **Built by:** the builder. A diagnosis of committed evidence; nothing re-run, nothing adopted.
- **Files:**
  - `scripts/b20r65_unsupported_hosts.py`;
  - `evidence/unsupported_hosts_b20r65/`;
  - `tests_genesis/test_unsupported_hosts.py`.

## Problem

The registered analysis excludes CONFIRM hosts the reference cannot certify. The brief noted that E1d's exclusions
cluster in one stratum. If the reason correlates with the outcome, exclusion biases the estimate.

## Result

**Every E1d exclusion is the 200-edge certificate bound.** Each excluded host is above the bound, and each host
above the bound was excluded:
- B20_R43: three hosts, of 204, 202 and 202 edges;
- B20_R45: one host, of 202 edges.

All four are in planted_cluster:9491bde8. The custody path refuses a certified reference for such a host before any
search. So the exclusion is a host-size cut, blind to both arms, and on E1d it removes the hosts where the
candidate's lead is largest.

**E1b's single exclusion** (B20_R24) is a 166-edge host the reference did not certify in time.

## A trap avoided

Task ids are not unique across panels. B20_R43's development look reused a CONFIRM task id for a different,
190-edge host. The script reads each rehearsal's own CONFIRM hosts.

## Consequence

The brief's finding 5 is updated with the mechanism and two cleaner fixes:
- state the cut as a panel eligibility rule;
- or lift the bound for the exact LP-dual route.

## Tests

`tests_genesis/test_unsupported_hosts.py` (3).
