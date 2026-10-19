# B20_R76 record (part 1, engineering): the BURER2002 kind fixed; CP-SAT installed from the supplied wheel

- **Run by:** the builder. Engineering for B20_R76's study; no claim, rule, comparator or package change.

## `mqlib-v1` fixed

B20_R75 found every BURER2002 run empty: MQLib accepts seeds 0..65535 only, the kind passed seeds modulo 2^31, MQLib
exited with a usage error, and the kind returned an empty witness instead of failing. Now the seed is taken modulo
65,536 and any MQLib failure raises, so the run is a failure (counted by a study's failure check) and never an empty
answer. A test uses a study-sized seed and checks that a failing binary fails the run.

## `cpsat-v1`: Google OR-Tools CP-SAT

- **Source:** the official wheel `ortools-9.15.6755-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`,
  supplied by Daniel from pypi.org (PyPI itself is refused to this workspace, B20R74-OPEN-1), SHA-256
  `ebd5aea0…3c9a`. Two earlier uploads were the `cp314t` (Python 3.14 free-threaded) wheel and the macOS Java natives,
  neither usable here; their metadata was read, nothing was run.
- **Install:** `scripts/b20r74_sota_tools.py --ortools-wheel PATH` checks the wheel's hash, unpacks it without
  dependencies into `/usr/local/genesis-sota/py313` (inside `/usr`, so the sandbox sees it; outside every Python path,
  so the locked environment does not), and checks the tree digest `fb5ef9ac…67f9`, pinned in the kind. A reinstall
  gives the same digest. The environment lock check passes unchanged.
- **Dependencies:** OR-Tools 9.15 declares protobuf >= 6.33.1, < 6.34; it runs here with the system's protobuf 7.36.1
  (model building and solving tested); numpy, pandas, absl-py and typing-extensions are present in accepted versions;
  immutabledict is not needed for CP-SAT. The mismatch is recorded in the kind.
- **Configuration:** CP-SAT runs its portfolio of 8 search workers on the child's single pinned core, so its CPU
  equals its budget like the other arms.

## Development looks, disclosed (B20_R66 hosts only)

- CP-SAT, one worker, in process, 0.1 / 0.5 / 2 s on three hosts: 215/216/223, 223/223/227, 200/201/203 (optima or
  bounds 264, [279, 280], 267).
- One against eight workers on one core, 0.5 and 2 s, two hosts: 216/220 → 223/245 and 223/233 → 227/266. Eight
  workers were chosen because that is how CP-SAT is designed to run; the comparison makes the baseline stronger.
- The fixed BURER2002 at 0.5 s with a study-sized seed on three hosts: 261, 279, 265.

## Tests

`tests_genesis/test_cpsat_kind.py` (6): the installed tree is the pinned one; a changed or missing tree is refused;
the locked environment does not import it; closed parameters; known optima; a metered runc run with a checked witness.
`tests_genesis/test_mqlib_kind.py` (7): adds the study-sized seed and loud-failure test.
