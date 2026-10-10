"""Certificate custody and checker-only replay (roadmap W03, defect R-03).

A CertificateBundle carries everything needed to re-check a BoundState without
the program that produced it:

* the exact problem (task JSON and its hash, domain);
* the lower witness, re-checked by the dual graph predicates;
* the upper justification, one of
    - SAT_DRAT: the original CNF and DRAT proof (as content-addressed objects),
      the encoding name, producer and checker identities and the checker verdict;
    - HOST_EDGE_COUNT: the trivial bound "a subgraph has at most every host edge";
    - THEOREM: a published bound (named), recorded but NOT independently checked,
      so it can never support OPTIMALITY_CHECKED;
* the replay command.

`replay` never invokes the producing solver: it re-derives the CNF from the
problem, compares it byte-for-byte (by hash) with the stored CNF, and runs the
pinned proof checker on the stored proof. Missing or altered proof objects
make the upper side REJECTED, which blocks the corresponding status.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from ..common import canonical, digest
from ..graphs import check_witness
from ..models import GraphTask

SCHEMA = 'genesis-certificate-bundle-v1'
CHECKED_METHODS = ('SAT_DRAT', 'HOST_EDGE_COUNT')
REPLAY = 'python -m genesis.verification.certificates <bundle.json> --objects <objects/sha256 directory>'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def build(task, bounds):
    """CertificateBundle + raw objects {sha256: bytes} from a `certified_bounds` result."""
    from .sat import ENCODING, encode
    task_json = task.model_dump(mode='json')
    witness = [list(e) for e in (bounds.get('witness') or ())]
    lower = {'value': bounds['lower'], 'witness': witness,
             'checker': 'genesis.graphs.check_witness (dual predicates)'}
    up = dict(bounds.get('upper_certificate') or {})
    method = up.get('method')
    blobs = {}
    if method == 'SAT_DRAT':
        cnf = encode(task, up['upper'] + 1)
        proof = bounds.get('proof')
        if not proof or _sha(cnf) != up.get('cnf_sha256') or _sha(proof) != up.get('proof_sha256'):
            raise ValueError('SAT_DRAT certificate without its original CNF/proof bytes cannot be taken into custody')
        blobs[_sha(cnf)] = cnf
        blobs[_sha(proof)] = proof
        upper = {'method': 'SAT_DRAT', 'value': up['upper'], 'encoding': ENCODING, 'cnf_sha256': _sha(cnf),
                 'proof_sha256': _sha(proof), 'proof_bytes': len(proof), 'producer': up.get('solver'),
                 'checker': up.get('checker'), 'checker_verdict': up.get('verdict'),
                 'checker_output_tail': up.get('checker_output_tail')}
    elif method == 'HOST_EDGE_COUNT' or (method is not None and up.get('upper') == len(task.edges)):
        upper = {'method': 'HOST_EDGE_COUNT', 'value': len(task.edges),
                 'justification': 'every subgraph of the host has at most all host edges'}
    else:
        upper = {'method': 'THEOREM', 'theorem': method, 'value': up.get('upper', bounds.get('upper')),
                 'justification': 'published bound; recorded, not independently checked here'}
    gap = upper['value'] - lower['value']
    status = ('OPTIMALITY_CHECKED' if gap == 0 and upper['method'] in CHECKED_METHODS else
              'OPTIMALITY_BY_THEOREM_UNCHECKED' if gap == 0 else 'BOUNDS_ONLY')
    bundle = {'schema': SCHEMA, 'problem': {'domain': task.domain, 'task': task_json, 'task_sha256': digest(task_json)},
              'lower': lower, 'upper': upper, 'gap': gap, 'status': status, 'replay': REPLAY}
    return bundle, blobs


def persist(store, bundle, blobs):
    """Write objects then the bundle into the store's CAS; returns the bundle identity."""
    for h, data in blobs.items():
        if store.put_bytes(data) != h:
            raise RuntimeError('object identity mismatch')
    return store.put(bundle)


def custody_problems(bundle, has_object):
    """Structural custody check (no tools run): is everything needed for replay present?"""
    if not isinstance(bundle, dict) or bundle.get('schema') != SCHEMA:
        return ['not a certificate bundle']
    out = []
    up = bundle.get('upper') or {}
    if up.get('method') not in CHECKED_METHODS:
        out.append(f'upper bound is not independently certified (method {up.get("method")})')
    if up.get('method') == 'SAT_DRAT':
        for k in ('cnf_sha256', 'proof_sha256'):
            if not has_object(up.get(k)):
                out.append(f'{k[:-7]} object missing or altered')
        if up.get('checker_verdict') != 'VALID':
            out.append('recorded checker verdict is not VALID')
    if digest(bundle['problem']['task']) != bundle['problem']['task_sha256']:
        out.append('problem hash mismatch')
    return out


def replay(bundle, get_bytes):
    """Checker-only reproduction. Returns {'status', 'lower', 'upper', 'problems'}."""
    problems = []
    if not isinstance(bundle, dict) or bundle.get('schema') != SCHEMA:
        return {'status': 'REJECTED', 'lower': 'REJECTED', 'upper': 'REJECTED', 'problems': ['not a certificate bundle']}
    task = GraphTask.model_validate_json(canonical(bundle['problem']['task']))
    if digest(task.model_dump(mode='json')) != bundle['problem']['task_sha256']:
        problems.append('problem does not match its hash')
    try:
        checked = check_witness(task, tuple(tuple(e) for e in bundle['lower']['witness']))
        lower = 'VALID' if checked['value'] == bundle['lower']['value'] else 'REJECTED'
    except Exception as exc:
        lower = 'REJECTED'; problems.append(f'lower witness rejected: {type(exc).__name__}')
    up = bundle['upper']
    if up['method'] == 'HOST_EDGE_COUNT':
        upper = 'VALID' if up['value'] == len(task.edges) else 'REJECTED'
    elif up['method'] == 'SAT_DRAT':
        from .sat import ENCODING, check_proof, encode
        try:
            cnf, proof = get_bytes(up['cnf_sha256']), get_bytes(up['proof_sha256'])
        except Exception as exc:
            cnf = proof = None; problems.append(f'proof object missing or altered ({type(exc).__name__})')
        if cnf is None or proof is None:
            upper = 'REJECTED'
        elif up.get('encoding') != ENCODING or encode(task, up['value'] + 1) != cnf:
            upper = 'REJECTED'; problems.append('stored CNF is not the encoding of this problem and bound')
        elif _sha(proof) != up['proof_sha256'] or _sha(cnf) != up['cnf_sha256']:
            upper = 'REJECTED'; problems.append('object hash mismatch')
        else:
            upper = check_proof(cnf, proof)[0]
            if upper != 'VALID':
                problems.append(f'proof checker verdict {upper}')
    else:
        upper = 'NOT_INDEPENDENTLY_CHECKED'
    gap = up['value'] - bundle['lower']['value']
    if lower == 'VALID' and upper == 'VALID':
        status = 'OPTIMALITY_CHECKED' if gap == 0 else 'BOUNDS_CHECKED'
    elif upper == 'CHECKER_ERROR':
        status = 'CHECKER_ERROR'
    elif lower == 'REJECTED' or upper == 'REJECTED':
        status = 'REJECTED'
    else:
        status = 'UNSETTLED'
    if bundle.get('status') == 'OPTIMALITY_CHECKED' and status != 'OPTIMALITY_CHECKED':
        problems.append(f'recorded OPTIMALITY_CHECKED does not replay (replayed {status})')
    return {'status': status, 'lower': lower, 'upper': upper, 'gap': gap, 'problems': problems}


def main(argv=None):
    p = argparse.ArgumentParser(description='Checker-only replay of a Genesis certificate bundle')
    p.add_argument('bundle', type=Path)
    p.add_argument('--objects', type=Path, required=True)
    a = p.parse_args(argv)
    os.environ['GENESIS_CHECKER_ONLY'] = '1'

    def get_bytes(h):
        data = (a.objects / h).read_bytes()
        if _sha(data) != h:
            raise RuntimeError('object corruption')
        return data

    result = replay(json.loads(a.bundle.read_bytes()), get_bytes)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] in ('OPTIMALITY_CHECKED', 'BOUNDS_CHECKED') and not result['problems'] else 1


if __name__ == '__main__':
    sys.exit(main())
