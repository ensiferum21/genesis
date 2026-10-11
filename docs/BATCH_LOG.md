# Completion batch log

## Batch 1 — solver speed, store scaling, known-answer ladder
- `dsl.solve` checks only motifs containing newly added edges. Output-identical
  to the frozen v1 interpreter (600 random cases + complete hosts); ~8x faster.
- `Store.recover_export` appends only new events. Before: write cost grew with
  history (2.9 s → 10.7 s per 250 attempts over 2,000 events). After: flat
  (~1.7 s). Full prefix checks still run on open, in `verify()` and on export.
- `genesis benchmark ladder`: preregistered known-answer ladder on complete
  hosts (OEIS A006855 for C4-free, Mantel for triangle-free), equal realized-CPU
  budgets, every invocation bounded and charged, frontier rungs (n = 41–49)
  classified without discovery claims. Transcribed A006855 values are
  cross-checked against the dual exact solvers for n ≤ 7.
- Pinned toolchain: Lean 4.34.1, CaDiCaL 3.0.1, drat-trim, E 3.5.1, zstd.

## Batch 2 — custodian trust holes (GI6-10, GI6-11)
See `docs/AUDIT_REMEDIATION.md` (GI6 section).

## Batch 3 — legacy trust paths (GI6-01/02/03/08)
- The current tree already carries the REV18 fixes for reused lemma IDs and
  pickle loading; the vulnerable code is in the old accepted archive. New
  tests reproduce each audit attack against this tree and fail closed.
- `eligibility.py`: only registered routes can feed confirmation-level claims.
  Legacy `gap_engine`, `legacy_batch42`, `custody_reference`, public campaigns
  and the ladder are ineligible; the accepted-base archive hash is revoked.

## Batch 4 — evidence kernel
- `genesis/kernel/evidence.py`: immutable evidence DAG; typed effects (unknown
  names refused); speculative taint resolved only by passing checks;
  promotion per axis requires the right kinds of checked artifacts (two
  distinct exact checkers for FINITE_CERTIFIED, gap-0 BoundState for
  OPTIMALITY_CHECKED, externally signed sealed evaluations for any
  confirmation); contamination, approximation, self-judgement and manual
  rescue block the levels they must; transitive revocation invalidates
  dependent claims; trust graph labels self- or mutually-validated verifiers
  CIRCULAR_JUSTIFICATION.
- `genesis/kernel/wording.py`: report linter for §21.2 forbidden
  transformations; campaign and ladder reports must pass it to be written.
- `genesis/kernel/signing.py`; architecture boundary test (kernel imports no
  research/campaign/DSL/IR code).

## Batch 5 — coordinator, recovery, storage, identity
- `kernel/phases.py`: one state machine. Engineering phases are local;
  LEAK_SCAN_PASSED / SEALED_RUNNING / JUDGED / RELEASED / REJECTED need an
  envelope signed by the role the external registry assigns (prereg, custodian,
  release), bound to the campaign's frozen request hash, stored before the
  phase changes. ABORTED/INVALIDATED need only a recorded reason.
  End-to-end test: real campaign → custodian register/evaluate → research
  process as UID 65534 reaches RELEASED; wrong-role signatures, skipped gates
  and root processes are refused.
- Role registry now includes `release_key`; loader moved to `kernel/roles.py`.
- `store.rebuild_from_export`: rebuilds the database from `events.jsonl` + CAS,
  quarantining the old files. Recovered the 10 Oct run whose live database was
  malformed (`dev_three_generations_wal_reopen_failed`): 1,372 events, head
  `c69b1c99…`, phase CANDIDATE_FROZEN, 600/600 attempts. Opening a store with
  WAL sidecars now refuses instead of letting SQLite rewrite them.
- Root cause of that corruption remains unproven. Evidence: 0-byte WAL plus a
  32 KiB SHM beside a malformed main file, written after the last export —
  consistent with a WAL checkpoint/truncate interrupted by a non-atomic
  workspace snapshot. Mitigations: rollback journal, full fsync, sidecar
  refusal, and rebuild from the append-only export.
- `kernel/version.py`: full §2.1 SystemVersion (solver, tool library, memory
  snapshot, curriculum, research policy, model configuration, cognitive kernel
  digest, verifier set, config, dependency lock, environment digest, source).
- `kernel/index.py` + `genesis store index`: derived read-only §16.4 tables.
- Property test: 25 random histories rebuild to the exact online state.
- Ladder baseline evidence: `evidence/ladder_c4_b1/`.

## Batch 6 — container sandbox and authority
- `sandbox.py`: runc/OCI backend for arbitrary generated code — new
  pid/net/ipc/uts/mount/cgroup namespaces (no network), read-only root from
  host /usr + generated /etc, size-limited tmpfs /tmp and /work, UID 65534,
  no capabilities, no_new_privs, seccomp denying mount/namespace/module/
  ptrace/bpf/keyring/reboot calls, cgroup memory/pids/CPU limits, rlimits,
  wall kill, scrubbed environment, symlink-safe capped output collection.
  RLIMIT_AS is applied by an in-container shim because applying it to runc's
  Go init crashes libseccomp (found while testing).
- `tests_sandbox/test_escape.py` (13 tests, all executed here): outbound
  network, DNS, host proxy and metadata unreachable; root/usr/etc/proc not
  writable; host secrets, home, evaluator paths and docker socket invisible;
  environment scrubbed; uid 65534, CapEff 0, seccomp mode 2; setuid, mount,
  unshare, chroot, ptrace, keyctl, bpf, init_module, mknod, reboot denied;
  only the container's own PIDs visible; fork bomb, memory hog, CPU spin,
  sleep, output flood and disk fill contained with truthful receipts. The test
  matrix treats a skip in this suite as release-blocking.
- `kernel/authority.py`: grant ledger. Children lease from a parent's
  remaining budget and cannot gain permissions; network/release/provider
  permissions need an external authorization record; charges (including
  overshoot) are recorded as events; the sandbox requires a grant with
  `execute_sandboxed_code` when a ledger is supplied.
- Container image pinning: the sandbox root is the host's read-only /usr.
  Pinning by registry digest was not possible here (Docker Hub blocked); the
  receipt records the policy and config hashes instead.

## Batch 7 — SAT/DRAT upper-bound certificates and harder panels
- `verification/tools.py`: pinned tool resolution; a binary whose SHA-256
  differs from `toolchain/PINS.json` is refused (checker identity = hash).
- `verification/sat.py`: CNF encoding (motif clauses + Sinz counter), CaDiCaL
  solve with DRAT proof, drat-trim check, certificate replay that re-encodes
  from (host, U) and binds CNF and proof hashes, and an anytime
  `certified_bounds` search (SAT models → checked witnesses; UNSAT → verified
  upper certificate; theorem bounds upgraded to DRAT when time allows).
- Tests: encoding agrees with brute force on 100+ (host, k) pairs; certified
  optima equal the dual exhaustive solvers on 30 random hosts; truncated or
  corrupted proofs, stronger-claim reuse, host swaps and empty proofs are
  rejected; bogus solver models are rejected by the dual predicates; pin
  mismatch refuses the tool.
- `panels.make_hard_panel`: hosts with 30–64 edges, defined by parameters and
  seed only (no per-task selection by solver outcome); the only filter is that
  the evaluator can certify the optimum.
- Custodian `reference_optimum`: dual exhaustive solvers up to 24 edges,
  otherwise SAT/DRAT upper certificate + checked witness, proof stored in the
  private evidence store.
- Calibration (`evidence/hard_panel_calibration/`): on 12 C4 hard hosts the
  baselines reach the certified optimum on 1 (multistart), 6 (exchange) and 2
  (low_cycle); on triangle-free hosts at the same parameters exchange solves
  12/12, so that domain needs larger hosts to be informative.
- Complete hosts are much harder to certify (K10 timed out at 60 s) because of
  symmetry; symmetry breaking is future work, and the ladder keeps using the
  published values there.

## Batch 8 — Lean checker
- Pinned Lean 4.34.1 (GitHub release tarball, SHA-256 pinned; binary hash
  pinned). `verification/lean.py` uses the comparator pattern: a TRUSTED
  generated `GenesisSpec` (definitions + `Statement`), an UNTRUSTED
  `GenesisProof`, and a TRUSTED `GenesisCheck` that type-checks
  `GenesisProof.proof : GenesisSpec.Statement`, audits axioms (allowed:
  propext, Classical.choice, Quot.sound) with per-run nonces, and replays the
  proof module with `leanchecker`.
- Lean elaboration can execute code, so checking runs in the OCI sandbox as
  three separate runs (compile spec / compile untrusted proof / trusted check);
  untrusted elaboration never shares writable state with trusted stages. This
  closed a real hole found while writing tests (a proof's `#eval` could have
  overwritten the compiled spec in a shared output directory).
- Sandbox fixes found on the way: clone3 must return ENOSYS (not EPERM) so
  libc falls back to clone; Lean needs a large address-space cap (mmapped
  libraries) separate from the cgroup memory limit; many open files.
- Distinct outcomes: CHECKED, ELABORATION_ERROR, KERNEL_REJECTED,
  STATEMENT_MISMATCH, DISALLOWED_AXIOM, FORBIDDEN_CONSTRUCT, TIMEOUT,
  RESOURCE_LIMIT, CHECKER_ERROR. Canaries: positive (C4 and triangle), false
  statement, wrong statement, invalid witness, sorry/axiom/native_decide/
  #eval/skipKernelTC/initialize/foreign imports; with the prescreen disabled
  the axiom audit still catches native_decide (Lean 4.34 generates
  `…native_decide.ax_*`), declared axioms and sorryAx, and elaboration-time
  tampering cannot produce CHECKED.
- Scope: finite witness obligations (validity + edge count). No optimality or
  universal theorem is formalized; Mathlib is not used.
- `genesis formal <task> <witness> <dir> --check`; `genesis doctor` reports
  pinned Lean, SAT tools and sandbox.

## Batch 9 — leak firewall
- `kernel/leakscan.py`: `screen()` returns BLOCK (EXACT / STRUCTURAL /
  ELABORATED / NEAR_DUPLICATE), QUARANTINE_FOR_ADJUDICATION or ALLOW; unknown
  candidate kinds fail closed. Statement canonicalization per §35.1 (comments,
  names, attributes, whitespace removed; binders alpha-renamed including
  generalized field notation; no commutative reordering). Graphs: exact,
  isomorphic, one-edge neighbours. Scanner version binds rules and thresholds.
- Elaborated layer (`verification/lean.elaborated_fingerprints`): sandboxed
  Lean elaboration (core library, autoImplicit off) hashing the
  binder-anonymized type; error-recovered types (containing sorry) get no
  fingerprint. Catches ∀-form vs binder-form restatements the text layer misses.
  Sealed and candidate statements are elaborated in separate sandbox runs.
- `OracleScreener`: research receives only the decision and scanner version;
  reasons/similarities stay in the evaluator's private ledger; query budget.
- `kernel/memory.TheoremMemory`: only ALLOW enters visible memory; a later
  audit that blocks an admitted item revokes its evidence node, invalidating
  dependent claims (§37.3).
- Custodian `sealed_index` / `screen_for_research`: signed decision receipts
  against reserved pools and sealed statements; private ledger append.

## Batch 10 — Research IR macros, research market, world loop, registry
- `ir.py`: primitives keep their 16 names; typed overloads (e.g. VERIFY a
  witness or an upper-bound contract; TRANSFORM relabel or induced subgraph;
  TRANSPORT relabel or embedding; COMPOSE variadic), explicit discriminators,
  every invocation traced with a digest of its deterministic output, and
  `replay()` re-executes a recorded program and reports mismatching nodes.
- `macros.py`: Ghost Census (PROVED / GHOST_FOUND / UNSETTLED / HARNESS_ERROR
  kept distinct; "no ghost found" is never proof), Barrier & Escape,
  Local-to-Global, Gap Engine, Cognitive Compilation — all driven only through
  the primitives, all replay byte-identically from their IR records. Example:
  a greedy search class stalls at 30 edges on a hard host; Barrier & Escape
  moves to the exact representation and certifies 33.
- `market.py` (§34): score formula, Pareto prefilter, budgeted portfolio,
  diversity slot under premature convergence, per-kind calibration from
  realized outcomes, stop-thinking rule.
- `worldstep.py` (§26.3): diagnose → propose → allocate → execute macros under
  leased grants → verify → recalibrate → Pareto ecology → retire → meta-gap
  candidates; claims promoted only to WITNESS_VALID / OPTIMALITY_CHECKED.
  Example run (4 hard hosts, 3 epochs): all 4 optima certified; calibration
  error 4.04 → 0.74.
- `registry.py`: all 137 Appendix A engines as data — 5 IMPLEMENTED_BOUNDED,
  16 INFRASTRUCTURE_BOUNDED, 116 EXPRESSIBLE_NOT_INSTANTIATED (composition
  hypotheses, no stubs). `genesis registry summary`, `genesis research loop`.

## Batch 11 — Experiment B (Ghost Census kill gate)
- `fol.py`: TPTP-FOF subset parser, signature checks, TPTP printer and an
  independent recursive finite-model evaluator.
- `modelfind.py`: Mace-style SAT model finder (one-hot function tables,
  memoized ground-term value variables, Tseitin, constant symmetry breaking)
  using pinned CaDiCaL; every model is re-checked by the independent
  evaluator; "no model up to size d" is never a proof.
- `verification/eprover.py`: pinned E prover; THEOREM is a prover claim with
  the proof object recorded but not replayed (THEOREM_CHECKED needs Lean).
- `experiment_b.py`: preregistered algebra family (group, monoid, band, loop;
  goals and candidate lemmas, some false), three arms with equal per-problem
  CPU budgets in randomized order — portfolio (countermodel search + E),
  lemmas_unfiltered, ghost_lemmas (drop lemmas with validated ghosts first).
  States PROVED / GHOST_FOUND / UNSETTLED / HARNESS_ERROR; cross-arm
  contradiction check; preregistered gate.
- DEV run (12 problems, 8 s each; `evidence/experiment_b_dev/`): ghost_lemmas
  settled 12, portfolio 12, lemmas_unfiltered 8; ghost_lemmas used 2.4× the
  portfolio's CPU. Gate (margin 1): KILL on this family. The family is too
  easy for lemma selection to matter; a meaningful run needs harder problems.
- `genesis experiment ghost-census <dir>`.

## Batch 12 — reproducibility, CI, test matrix
- `release_bundle.py` (§43): `genesis export release-bundle` writes the full
  release layout (claims, config, SystemVersion, dependency lock with observed
  distributions + RECORD hashes, toolchain pins, events, snapshot, objects,
  certificates, checker and resource receipts, preregistrations, shipped
  analysis code with code identity, REPRODUCE/LIMITATIONS); `genesis
  verify-bundle` independently checks file hashes, rebuilds the event chain
  from the export and recomputes the shipped code identity. Tampered claims or
  truncated events fail verification.
- §38 classes added: mutation (receipt/object/event/derived-state corruption),
  load/concurrency (single writer, concurrent worker returns, resource
  receipts), baseline regression against `golden/baselines.json` (regenerated
  only deliberately via `scripts/regenerate_golden.py`), end-to-end smoke
  under the 600 s cap. Map in `docs/TEST_MATRIX.md`.
- `run_test_matrix.py --profile commit|nightly|release`; CI workflow
  `.github/workflows/ci.yml` (release profile requires a privileged
  self-hosted runner with runc; skips there are release-blocking).
- `containers/Containerfile` + `scripts/pin_container.sh` (base image digest
  must be resolved where a registry is reachable — not possible here) and
  `environment/observed_python313.json` via `scripts/environment_lock.py`.

## Batch 13 — integration and verification
- Ladder gains a specialist baseline arm (`--sat-baseline`): warm-started
  CaDiCaL search under the same realized-CPU budget. Result on n = 21–40
  (`evidence/ladder_c4_sat/`): shortfall 225 vs 194/194/232 for the greedy
  arms — on complete hosts the greedy arms are the strongest baselines; on
  random hard hosts SAT is. A receipt bug (failure reason dropped) was fixed.
- `scripts/e2e_walkthrough.py` (§40): every step runs with real components;
  steps 11–13 use fixture roles in a separate UID; step 14 not performed.
  Fixture sealed panel (3 hard CONFIRM hosts): candidate 0 wins / 1 loss / 2
  ties vs baseline; preflight BLOCKED with the expected reasons
  (`evidence/e2e_walkthrough/`).
- `docs/REQUIREMENTS_AND_GAPS.md` rewritten section by section, with the §31
  checklist and the builder's §48 assessment (P0–P2 engineering; P3–P7 not
  claimed).

## Batch 14 — repair acceptance (reviewer roadmap B14)
- Started from tag `b13-baseline` (`82aa557`) on branch `continuation-b14`;
  B13 itself is unchanged.
- **Reproduced** R-01 (two attacks) and R-02 on B13 before touching code
  (`audit/reproductions/logs/b13_baseline_82aa557.log`).
- **R-01**: `kernel/receipts.py` is the one place that interprets signed
  scientific records (trusted kind→role map, exact schemas, signed outcome
  re-derived from signed counts, claim binding, evaluation-identity counting,
  consecutive program-linked generation chains, salted panel commitments in
  anchors, one registration per claim slot). The kernel, phase machine,
  preflight and custodian all use it. Request schema v3 and receipt v2.
- **R-02**: the kernel reads only immutable records; `levels()` re-derives
  effective levels (node, verifier, key and evaluation revocations). Bundles
  carry historical vs effective status and REVOCATIONS.json; `verify_bundle`
  rebuilds the store and regenerates every derived file byte-for-byte, checks
  the snapshot, lints report and statements, and can apply a later revocation
  feed to an older release.
- **R-03**: `verification/certificates.py` CertificateBundle keeps the original
  CNF, DRAT proof and witness; IR traces reference them; bound_state v2 links
  its lower witness check and certificate; the kernel replays the certificate
  (solver disabled) before granting OPTIMALITY_CHECKED; a real world-loop
  export verifies with only drat-trim installed.
- **Internal red team** (fresh agent): 11 findings on the first repair, 4
  critical; all closed with regression tests (`audit/redteam_b14/`).
- **W01**: `scripts/build_ledger.py` → `ledger/requirements_ledger.json` and
  `docs/REQUIREMENTS_LEDGER.md` (157 spec sections, R-01..R-04, GV0..GV8,
  W01..W28, E0..E7, 137 engines; every test reference resolved; nothing
  accepted).
- Matrix: undeclared skips now fail; `networkx` declared in `pyproject.toml`.
- e2e walkthrough re-run with the new schemas (`evidence/e2e_walkthrough_b14/`):
  fixture sealed panel 0 wins / 0 losses / 3 ties → signed NOT_SUPPORTED;
  preflight BLOCKED; release refused for a non-supported outcome.
- Open: R-04, B14-OPEN-1, independent review for GV0.
- **Internal red team, round 2** (fresh agent, on `9c71dbe`): 12 findings, 2
  critical — a transfer label for a candidate that never saw the source domain
  (request facts were never checked against the campaign) and math/causal/
  replication levels licensed by producer-written verdicts. Repairs: the
  custodian rebuilds the campaign export and checks campaign, source and
  domain, and refuses improver/generation kinds until a lineage protocol
  exists; only kernel-replayable evidence licenses a level (witness checks are
  re-run, certificates replayed, receipts role-signed; other kinds license
  nothing); the verified phase re-applies every binding check and is bound to
  the campaign's own export history; strict JSON and byte equality in bundle
  verification; shipped code must match its identity; wording gate hardened;
  slots keyed by candidate program. Regressions in
  `tests_genesis/test_redteam_b14_round2.py`; scripts and original logs in
  `audit/redteam_b14_round2/`.
- Walkthrough re-run on the final code (`evidence/e2e_walkthrough_b14/final/`;
  earlier B14 runs are kept in `run1_commit_9c71dbe/` and `run2_commit_439b764/`).
- Open after B14: R-04; B14-OPEN-2 (multiplicity across candidates);
  B14-OPEN-3 (improver/generation lineage); B14-OPEN-4 (replay contracts for
  the other evidence kinds); B14-OPEN-5 (per-claim report wording); GV0
  independent review.
- **Internal red team, round 3** (fresh agent, on `439b764`): 9 findings, 1
  critical — the custodian signed SUPPORTED for a labelled frozen candidate
  while evaluating a different program, and one claim could be registered
  repeatedly. Repairs: the frozen version document is recorded before the
  export and the custodian requires the request to describe the campaign's
  frozen candidate and strongest baseline; claim and candidate slots; bindings
  carry the candidate program; the recorded configuration cannot diverge from
  the config file; math statements are generated from the stored problem;
  anchors are revocable everywhere; campaign identity is write-once and bound
  requests must be this campaign's; preflight and verified phase apply
  revocations; wording vocabulary widened; the world-loop summary is re-derived.
  Regressions in `tests_genesis/test_redteam_b14_round3.py`
  (`audit/redteam_b14_round3/`).

## Batch 14, review fix 1 (B14_R1)
- External review of B14 (`audit/review_b14_external/GENESIS_B14_REVIEW.md`)
  found F-01: a requested optimum ("is 0 edges", true optimum 3) was exported as
  the claim's statement at WITNESS_VALID and the bundle verified. Reproduced on
  `30a61fc` before any change.
- Repair: the kernel separates the requested proposition from what the
  evidence establishes (`current_wording`, per claim, from that claim's own
  levels); CLAIMS.json exports current statement, marked conjecture, contract
  and requested statement; `report.md` is generated from them; caller prose is
  floor-checked operator notes; math scope is fixed; free text is never
  asserted. B14-OPEN-5 closed. Regressions:
  `tests_genesis/test_external_review_b14.py` (the review's six cases + 2).

## Batch 15 — Independent execution (W04, R-04)

Environment findings:

- PyPI returned 403 from the egress proxy, so there are no wheel download hashes.
- No container registry was reachable, and no Docker daemon ran.
- No second machine was available.

What was built:

- **Platform and lock.**
  - `deployment/SUPPORTED_PLATFORM.json` and `genesis platform check` (12 host checks).
  - `requirements.lock` v2: Python 3.13, 17 pins, the full closure, wheel-content
    fingerprints and shadowed-import detection.
  - `requires-python` is pinned to 3.13 and the Containerfile moved to 3.13.
  - The sandbox reads cgroup v2 statistics.
- **Crash consistency.**
  - `genesis.faults` defines 14 crash points.
  - CAS objects are written to `objects/tmp` and linked into place; directories are
    fsynced before commit.
  - Export appends are recoverable; the zip, snapshot, report and request writes
    are atomic.
  - Rebuild constructs the new database aside and swaps it in.
  - Each generation is committed in one transaction.
- **Resume and recovery.**
  - `genesis campaign resume` reuses journalled attempts, charges interrupted ones
    and keeps an existing freeze.
  - `custodian.recover` publishes a receipt for an interrupted sealed evaluation.
- **Backup and restore.** `genesis store backup|restore`, with a manifest, safe
  extraction, a chain rebuild and an optional pinned head.
- **Toolchain.**
  - `toolchain/build_reproducible.sh` reproduced identical bytes for all four
    source-built tools across paths and times.
  - `toolchain/known_answers.py` runs 10 behavioural cases.
  - `toolchain/revise_pins.py` and `PINS_HISTORY.jsonl` record three entries:
    the baseline, the reproducible rebuild and a recipe guard.
- **Roles.** The `genesis.launcher` root service and unprivileged worker
  delegation, `scripts/genesis_launcher.py`, and the role-layout check.
- **Reproduction.** `deployment/reproduce.{py,sh}` and `deployment/reference_run.py`
  with `deployment/EXPECTED_RESULTS.json`.
- **Internal red team** (same operator, not independent): 5 findings, all repaired.

Tests added:

- `test_deployment`
- `test_crash_consistency`
- `test_backup_restore`
- `test_toolchain_revision`
- `test_reproduce`
- `test_redteam_b15`
- `tests_sandbox/test_launcher`
- `tests_certificates/test_known_answers`

Not done:

- second-machine acceptance;
- the image digest;
- wheel hashes;
- compute sizing.

## Batch 15, follow-up 1 (B15_R1)

The clean-room rehearsal of the B15 checkpoint ran `deployment/reproduce.sh` on the
build host. The toolchain was rebuilt from GitHub and the Lean tarball, and every
pin matched byte for byte. The rehearsal then failed at the release matrix: one
integration test skipped outside a git checkout, so the mandatory matrix had
depended on hidden state.

The test now checks every shipped file instead of skipping. Evidence is in
`audit/b15_rehearsal/`.

## Batch 15, follow-up 2 (B15_R2): external review of B15_R1

The review (`audit/review_b15_external/`) confirmed that the B14 F-01 repair holds
and that the checkpoint is intact. It reproduced two new defects on `eb1ae3c`.

- **B15-REV-01.** The lock check hashed RECORD's strings, not the installed files.
  It now compares installed bytes file by file against a per-file manifest, which
  the lock writer refuses to record if the bytes already disagree with RECORD. It
  also rejects:
  - RECORD entries the lock does not list;
  - unowned files and symlinks in a distribution's directories;
  - imports that resolve to files the distribution does not own;
  - changed start-up hooks.

  Bytecode in site-packages is never deserialized; it must be inert under a
  private `PYTHONPYCACHEPREFIX`. The matrix, reproduction, checkpoint and
  Containerfile all set one.
- **B15-REV-02.** A claim identifier injected an `Established` line into report.md.
  - Identifiers, statements, scopes and task labels must be one printable line.
  - Report fields render as literal code spans.
  - `verify_bundle` re-parses report.md's structure without the renderer.

Regressions are in `tests_genesis/test_external_review_b15.py`, with before and
after logs in `audit/review_b15_external/logs/`.

## Batch 16 — Evaluator readiness (W05–W07)

**W05 (domains).**
- `genesis.domains` defines the DomainAdapter interface and implements it for both
  graph domains. Its operations are parse, supports, exposure identity, candidate
  and evaluator views, validate, score, certified reference, certificate
  obligations, cost, families, generate and replay.
- Unsupported input produces an explicit UNSUPPORTED outcome.
- The solver child now receives only the candidate view (domain, n, edges); the
  receipt records its hash.
- A conformance suite runs against every registered adapter.

**Calibration.**
- `genesis.calibration` uses DEV material only, under a selection rule frozen in code.
- The v1 panels had a ceiling rate of 1.0 and headroom of 0.0.
- c4: three erdos settings were adopted (n = 12, 16, 20).
- Triangle-free: round 1 selected nothing. Round 2 kept the same rule, extended the
  grid, and selected erdos n=22 p=0.35.
- The adopted records are pinned by hash in `configs/dev_calibration.json`.

**W07 (statistics).**
- `kernel/analysis.py` defines plan v2. Its parts are:
  - a stratified sign-flip test (exact when small);
  - a stratified bootstrap interval;
  - the minimum useful effect kept separate from the design effect;
  - Holm across the custodian family;
  - a single-analysis stopping rule;
  - failures scored zero;
  - an unsupported-task policy;
  - cost and regression bounds;
  - four sensitivity analyses.
- Receipt v3 signs the analysis result. The kernel re-derives the decision from it
  and rejects internal forgeries.
- `genesis.judge` recomputes the analysis from the raw receipts.
- `genesis.power` uses a headroom-limited power model with a design floor, and uses
  only DEV pilots.
- `genesis.resources` keeps a resource account of every journal. It covers discovery,
  inference per arm, verification, ground truth, retrieval, model calls and memory.
  Human time is only ever declared, with the name of whoever declared it. Every
  attempt is charged, including failures and interruptions.
  - Ground truth is never charged to an arm.
  - The custodian records the account inside the signed evidence root. The judge
    recomputes it and checks the arms were paired, with the same task, limits and
    seed.
  - A test checks that no module imports a model client.
- `genesis.decision_record` writes the Appendix B record. Its embedded plan core is
  named by hash from the plan.

**W06 (custody).**
- The registration log is signed and hash-chained. Its entries are REGISTERED,
  RESERVED, PUBLISHED and RECOVERED, and each carries its family.
- Hypothesis families are assigned by the custodian, and declared sizes are enforced.
- Control declarations for the custodian, auditor and release authority name their
  controllers, machines, keys, data and analysis. Shared control yields
  LIMITED_SAME_OPERATOR.
- Release preflight requires the log and the declarations for v3 receipts.

**Study design.** A DEV pilot of 60 tasks gave an E1 power analysis: 10 tasks per
family (30 in total) reach a power of 0.946 at a design effect of 0.5. The
decision record is a DRAFT for review (`evidence/study_design_b16/`).

**Internal red team** (same operator, not independent): five regressions in
`tests_genesis/test_redteam_b16.py`. They cover family shopping, plan swap, a
rewritten log chain, evidence extended after sealing, and v1 receipts in a crowded
family.

**Not done.**
- Independent review of custody, fairness and study design (the phase's exit).
- External time anchoring.
- A Lean adapter (W08).

## Batch 17 — Formal research (W08 and the first theory-package path)

**Workspace (W08).**
- `toolchain/FORMAL_WORKSPACE.json` pins Lean 4.34.1, Mathlib `d13f23b7` (tag
  v4.34.1) and all eight Lake dependency commits.
- `toolchain/build_formal_workspace.py` fetches exactly those commits. It checks that
  Mathlib's own manifest names the same commits, then builds the import closure of
  `Mathlib.Data.Finset.Powerset` (699 modules):
  - offline, with no proxy variables;
  - with Lake's cache disabled, so no precompiled Mathlib is downloaded;
  - with any npm rebuild of ProofWidgets refused.
- The artifacts are copied into one read-only tree and hashed.
- `install_tools.sh` builds the workspace and `deployment/reproduce.py` audits it.
- Two independent builds on this host gave byte-identical artifacts (identity
  `95a6ec9f…`). Mathlib's precompiled cache hosts are refused by this network's
  policy (403), and nothing was routed around them.

**Acceptance (`formal_research/checker.py`).**
- Module chains of trusted modules (generated by Genesis) and untrusted ones
  (proofs). Each module compiles in its own sandbox, with the workspace mounted
  read-only.
- Untrusted modules are prescreened: forbidden constructs, options other than
  heartbeat and recursion limits, the `module` header, and any import outside the
  workspace and the earlier modules.
- A trusted check stage then:
  - binds each proof to its statement constant (`theorem genesis_bind_i : Spec := Proof`);
  - audits axioms;
  - extracts every declaration (kind, type fingerprint, used constants and their
    modules, axioms);
  - replays every untrusted module with leanchecker.
- Nonces guard every printed result.
- Detailed statuses map onto the roadmap's outcome classes.

**Search (`formal_research/search.py`).**
- Separate from acceptance. It compiles its own context and tries named recipes:
  generic tactics, hypothesis application, instantiation, library elimination and a
  cover-split strategy that uses library lemmas.
- All candidates for a conjecture run in one sandbox and are attributed by line.
  Every attempt is charged.
- A found proof is recompiled from source by acceptance.

**First theory package** (`formal_research/triangle_theory.py`, `theory_package.py`).
- The domain contract `GT.TriangleFree` is builder-written.
- Generated concepts: the bound concept, a normal form, and gadget families from an
  exhaustive search that kept the triangle and K4.
- Generated conjectures from 12 templates. Each was screened against a Python model
  of the same definitions, and three counterexamples outside the normal form led to
  corrected hypotheses.
- Outcomes: 9 CHECKED, 7 DISPROVED (counterexamples checked in Lean), 2 UNRESOLVED,
  1 UNSUPPORTED.
- Reuse is visible in the dependency closure: bound_union's proof uses the generated
  down_closed lemma.
- The executable method (gadget packing) uses only CHECKED material.
  - It was sound on 12 fresh DEV tasks, with a gap to the optimum of 1 to 9 edges.
  - For two tasks a Lean-checked bound certificate reuses bound_card, bound_union
    and bound_mono.
- The package replays from its sources alone: REPLAYED, no differences.

**Lean domain (W05).** `formal_research/lean_domain.py` implements the DomainAdapter
interface. Validation is acceptance, and exact_reference is explicitly UNSUPPORTED.
It is not a sealed-receipt domain.

**Not done.**
- An independent replay of the package.
- Proof strategies beyond builder-written recipes (W18/W20).
- A structural result used by a solver on fresh tasks (W11's done-when).
- A second machine.

## Batch 18 — Concept invention (W09–W12)

Shared machinery: `formal_research/loop.py` turns any typed conjecture (binders,
hypotheses, a Python model) into the B17 cycle of screening, checked disproof, recipe
search and acceptance. The cycle ends in a package in the B17 schema, so `replay`
applies to it unchanged. Search now tries the specialised candidates before the generic
portfolio, at a lower heartbeat limit. Acceptance limits stay as they were. The trusted
check stage also returns statement trees and proof-term sizes.

**W10 representations** (`invention/representations.py`).
- A typed grammar of vertex-class encodings (`ℕ → Fin k`, k ≤ 3) with four decoders. Each
  proposal is typechecked and bounded, and records its semantics, what it keeps and loses,
  its cost and its failure conditions.
- Lean obligations: image, soundness, dominance and loss. Four representations are sound
  for triangle-free. All C4 soundness claims are disproved.
- represent-and-repair, on a fresh DEV panel, against the strongest baseline per task:
  - 6 wins, 5 ties, 1 loss;
  - 4 against 2 optimum hits;
  - every witness valid.
  This is W11's done-when, checked on DEV only.

**W12 worlds** (`invention/worlds.py`). Worlds with explicit assumptions and their
interventions:
- consistency only with a checked model, inconsistency only with a checked proof of
  False;
- implications, separations and transport decisions;
- claims from an inconsistent world are VACUOUS.
- A discriminating experiment on erdos and bipartite DEV hosts picks the world host by
  host.

**W09 recovery** (`invention/recovery.py`, `recovery_experiment.py`).
- History library → cutoff snapshot of statement trees → typed first-order
  anti-unification → reified concept with rfl-checked instances and no hidden constants.
- The concept recovered is definitionally Mathlib's `Antitone`.
- Fresh families in four arms (none, retrieval, concept, manual): proved 4, 4, 8 and 8 of
  16 statements. The concept enables the Matching family and shortens the LoopFree proofs
  about 60-fold in proof-term size. The manual abstraction does equally well.

**Evidence.** `evidence/invention_b18/`: eight packages, all replayed (3,907 s). Proof
sizes were recomputed after a bug fix: theorem values had been read as opaque. The fix
is recorded in `comparison.json`.

**Not done.**
- A historical Mathlib cutoff study.
- Representations beyond vertex classes.
- Sealed evaluation (B19).
- Learned proof strategies.


## Batch 19 — Useful discovery (W13–W17; E1/E2 readiness)

**W13 construction meets obstruction** (`discovery/obstruction.py`).
- LP relaxation of the largest motif-free subgraph. Its dual comes from scipy/HiGHS, an
  untrusted producer, and is converted to exact rationals and repaired.
- `check_certificate` is an independent exact checker. It verifies task identity, that
  each inequality is a motif of this host with the right side, dual feasibility edge by
  edge, and the bound.
- The validity of the inequalities is Lean-checked (`tri_not_all`, `c4_not_all`).
- Joint certification: construction (represent-and-repair) + LP certificate + SAT/DRAT
  on the remaining gap only. An optimum is claimed only when lower and upper meet.
- 12 fresh hard DEV hosts, same 60 s wall budget as the reference loop:

  | | Optimum certified | Mean gap |
  |---|---|---|
  | joint | 11 / 12 | 0.08 |
  | reference | 6 / 12 | 21.2 |

  0 disagreements.

**W14 active experiments** (`discovery/active.py`).
- Hypotheses: the best method per task family. Beta–Bernoulli observation model with
  calibration.
- Methods that no admissible action can separate are collapsed first and reported
  UNRESOLVED. They are declared equal by B18's checked decoder theorems, or have identical
  per-task values.
- First evaluation: EIG lost to round-robin and random. That result is kept.
- Second evaluation, on fresh pools from a new seed: a lookahead knowledge gradient (KG*),
  added after the first result, beat fixed and random selection at both budgets. P(correct)
  0.93 vs 0.78 / 0.81 at 20%, and 1.00 vs 0.93 / 0.96 at 40%; lower regret at both.

**W15 catalysis** (`scripts/b19_discovery.py`).
- Solver factorial (encoding × repair), with removal, placebo, 4× effort and a conventional
  alternative, on 24 fresh DEV tasks.
- The represent-and-repair gain survives every control: +3.2 vs placebo, +2.4 vs removal,
  +1.7 vs removal at 4× CPU, +1.6 vs low_cycle. Optimum hits: 10 vs at most 4.
- Concept controls added to B18's arms: placebo concept 4/16 and effort (4× heartbeats)
  4/16, against concept 8/16 and manual 8/16. The concept's gain is not effort and not any
  concept-shaped definition.

**W16 Ghost Census, beyond the small family** (`discovery/ghost_census.py`,
`formal_research/fof_lean.py`).
- E proof objects are replayed step by step in Lean against a trusted statement generated
  from the problem, so THEOREM_CHECKED needs a kernel-checked proof object.
- A preregistered DEV diagnostic on 125 problems from ten equational theories.
- Run 2, the one with the fixed harness, settled at 8 s / 2 s:
  - strongest baseline 123–124 / 48–50;
  - free true lemmas (oracle) 123 / 48;
  - Ghost Census arms 76–102 / 37–39.
- Decision: **RETIRE_NO_HEADROOM** for this scope. E proves almost every true goal from the
  axioms, and B11's one-second slices starve the goal at 2 s.
- Run 1 is kept. It had the model-finder budget defect described below and reached the
  same decision.

**W17 literature** (`literature.py`). Sources with provenance and fidelity; retrieved text
is untrusted and screened for injection. Further:
- exact-quote claims, with notation resolved against Genesis definitions;
- links with Lean or executable checks;
- ambiguity records with distinguishing instances;
- an adjudication queue (PENDING_HUMAN);
- novelty reports that never conclude "novel".

Evidence in `evidence/literature_b19/`:
- 7 sources, 8 claims, 7 links. Two of the links are Lean-checked: RC.C0 ↔ `Antitone`
  and RC.C0 ↔ `IsLowerSet`.
- 3 ambiguity records, 2 of them material: "monotone" and "C4-free".
- 4 novelty reports, all PRIOR_ART_FOUND.

**E1/E2 readiness** (`scripts/b19_readiness.py`).
- E1 candidate: B18's represent-and-repair with `cross_2`, identified by code hash and
  parameters.
- Fresh 60-task DEV pilot from the adopted triangle-free calibration: +1.27 edges per task
  over `low_cycle` (41W/9T/10L); optimum 36 vs 13.
- The B16 power model reports INFEASIBLE. It takes headroom from the uncentred candidate,
  which is already near the optimum.
- A centred-headroom option was added to `power.py`; the default is unchanged. With it, 25
  tasks give power 0.83.
- The DRAFT decision record embeds the corrected analysis and has no problems. It is not
  frozen, and the custodian's evaluator cannot run the candidate yet.
- E2 design draft built from the B18/B19 DEV arms.

**Harness defect found and fixed.** `modelfind.find_model(total_seconds=…)` was new in
B19. It required a full second left before each size, so a one-second budget stopped after
size 1. W16 run 1 is kept with this defect; run 2 uses the fix. A regression test is in
`tests_formal/test_ghost_census.py`.

**Not done.**
- Symmetry reduction, kernelization and continuation (W13).
- A sealed comparison of any kind.
- An E1-capable evaluator adapter for non-DSL candidates.
- A harder Ghost Census family.
- Confirmation of the retrieved quotes by a person.

## Batch 20 — Learning to research (W18–W20; E3)

**Domain** (`learning/equational.py`). Equational research with exact deciders:
- Boolean algebra through the 2-element algebra, free-group reduction for groups, and
  Boolean rings and distributive lattices.
- Five Boolean-algebra and group axiomatizations, plus a Boolean ring and a distributive
  lattice.
- Conjecture pools come from term enumeration bucketed by term function, with
  canonicalization up to renaming and orientation.
- Target sampling never touches the pool.

**Research runs** (`learning/research.py`).
- Each run spends a CPU budget on decider checks and E proof attempts. Lemmas carry proof
  objects, the premises they were given, and the premises they used.
- The successor is the frozen library, evaluated on unused targets.
- Policies: fixed, random, goal-directed heuristic, UCB bandit, and a logistic policy
  trained on other runs and frozen before use.
- `lean_chain` assembles the lemma chain that a proof depends on.
- `fof_lean` gained chained replay: lemmas proved from earlier lemmas, and inputs
  addressed by their E positions. Successor proofs are therefore Lean-checked down to
  the axioms.

**W18 macros** (`learning/macros.py`).
- Induction keeps the used lemmas and their dependency closure, and records the attempts
  it dropped.
- Faithful replay, revocation with transitive invalidation, and description length.
- Strict expansion skips a step whose dependency failed. A non-strict mode was added post
  hoc.

**W20 memory** (`learning/memory.py`).
- Contamination screening against evaluation targets (EXACT, INSTANCE), retrieval and
  demotion.
- Failure-driven curriculum built from development targets only: specializations and equal
  sub-equations, checked by the decider.

**Evidence** (`evidence/learning_b20/`). All of it is DEV.
- **Main run.** Over 8 independent runs, the learned policy ties the fixed one on 7 and
  wins 1 (+0.125 targets); it scores −0.125 against the best baseline. Calibration is
  near-uninformative. Most systems leave research little room: Huntington sits at the
  ceiling.
- **Macros.** Faithful in both systems, with 2.2–4.2× description-length compression. On
  unseen seeds they match plain research. Strict transfer to Wolfram's axiom failed at
  its first step: 0 of 15, against 6 for plain research. Non-strict expansion matches
  plain research at 6.
- **Lean.** 67 of 68 successor proofs that used lemmas replay, with 583 chained lemmas.
- **Wolfram's axiom.** This is the one system with headroom. 60 s of research raises
  successors from 0 to 8–12 of 15. The curriculum matches plain research at equal effort
  (+2 on one seed of 4). The main budget rule, a quarter of the exhaustion CPU, starved
  10-second attempts and left almost every policy run with nothing.

**E3 / GV4.** The better-improver claim is **explicitly UNESTABLISHED**: DEV runs only,
with no sealed panels and no custodian.

**Not done.**
- A sealed E3 study.
- Learned policies that beat fixed rules.
- Macro transfer that beats plain research.
- Research on the Lean/Mathlib domain with these tools.
