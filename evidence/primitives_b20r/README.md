# W22: comparison of the starting derived primitives (DEV design diagnostic)

- **Script:** `scripts/b20r_primitives.py`, committed before it ran. The rule (`primitives.VERDICT_RULE`) was committed with the module.
- **Primitives:** builder-written, all four with native implementations.
- **Hosts:**
  - conformance on every graph on 4 vertices (64) plus 28 DEV hosts (seed 2026101301);
  - comparison on 28 fresh DEV hosts (seed 2026101302) from the same seven families.
- **CPU timings:** this host's.

| Primitive | Conformance | Verdict | Why |
|---|---|---|---|
| EdgeCount | CONFORMANT | NOT_A_CAPABILITY_GAIN | native + conformance 117 ms vs 132 ms expanded: less than a 2x saving |
| TriangleCount | CONFORMANT | NOT_A_CAPABILITY_GAIN | 166 ms vs 190 ms |
| SumDegreeSquares | CONFORMANT | NOT_A_CAPABILITY_GAIN | 91 ms vs 80 ms: the native one costs more once its conformance run is charged |
| PairCodegreeFalling2 | CONFORMANT where expandable | REJECTED | on 20 of 28 fresh hosts the expansion exceeds the 256-node language cap, so the native one would answer where the trusted language cannot |

**Reading.** Each primitive agrees with its reference expansion wherever that expansion can be evaluated. Agreement is tested, not proved. Under the rule fixed beforehand, none of them is a capability gain:
- **Three are renamed macros.** EdgeCount, TriangleCount and SumDegreeSquares give a shorter description at about the same cost, once their verification cost is charged against this workload.
- **One overreaches.** PairCodegreeFalling2 is an operation the trusted language cannot express at the sizes where it would matter.

A larger intended workload could change the first three verdicts. That would be a new comparison with its own preregistered workload, not a reinterpretation of this one.

**Not exercised.** Proposal by mining DEV traces: no DEV trace corpus of MRDL expressions exists yet. `primitives.mine` is tested on a fixture only.

**Claim ceiling.** This is a DEV diagnostic of the representation language's evolution machinery. It is not a research result, and nothing here licenses a claim.
