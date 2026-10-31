"""B20_R183 (SR-2b): B20_R182 repeated with fresh seeds, plus the arm that tests step 6 (the inventor improving how
it invents). Preregistered after B20_R182's result was read (disclosed; its record was written while this ran). The
code, curriculum, catalogue, budgets, criteria and the four arms are B20_R182's; the seeds differ (DETECT_SEED,
ADMIT_SEED, JOB_SEEDS, SEARCH_SEED, CONTROL_SEED), and with them the diagnosis trials' keys. The fourth catalogue's 12
defects were seen by B20_R182, so this is not a test on new defects: it asks whether B20_R182's findings (a rule
invented and admitted; version 4 equal to version 3; the grammar searched online ahead of version 4) hold under other
jobs and other searches (`replication`, each finding against B20_R182's).

The added arm is 'dream': version 3 plus the grammar, ordered by the inventor's posterior over grammar productions,
learned from the curriculum's verified dreams (frozen with the library). 'dream_online' is the same search with the
grammar in its fixed order. Step 6 (`inventor`): the sign test on the obstacles one of them repairs and the other does
not decides if p < 0.05; otherwise the sign test on which found its first passing candidate earlier, over the
obstacles both repaired (ties dropped), decides if p < 0.05: INVENTOR_IMPROVED (for 'dream') or INVENTOR_WORSE;
otherwise NO_DIFFERENCE_SHOWN. Expected (the builder's guess, recorded before the run): RULES_INVENTED again;
DREAM_ONLINE_BEATS_LOOP_V4 again; the inventor NO_DIFFERENCE_SHOWN (six learned dreams are little to learn from).

Alone on CPU 0. Usage: b20r183_rule_invention_replica.py OUT [--rehearse]."""
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
from genesis.repairkernel import defects4 as DF4  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

DEFECTS4_SHA256 = '7143763d0847f46e552a1e2d149529ae1e772d8b3f1200d699d4ec4bc40c14e0'
CURRICULUM = [d['id'] for d in DF.DEFECTS + DF2.DEFECTS + DF3.DEFECTS]
HELDOUT = ['X1', 'X2', 'X3', 'X4', 'C1', 'C2', 'C3', 'C4', 'B1', 'B2', 'B3', 'B4']
CURRICULUM_REHEARSAL = ['N1', 'N2', 'K1', 'K2', 'M1', 'S1']
HELDOUT_REHEARSAL = ['E3', 'N4', 'W2']
TARGETS = ['bag', 'bimap', 'calendar', 'graph', 'lease', 'ledger', 'log', 'lru', 'memo', 'pq', 'registry', 'stats',
           'stock', 'ttl', 'window']
ARMS = ('loop', 'loop_v3', 'dream_online', 'enum', 'dream')
COMPARATORS = ('loop_v3', 'dream_online', 'enum')
B20R182 = {'verdict': 'RULES_INVENTED',
           'comparison': {'loop_v3': 'NO_DIFFERENCE_SHOWN', 'dream_online': 'DREAM_ONLINE_BEATS_LOOP_V4',
                          'enum': 'NO_DIFFERENCE_SHOWN'},
           'repaired': {'loop': 21, 'loop_v3': 21, 'dream_online': 30, 'enum': 18}}
JOB_SEEDS = (6, 7, 8)
DETECT_SEED = 4
ADMIT_SEED = 5
JOB_VERSION = 2
BUDGET = 300
DREAM_BUDGET = 1000
PROBE_BUDGET = 120
SEARCH_SEED = 1
CONTROL_SEED = 9
FAULT_AT = 700
TIMEOUT = 1500
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


def run_episode(work, rows, key, phase, kind, name, seed, arm, budget=BUDGET, vault_dir=None, vault_copy=None):
    """One obstacle, isolated. `vault_dir`: the research plane's own directory, shared (Genesis's library grows in
    it); `vault_copy`: a directory whose files are copied into a private vault (a frozen library)."""
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
    if vault_dir is None:
        vault_dir = d / 'vault'
        vault_dir.mkdir(parents=True)
        if vault_copy is not None:
            for f in Path(vault_copy).iterdir():
                shutil.copy(f, vault_dir / f.name)
    lib_before = _lib_state(vault_dir)
    rec, krec = FD.handle_obstacle(job, vault_dir=vault_dir, arm=arm, budget=budget, seed=SEARCH_SEED,
                                   trial_key=f'{kind}/{name}/{seed}', family=name if kind == 'defect' else None,
                                   repair_id=key.replace('/', '-'), log_path=work / 'supervisor.jsonl',
                                   isolated=True, timeout=TIMEOUT, stderr_path=work / 'stderr.log')
    rec = rec or {'outcome': 'no-record'}
    st = rec.get('steps', {})
    after = job.file.read_text()
    row = {'key': key, 'phase': phase, 'kind': kind, 'name': name, 'seed': seed, 'arm': arm, 'budget': budget,
           'interrupted_at': first.get('op') if first['status'] == 'failed' else None,
           'outcome': rec.get('outcome'), 'why': rec.get('why'),
           'verified': bool((krec.get('verdict') or {}).get('accepted')),
           'promoted': bool((krec.get('decision') or {}).get('decision', {}).get('promote')),
           'resumed_from': st.get('resume', {}).get('from_op'), 'finished': st.get('resume', {}).get('status'),
           'retained': bool(rec.get('retained')), 'false_repair': rec.get('outcome') == 'false-repair',
           'patch': (rec.get('patch') or {}).get('name'), 'rule': rec.get('rule'),
           'invented': rec.get('invented', []), 'library_before': lib_before, 'library_after': _lib_state(vault_dir),
           'source_changed': after != before, 'proposals': krec.get('proposals'),
           'evaluations': st.get('synthesise', {}).get('evaluations'),
           'first_solution': st.get('synthesise', {}).get('first_solution'),
           'total_cpu_s': (krec.get('cpu_s') or {}).get('total'), 'wall_s': krec.get('wall_s'),
           'research_uid': rec.get('uid'), 'exit': krec.get('exit'),
           'promoted_file_is_component': (krec.get('decision') or {}).get('file') in (None, str(job.file))}
    rows.add(row, (rec, krec), after if after != before else None)
    return row


def _lib_state(vault_dir):
    p = Path(vault_dir) / 'rules.jsonl'
    if not p.exists():
        return {'candidate': 0, 'admitted': 0, 'rejected': 0}
    rules = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    return {s: sum(r['status'] == s for r in rules) for s in ('candidate', 'admitted', 'rejected')}


def analyse(all_rows, iso, heldout, library, inventor):
    rows_ = list(all_rows)
    isolation_ok = isolation_passes(iso)
    controls = [r for r in rows_ if r['phase'] == 'controls']
    controls_ok = len(controls) == 2 * len(TARGETS) and all(control_passes(r) for r in controls)
    admitted = [r for r in library if r['status'] == 'admitted']
    ps = [r for r in rows_ if r['phase'] == 'admit1']
    probes = {'probes': len(ps), 'probes_with_candidates': sum(1 for r in ps if r['evaluations']),
              'admissions': sum(1 for r in ps if r['rule'] and r['rule']['after'] == 'admitted'
                                and r['rule']['before'] != 'admitted'),
              'false_repairs': sum(r['false_repair'] for r in ps)}
    dreams = [r for r in rows_ if r['phase'].startswith('dream')]
    detect = [r for r in rows_ if r['phase'] == 'detect1']
    invention = {'curriculum': len(detect), 'unsolved_by_v3': sum(not repaired(r) for r in detect),
                 'dreams': len(dreams), 'dreams_repaired': sum(repaired(r) for r in dreams),
                 'rules_lifted': len(library), 'rules_admitted': len(admitted),
                 'rules_rejected': sum(r['status'] == 'rejected' for r in library),
                 'admitted': [{k: r[k] for k in ('id', 'level', 'kind', 'template', 'admitted_by')} | {
                     'source': r['provenance'].get('family')} for r in admitted],
                 'probes': probes, 'inventor_beliefs': inventor,
                 'dream_first_solutions': [[r['name'], r['first_solution'], repaired(r)] for r in dreams],
                 'cpu_s': round(sum(r['total_cpu_s'] or 0 for r in rows_ if r['phase'] in (
                     'detect1', 'dream1', 'admit1')), 2)}
    p3 = {(r['name'], r['seed'], r['arm']): r for r in rows_ if r['phase'] == 'test'}
    obstacles = [(d, s) for d in heldout for s in JOB_SEEDS if p3[(d, s, 'loop')]['interrupted_at'] is not None]
    per_arm = {}
    for arm in ARMS:
        rs = [p3[(d, s, arm)] for d, s in obstacles]
        per_arm[arm] = {'obstacles': len(rs), 'repaired': sum(repaired(r) for r in rs),
                        'false_repairs': sum(r['false_repair'] for r in rs),
                        'by_invented_rule': sum(1 for r in rs if repaired(r) and (r['patch'] or '').startswith('rule ')),
                        'evaluations': sum(r['evaluations'] or 0 for r in rs),
                        'total_cpu_s': round(sum(r['total_cpu_s'] or 0 for r in rs), 2)}
    comparison = {}
    for x in COMPARATORS:
        a = sum(1 for d, s in obstacles if repaired(p3[(d, s, 'loop')]) and not repaired(p3[(d, s, x)]))
        b = sum(1 for d, s in obstacles if repaired(p3[(d, s, x)]) and not repaired(p3[(d, s, 'loop')]))
        p = sign_test(a, b)
        comparison[x] = {'loop_v4_only': a, f'{x}_only': b, 'p': round(p, 5),
                         'verdict': f'LOOP_V4_BEATS_{x.upper()}' if a > b and p < 0.05 else
                         f'{x.upper()}_BEATS_LOOP_V4' if b > a and p < 0.05 else 'NO_DIFFERENCE_SHOWN'}
    milestone = [f'{d}/{s}' for d, s in obstacles if repaired(p3[(d, s, 'loop')]) and p3[(d, s, 'loop')]['retained']]
    inventor_cmp = compare_inventor([(p3[(d, s, 'dream')], p3[(d, s, 'dream_online')]) for d, s in obstacles])
    if not isolation_ok:
        verdict = 'ISOLATION_FAILED'
    elif not controls_ok:
        verdict = 'CONTROLS_FAILED'
    else:
        verdict = 'RULES_INVENTED' if admitted else 'NO_RULE_INVENTED'
    replication = {'verdict': {'b20r182': B20R182['verdict'], 'b20r183': verdict}}
    for x in COMPARATORS:
        replication[x] = {'b20r182': B20R182['comparison'][x], 'b20r183': comparison[x]['verdict']}
    for v in replication.values():
        v['same'] = v['b20r182'] == v['b20r183']
    return dict(verdict=verdict, isolation_ok=isolation_ok, controls_ok=controls_ok, invention=invention,
                obstacles=len(obstacles), milestone=bool(milestone), milestone_obstacles=milestone, per_arm=per_arm,
                comparison=comparison, inventor=inventor_cmp, replication=replication,
                replicated=all(v['same'] for v in replication.values()),
                promotions_outside_component=sum(not r.get('promoted_file_is_component', True) for r in rows_))


def compare_inventor(pairs):
    """Step 6: 'dream' (the learned production order) against 'dream_online' (the fixed order), per obstacle."""
    a = sum(1 for x, y in pairs if repaired(x) and not repaired(y))
    b = sum(1 for x, y in pairs if repaired(y) and not repaired(x))
    both = [(x['first_solution'], y['first_solution']) for x, y in pairs if repaired(x) and repaired(y)
            and x['first_solution'] is not None and y['first_solution'] is not None]
    earlier = sum(1 for u, v in both if u < v)
    later = sum(1 for u, v in both if u > v)
    p, p2 = sign_test(a, b), sign_test(earlier, later)
    if p < 0.05:
        verdict = 'INVENTOR_IMPROVED' if a > b else 'INVENTOR_WORSE'
    elif p2 < 0.05:
        verdict = 'INVENTOR_IMPROVED' if earlier > later else 'INVENTOR_WORSE'
    else:
        verdict = 'NO_DIFFERENCE_SHOWN'
    return {'dream_only': a, 'dream_online_only': b, 'p': round(p, 5), 'both_repaired': len(both),
            'dream_earlier': earlier, 'dream_later': later, 'ties': len(both) - earlier - later, 'p_first': round(p2, 5),
            'mean_first': [round(sum(u for u, _ in both) / len(both), 1), round(sum(v for _, v in both) / len(both), 1)]
            if both else None, 'verdict': verdict}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    rehearse = '--rehearse' in argv
    out.mkdir(parents=True, exist_ok=True)
    assert sha256(ROOT / 'src/genesis/repairkernel/defects4.py') == DEFECTS4_SHA256, 'the sealed catalogue changed'
    assert [d['id'] for d in DF4.DEFECTS] == HELDOUT
    assert sorted(TG.KERNEL_SOURCES) == TARGETS
    assert os.geteuid() == 0, 'the kernel runs as root (it starts the isolated parties)'
    curriculum = CURRICULUM_REHEARSAL if rehearse else CURRICULUM
    heldout = HELDOUT_REHEARSAL if rehearse else HELDOUT
    work = Path('/home/claude/work/scratch-foundry') / ('b20r183-rehearsal' if rehearse else 'b20r183')
    work.mkdir(parents=True, exist_ok=True)
    genesis = work / 'genesis-research'                 # the research plane's own directory: Genesis's library
    genesis.mkdir(exist_ok=True)
    rows = Rows(out / 'rows.jsonl')
    t0 = time.time()
    meta = {'study': 'B20_R183', 'replicates': 'B20_R182', 'rehearsal': rehearse, 'script_sha256': sha256(__file__),
            'seeds': {'detect': DETECT_SEED, 'admit': ADMIT_SEED, 'search': SEARCH_SEED, 'control': CONTROL_SEED},
            'defects4_sha256': DEFECTS4_SHA256, 'job_version': JOB_VERSION, 'budget': BUDGET,
            'dream_budget': DREAM_BUDGET, 'probe_budget': PROBE_BUDGET, 'arms': ARMS, 'job_seeds': JOB_SEEDS,
            'curriculum': curriculum, 'heldout_used': heldout,
            'commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                     text=True).stdout.strip()}
    iso_path = out / 'isolation.json'
    if not iso_path.exists():
        iso_path.write_text(json.dumps(FD.isolation_report(work / 'isolation-vault'), indent=1))
    iso = json.loads(iso_path.read_text())

    # generation 1: detect, dream, admit
    unsolved = []
    for did in curriculum:
        r = run_episode(work, rows, f'detect1/{did}/{DETECT_SEED}/loop_v3', 'detect1', 'defect', did, DETECT_SEED,
                        'loop_v3', vault_dir=genesis)
        if not repaired(r):
            unsolved.append(did)
    for did in unsolved:
        run_episode(work, rows, f'dream1/{did}/{DETECT_SEED}/dream', 'dream1', 'defect', did, DETECT_SEED, 'dream',
                    budget=DREAM_BUDGET, vault_dir=genesis)
    for did in curriculum:
        run_episode(work, rows, f'admit1/{did}/{ADMIT_SEED}/probe', 'admit1', 'defect', did, ADMIT_SEED, 'probe',
                    budget=PROBE_BUDGET, vault_dir=genesis)
    frozen = out / 'genesis_library'
    if not frozen.exists():
        shutil.copytree(genesis, frozen, ignore=shutil.ignore_patterns('*.tmp'))
    # controls and the test, with the library frozen
    for t in TARGETS:
        for kind in ('clean', 'fault'):
            run_episode(work, rows, f'controls/{kind}-{t}/{CONTROL_SEED}/loop', 'controls', kind, t, CONTROL_SEED,
                        'loop', vault_copy=frozen)
    for did in heldout:
        for s in JOB_SEEDS:
            for arm in ARMS:
                run_episode(work, rows, f'test/{did}/{s}/{arm}', 'test', 'defect', did, s, arm,
                            vault_copy=None if arm == 'enum' else frozen)
    library = [json.loads(x) for x in (frozen / 'rules.jsonl').read_text().splitlines() if x.strip()] \
        if (frozen / 'rules.jsonl').exists() else []
    inventor = json.loads((frozen / 'inventor.json').read_text()) if (frozen / 'inventor.json').exists() else {}
    result = dict(meta, **analyse(rows.rows, iso, heldout, library, inventor), wall_s=round(time.time() - t0, 1))
    (out / 'result.json').write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: result[k] for k in ('verdict', 'invention', 'obstacles', 'milestone', 'per_arm',
                                             'comparison', 'inventor', 'replication')}, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
