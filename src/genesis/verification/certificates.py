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


class checker_only:
    """Context: the producing solver refuses to run (sat.solve checks GENESIS_CHECKER_ONLY)."""

    def __enter__(self):
        self.previous = os.environ.get('GENESIS_CHECKER_ONLY')
        os.environ['GENESIS_CHECKER_ONLY'] = '1'
        return self

    def __exit__(self, *exc):
        if self.previous is None:
            os.environ.pop('GENESIS_CHECKER_ONLY', None)
        else:
            os.environ['GENESIS_CHECKER_ONLY'] = self.previous


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


# ---------------------------------------------------------------- bundle v2 (B20_R1, Repair D)
#
# v2 adds the exact LP dual method used by the B19 joint certification loop, keeps the
# original CNF/DRAT bytes of SAT certificates, keeps the lower witness as an object, and
# records every LP/SAT attempt and the checker identities. v1 readers reject v2 bundles
# (schema mismatch); v1 bundles keep their original semantics. The supported mathematical
# inequalities are unchanged.

SCHEMA_V2 = 'genesis-certificate-bundle-v2'
CHECKED_METHODS_V2 = ('SAT_DRAT', 'HOST_EDGE_COUNT', 'LP_DUAL_EXACT', 'PAIR_COUNT_LEAN')
# PAIR_COUNT_LEAN (CRPD-2b): the C4 pair-count bound 4m^2 <= n^2 (n - 1) + 2nm, a Lean-checked theorem
# (invention.pair_count; evidence/pair_count_b20r). The bundle carries the theory package as an
# object; replay re-checks the host contract, recomputes the bound from n alone and replays the
# package in the pinned workspace. v1 bundles keep recording this bound as an unchecked THEOREM.
OBJECTIVE = 'maximum number of host edges in a motif-free subgraph (domain motif)'


def build_v2(task, *, witness, lower, upper, attempts=()):
    """Bundle v2 + raw objects {sha256: bytes}.

    upper: {'method': 'HOST_EDGE_COUNT'}
         | {'method': 'LP_DUAL_EXACT', 'certificate': <lp dual certificate>, 'lp_value_float': float}
         | {'method': 'PAIR_COUNT_LEAN', 'package': <checked pair-count theory package>}
         | {'method': 'SAT_DRAT', 'certificate': <sat certificate>, 'cnf': bytes, 'proof': bytes}
    A certificate whose own checker verdict is not VALID, or whose objects are missing,
    cannot be taken into custody as a checked upper bound (ValueError).
    """
    from .lp_dual import check_certificate, checker_identity
    task_json = task.model_dump(mode='json')
    blobs = {}
    wbytes = canonical([list(e) for e in witness])
    blobs[_sha(wbytes)] = wbytes
    lower_rec = {'value': lower, 'witness': [list(e) for e in witness], 'witness_sha256': _sha(wbytes),
                 'checker': 'genesis.graphs.check_witness (dual predicates)'}
    method = upper.get('method')
    if method == 'HOST_EDGE_COUNT':
        up = {'method': 'HOST_EDGE_COUNT', 'value': len(task.edges),
              'justification': 'every subgraph of the host has at most all host edges'}
    elif method == 'LP_DUAL_EXACT':
        cert = upper['certificate']
        verdict = check_certificate(task, cert)
        if verdict['verdict'] != 'VALID':
            raise ValueError(f'LP certificate does not check: {verdict["reason"]}')
        cbytes = canonical(cert)
        blobs[_sha(cbytes)] = cbytes
        up = {'method': 'LP_DUAL_EXACT', 'value': verdict['bound'], 'certificate_sha256': _sha(cbytes),
              'certificate_schema': cert['schema'], 'objective_rational': cert['objective'],
              'rounding': 'floor of the exact rational dual objective (integer primal)',
              'producer': 'scipy.optimize.linprog/HiGHS (untrusted float proposal, repaired exactly)',
              'lp_value_float': upper.get('lp_value_float'), 'checker': checker_identity(),
              'checker_verdict': 'VALID', 'validity_lemma': 'motif_not_all (B19 obstruction Lean package)'}
    elif method == 'SAT_DRAT':
        from .sat import ENCODING, encode
        cert, cnf, proof = upper['certificate'], upper.get('cnf'), upper.get('proof')
        if not cnf or not proof or _sha(cnf) != cert.get('cnf_sha256') or _sha(proof) != cert.get('proof_sha256'):
            raise ValueError('SAT_DRAT certificate without its original CNF/proof bytes cannot be taken into custody')
        if encode(task, cert['upper'] + 1) != cnf:
            raise ValueError('stored CNF is not the encoding of this task and bound')
        if cert.get('verdict') != 'VALID':
            raise ValueError('SAT_DRAT certificate was not verified by its checker')
        blobs[_sha(cnf)] = cnf
        blobs[_sha(proof)] = proof
        up = {'method': 'SAT_DRAT', 'value': cert['upper'], 'encoding': ENCODING, 'cnf_sha256': _sha(cnf),
              'proof_sha256': _sha(proof), 'proof_bytes': len(proof), 'producer': cert.get('solver'),
              'checker': cert.get('checker'), 'checker_verdict': cert.get('verdict'),
              'checker_output_tail': cert.get('checker_output_tail')}
    elif method == 'PAIR_COUNT_LEAN':
        from ..invention import pair_count as PC
        package = upper.get('package')
        why = PC.applicability_problems(task) + PC.package_problems(package)
        if why:
            raise ValueError('pair-count bound cannot be taken into custody: ' + '; '.join(why))
        verdict = PC.replay_verdict(package)
        if verdict != 'REPLAYED':
            raise ValueError(f'pair-count theory package does not replay: {verdict}')
        pbytes = canonical(package)
        blobs[_sha(pbytes)] = pbytes
        up = {'method': 'PAIR_COUNT_LEAN', 'value': PC.quadratic_upper(task.n), 'package_sha256': _sha(pbytes),
              'theory_package_sha256': package['package_sha256'], 'statement': PC.STATEMENT_ID,
              'lean_statement': PC.expected_statement(), 'checker': PC.checker_identity(),
              'checker_verdict': 'REPLAYED',
              'justification': 'largest m with 4m^2 <= n^2 (n - 1) + 2nm, by the Lean-checked C4 pair-count bound'}
    else:
        raise ValueError(f'unsupported upper-bound method {method!r}')
    gap = up['value'] - lower
    if gap < 0:
        raise ValueError('lower witness exceeds the certified upper bound: inconsistent bounds')
    bundle = {'schema': SCHEMA_V2, 'problem': {'domain': task.domain, 'task': task_json, 'task_sha256': digest(task_json),
                                                'objective': OBJECTIVE},
              'lower': lower_rec, 'upper': up, 'gap': gap, 'status': 'OPTIMALITY_CHECKED' if gap == 0 else 'BOUNDS_ONLY',
              'attempts': json.loads(canonical(list(attempts))), 'replay': REPLAY}
    return bundle, blobs


def persist_dir(root, bundle, blobs):
    """Write objects then the bundle to a content-addressed directory; returns the bundle sha256."""
    root = Path(root)
    (root / 'objects').mkdir(parents=True, exist_ok=True)
    for h, data in blobs.items():
        if _sha(data) != h:
            raise RuntimeError('object identity mismatch')
        p = root / 'objects' / h
        if not p.exists():
            p.write_bytes(data)
    data = canonical(bundle)
    h = _sha(data)
    (root / 'bundles').mkdir(parents=True, exist_ok=True)
    (root / 'bundles' / f'{h}.json').write_bytes(data)
    return h


def _custody_problems_v2(bundle, has_object, revoked_checkers=()):
    out = []
    up = bundle.get('upper') or {}
    low = bundle.get('lower') or {}
    if up.get('method') not in CHECKED_METHODS_V2:
        out.append(f'upper bound is not independently certified (method {up.get("method")})')
    if not has_object(low.get('witness_sha256')):
        out.append('lower witness object missing or altered')
    if up.get('method') == 'SAT_DRAT':
        for k in ('cnf_sha256', 'proof_sha256'):
            if not has_object(up.get(k)):
                out.append(f'{k[:-7]} object missing or altered')
        if up.get('checker_verdict') != 'VALID':
            out.append('recorded checker verdict is not VALID')
    if up.get('method') == 'LP_DUAL_EXACT':
        if not has_object(up.get('certificate_sha256')):
            out.append('LP certificate object missing or altered')
        if up.get('checker') in set(revoked_checkers):
            out.append('LP certificate checker identity is revoked')
    if up.get('method') == 'PAIR_COUNT_LEAN':
        if not has_object(up.get('package_sha256')):
            out.append('pair-count theory package object missing or altered')
        if up.get('checker') in set(revoked_checkers):
            out.append('pair-count Lean replay identity is revoked')
    try:
        if digest(bundle['problem']['task']) != bundle['problem']['task_sha256']:
            out.append('problem hash mismatch')
    except (KeyError, TypeError):
        out.append('problem missing')
    if isinstance(up.get('value'), int) and isinstance(low.get('value'), int) and low['value'] > up['value']:
        out.append('lower bound exceeds upper bound')
    if bundle.get('status') == 'OPTIMALITY_CHECKED' and bundle.get('gap') != 0:
        out.append('OPTIMALITY_CHECKED recorded with a non-zero gap')
    return out


def _replay_v2(bundle, get_bytes, revoked_checkers=()):
    from .lp_dual import check_certificate, checker_identity
    problems = []
    task = GraphTask.model_validate_json(canonical(bundle['problem']['task']))
    if digest(task.model_dump(mode='json')) != bundle['problem']['task_sha256']:
        problems.append('problem does not match its hash')
    low = bundle['lower']
    try:
        wit = json.loads(get_bytes(low['witness_sha256']))
        if [list(e) for e in wit] != low['witness']:
            raise ValueError('witness object differs from the recorded witness')
        checked = check_witness(task, tuple(tuple(e) for e in wit))
        lower = 'VALID' if checked['value'] == low['value'] else 'REJECTED'
        if lower != 'VALID':
            problems.append('lower witness value does not match')
    except Exception as exc:
        lower = 'REJECTED'
        problems.append(f'lower witness rejected: {type(exc).__name__}')
    up = bundle['upper']
    dead = set(revoked_checkers)
    if up['method'] == 'HOST_EDGE_COUNT':
        upper = 'VALID' if up['value'] == len(task.edges) else 'REJECTED'
    elif up['method'] == 'LP_DUAL_EXACT':
        if checker_identity() in dead or up.get('checker') in dead:
            upper = 'REJECTED'
            problems.append('LP checker identity is revoked')
        else:
            try:
                v = check_certificate(task, json.loads(get_bytes(up['certificate_sha256'])))
                if v['verdict'] != 'VALID':
                    upper = 'REJECTED'
                    problems.append(f'LP certificate rejected: {v["reason"]}')
                elif v['bound'] != up['value']:
                    upper = 'REJECTED'
                    problems.append('LP certificate certifies a different bound')
                else:
                    upper = 'VALID'
            except Exception as exc:
                upper = 'REJECTED'
                problems.append(f'LP certificate missing or altered ({type(exc).__name__})')
    elif up['method'] == 'SAT_DRAT':
        from .sat import ENCODING, check_proof, encode
        try:
            cnf, proof = get_bytes(up['cnf_sha256']), get_bytes(up['proof_sha256'])
        except Exception as exc:
            cnf = proof = None
            problems.append(f'proof object missing or altered ({type(exc).__name__})')
        if cnf is None or proof is None:
            upper = 'REJECTED'
        elif up.get('encoding') != ENCODING or encode(task, up['value'] + 1) != cnf:
            upper = 'REJECTED'
            problems.append('stored CNF is not the encoding of this problem and bound')
        elif _sha(proof) != up['proof_sha256'] or _sha(cnf) != up['cnf_sha256']:
            upper = 'REJECTED'
            problems.append('object hash mismatch')
        elif up.get('checker') in dead:
            upper = 'REJECTED'
            problems.append('DRAT checker identity is revoked')
        else:
            upper = check_proof(cnf, proof)[0]
            if upper != 'VALID':
                problems.append(f'proof checker verdict {upper}')
    elif up['method'] == 'PAIR_COUNT_LEAN':
        upper, why = _replay_pair_count(task, up, get_bytes, dead)
        problems += why
    else:
        upper = 'REJECTED'
        problems.append(f'unsupported upper-bound method {up["method"]!r}')
    gap = up['value'] - low['value']
    if lower == 'VALID' and upper == 'VALID':
        if gap < 0:
            status = 'REJECTED'
            problems.append('lower bound exceeds upper bound')
        else:
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


def _replay_pair_count(task, up, get_bytes, dead):
    """(verdict, problems) for a PAIR_COUNT_LEAN upper bound. The value is recomputed from n alone;
    the stored package must be the checked statement over the repository definitions and must
    replay in the pinned workspace (CHECKER_ERROR when that workspace is unavailable here)."""
    from ..invention import pair_count as PC
    if up.get('checker') in dead or PC.checker_identity() in dead:
        return 'REJECTED', ['pair-count Lean replay identity is revoked']
    why = PC.applicability_problems(task)
    if up.get('value') != PC.quadratic_upper(task.n):
        why.append('recorded value is not the pair-count bound for this n')
    try:
        raw = get_bytes(up['package_sha256'])
        if _sha(raw) != up['package_sha256']:
            raise ValueError('object hash mismatch')
        package = json.loads(raw)
    except Exception as exc:
        return 'REJECTED', why + [f'pair-count theory package missing or altered ({type(exc).__name__})']
    why += PC.package_problems(package)
    if package.get('package_sha256') != up.get('theory_package_sha256'):
        why.append('stored package is not the one the bundle names')
    if why:
        return 'REJECTED', why
    verdict = PC.replay_verdict(package)
    if verdict.startswith('CHECKER_ERROR'):
        return 'CHECKER_ERROR', [verdict]
    if verdict != 'REPLAYED':
        return 'REJECTED', [f'pair-count theory package does not replay: {verdict}']
    return 'VALID', []


def custody_problems(bundle, has_object, revoked_checkers=()):
    """Structural custody check (no tools run): is everything needed for replay present?"""
    if isinstance(bundle, dict) and bundle.get('schema') == SCHEMA_V2:
        return _custody_problems_v2(bundle, has_object, revoked_checkers)
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


def replay(bundle, get_bytes, revoked_checkers=()):
    """Checker-only reproduction. Returns {'status', 'lower', 'upper', 'problems'}."""
    problems = []
    if isinstance(bundle, dict) and bundle.get('schema') == SCHEMA_V2:
        return _replay_v2(bundle, get_bytes, revoked_checkers)
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
