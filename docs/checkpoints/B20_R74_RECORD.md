# B20_R74 record: state-of-the-art baselines: MQLib's BURER2002 built and pinned; CP-SAT and MaxSAT blocked

- **Run by:** the builder. Engineering only; no study, claim, rule, comparator or package change.
- **Why:** Daniel asked (19 Oct 2026) to compete with the most advanced tools. A speed or quality claim needs the best
  *known* methods (Rønnow et al. 2014; Dunning et al. 2018).

## What was built

- **`mqlib-v1`** (`candidate_kinds/mqlib.py`): MQLib's BURER2002 (the rank-two relaxation heuristic of Burer,
  Monteiro and Zhang, 2002), the best single heuristic in Dunning, Gupta and Silberholz's comparison of 37 max-cut
  and QUBO heuristics on 3,296 instances (it matched the best result on 22.9% of instances). The child passes the
  host to MQLib through a pipe (the child may not write files), reads the best cut, and completes it exactly as the
  other max-cut kinds do. Parameters `{heuristic, cpu_seconds}`, heuristic in (BURER2002,).
- **The binary**, built by `scripts/b20r74_sota_tools.py` from MQLib at commit `5854962` (GitHub), compiled from
  outside its source tree with a fixed command (relative paths and a file-prefix map, so no build path is embedded),
  installed at `/usr/local/genesis-sota/bin/MQLib`: inside `/usr`, which the runc sandbox bind-mounts read-only, and
  outside every Python path and the locked environment. SHA-256 `9e760cb7…c4e3`, pinned in the kind (so in its
  identity); the kind refuses to build or run a descriptor against any other binary. A first build embedded its
  build directory and was not reproducible; with the fix, two clean builds give the same binary.

## Blocked: CP-SAT and MaxSAT

Google OR-Tools CP-SAT (gold in the fixed, free and parallel categories of the MiniZinc Challenge 2025) and the
MaxSAT solver RC2 (PySAT) come from PyPI. This workspace could not reach PyPI on 19 Oct 2026: direct connections do
not resolve, and the egress proxy refused pypi.org with 403. Policy denials are not retried or routed around. A
`cpsat-v1` kind is drafted (pinned-tree design, the same as MQLib's) and kept off the registry; it can be added if
the wheels are supplied. B20R74-OPEN-1 records this. Commercial tools (Gurobi, Toshiba's SQBM+) need licences and are
out of reach.

## Development look, disclosed

BURER2002 in process at 0.1 and 0.5 s on the first three B20_R66 hosts: 261, 279, 266 (certified or reference
values 264, [279, 280], 267; dSB in B20_R69's look 264, 280, 267). It optimizes the cut and returns one best cut,
which the completion then repairs.

## Tests

`tests_genesis/test_mqlib_kind.py` (6): the installed binary is the pinned one and the kind's identity includes the
pin; a changed or missing binary is refused; closed parameters; parsing of MQLib's output; K10 gives 25 with a checked
witness; a metered runc run returns a checked witness.
