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
