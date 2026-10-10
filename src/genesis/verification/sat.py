"""SAT upper-bound certificates for forbidden-subgraph host problems (spec §5.5, §8, §27).

Claim certified: "every C4-free (or triangle-free) subgraph of host H has at
most U edges". Encoding: one variable per host edge, one clause per forbidden
motif in H, and a Sinz sequential counter forcing at least U+1 chosen edges.
CaDiCaL (untrusted producer) must report UNSAT and emit a DRAT proof;
drat-trim (separately implemented, pinned checker) must print `s VERIFIED`.
The verifier re-derives the CNF from (H, U) itself and compares hashes before
checking, so a certificate cannot be replayed against a weaker formula.

Lower bounds come from SAT models or other witnesses and are always re-checked
by the dual graph predicates. A BoundState is OPTIMALITY_CHECKED only when the
lower witness and the verified upper certificate meet.
"""
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

from ..common import digest
from ..graphs import check_witness, motifs, universal_upper
from .tools import tool, ToolUnavailable

ENCODING = 'motif-clauses+sinz-at-most-on-negated-edges-v1'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(task, at_least):
    """DIMACS CNF that is satisfiable iff H has a valid subgraph with >= at_least edges."""
    m = len(task.edges)
    if not 1 <= at_least <= m:
        raise ValueError('at_least must be within 1..edge count')
    clauses = []
    for c in motifs(task):
        lits = []
        rest = c
        while rest:
            bit = rest & -rest; rest ^= bit
            lits.append(-(bit.bit_length()))   # edge index i -> variable i+1
        clauses.append(lits)
    # at most K of the negated edge literals are true, K = m - at_least
    K = m - at_least
    nvars = m
    if K == 0:
        clauses.extend([[i] for i in range(1, m + 1)])
    elif K < m:
        def s(i, j):  # 1-based i in 1..m-1, j in 1..K
            return m + (i - 1) * K + j
        nvars = m + (m - 1) * K
        x = lambda i: i  # negation of l_i = not x_i is x_i
        clauses.append([x(1), s(1, 1)])
        clauses.extend([[-s(1, j)] for j in range(2, K + 1)])
        for i in range(2, m):
            clauses.append([x(i), s(i, 1)])
            clauses.append([-s(i - 1, 1), s(i, 1)])
            for j in range(2, K + 1):
                clauses.append([x(i), -s(i - 1, j - 1), s(i, j)])
                clauses.append([-s(i - 1, j), s(i, j)])
            clauses.append([x(i), -s(i - 1, K)])
        clauses.append([x(m), -s(m - 1, K)])
    lines = [f'c genesis {ENCODING} task {digest(task.model_dump(mode="json"))} at_least {at_least}',
             f'p cnf {nvars} {len(clauses)}'] + [' '.join(map(str, cl)) + ' 0' for cl in clauses]
    return ('\n'.join(lines) + '\n').encode()


def _limits(cpu_seconds, memory_mib):
    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS, (memory_mib << 20, memory_mib << 20))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.setsid()
    return apply


def solve(cnf, *, seconds=60, memory_mib=4096):
    """Run CaDiCaL. Returns {'status': SAT|UNSAT|UNKNOWN, 'model', 'proof', 'solver', 'seconds'}."""
    solver = tool('cadical')
    with tempfile.TemporaryDirectory(prefix='genesis-sat-') as d:
        cnf_path = Path(d) / 'f.cnf'; proof_path = Path(d) / 'f.drat'
        cnf_path.write_bytes(cnf)
        start = time.monotonic()
        try:
            proc = subprocess.run([solver['path'], '-q', '--no-binary', '-t', str(int(seconds)), str(cnf_path),
                                   str(proof_path)], capture_output=True, text=True, timeout=seconds + 30,
                                  preexec_fn=_limits(int(seconds) + 5, memory_mib), env={'PATH': '/usr/bin:/bin'})
            code = proc.returncode; out = proc.stdout
        except subprocess.TimeoutExpired:
            code = None; out = ''
        elapsed = time.monotonic() - start
        status = {10: 'SAT', 20: 'UNSAT'}.get(code, 'UNKNOWN')
        model = None
        if status == 'SAT':
            values = []
            for line in out.splitlines():
                if line.startswith('v '):
                    values.extend(int(t) for t in line[2:].split())
            model = {abs(v) for v in values if v > 0}
        proof = proof_path.read_bytes() if status == 'UNSAT' and proof_path.exists() else None
        return {'status': status, 'model': model, 'proof': proof, 'solver': solver['identity'],
                'seconds': round(elapsed, 3), 'exit_code': code}


def check_proof(cnf, proof, *, seconds=300, memory_mib=4096):
    """Run drat-trim. Returns (verdict, output tail): VALID, REJECTED or CHECKER_ERROR."""
    checker = tool('drat-trim')
    with tempfile.TemporaryDirectory(prefix='genesis-drat-') as d:
        cnf_path = Path(d) / 'f.cnf'; proof_path = Path(d) / 'f.drat'
        cnf_path.write_bytes(cnf); proof_path.write_bytes(proof)
        try:
            proc = subprocess.run([checker['path'], str(cnf_path), str(proof_path), '-t', str(int(seconds))],
                                  capture_output=True, text=True, timeout=seconds + 30,
                                  preexec_fn=_limits(int(seconds) + 5, memory_mib), env={'PATH': '/usr/bin:/bin'})
        except subprocess.TimeoutExpired:
            return 'CHECKER_ERROR', 'drat-trim timed out', checker['identity']
        lines = (proc.stdout + proc.stderr).splitlines()
        tail = '\n'.join(lines[-6:])
        if any(l.strip() == 's VERIFIED' for l in lines):
            return 'VALID', tail, checker['identity']
        if any(l.strip() in ('s NOT VERIFIED',) for l in lines):
            return 'REJECTED', tail, checker['identity']
        return 'CHECKER_ERROR', tail, checker['identity']


def certify_upper(task, upper, *, seconds=60):
    """Try to certify optimum <= upper. Returns (certificate | None, solve record, cnf, proof)."""
    m = len(task.edges)
    if upper >= m:
        cert = {'schema': 'genesis-upper-bound-v1', 'method': 'HOST_EDGE_COUNT', 'upper': m,
                'task_sha256': digest(task.model_dump(mode='json')), 'verdict': 'VALID'}
        return cert, {'status': 'TRIVIAL'}, None, None
    cnf = encode(task, upper + 1)
    record = solve(cnf, seconds=seconds)
    if record['status'] != 'UNSAT' or not record['proof']:
        return None, record, cnf, None
    verdict, tail, checker = check_proof(cnf, record['proof'])
    cert = {'schema': 'genesis-upper-bound-v1', 'method': 'SAT_DRAT', 'upper': upper, 'encoding': ENCODING,
            'task_sha256': digest(task.model_dump(mode='json')), 'domain': task.domain,
            'cnf_sha256': _sha(cnf), 'proof_sha256': _sha(record['proof']), 'proof_bytes': len(record['proof']),
            'solver': record['solver'], 'solver_seconds': record['seconds'], 'checker': checker,
            'checker_output_tail': tail, 'verdict': verdict}
    return cert, record, cnf, record['proof']


def verify_upper_certificate(task, cert, proof):
    """Independent replay: re-encode from (task, upper), compare hashes, re-run drat-trim."""
    if cert.get('method') == 'HOST_EDGE_COUNT':
        return 'VALID' if cert['upper'] >= len(task.edges) else 'REJECTED'
    if cert.get('task_sha256') != digest(task.model_dump(mode='json')) or cert.get('encoding') != ENCODING:
        return 'REJECTED'
    cnf = encode(task, cert['upper'] + 1)
    if _sha(cnf) != cert.get('cnf_sha256') or _sha(proof) != cert.get('proof_sha256'):
        return 'REJECTED'
    return check_proof(cnf, proof)[0]


def witness_from_model(task, model):
    return tuple(e for i, e in enumerate(task.edges) if (i + 1) in model)


def certified_bounds(task, *, seconds=120, start_witness=(), per_call_seconds=60):
    """Anytime-correct BoundState search (spec §6.7, §7.3).

    Returns the best checked lower witness, the best certified upper bound and
    the gap. Never reports an optimum unless both sides are independently valid.
    """
    deadline = time.monotonic() + seconds
    witness = check_witness(task, start_witness)['selected'] if start_witness else ()
    lower = len(witness)
    universal = universal_upper(task)
    upper, upper_cert, proof = universal['value'], {'schema': 'genesis-upper-bound-v1',
                                                    'method': universal['method'], 'upper': universal['value'],
                                                    'verdict': 'VALID'}, None
    calls = []
    while lower < upper and time.monotonic() < deadline:
        budget = max(1, min(per_call_seconds, int(deadline - time.monotonic())))
        cert, record, cnf, pf = certify_upper(task, lower, seconds=budget)
        calls.append({'k': lower + 1, 'status': record['status'], 'seconds': record.get('seconds')})
        if cert is not None:
            if cert['verdict'] != 'VALID':
                return {'status': 'CHECKER_ERROR', 'certificate': cert, 'calls': calls}
            upper, upper_cert, proof = lower, cert, pf
            break
        if record['status'] == 'SAT':
            candidate = witness_from_model(task, record['model'])
            checked = check_witness(task, candidate)  # producer output is never trusted
            if checked['value'] <= lower:
                return {'status': 'CHECKER_ERROR', 'reason': 'SAT model does not improve the bound', 'calls': calls}
            witness, lower = checked['selected'], checked['value']
        else:
            break  # UNKNOWN: keep the anytime bounds
    if lower == upper and upper_cert.get('method') not in ('SAT_DRAT', 'HOST_EDGE_COUNT') \
            and lower < len(task.edges) and time.monotonic() < deadline:
        # Met a theorem-based bound: still try for an independently checked certificate.
        budget = max(1, min(per_call_seconds, int(deadline - time.monotonic())))
        cert, record, cnf, pf = certify_upper(task, lower, seconds=budget)
        calls.append({'k': lower + 1, 'status': record['status'], 'seconds': record.get('seconds')})
        if cert is not None and cert['verdict'] == 'VALID':
            upper_cert, proof = cert, pf
    if upper_cert.get('method') == 'host-edge-count' or upper == len(task.edges):
        upper_cert = dict(upper_cert, method='HOST_EDGE_COUNT')
    return {'status': 'OPTIMALITY_CHECKED' if lower == upper and upper_cert.get('method') in ('SAT_DRAT',
                                                                                            'HOST_EDGE_COUNT')
            else ('OPTIMALITY_CHECKED_BY_THEOREM' if lower == upper else 'BOUNDS_ONLY'),
            'lower': lower, 'witness': witness, 'upper': upper, 'gap': upper - lower,
            'upper_certificate': upper_cert, 'proof': proof, 'calls': calls}
