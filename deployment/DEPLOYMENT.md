# Supported deployment (B15: W04, R-04)

This file says what a supported Genesis host is, how its roles are separated, and
how to reproduce a checkpoint on a second machine. Everything below was built and
exercised on the build host. Two things remain outside this repository:

- acceptance by an independent second machine;
- a pinned container image (no registry was reachable).

## 1. Supported platform

The requirements live in `deployment/SUPPORTED_PLATFORM.json`. In short:

- Linux on x86_64, kernel 5.15 or later, glibc 2.35 or later.
- CPython 3.13, matching `requirements.lock`.
- runc 1.1 or later, with cgroup v1 (cpu, cpuacct, memory, pids) or cgroup v2 (cpu, memory, pids).
- Seccomp available.
- Store roots on a local journaling filesystem: ext4, xfs or btrfs. tmpfs, NFS and FUSE are not supported.

Check a host with:

    genesis platform check --store-root /srv/genesis/campaigns

The command exits 0 when the host is SUPPORTED, 2 when something is UNVERIFIED and
1 when it is UNSUPPORTED. It checks:

- interpreter, kernel, glibc, runc, cgroup controllers and seccomp;
- the dependency lock (versions, wheel-content fingerprints, shadowed imports);
- the toolchain pins and their revision history;
- the store filesystem;
- that `GENESIS_FAULT` is unset.

**Dependency lock.** `requirements.lock` (format `genesis-lock-v2`) lists the full
transitive closure of the `pyproject.toml` dependencies for Python 3.13.

`environment/lock_fingerprints.json` (format `genesis-lock-fingerprints-v2`) holds
a per-file manifest of the installed bytes: path, size and SHA-256 for every file
in each wheel's RECORD, native libraries and package data included. Only two
kinds of file are explicitly excluded:

- console scripts installed outside site-packages, because their shebang names the
  local interpreter;
- the installer-written dist-info files (RECORD, INSTALLER, REQUESTED and
  direct_url.json).

`--check` re-reads the files on disk and fails on any of the following:

- a missing or changed file;
- a RECORD entry the lock does not list;
- an unowned file or symlink inside a distribution's directories;
- a .pyc that is not the compilation of its owned source;
- a top-level import that resolves to a file the distribution does not own;
- a changed .pth file or sitecustomize start-up hook.

Since the external review of B15_R1 (B15-REV-01), the check reads the files on
disk; before that it hashed RECORD's own text.

The check never deserializes compiled bytecode, and Python trusts any .pyc whose
header matches its source. Site-packages bytecode is therefore required to be
inert: the runtime must set `PYTHONPYCACHEPREFIX` to a private directory, so every
import compiles from the verified source. The test matrix, `reproduce.py`,
`make_checkpoint.py` and the Containerfile all do this, and the check fails when
it is unset.

Wheel archive download hashes are a separate stage and are missing: PyPI
returned 403 from the build host's egress proxy.

Regenerate the lock and fingerprints with `scripts/environment_lock.py --write` on
a host that can install the pins. The command refuses if the installed bytes
already disagree with RECORD.

**Container.** `containers/Containerfile` targets `python:3.13-slim-bookworm`. The
digest is still the `PIN_REQUIRED` placeholder, so the build fails until
`scripts/pin_container.sh` runs where a registry is reachable.

## 2. Toolchain

`toolchain/install_tools.sh` builds zstd, CaDiCaL, drat-trim and E with
`toolchain/build_reproducible.sh`. Build paths are mapped, `SOURCE_DATE_EPOCH` is the
commit time, and CaDiCaL is built with `-DNBUILD`. Lean is installed from its pinned
release tarball. Two builds at different paths and times gave identical bytes with
gcc 13.3.0 and glibc 2.39; the evidence is in `audit/b15_toolchain/`.

Another compiler may give other bytes. In that case:

1. `toolchain/check_pins.py` reports the mismatch.
2. The host is UNSUPPORTED until the operator re-pins.

**Re-pinning.** `toolchain/revise_pins.py` is the only sanctioned way to change
`PINS.json`. It appends a hash-chained entry to `PINS_HISTORY.jsonl` that records
the old and new values and the anchors it retires. It refuses any binary change
unless `toolchain/known_answers.py` passed on exactly the new binaries. Retired
hashes stop being verifier anchors.

## 3. Roles

| Role | Runs as | Holds | Can write |
|---|---|---|---|
| Sandbox launcher (`scripts/genesis_launcher.py serve`) | root | runc, the launcher log | its log |
| Research worker (`genesis campaign run`, research loop) | unprivileged UID | nothing secret | its campaign store |
| Custodian (`scripts/genesis_custodian.py`) | separate account | signing key, private root (0700) | its private root |
| Verifier / release board | anywhere | its own trust root | nothing of the others |

**Launcher.** The launcher listens on a Unix socket in a root-owned directory. It
serves only the configured worker UID, which it checks with SO_PEERCRED and never
takes from the request. It enforces:

- a policy ceiling;
- an argv[0] allowlist and a read-only mount allowlist;
- an environment-key allowlist;
- a total budget of runs and CPU seconds.

Every decision is appended to a hash-chained log that the worker cannot write. Each
receipt carries the log head, so the worker's own evidence anchors the log
(`verify-log --anchors`).

**Worker.** A worker process sets `GENESIS_LAUNCHER_SOCKET` and calls
`sandbox.run` as before; without the socket it gets `SANDBOX_UNAVAILABLE`.

**Checking the layout.** Check a deployment with:

    scripts/genesis_launcher.py roles --worker-uid 65534 --socket … --log … --trust-root … \
        --secret /srv/custody --evidence /srv/genesis/campaigns

The check models POSIX mode bits only. ACLs, capabilities and LSM policy are the
operator's responsibility.

## 4. Durability and recovery

| Situation | Behaviour |
|---|---|
| Content-addressed objects, exports, bundles, reports, snapshots | Written atomically (temporary file, fsync, link or rename, directory fsync). |
| Crash at any of the 14 points in `genesis.faults` | Tested by real process death in `tests_genesis/test_crash_consistency.py`. The state reopens all-or-nothing. |
| DEV campaign interrupted | `genesis campaign resume ROOT` continues it. Committed generations are kept, completed attempts are reused from the journal, and interrupted attempts stay charged. A successor frozen before the crash stays frozen. |
| Sealed evaluation interrupted after reservation | The panel stays consumed. `genesis_custodian.py recover` publishes a signed receipt: the complete result if every row had finished, otherwise `raw_evidence_complete=false`, which derives the outcome INVALID. |
| Backup | `genesis store backup ROOT --out B.zip` takes the writer lock and verifies the store first. |
| Restore | `genesis store restore NEW --from B.zip [--expected-head H]` re-derives the database from the hash chain. Pin the head to one recorded elsewhere (a bundle manifest or a signed receipt), because local hashes alone can be recomputed. |

## 5. Second-machine reproduction

On the second machine, as root, run:

    deployment/reproduce.sh GENESIS_COMPLETION_CHECKPOINT_Bnn.zip <sha256 sent separately> \
        /srv/genesis-repro --build-toolchain

The script runs seven steps and stops at the first one that fails:

1. checkpoint hash;
2. safe extraction against the manifest;
3. the git bundle's commit and tree, compared file by file;
4. toolchain build and pins;
5. `genesis platform check`;
6. the release test matrix, all suites;
7. deterministic reference results (`deployment/reference_run.py` against
   `deployment/EXPECTED_RESULTS.json`).

It writes `/srv/genesis-repro.report.json` with the verdict REPRODUCED or
NOT_REPRODUCED. The report leaves `operator_attestation` empty: the second
machine's operator, not this repository, attests to it.
