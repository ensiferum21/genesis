# B20_R43 record: the E1d DRAFT package, and a same-operator rehearsal through the v5 path (SUPPORTED, judge agrees)

- **Run by:** the builder, on DEV, with fixture keys. The DRAFT rule was adopted only in a throwaway
  copy. Nothing is registered or adopted, and nothing licenses a claim.
- **Commits:**
  - `ab11467` (setup): the script, committed before the run. Its SHA-256 was sent to the user
    beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/e1d_package_b20r43/`.
- **Package:** `handoff/e1d/`.

## Why

B20_R41 found E1d READY_FOR_REVIEW, and B20_R42 wired the opt-in path a custodian would need. Before
a reviewer decides, the whole custody path should run once on this family with fixture keys, as
B20_R24 did for E1 and E1b. The reviewer also needs the package itself.

## Result

| Item | Result |
|---|---|
| Comparator chosen by the custodian's SELECT | **HiGHS at four times the candidate's budget** |
| CONFIRM panel | 240 hosts: 237 certified by the generated-rows LP, 3 unsupported (1.25%) |
| Wins / losses / ties | **198 / 0 / 39** |
| Estimate | **+9.80 per host** [9.30, 10.35] |
| Cost ratio | 0.338 |
| Outcome | **SUPPORTED** |
| `judge.recompute` | agrees: 474 witnesses re-checked, fairness clean |

**The package** has:
- an evidence card in five dimensions;
- the candidate, which is E1's frozen descriptor, unchanged;
- the five baselines, two of them registry v2;
- the reference route, a campaign export and the DRAFT decision record (no problems when frozen);
- the B20_R41 re-pilot and power analysis, and the rehearsal summary;
- 2,641 exposure hosts in six files.

## What it means

**GV3.** E1d is now at the same stage E1 and E1b reached in B20_R24: READY_FOR_REVIEW, with a SUPPORTED
same-operator rehearsal and the judge agreeing. The difference is that E1d's comparator is an exact
solver given four times the CPU. That makes it the first package in which "beyond strong baselines"
is the claim actually being tested.

**What is still missing:**
- a causal control for the discovered representation (B20_R44);
- the reviewer's decisions (B20R41-OPEN-1);
- a statistician;
- an independent custodian.

## Tests

`tests_genesis/test_e1d_package.py` (8).

**Design checks:**
- the record is B20_R41's Part A under the draft rule;
- no study in the repository adopts it;
- the arms and the reference route;
- the DRAFT decision record has no structural problems.

**Record checks:**
- the record on disk equals the derived record;
- the rehearsal went through v5: route, comparator, rows, judge, log, reference methods;
- the package files match the index, and each exposure file holds at most 500 hosts;
- the rehearsal hosts are in the package's exposure files and in the addenda.

## Open

B20R41-OPEN-1 is updated: the package and the rehearsal now exist.
