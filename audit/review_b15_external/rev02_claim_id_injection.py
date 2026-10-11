# B15-REV-02 reproduction, verbatim from the external review.
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
