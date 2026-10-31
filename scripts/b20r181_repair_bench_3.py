"""B20_R181 (SR-1a3): invented repair operators. The obstacle loop version 3 against its predecessor (B20_R180's
loop, frozen) and the unfocused searchers, on 12 new held-out defects in three new components
(`docs/OMEGA_SELF_REPAIR.md` §7-§8; the Foundry directive's item 4: capability invention, measured against strong
predecessors at matched compute). Preregistered: this script, its criteria and the third sealed catalogue are
committed before any loop runs on any of its defects.

**What changed since B20_R180** (developed on its 12 defects and B20_R178's 21, all development data now):
  * three **invented operators** (`synth.inventions`), each a structural principle from nature or physics, for the
    class no earlier operator reached (a statement with no homologue to transplant): **symmetry completion** (a
    statement about one of two interchangeable arguments gets its mirror image), **vestigial calls** (a private
    method nothing calls any more gets a call restored), **dimensional offsets** (a duration stored where a point in
    time belongs gets the clock added);
  * candidates ordered by the posterior of the line they change first and the vault's operator kinds second (B20_R180's
    loop let the kinds override the posterior);
  * every diagnosing arm sees the same diagnosis trials for the same obstacle (common random numbers: B20_R180's arms
    differed partly by the luck of their trials).
  The third catalogue (`genesis.repairkernel.defects3`, sha256 DEFECTS3_SHA256) was written after the operators: four of
  its twelve defects are in the operators' classes, in components and sites they were not developed on; eight are in
  other classes. Its author is the operators' author (disclosed); "held out" means unseen by the loop's development.

**Phases**, as in B20_R180: 0 isolation; 1 the development vault (the loop on the 33 development defects, job seed 1);
2 controls (each of the TARGETS: a clean job and a kernel fault; 24); 3 the comparison (held-out defects x JOB_SEEDS x
ARMS at BUDGET evaluations; 'loop' reads a copy of the development vault, the others none); 4 retention and reuse
(4(a) the loop with a growing vault; 4(b) 'retrieval' on the seed-2/3 jobs with the vault after seed 1, against
'retrieval' with the development vault, run in 4(b) too).

**Criteria** (fixed here):
  * ISOLATION and CONTROLS (24) as before, else ISOLATION_FAILED or CONTROLS_FAILED; MILESTONE as in B20_R180;
  * **the question**: LOOP_BEATS_LOOP_V2 if the loop repairs more held-out obstacles than its frozen predecessor, exact
    two-sided sign test on the discordant obstacles, p < 0.05; LOOP_V2_BEATS_LOOP for the reverse; else
    NO_DIFFERENCE_SHOWN; the same test against 'nolocal', 'random' and 'enum';
  * **invention reach** (reported with the same test): the loop against each arm on the 12 obstacles of the four
    defects in the operators' classes, and on the 24 others (an invention must not cost reach elsewhere);
  * reuse: REUSE_SHOWN or REUSE_NOT_SHOWN as before.
  Also reported: which operator made each promoted patch, rollbacks, false repairs, costs, repaired per CPU second.

**Deviation disclosed in advance:** it runs on CPU 1 while CPU 0 runs PT-2.

Usage: b20r181_repair_bench_3.py OUT [--rehearse]. `--rehearse` uses six development defects for the held-out ones.
Resumable. Exit 0 when done."""
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
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

DEFECTS_SHA256 = 'bcadeca3bd59dfbe31ce639492c32c30353a9363fba7107026d4f17a8941de63'
DEFECTS2_SHA256 = '6a7d091064fec91bda2dca40011b5c1598f07218604f0c5ddeb8a68c89049c85'
DEFECTS3_SHA256 = 'ce4506573532f2b5d314a4fb96b4edd66decfd64254532ed1862afcd95e40254'
DEV = ['M1', 'L2', 'S1', 'W2', 'M2', 'L1', 'L3', 'L4', 'R1', 'R2', 'R4', 'S2', 'S3', 'W1', 'G1', 'G2', 'G3', 'L5', 'W3',
       'R5', 'S4', 'T1', 'T2', 'T3', 'T4', 'P1', 'P2', 'P3', 'P4', 'D1', 'D2', 'D3', 'D4']
DEV_REHEARSAL = ['T3', 'T4', 'M1', 'S1', 'W2', 'G1']
HELDOUT = ['E1', 'E2', 'E3', 'E4', 'N1', 'N2', 'N3', 'N4', 'K1', 'K2', 'K3', 'K4']
INVENTION_CLASS = ['E1', 'E2', 'N1', 'N2']
INVENTION_CLASS_REHEARSAL = ['T3', 'T4']                   # development defects the operators came from
TARGETS = ['bimap', 'graph', 'lease', 'ledger', 'log', 'lru', 'memo', 'pq', 'registry', 'stats', 'ttl', 'window']
JOB_VERSION = 2
JOB_SEEDS = (1, 2, 3)
ARMS = ('loop', 'loop_v2', 'nolocal', 'random', 'enum')
COMPARATORS = ('loop_v2', 'nolocal', 'random', 'enum')
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
                                   trial_key=f'{kind}/{name}/{seed}',
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
           'equals_reference_source': after == TG.SOURCES_ANY[job.target],
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
    controls_ok = len(controls) == 2 * len(TARGETS) and all(control_passes(r) for r in controls)
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
    def compare(subset):
        out = {}
        for x in COMPARATORS:
            a = sum(1 for d, s in subset if repaired(p3[(d, s, 'loop')]) and not repaired(p3[(d, s, x)]))
            b = sum(1 for d, s in subset if repaired(p3[(d, s, x)]) and not repaired(p3[(d, s, 'loop')]))
            p = sign_test(a, b)
            out[x] = {'loop_only': a, f'{x}_only': b, 'p': round(p, 5),
                      'verdict': f'LOOP_BEATS_{x.upper()}' if a > b and p < 0.05 else
                      f'{x.upper()}_BEATS_LOOP' if b > a and p < 0.05 else 'NO_DIFFERENCE_SHOWN'}
        return out
    comparison = compare(obstacles)
    inv_ids = INVENTION_CLASS if list(heldout) == HELDOUT else INVENTION_CLASS_REHEARSAL
    inv = [(d, s) for d, s in obstacles if d in inv_ids]
    reach = {'invention_class': {'obstacles': len(inv), 'repaired': {a: sum(repaired(p3[(d, s, a)]) for d, s in inv)
                                                                      for a in ARMS}, 'comparison': compare(inv)},
             'other': {'obstacles': len(obstacles) - len(inv),
                       'repaired': {a: sum(repaired(p3[(d, s, a)]) for d, s in obstacles if (d, s) not in inv)
                                    for a in ARMS},
                       'comparison': compare([o for o in obstacles if o not in inv])}}
    operators = {}
    for d, s in obstacles:
        r = p3[(d, s, 'loop')]
        if repaired(r):
            k = (r['patch'] or '').split()[0]
            if k == 'retrieve' and ': ' in (r['patch'] or ''):
                k = 'retrieve ' + r['patch'].split(': ', 1)[1].split()[0]
            operators[k] = operators.get(k, 0) + 1
    p4b = {(r['name'], r['seed']): r for r in rows_ if r['key'].startswith('p4b/')}
    p4c = {(r['name'], r['seed']): r for r in rows_ if r['key'].startswith('p4c/')}
    later = [(d, s) for d, s in obstacles if s != JOB_SEEDS[0]]
    a = sum(1 for d, s in later if repaired(p4b[(d, s)]) and not repaired(p4c[(d, s)]))
    b = sum(1 for d, s in later if repaired(p4c[(d, s)]) and not repaired(p4b[(d, s)]))
    p = sign_test(a, b)
    p4a_rows = {(r['name'], r['seed']): r for r in rows_ if r['key'].startswith('p4a/')}
    pairs = [(p3[(d, s, 'loop')]['first_solution'], p4a_rows[(d, s)]['first_solution']) for d, s in later
             if p3[(d, s, 'loop')]['first_solution'] is not None and p4a_rows[(d, s)]['first_solution'] is not None]
    reuse = {'jobs': len(later), 'grown_vault_repaired': sum(repaired(p4b[k]) for k in later),
             'first_solution_pairs': len(pairs),
             'first_solution_dev_vault_mean': round(sum(a for a, _ in pairs) / len(pairs), 2) if pairs else None,
             'first_solution_grown_vault_mean': round(sum(b for _, b in pairs) / len(pairs), 2) if pairs else None,
             'dev_vault_repaired': sum(repaired(p4c[k]) for k in later),
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
                invention_reach=reach, loop_operators=operators, reuse=reuse, retention=retention,
                promotions_outside_component=sum(not r.get('promoted_file_is_component', True) for r in rows_))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    rehearse = '--rehearse' in argv
    out.mkdir(parents=True, exist_ok=True)
    assert sha256(ROOT / 'src/genesis/repairkernel/defects.py') == DEFECTS_SHA256, 'the first catalogue changed'
    assert sha256(ROOT / 'src/genesis/repairkernel/defects2.py') == DEFECTS2_SHA256, 'the sealed catalogue changed'
    assert sha256(ROOT / 'src/genesis/repairkernel/defects3.py') == DEFECTS3_SHA256, 'the sealed catalogue changed'
    assert sorted(d['id'] for d in DF.DEFECTS + DF2.DEFECTS) == sorted(DEV)
    assert [d['id'] for d in DF3.DEFECTS] == HELDOUT
    assert sorted(TG.SOURCES_ANY) == TARGETS
    assert os.geteuid() == 0, 'the kernel runs as root (it starts the isolated parties)'
    heldout = DEV_REHEARSAL if rehearse else HELDOUT
    work = Path('/home/claude/work/scratch-foundry') / ('b20r181-rehearsal' if rehearse else 'b20r181')
    work.mkdir(parents=True, exist_ok=True)
    rows = Rows(out / 'rows.jsonl')
    t0 = time.time()
    meta = {'study': 'B20_R181', 'rehearsal': rehearse, 'script_sha256': sha256(__file__),
            'defects_sha256': DEFECTS_SHA256, 'defects2_sha256': DEFECTS2_SHA256, 'defects3_sha256': DEFECTS3_SHA256,
            'job_version': JOB_VERSION,
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
    for did in (DEV_REHEARSAL if rehearse else DEV):          # the rehearsal's vault: its own six defects
        run_episode(work, rows, f'p1/{did}/1/loop', 1, 'defect', did, 1, 'loop', vault_into=dev_vault)
    shutil.copy(dev_vault / 'vault.jsonl', out / 'vault_dev.jsonl')
    dev_vault_file = out / 'vault_dev.jsonl'

    # 2. controls
    for t in TARGETS:
        for kind in ('clean', 'fault'):
            run_episode(work, rows, f'p2/{kind}-{t}/{CONTROL_SEED}/loop', 2, kind, t, CONTROL_SEED, 'loop',
                        vault_from=dev_vault_file)

    # 3. the comparison
    for did in heldout:
        for s in JOB_SEEDS:
            for arm in ARMS:
                vf = dev_vault_file if arm == 'loop' else None
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
            run_episode(work, rows, f'p4c/{did}/{s}/retrieval', 4, 'defect', did, s, 'retrieval',
                        vault_from=dev_vault_file)

    # verdicts
    result = dict(meta, **analyse(rows.rows, iso, heldout, len(dev_vault_file.read_text().splitlines()),
                                  len((out / 'vault_grown.jsonl').read_text().splitlines())),
                  wall_s=round(time.time() - t0, 1))
    (out / 'result.json').write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: result[k] for k in ('verdict', 'obstacles', 'milestone_obstacles', 'comparison',
                                             'invention_reach', 'loop_operators', 'reuse', 'retention')}, default=str))
    print(json.dumps({a: {k: v[k] for k in ('repaired', 'false_repairs', 'total_cpu_s')}
                      for a, v in result['per_arm'].items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
