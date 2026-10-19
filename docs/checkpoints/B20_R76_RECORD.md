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

# B20_R76 record (part 2, the study): against CP-SAT and BURER2002, **UNRESOLVED**

- **Run by:** the builder. DEV only.
- **Setup:** `1b01159`; script SHA-256 `39509fd3…bdf0`, sent before the run. Alone, pinned to CPU 0, 3,306 s.
  `code_identity` of the run equals the committed tree's.
- **Evidence:** `evidence/sota_b20r76/` (README with the tables).

## Result: **UNRESOLVED**

Valid (CPU delivered by every arm, no failed run). At n63 the system's engine is UNRESOLVED against both tools
(vs BURER2002: 0.0 [−0.5, 10.0]; vs CP-SAT anytime: 10.0 [0.0, 10.0], in log2 units, positive = the system faster).
Of all n63 pairs only simulated bifurcation is resolved: X_FASTER than CP-SAT, 10.0 [5.0, 10.0]. At n60 the
system, the candidate and simulated bifurcation are X_FASTER than CP-SAT; nothing is resolved against BURER2002 at
either size. An independent recomputation from the rows (no study code) gives the same ratios, intervals and
verdicts, and 20 other bootstrap seeds give the same verdict for every pair.

**Why.** Six hosts per size, with capped ratios: hosts where neither method reaches the target within 2 s tie at 0,
hosts where one does count ±10. BURER2002 is fastest where it succeeds (0.05 s on three hosts) but reaches the
target on only 5 of 12, so its comparisons swing both ways.

**Descriptive.** Hosts (of 12) where the target was reached within 2 s: simulated bifurcation 11, the system's
engine 10, the frozen candidate 9, tabu 7, BURER2002 5, CP-SAT anytime 0, HiGHS anytime 0. With 60 s, CP-SAT reached
2 targets and HiGHS none, neither claimed optimality anywhere, and on the 490-edge n63 host CP-SAT found the certified
optimum 315, which no heuristic found within 2 s. The system's checked route certified 10 of 12 targets (median 34 s).

**Against the expectation.** The builder expected SYSTEM_BEATS_SOTA, and said so provisionally to Daniel during the
run after the first n63 hosts. Both were wrong; the preregistered verdict stands.

## Consequence

- No claim may say the system or E1d beats the state of the art. What can be said descriptively: at budgets up to
  2 CPU s on these hosts, the max-cut heuristics (simulated bifurcation and the system's engine most often) reach the
  best known value where CP-SAT and HiGHS run anytime do not; BURER2002 is the fastest when it succeeds; CP-SAT, given
  60 s, finds what the heuristics miss on the hardest host.
- B20R74-OPEN-1 stays PARTLY RESOLVED (CP-SAT in; MaxSAT missing).
- A natural next batch: the same comparison powered (more n63 hosts, fixed beforehand), since six per size cannot
  separate methods that each fail on some hosts.

## Tests

`tests_genesis/test_sota_v2.py`: Design (5); Record (5).
