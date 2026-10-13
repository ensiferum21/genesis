# B20_R5 record: H05, executable candidates through the custodian (B19-OPEN-3, B20R-OPEN-4)

- **Parent:** B20_R4 (commit `f5c853d`). This batch is commit `d8052df`.
- **Run by:** the builder, on DEV material, using fixture keys. No part of this batch has been independently reviewed.

## Problem

The custodian validated every arm as a `SolverProgram`, the fixed DSL. B19's represent-and-repair candidate is not a DSL program, so the scientific evaluator could not run it. The B20_R2 trusted runner existed but was not wired into the custodian.

## Implementation (handoff s12.1 schema extension, s13.1–13.2 adapter contract)

### Schemas (`kernel/receipts.py`)

The new forms below were checked against the branch before their numbers were chosen. Old readers reject them, because field sets are exact. v3 requests and v2/v3 receipts keep their meaning.

- **Request v4.**
  - The arms are candidate descriptors rather than programs.
  - There is no separate DSL `limits`; each descriptor carries its own resource profile.
  - Analysis plan v2 is required.
  - Only `sealed_evaluation` is allowed for now.
- **Receipt v4.** Binds the candidate and baseline descriptor ids, a hash of all arms, and the isolation the arms ran in.
- **Claim binding v2.** Used for claims evaluated by v4 requests. A claim is bound by either v3 or v4 requests, never a mix of the two.

### Custodian (`custodian.py`)

- **Arm checks.**
  - Every arm descriptor is rebuilt and checked: kind, implementation digests, licensed parameters and a valid profile.
  - All arms must share one resource profile.
- **Rebuilt from the frozen export (s13.1).**
  - The candidate arm must be the campaign's write-once `frozen_candidate_descriptor`, recorded in a `candidate_version` document together with the campaign source.
  - The baseline arm must be the campaign's strongest conventional baseline, as a DSL descriptor under the same profile.
  - Any further arm must also be a conventional baseline.
- **Sandbox gate.** If the OCI sandbox is unavailable, evaluation is refused before the panel is reserved, so no panel is burned.
- **Execution.** Every arm runs through `candidates.run(..., isolation='runc')`. The resulting v4 receipts are sealed, logged and recoverable.

### Runner (`candidates.py`)

- **Sandbox for each arm.**
  - No network, with a read-only root.
  - Runs as uid 65534, under seccomp.
  - cgroup limits on CPU, memory and process count, and cgroup metering.
- **What is visible inside the sandbox.**
  - The only input is the candidate view.
  - The reviewed source tree is mounted read-only.
  - Nothing of the custodian's private root, panels, keys or references is visible.
- **Equal accounting.** The DSL kind also runs inside the sandbox, so both arms are metered by the same cgroup accounting.
- **Query cap.** The resource profile gained a query cap for the DSL kind.

### Judge (`judge.py`)

- Accepts v4 receipts.
- Re-checks every scored witness with the domain checker, for v3 as well as v4.
- For v4 it also confirms that each attempt ran the request's descriptor for its arm, inside the declared sandbox.

### CLI (`cli.py`)

- `freeze_candidate_descriptor` (write-once, with a recorded origin).
- `descriptor_request_bundle`.

## Evidence

`tests_genesis/test_candidate_custody.py` has 21 tests, which run the s13.3 acceptance list end to end:

- **A valid frozen non-DSL candidate** (represent-and-repair `cross_2` on triangle-free hosts) registers, executes in the sandbox and yields a v4 receipt. The judge recomputes the analysis and re-checks all 12 witnesses. The registration log agrees.
- **Wrong candidate digest:** `NOT_THE_FROZEN_CANDIDATE`.
- **Swapped domain:** `DOMAIN_MISMATCH`, or an export-domain mismatch.
- **Mutated artifact after freeze:** `IMPLEMENTATION_CHANGED`. A request descriptor whose parameters changed but whose id did not gives `DESCRIPTOR_ID_MISMATCH`.
- **Malformed output and resource overrun:** the attempt is CHECKER_ERROR or CPU_LIMIT, with no `result` recorded. It counts as an execution failure and is never scored.
- **Filesystem and network access from inside the runner's sandbox** were all refused: the private root, writes to the source tree or `/`, outbound TCP, DNS, and proxy or token variables.
- **Exposed reference fields:** the child receives only `{view, kind, parameters, cpu_seconds, queries, seed}`, and the view has no task id, family or split.
- **Interrupted private reservation:** a crash after rows ran leaves no retry; `recover` gives a v4 receipt with outcome INVALID.
- **Inconsistent export** is refused in each of these forms: no frozen descriptor, a rewritten descriptor, an unknown candidate version, or a wrong export hash.
- **Kernel:** a SUPPORTED v4 receipt licenses `CONFIRMED_SAME_DOMAIN` only through a v2 binding of the same descriptor.

These existing suites pass unchanged, apart from two expectations updated for the new field and kind:

- `test_candidate_adapters.py` (12). The child request now carries the `queries` cap. The custodian check class was renamed `CustodianDispatch`.
- Acceptance regressions, custodian registry, evaluator readiness, evidence kernel, external custodian, phase receipts, readiness, campaign lineage and generation lineage: 132 tests in total.

## Limitations

- **Two kinds only.** The registry holds the DSL kind and represent-and-repair. The handoff's third suggested kind, a frozen formal-research successor, is not implemented. Neither is the sealed theorem generator (s13.3; B20R5-OPEN-1).
- **Scope of v4.** v4 covers `sealed_evaluation` only; transfer, generation and improver evaluations stay on v3 or are refused.
- **What the sandbox is for.** It is OCI runc on this host. It isolates reviewed code. It is not a reason to accept arbitrary candidate code, which remains refused.
- **No real panel yet.** No sealed evaluation of the B19 represent-and-repair candidate has been run on a real panel.

## Consequence

The handoff's H05 exit condition is met on DEV: "custodian can run real frozen candidates safely". This is still pending independent review.
