# Operations runbook (H11)

This runbook covers the continuation line as of B20_R23. It says how to run, recover and check each part. The supported platform and its roles are in `deployment/DEPLOYMENT.md`, and what is and is not established is in `docs/REQUIREMENTS_LEDGER.md` and `docs/BLOCKING_DEFECTS.md`.

Every command assumes:

    export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src

## 1. Environment and release gate

| Step | Command | Notes |
|---|---|---|
| Toolchain | `bash toolchain/install_tools.sh` | Builds from pinned sources: Lean, CaDiCaL, drat-trim, E, and the formal workspace (CRPD-2b pin). Takes 30–60 min. |
| Platform | `python3 -m genesis platform check` | Python 3.13 and the lock in `requirements.lock`. |
| Release matrix | `python3 scripts/run_test_matrix.py --profile release --report R.json` | Run as root, because the sandbox uses runc. Suites: integration, legacy_regression, sandbox_escape, certificates, formal. Undeclared skips fail the run. About 25 min on 2 cores. |
| Checkpoint | `python3 scripts/make_checkpoint.py --batch 20 --suffix _Rnn --parent <previous zip> --parent-ref <commit>` | Needs a clean tree. It runs the matrix, then writes the zip and its `.sha256`. Run it from a clone without the `archive` branch, because the bundle includes every ref. |
| Restore check | Unzip, recompute every hash in `CHECKPOINT_MANIFEST.json`, clone `source-history.bundle`, and compare the commit, tree and files with the archive | `deployment/reproduce.sh` does all of this on a second machine and adds the toolchain, the matrix and the reference results. |

## 2. Campaigns (research operator, unprivileged)

| Action | How |
|---|---|
| Create, run, resume | `genesis init ROOT --config C`, then `genesis campaign run ROOT`. After a crash, `genesis campaign resume ROOT`: interrupted attempts stay charged and frozen successors stay frozen. |
| Active version (B20_R16) | `versions.active(store)` and `versions.status(store)`. A retained generation moves the pointer inside its own commit. |
| Roll back | `versions.rollback(store, ancestor_id, reason=..., actor=...)`. The child is kept and reported ROLLED_BACK. Sideways switches are refused, so roll back to the common ancestor first. |
| Revoke a version | `versions.revoke(store, vid, reason=..., actor=..., kernel=EvidenceKernel(store))`. Descendants inherit the revocation, and kernel nodes naming an affected version are revoked. A campaign whose active version is revoked refuses to resume until you roll back. |
| Freeze a candidate | `cli.freeze_candidate_descriptor(campaign, descriptor, origin=...)` (write-once), then `cli.export_replication(...)`. The descriptor kinds are in `candidates.KINDS`: DSL programs (plain and time-matched), represent-and-repair, the formal successor and, since B20_R23, `construct-pipeline-v1`. |
| Comparator selection | The custodian signs it (§3). Record it with `cli.record_comparator_selection(campaign, envelope)` (write-once) before building the request. |
| Requests | `cli.descriptor_request_bundle(campaign, n, analysis=plan)` builds the sealed evaluation. `cli.followup_request(campaign, kind, ...)` builds ablation, placebo, internal replication and external reproduction requests, which keep the claim, the candidate and the export binding. |

## 3. Custodian (separate account, private root 0700, its own keys)

| Action | Function | Refuses |
|---|---|---|
| Comparator selection | `custodian.select_comparator(root, export, baselines, key, operator, exposure_manifest=..., study=...)` | baselines that are not conventional, mixed resource profiles, too little distinct material, a study with no adopted calibration (E1b until B20R23-OPEN-1 is decided) |
| Register | `custodian.register(root, request, prereg_key, operator, exposure_manifest=..., campaign_export=..., pool=..., decision_record=frozen, accepted_selection_keys=())` | a request the export does not show; an unfrozen or underpowered decision record; a used claim or candidate slot; a full hypothesis family; an ablation or placebo baseline that is not a registered intervention; a comparator this custodian did not select. A repetition kind may instead name the selecting custodian's key. |
| Evaluate | `custodian.evaluate(root, request_hash, pool, custodian_key, operator)` | — (every arm runs in the OCI sandbox under one profile, metered by cgroup) |
| Recover | `scripts/genesis_custodian.py recover` | — (an interrupted evaluation publishes `raw_evidence_complete=false`, which is INVALID) |
| Publish | `custodian.registration_log(root, key)` | — |

The exposure manifest is a custodian-owned file that no one else can write. List every DEV panel named in the evidence, plus each handoff package's host list (for example `handoff/e1/exposure_hosts_all.json`).

## 4. Judge, kernel and release

| Action | How |
|---|---|
| Recompute an evaluation | `judge.recompute(evaluation_dir, request, receipt, registration_log_entries=...)` re-checks every witness and the analysis. |
| Record evidence | `kernel.record_signed(kind, envelope, ...)` for signed receipts and anchors; `kernel.record(kind, payload, ...)` for replayable kinds. |
| Promote | `kernel.promote(claim, axis, level)`. Every level has a replay contract (`kernel/replay_contracts.py`). A producer-written verdict never licenses a level. Confirmation levels need the externally pinned role registry (`GENESIS_TRUST_ROOT`, roles v2 for the optional replicator, priority-reviewer and internal-replicator keys). |
| Revoke | `kernel.revoke(node, ...)`, `revoke_key`, `revoke_evaluation`. Revoking a verifier registration revokes that replay route; for example the Lean-package route's identity is `replay_contracts.package_checker_identity()`. |
| Release preflight | `scripts/promotion_preflight.py`, or `custodian.release_preflight`, against the external trust root and the control declarations. |

## 5. DEV studies (builder)

- Each study is one script whose rules, seeds and verdicts are in its docstring. The script is committed, and pushed, before it runs. If the push is unavailable, send the commit and the script's SHA-256 to Daniel before running, as an external anchor, and say so in the evidence README. Its evidence goes to `evidence/<study>/`, together with a README, the console log and the rows.
- Hosts are always fresh DEV hosts. Each study excludes the hosts named in earlier evidence: `scripts/b20r23_e1b_readiness.py` (`named_hosts`) scans every JSON and JSONL file under `evidence/` and `handoff/`, and `scripts/b20r12_e1_redo.py` regenerates the E1 hosts. Budgets are matched in CPU, counting child processes where they exist (`discovery.construct.Budget`).
- A fair negative result is kept, and so is every attempt in a family. A follow-up is a new, separately preregistered step. A threshold is never changed after a result.

## 6. Storage

- The source and evidence live on GitHub `ensiferum21/genesis`: branch `continuation-b20-rx`, plus the `archive` branch with the checkpoint zips, patches, inputs and `SHA256SUMS`.
- Tag pushes are refused by the session proxy, so checkpoint commits are recorded in `archive/README.md` and `batch_state.json` instead.
- Store backups: `genesis store backup ROOT --out B.zip`. Restore with `genesis store restore NEW --from B.zip --expected-head H`, pinning the head to an independently recorded value.
