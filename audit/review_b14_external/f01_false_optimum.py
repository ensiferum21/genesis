"""F-01 from the external B14 review (verbatim logic): a false optimum statement exported
and verified while its effective level is only WITNESS_VALID. Prints the observed values;
exit 1 if the vulnerable behaviour is present (an asserted false optimum that verifies)."""
from pathlib import Path
import json
import sys
import tempfile
import zipfile
from genesis.common import code_identity
from genesis.graphs import check_witness, exact_checker
from genesis.kernel.evidence import EvidenceKernel
from genesis.models import GraphTask
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.store import Store

with tempfile.TemporaryDirectory() as d:
    root = Path(d) / 'campaign'
    archive = Path(d) / 'release.zip'
    task = GraphTask(task_id='path4', n=4, edges=((0, 1), (1, 2), (2, 3)), family='path')
    with Store(root) as store:
        store.set_state('source_hash', code_identity(Path.cwd())['sha256'])
        kernel = EvidenceKernel(store)
        task_hash = store.put(task.model_dump(mode='json'))
        payload = {'schema': 'genesis-witness-check-v2', 'task': task.task_id, 'task_sha256': task_hash,
                   'witness': [], 'value': 0}
        assert check_witness(task, ())['value'] == 0
        node = kernel.record('witness_check', payload, route='genesis.campaign', source_hash='a' * 64, verdict='VALID')
        problem = {'task_sha256': task_hash, 'value': 0, 'claim': 'optimum'}
        statement = kernel.math_statement(problem)
        kernel.create_claim('false-optimum', statement, 'this finite host only', [node], problem=problem)
        kernel.promote('false-optimum', 'math', 'WITNESS_VALID')
        print(statement)
        print('actual_optimum =', exact_checker(task)['value'])
        print('effective_math =', kernel.levels('false-optimum')['math'])
    build_bundle(root, archive)
    result = verify_bundle(archive)
    with zipfile.ZipFile(archive) as z:
        claims = json.loads(z.read(next(n for n in z.namelist() if n.endswith('/CLAIMS.json'))))['claims']
    exported = claims[0]
    asserted = exported.get('current_statement', exported.get('statement'))
    print('exported asserted wording =', asserted)
    print('exported conjecture =', exported.get('conjecture'))
    print('bundle_ok =', result['ok'])
    print('problems =', result['problems'])
    vulnerable = result['ok'] and asserted is not None and 'optimum' in asserted
    print('VULNERABLE' if vulnerable else 'BLOCKED: the optimum is not asserted')
    sys.exit(1 if vulnerable else 0)
