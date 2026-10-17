# B20_R65: why rehearsal hosts were unsupported (statistician's brief, finding 5)

- **Script:** `scripts/b20r65_unsupported_hosts.py`.
- **Inputs:** each rehearsal's own evidence file, the one that carries the CONFIRM hosts the custodian drew.
- **What it is:** a diagnosis of committed evidence. Nothing is re-run, and nothing is adopted.

## Result

| Rehearsal | CONFIRM hosts | Unsupported | Reason |
|---|---|---|---|
| E1 (B20_R24) | 30 | 0 | — |
| E1b (B20_R24) | 30 | 1 (166 edges) | REFERENCE_LIMIT: within the bound, not certified in time |
| E1b-C4 (B20_R52) | 20 | 0 | — |
| E1d (B20_R43) | 240 | 3 (204, 202, 202 edges), all in planted_cluster:9491bde8 | SIZE_BOUND |
| E1d ablation (B20_R45) | 45 | 1 (202 edges), in planted_cluster:9491bde8 | SIZE_BOUND |

**The size bound explains every E1d exclusion.** Every CONFIRM host above 200 edges was unsupported, and every
unsupported E1d host is above 200 edges. The custody path refuses a certified reference for such a host before any
search (`GraphHostAdapter.CERTIFICATE_MAX_EDGES`, `supports(task, 'exact_reference')`).

**A trap avoided.** Task ids are not unique across panels. B20_R43's development look reused
`confirm-planted_cluster-9491bde8-20272220-0000` for a 190-edge host; the CONFIRM host with that id has 204 edges.
The script reads each rehearsal's own hosts.

## Reading

- **The mechanism.** E1d's exclusion is a host-size cut that depends only on the host and is applied before either
  arm runs. It is not a reference failure that could track the outcome.
- **Its cost.** It removes the largest hosts of the densest setting, where the candidate's lead is largest, so on
  E1d it works against the candidate.
- **The cleaner fix,** for the statistician and reviewer: state the cut as a panel eligibility rule, or lift the
  bound for the exact LP-dual route.
- **E1b's single exclusion** is a reference limit, too rare to assess.

## Tests

`tests_genesis/test_unsupported_hosts.py` (3).
