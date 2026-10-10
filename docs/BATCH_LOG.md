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
