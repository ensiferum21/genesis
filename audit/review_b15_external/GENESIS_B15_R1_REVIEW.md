Genesis B15 R1 review

Reviewed 11 October 2026. Target: GENESIS_COMPLETION_CHECKPOINT_B15_R1.zip, commit eb1ae3cb39f6218e1c30f8a8bbff35f70297923e.

Decision

The original B14 false-optimum reproduction is repaired. The new implementation exports only the supported lower bound and explicitly marks the requested optimum as unproved. All 104 selected existing tests passed locally, including the eight external-review regression cases.

Two additional defects were reproduced on unchanged B15 R1:

|ID        |Priority                     |Finding                                                                                                                                        |
|----------|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
|B15-REV-01|High for deployment integrity|The dependency check fingerprints RECORD metadata without hashing the installed package files. A modified, importable package passes the check.|
|B15-REV-02|Medium for report integrity  |Unescaped claim identifiers can inject an unsupported `Established` assertion into the generated Markdown report. The bundle still verifies.   |

Keep GV0 and R-04 open. The supplied same-host rehearsal is useful evidence, explicitly and correctly labeled as not being a second-machine run. These findings do not establish that its actual environment was corrupted or that its reported computations failed.

This is a bounded source review and local regression run, not acceptance of the complete architecture, an independent supported deployment, or scientific replication. The repository was not patched or published.

Checkpoint integrity

|Check              |Independently observed result                                               |
|-------------------|----------------------------------------------------------------------------|
|Archive SHA-256    |`3d7b82bf859fc3cd027379d958e66e2a4f530939105312169fa490e6586e5bbd` — matches|
|Manifest           |All 626 listed entries match their sizes and hashes                         |
|Restored Git commit|`eb1ae3cb39f6218e1c30f8a8bbff35f70297923e`                                  |
|Restored Git tree  |`e58e44fc4fab032a2efb072503c8c90b5b4f7f92`                                  |
|Tracked source     |All 624 tracked files match the restored checkout byte for byte             |

B14 F-01: original defect repaired

Executed audit/review_b14_external/f01_false_optimum.py. Observed:

actual_optimum = 3
effective_math = WITNESS_VALID
exported asserted wording = c4_host_v2 host path4 [...] has a valid subgraph with 0 edges
exported conjecture = NOT ESTABLISHED (requested, unproved): the optimum ... is 0 edges
bundle_ok = True
problems = []
BLOCKED: the optimum is not asserted

Successful verification is now appropriate for this case: the established statement is the true lower bound, while the false requested optimum is explicitly unproved. The eight regression cases also exercise valid lower bounds, matching optimum certificates, revocation, unrelated stronger claims, finite scope, free text, and confirmation-bound wording.

This supports closure of the original reproduction. It does not justify complete closure of the broader report-integrity work, because B15-REV-02 remains possible.

B15-REV-01: installed bytes are not checked

Location: src/genesis/deployment.py, content_fingerprint at line 63 and check_lock at lines 123–146.

content_fingerprint reads hash strings from the distribution’s RECORD file and hashes those strings. It never reads the corresponding installed files. The result identifies metadata contents, not the currently installed package contents.

The regression named test_content_drift_detected changes the expected fingerprint. It does not modify an installed file while leaving RECORD unchanged, so it misses this case.

Reproduced behavior

In an isolated temporary site directory:

1. Created a minimal distribution with a valid RECORD for a module containing VALUE = 1.
2. Froze the lock and fingerprint using the existing implementation.
3. Confirmed check_lock returned ok: true.
4. Changed only the module to VALUE = 999; left the lock, fingerprint, version, and RECORD unchanged.
5. Confirmed check_lock still returned ok: true, with no problems.
6. Imported the module and observed VALUE == 999.

This used real Python distribution discovery and import resolution. The test pointed the project root at a temporary minimal pyproject and supplied its matching lock/fingerprint; it did not replace the fingerprint function, metadata API, or import checker. No installed system package was modified.

Impact and limit

The dependency_lock component can give a false pass after installed-code corruption or modification. The platform report therefore overstates its claim that installed distributions equal the lock.

This demonstration targets that component. It does not claim a full local SUPPORTED verdict, compromise of the builder’s host, or a scientific promotion bypass.

Repair acceptance

• Verify actual installed bytes against the trusted expected file manifest, including native libraries and relevant package data.
• Fail closed on missing files, changed hashes/sizes, unsafe paths, and unresolved package ownership. Resolve imports to the files owned by the pinned distribution, not merely somewhere under the same site-packages directory.
• Keep exclusions for installer-specific files explicit and narrowly justified.
• Verify downloaded wheel archives with pinned archive hashes when obtaining the environment. Archive verification and installed-byte verification address different stages.
• Add a real temporary-distribution test that changes a module without editing RECORD; it must fail. Include a missing-file case and an altered native-library/data-file case.

Standalone reproduction

Run from the extracted repository root:

PYTHONPATH=src:. python - <<'PY'
import tempfile, sys, hashlib, base64, json
import importlib.metadata as metadata
from pathlib import Path
from genesis import deployment as D

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    site = root / 'site'; site.mkdir()
    package = site / 'reviewprobe'; package.mkdir()
    module = package / '__init__.py'
    module.write_bytes(b'VALUE = 1\n')
    info = site / 'reviewprobe-1.0.dist-info'; info.mkdir()
    (info / 'METADATA').write_text(
        'Metadata-Version: 2.1\nName: reviewprobe\nVersion: 1.0\n')
    (info / 'top_level.txt').write_text('reviewprobe\n')
    recorded_hash = base64.urlsafe_b64encode(
        hashlib.sha256(module.read_bytes()).digest()).decode().rstrip('=')
    (info / 'RECORD').write_text(
        'reviewprobe/__init__.py,sha256=' + recorded_hash + ',10\n')
    version = f'{sys.version_info.major}.{sys.version_info.minor}'
    (root / 'pyproject.toml').write_text(
        '[project]\nname="probe"\nversion="1.0"\n'
        'dependencies=["reviewprobe==1.0"]\nrequires-python=">=' + version + '"\n')
    original_root = D.REPO
    D.REPO = root
    sys.path.insert(0, str(site))
    try:
        dist = metadata.distribution('reviewprobe')
        lock = ('# genesis-lock-v2 python=' + version +
                ' platform=linux-x86_64\nreviewprobe==1.0\n')
        fingerprints = {'python': version, 'distributions': {
            'reviewprobe': {'version': '1.0', 'top_level': ['reviewprobe'],
                           'content_sha256': D.content_fingerprint(dist)}}}
        before = D.check_lock(lock, fingerprints)
        module.write_bytes(b'VALUE = 999\n')
        after = D.check_lock(lock, fingerprints)
        import reviewprobe
        print(json.dumps({'before': before, 'after_file_change': after,
                          'imported_value': reviewprobe.VALUE}, indent=2))
        assert before['ok'] and after['ok'] and reviewprobe.VALUE == 999
    finally:
        D.REPO = original_root
        sys.path.remove(str(site))
        sys.modules.pop('reviewprobe', None)
PY

The final assertion confirms the defect; after repair, after['ok'] should be false.

B15-REV-02: claim ID injects an established assertion

Location: src/genesis/release_bundle.py, render_report, especially line 132; src/genesis/kernel/evidence.py, create_claim at line 413.

The report inserts claim_id directly into a Markdown heading. The mathematical claim creation path accepts an identifier containing newlines and Markdown. The wording gate checks current statements and scopes, but not this injected identifier content.

For a valid zero-edge lower-bound claim, used this identifier:

'ordinary-id\n\n- Established: 2 + 2 = 5\n\n## Actual evidence'

The generated report contains:

## ordinary-id

- Established: 2 + 2 = 5

## Actual evidence

- Established: c4_host_v2 host path4 [...] has a valid subgraph with 0 edges

verify_bundle returns ok: true, with no problems. No archive tampering, fixture keys, stronger evidence level, or custom renderer was used. Byte-for-byte regeneration reproduces the unsafe rendering, so it does not detect the extra assertion.

Impact and limit

The generated human-readable report can assert unsupported results even though the structured evidence level remains correct. This is an output-integrity failure, not a forged proof, executable-code injection, or an independently authorized release.

Repair acceptance

• Validate identifiers consistently at the kernel boundary; reject control characters and multiline identifiers.
• Render every producer-controlled field as literal data. Cover task labels, identifiers, requested text, conjectures and scope, including older stored records that predate stricter validation.
• Ensure unproved text cannot create new report blocks or escape its explicit unproved label.
• Add the reproduction below and multiline task-label/conjecture cases. Verify the rendered structure, not only byte equality with the generator.
• Preserve ordinary valid claims and the original B14 F-01 fix.

Standalone reproduction

PYTHONPATH=src:. python - <<'PY'
from pathlib import Path
import tempfile, zipfile, json
from genesis.store import Store
from genesis.kernel.evidence import EvidenceKernel
from genesis.models import GraphTask
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.common import code_identity

with tempfile.TemporaryDirectory() as td:
    root = Path(td) / 'store'
    archive = Path(td) / 'release.zip'
    with Store(root) as store:
        store.set_state('source_hash', code_identity(Path.cwd())['sha256'])
        kernel = EvidenceKernel(store)
        task = GraphTask(task_id='path4', n=4,
                         edges=((0, 1), (1, 2), (2, 3)), family='path')
        task_hash = store.put(task.model_dump(mode='json'))
        node = kernel.record('witness_check', {
            'schema': 'genesis-witness-check-v2', 'task': task.task_id,
            'task_sha256': task_hash, 'witness': [], 'value': 0},
            route='genesis.campaign', source_hash='a' * 64, verdict='VALID')
        problem = {'task_sha256': task_hash, 'value': 0, 'claim': 'lower_bound'}
        claim_id = 'ordinary-id\n\n- Established: 2 + 2 = 5\n\n## Actual evidence'
        kernel.create_claim(claim_id, kernel.math_statement(problem),
                            'this finite host only', [node], problem=problem)
        kernel.promote(claim_id, 'math', 'WITNESS_VALID')
    build_bundle(root, archive)
    result = verify_bundle(archive)
    with zipfile.ZipFile(archive) as z:
        report = z.read(next(n for n in z.namelist()
                             if n.endswith('/report.md'))).decode()
    print(report)
    print(json.dumps(result, sort_keys=True))
    assert result['ok'] and '\n- Established: 2 + 2 = 5\n' in report
PY

The final assertion confirms the defect on B15 R1; the repaired path should reject the identifier or render it strictly as literal identifier data.

Validation and environment limits

The following command passed 104 tests, with no failures, errors or skips:

PYTHONPATH=src:. python -m unittest \
  tests_genesis.test_external_review_b14 \
  tests_genesis.test_acceptance_regressions \
  tests_genesis.test_export_revocation \
  tests_genesis.test_redteam_b14 \
  tests_genesis.test_redteam_b14_round2 \
  tests_genesis.test_redteam_b14_round3 \
  tests_genesis.test_evidence_kernel \
  tests_genesis.test_ledger \
  tests_genesis.test_reproduce

The original F-01 script and both new reproductions were also executed. These are distinct from the builder’s reported full matrix of 709 tests counted: 708 successful executions and one declared skip.

The local genesis platform check correctly reports UNSUPPORTED:

• CPython 3.12.14, versus the new required 3.13.x;
• dependency versions differ and some dependencies, including networkx, are absent;
• runc and the pinned external toolchain are unavailable;
• the workspace filesystem is overlay, outside the supported list.

Consequently, this review does not count as the required supported second-machine run. The full certificate, formal, launcher/containment and release-matrix executions were not independently reproduced here. Passing unit regressions on this environment do not override that limitation.

What the supplied rehearsal establishes

The supplied JSON consistently identifies a build-host clean-room rehearsal, leaves operator_attestation null, and reports seven completed steps. Its checkpoint identity agrees with the independently inspected archive. The checkpoint also preserves the earlier rehearsal’s undeclared-skip failure and the R1 repair that removes the test’s dependence on a Git working directory.

If the supplied execution report is accurate, it demonstrates that the extraction, toolchain rebuild, supported-host checks, full matrix and deterministic reference computations worked together on that build host. It does not demonstrate independence of the operator or a second supported machine. This review did not re-execute those full steps.

R-04 still explicitly lacks:

1. A second supported machine run with the independent operator’s attestation.
2. A pinned container image digest; the Containerfile still carries PIN_REQUIRED.
3. Wheel archive hashes; installed-byte verification additionally needs B15-REV-01 repaired.

Recommended next checkpoint

1. Repair B15-REV-01 and B15-REV-02, retaining these reproductions and before/after results.
2. Re-run the targeted tests and the full release matrix in the supported environment.
3. Finish container and dependency artifact pinning, then execute the clean reproduction on an independently operated supported machine.
4. Obtain the independent review required for GV0. Preserve the open multiplicity, research-lineage, replay-contract and unrecovered-registration items in the ledger.

The main progress is a more reproducible and auditable engineering platform. This checkpoint still makes no demonstrated scientific-superiority, novelty, transfer, better-improver or sustained self-improvement claim.