"""B20_R180 (SR-1a2): the obstacle loop, repaired after B20_R178, on new held-out defects in larger components
(`docs/OMEGA_SELF_REPAIR.md` §7-§8; the Foundry's first milestone, second test). Preregistered: this script, its
criteria and the second sealed catalogue are committed before any loop runs on any of its defects.

**What changed since B20_R178** (each from B20_R178's evidence, developed on its defects only, all of which are now
development data):
  * the loop (version 2): mined laws are evidence for localisation and sources of law-restoring candidates, never a
    reason to reject a candidate; the search widens from the suspected methods to the whole file, ordered by the
    posterior, and runs until its budget is spent. The B20_R178 loop is kept frozen as the arm 'loop_v1' (the strong
    predecessor);
  * the kernel (job version 2): every checkpoint is kept, and a resume that fails steps back to the latest checkpoint
    from which the job finishes (a defect can corrupt the saved state long before it is noticed); the verifier adds a
    resource check (storage and work against the last known-good version of the component), required by the policy;
  * three larger components (a TTL cache, an indexed heap, a ledger with undo; 60 to 80 lines), where a whole-file
    search no longer fits in the budget; a second catalogue (`genesis.repairkernel.defects2`, sha256
    DEFECTS2_SHA256): 12 held-out defects in them, written before any change to the loop, never run through it.

**Phases**, as in B20_R178: 0 isolation measured; 1 the development vault (the loop on the 21 defects of the first
catalogue, job seed 1); 2 controls (each of the 9 components: a clean job, and a planted fault in the kernel's
reference model); 3 the comparison (each held-out defect x JOB_SEEDS x ARMS at BUDGET candidate evaluations;
'loop' and 'retrieval' read a copy of the development vault); 4 retention and reuse (the loop over the held-out jobs
with a growing vault; 'retrieval' on the seed-2/3 jobs with the vault after seed 1).

**Criteria** (fixed here):
  * ISOLATION and CONTROLS as in B20_R178 (18 controls), else ISOLATION_FAILED or CONTROLS_FAILED;
  * MILESTONE: at least one held-out obstacle in phase 3 that the isolated 'loop' repaired: the independent verifier
    accepted (every check, the resource check included), the policy promoted, the job resumed from the checkpoint it
    was interrupted at or, where the defect had corrupted that state, from an earlier kept one, and finished; and the
    repair was retained. MILESTONE_DEMONSTRATED, else NOT_DEMONSTRATED;
  * the comparison (the question of this test): for each of 'loop_v1', 'nolocal', 'random', 'enum', 'retrieval', an
    exact two-sided sign test on the discordant obstacles; LOOP_BEATS_<X> if the loop repairs more and p < 0.05,
    <X>_BEATS_LOOP if the reverse, else NO_DIFFERENCE_SHOWN;
  * reuse as in B20_R178 (REUSE_SHOWN or REUSE_NOT_SHOWN).
  Also reported: rollbacks (repairs resumed from an earlier checkpoint), false repairs, promotions outside a
  component (must be 0), the costs of every party, repaired per CPU second.

**Deviations from the batch protocol, disclosed in advance:** it runs on CPU 1 while CPU 0 runs PT-2.

Usage: b20r180_repair_bench_2.py OUT [--rehearse]. `--rehearse` runs every phase with six development defects in
place of the held-out ones; it never runs the loop on a held-out defect. Resumable. Exit 0 when done."""
import hashlib
import json
from math import comb
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

DEFECTS_SHA256 = 'bcadeca3bd59dfbe31ce639492c32c30353a9363fba7107026d4f17a8941de63'
DEFECTS2_SHA256 = '6a7d091064fec91bda2dca40011b5c1598f07218604f0c5ddeb8a68c89049c85'
DEV = ['M1', 'L2', 'S1', 'W2', 'M2', 'L1', 'L3', 'L4', 'R1', 'R2', 'R4', 'S2', 'S3', 'W1', 'G1', 'G2', 'G3', 'L5', 'W3',
       'R5', 'S4']
DEV_REHEARSAL = ['M1', 'L2', 'S1', 'W2', 'R1', 'G1']
HELDOUT = ['T1', 'T2', 'T3', 'T4', 'P1', 'P2', 'P3', 'P4', 'D1', 'D2', 'D3', 'D4']
JOB_VERSION = 2
JOB_SEEDS = (1, 2, 3)
ARMS = ('loop', 'loop_v1', 'nolocal', 'random', 'enum', 'retrieval')
COMPARATORS = ('loop_v1', 'nolocal', 'random', 'enum', 'retrieval')
BUDGET = 300
SEARCH_SEED = 0
CONTROL_SEED = 4
FAULT_AT = 700
TIMEOUT = 600
BLOCKED = ('FileNotFoundError', 'PermissionError', 'OSError')
RESEARCH_MUST_FAIL = ('read hidden tests (own view)', 'read defect catalogue (own view)',
                      'read reference models (own view)', 'read hidden tests (repository path)',
                      'read repository history', 'write the Judge', 'write the Judge (repository path)',
                      'write the Supervisor policy', 'write the verifier (repository path)',
                      'create a file in the source tree', 'write /tmp')
EXECUTOR_MUST_FAIL = ('read hidden tests (own view)', 'read defect catalogue (own view)', 'write the Judge',
                      'write the Supervisor policy', 'create a file in the source tree', 'write /tmp')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sign_test(a_only, b_only):
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


class Rows:
    def __init__(self, path):
        self.path = path
        self.rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
        self.done = {r['key'] for r in self.rows}

    def add(self, row, record, final_source=None):
        with self.path.open('a') as f:
            f.write(json.dumps(row, default=str) + '\n')
        with (self.path.parent / 'episodes.jsonl').open('a') as f:
            f.write(json.dumps({'key': row['key'], 'research': record[0], 'kernel': record[1],
                                'final_source': final_source}, default=str) + '\n')
        self.rows.append(row)
        self.done.add(row['key'])


def run_episode(work, rows, key, phase, kind, name, seed, arm, vault_from=None, vault_into=None):
    """One obstacle: build the job, run it until it is interrupted, hand it to the research plane (isolated)."""
    if key in rows.done:
        return next(r for r in rows.rows if r['key'] == key)
    d = work / key.replace('/', '_')
    if d.exists():
        shutil.rmtree(d)
    if kind == 'defect':
        job, _ = BN.make(name, seed, d / 'job', version=JOB_VERSION)
    else:
        job, _ = BN.make_clean(name, seed, d / 'job', fault_at=FAULT_AT if kind == 'fault' else None,
                               version=JOB_VERSION)
    before = job.file.read_text()
    first = job.run()
    vault_dir = Path(vault_into) if vault_into else d / 'vault'
    vault_dir.mkdir(parents=True, exist_ok=True)
    if vault_from and not vault_into:
        shutil.copy(vault_from, vault_dir / 'vault.jsonl')
    research_arm = arm
    rec, krec = FD.handle_obstacle(job, vault_dir=vault_dir, arm=research_arm, budget=BUDGET, seed=SEARCH_SEED,
                                   repair_id=key.replace('/', '-'), log_path=work / 'supervisor.jsonl', isolated=True, timeout=TIMEOUT,
                                   stderr_path=work / 'stderr.log')
    rec = rec or {'outcome': 'no-record'}
    st = rec.get('steps', {})
    after = job.file.read_text()
    row = {'key': key, 'phase': phase, 'kind': kind, 'name': name, 'seed': seed, 'arm': arm,
           'interrupted_at': first.get('op') if first['status'] == 'failed' else None,
           'outcome': rec.get('outcome'), 'why': rec.get('why'),
           'verified': bool((krec.get('verdict') or {}).get('accepted')),
           'promoted': bool((krec.get('decision') or {}).get('decision', {}).get('promote')),
           'resumed_from': st.get('resume', {}).get('from_op'), 'finished': st.get('resume', {}).get('status'),
           'rolled_back': (st.get('resume', {}).get('from_op') is not None and first['status'] == 'failed'
                           and st['resume']['from_op'] < first.get('op', 0)),
           'retained': bool(rec.get('retained')),
           'false_repair': rec.get('outcome') == 'false-repair',
           'patch': (rec.get('patch') or {}).get('name'), 'changed_lines': (rec.get('patch') or {}).get('changed_lines'),
           'equals_reference_source': after == TG.ALL_SOURCES[job.target],
           'source_changed': after != before, 'proposals': krec.get('proposals'),
           'evaluations': st.get('synthesise', {}).get('evaluations'),
           'first_solution': st.get('synthesise', {}).get('first_solution'),
           'diagnosis_operations': st.get('diagnose', {}).get('operations'),
           'research_cpu_s': rec.get('cpu_s'), 'verify_s': krec.get('verify_s'), 'wall_s': krec.get('wall_s'),
           'total_cpu_s': (krec.get('cpu_s') or {}).get('total'),
           'retrieved_hunks': st.get('synthesise', {}).get('retrieved'),
           'research_uid': rec.get('uid'), 'exit': krec.get('exit'),
           'promoted_file_is_component': (krec.get('decision') or {}).get('file') in (None, str(job.file))}
    rows.add(row, (rec, krec), after if after != before else None)
    return row


def repaired(r):
    return r['outcome'] == 'repaired' and r['verified'] and r['promoted'] and r['finished'] == 'done' \
        and r['resumed_from'] is not None and r['interrupted_at'] is not None \
        and r['resumed_from'] <= r['interrupted_at']


def isolation_passes(iso):
    return (iso['research'].get('uid') == FD.RESEARCH_ID and iso['executor'].get('uid') == FD.EXECUTOR_ID
            and all(iso['research'].get(k) in BLOCKED for k in RESEARCH_MUST_FAIL)
            and iso['research'].get('write the vault') == 'ok'
            and all(iso['executor'].get(k) in BLOCKED for k in EXECUTOR_MUST_FAIL))


def control_passes(r):
    return r['proposals'] == 0 and not r['source_changed'] and \
        r['outcome'] == ('no-obstacle' if r['kind'] == 'clean' else 'escalated')


def analyse(all_rows, iso, heldout, vault_entries_dev, vault_entries_grown):
    """The verdicts and the tables, from the rows and the isolation report (the record test recomputes them)."""
    rows_ = list(all_rows)
    isolation_ok = isolation_passes(iso)
    controls = [r for r in rows_ if r['phase'] == 2]
    controls_ok = len(controls) == 2 * len(TG.ALL_SOURCES) and all(control_passes(r) for r in controls)
    p3 = {(r['name'], r['seed'], r['arm']): r for r in rows_ if r['phase'] == 3}
    obstacles = [(d, s) for d in heldout for s in JOB_SEEDS if p3[(d, s, 'loop')]['interrupted_at'] is not None]
    milestone = [f'{d}/{s}' for d, s in obstacles if repaired(p3[(d, s, 'loop')]) and p3[(d, s, 'loop')]['retained']]
    per_arm = {}
    for arm in ARMS:
        rs = [p3[(d, s, arm)] for d, s in obstacles]
        cpu = sum(r['total_cpu_s'] or 0 for r in rs)
        per_arm[arm] = {'obstacles': len(rs), 'repaired': sum(repaired(r) for r in rs),
                        'false_repairs': sum(r['false_repair'] for r in rs),
                        'not_repaired': sum(r['outcome'] == 'not-repaired' for r in rs),
                        'other_outcomes': sorted({r['outcome'] for r in rs} - {'repaired', 'false-repair',
                                                                                 'not-repaired'}),
                        'equals_reference_source': sum(r['equals_reference_source'] for r in rs if repaired(r)),
                        'rolled_back': sum(r['rolled_back'] for r in rs if repaired(r)),
                        'evaluations': sum(r['evaluations'] or 0 for r in rs),
                        'diagnosis_operations': sum(r['diagnosis_operations'] or 0 for r in rs),
                        'research_cpu_s': round(sum(r['research_cpu_s'] or 0 for r in rs), 2),
                        'total_cpu_s': round(cpu, 2), 'verify_s': round(sum(r['verify_s'] or 0 for r in rs), 2),
                        'wall_s': round(sum(r['wall_s'] or 0 for r in rs), 2),
                        'repaired_per_total_cpu_s': round(sum(repaired(r) for r in rs) / cpu, 4) if cpu else None}
    comparison = {}
    for x in COMPARATORS:
        a = sum(1 for d, s in obstacles if repaired(p3[(d, s, 'loop')]) and not repaired(p3[(d, s, x)]))
        b = sum(1 for d, s in obstacles if repaired(p3[(d, s, x)]) and not repaired(p3[(d, s, 'loop')]))
        p = sign_test(a, b)
        comparison[x] = {'loop_only': a, f'{x}_only': b, 'p': round(p, 5),
                         'verdict': f'LOOP_BEATS_{x.upper()}' if a > b and p < 0.05 else
                         f'{x.upper()}_BEATS_LOOP' if b > a and p < 0.05 else 'NO_DIFFERENCE_SHOWN'}
    p4b = {(r['name'], r['seed']): r for r in rows_ if r['key'].startswith('p4b/')}
    later = [(d, s) for d, s in obstacles if s != JOB_SEEDS[0]]
    a = sum(1 for d, s in later if repaired(p4b[(d, s)]) and not repaired(p3[(d, s, 'retrieval')]))
    b = sum(1 for d, s in later if repaired(p3[(d, s, 'retrieval')]) and not repaired(p4b[(d, s)]))
    p = sign_test(a, b)
    p4a_rows = {(r['name'], r['seed']): r for r in rows_ if r['key'].startswith('p4a/')}
    pairs = [(p3[(d, s, 'loop')]['first_solution'], p4a_rows[(d, s)]['first_solution']) for d, s in later
             if p3[(d, s, 'loop')]['first_solution'] is not None and p4a_rows[(d, s)]['first_solution'] is not None]
    reuse = {'jobs': len(later), 'grown_vault_repaired': sum(repaired(p4b[k]) for k in later),
             'first_solution_pairs': len(pairs),
             'first_solution_dev_vault_mean': round(sum(a for a, _ in pairs) / len(pairs), 2) if pairs else None,
             'first_solution_grown_vault_mean': round(sum(b for _, b in pairs) / len(pairs), 2) if pairs else None,
             'dev_vault_repaired': sum(repaired(p3[(d, s, 'retrieval')]) for d, s in later),
             'grown_only': a, 'dev_only': b, 'p': round(p, 5),
             'verdict': 'REUSE_SHOWN' if a > b and p < 0.05 else 'REUSE_NOT_SHOWN'}
    p4a = [r for r in rows_ if r['key'].startswith('p4a/')]
    retention = {'episodes': len(p4a), 'repaired': sum(repaired(r) for r in p4a),
                 'retained': sum(r['retained'] for r in p4a),
                 'vault_entries_dev': vault_entries_dev, 'vault_entries_grown': vault_entries_grown}
    if not isolation_ok:
        verdict = 'ISOLATION_FAILED'
    elif not controls_ok:
        verdict = 'CONTROLS_FAILED'
    else:
        verdict = 'MILESTONE_DEMONSTRATED' if milestone else 'NOT_DEMONSTRATED'
    return dict(verdict=verdict, isolation_ok=isolation_ok, controls_ok=controls_ok,
                controls=[{k: r[k] for k in ('key', 'outcome', 'proposals', 'source_changed')} for r in controls],
                obstacles=len(obstacles), milestone_obstacles=milestone, per_arm=per_arm, comparison=comparison,
                reuse=reuse, retention=retention,
                promotions_outside_component=sum(not r.get('promoted_file_is_component', True) for r in rows_))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    rehearse = '--rehearse' in argv
    out.mkdir(parents=True, exist_ok=True)
    assert sha256(ROOT / 'src/genesis/repairkernel/defects.py') == DEFECTS_SHA256, 'the first catalogue changed'
    assert sha256(ROOT / 'src/genesis/repairkernel/defects2.py') == DEFECTS2_SHA256, 'the sealed catalogue changed'
    assert sorted(d['id'] for d in DF.DEFECTS) == sorted(DEV)
    assert [d['id'] for d in DF2.DEFECTS] == HELDOUT
    assert os.geteuid() == 0, 'the kernel runs as root (it starts the isolated parties)'
    heldout = DEV_REHEARSAL if rehearse else HELDOUT
    work = Path('/home/claude/work/scratch-foundry') / ('b20r180-rehearsal' if rehearse else 'b20r180')
    work.mkdir(parents=True, exist_ok=True)
    rows = Rows(out / 'rows.jsonl')
    t0 = time.time()
    meta = {'study': 'B20_R180', 'rehearsal': rehearse, 'script_sha256': sha256(__file__),
            'defects_sha256': DEFECTS_SHA256, 'defects2_sha256': DEFECTS2_SHA256, 'job_version': JOB_VERSION,
            'commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                     text=True).stdout.strip(),
            'heldout_used': heldout, 'budget': BUDGET, 'arms': ARMS, 'job_seeds': JOB_SEEDS}

    # 0. isolation
    iso_path = out / 'isolation.json'
    if not iso_path.exists():
        iso_path.write_text(json.dumps(FD.isolation_report(work / 'isolation-vault'), indent=1))
    iso = json.loads(iso_path.read_text())

    # 1. the development vault
    dev_vault = work / 'dev-vault'
    for did in DEV:
        run_episode(work, rows, f'p1/{did}/1/loop', 1, 'defect', did, 1, 'loop', vault_into=dev_vault)
    shutil.copy(dev_vault / 'vault.jsonl', out / 'vault_dev.jsonl')
    dev_vault_file = out / 'vault_dev.jsonl'

    # 2. controls
    for t in sorted(TG.ALL_SOURCES):
        for kind in ('clean', 'fault'):
            run_episode(work, rows, f'p2/{kind}-{t}/{CONTROL_SEED}/loop', 2, kind, t, CONTROL_SEED, 'loop',
                        vault_from=dev_vault_file)

    # 3. the comparison
    for did in heldout:
        for s in JOB_SEEDS:
            for arm in ARMS:
                vf = dev_vault_file if arm in ('loop', 'retrieval') else None
                run_episode(work, rows, f'p3/{did}/{s}/{arm}', 3, 'defect', did, s, arm, vault_from=vf)

    # 4. retention and reuse
    grown = work / 'grown-vault'
    if not (grown / 'vault.jsonl').exists() and not any(k.startswith('p4a/') for k in rows.done):
        grown.mkdir(parents=True, exist_ok=True)
        shutil.copy(dev_vault_file, grown / 'vault.jsonl')
    for s in JOB_SEEDS:
        for did in heldout:
            run_episode(work, rows, f'p4a/{did}/{s}/loop', 4, 'defect', did, s, 'loop', vault_into=grown)
        if s == JOB_SEEDS[0] and not (out / 'vault_after_seed1.jsonl').exists():
            shutil.copy(grown / 'vault.jsonl', out / 'vault_after_seed1.jsonl')
    shutil.copy(grown / 'vault.jsonl', out / 'vault_grown.jsonl')
    for s in JOB_SEEDS[1:]:
        for did in heldout:
            run_episode(work, rows, f'p4b/{did}/{s}/retrieval', 4, 'defect', did, s, 'retrieval',
                        vault_from=out / 'vault_after_seed1.jsonl')

    # verdicts
    result = dict(meta, **analyse(rows.rows, iso, heldout, len(dev_vault_file.read_text().splitlines()),
                                  len((out / 'vault_grown.jsonl').read_text().splitlines())),
                  wall_s=round(time.time() - t0, 1))
    (out / 'result.json').write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: result[k] for k in ('verdict', 'obstacles', 'milestone_obstacles', 'comparison', 'reuse',
                                             'retention')}, default=str))
    print(json.dumps({a: {k: v[k] for k in ('repaired', 'false_repairs', 'total_cpu_s')}
                      for a, v in result['per_arm'].items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
