"""B20_R185 (SR-2c): Genesis grows its own repair space, and the way it grows it (`docs/OMEGA_RULE_INVENTION.md` §6).

With no human step, on the 57 hand-written defects (development data, the curriculum):
  generation 1  detect1: version 3 on each, lifting every verified repair into transformations ('v3learn', job seed
                21); dream1: the dream on each it did not repair (1,000 evaluations), lifting too; probe1: every
                defect probed with the candidate transformations of other families ('probe_t', seed 22, 200
                evaluations); a verified repair admits. The library is frozen (`genesis_g1`).
  generation 2  learn2: version 3 with generation 1's admitted transformations ('analogy') on each defect still
                unsolved (seed 23), lifting what it repairs; probe2: the inventor derives new candidates from the
                admitted first-generation transformations (inverse, transfer, composition, generalisation) and every
                defect is probed again ('probe_t2', seed 24); a verified repair admits. Frozen (`genesis_g2`).
Then the 30 controls, and the test on the fifth catalogue (24 random mutants nobody chose, sealed before this code;
`defects5.py`), each in the jobs of seeds 11, 12, 13, at 300 evaluations, every arm with generation 2's vault but
for the transformations: version 3 (the builder's rules), 'analogy' with generation 1's transformations, 'analogy'
with generation 2's, the builder's grammar searched online ('dream_online'), enum.

Verdict: ISOLATION_FAILED / CONTROLS_FAILED / SPACE_INVENTED (at least one transformation admitted) /
NO_SPACE_INVENTED. The three questions, sign tests on the obstacles one arm repairs and the other does not, Holm over
the three: P1 generation 1 against version 3 (GENESIS_SPACE_BEATS_BUILDER_RULES, or the reverse); P2 generation 2
against generation 1 (INVENTOR_IMPROVED / INVENTOR_WORSE: step 6); P3 generation 2 against the builder's grammar
(GENESIS_SPACE_BEATS_BUILDER_GRAMMAR, or the reverse); otherwise NO_DIFFERENCE_SHOWN. Reported: what each generation
lifted, derived and admitted; the deriver's beliefs; every obstacle repaired by a transformation Genesis invented and
not by version 3 ('invented_reach'). Expected (the builder's guess, before the run): SPACE_INVENTED; P1
NO_DIFFERENCE_SHOWN; P2 INVENTOR_IMPROVED with low confidence (derived transfers of attribute renamings reach the
attribute mutants); P3 NO_DIFFERENCE_SHOWN.

Alone on CPU 0, resumable, in slices: no episode starts after SLICE_S seconds of a slice, and the script then exits
with 3 (paused; run it again to go on). Usage: b20r185_space_invention.py OUT [--rehearse] (`--rehearse`: an
eight-defect curriculum and four other development defects in place of the mutants)."""
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
from genesis.repairkernel import defects5 as DF5  # noqa: E402
from genesis.repairkernel import foundry as FD  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

DEFECTS5_SHA256 = '59c4fc31a2500a4976a007f8f7fd66f548404f379a2600eba395f7eb910e3baa'
CURRICULUM = [d['id'] for d in DF.DEFECTS + DF2.DEFECTS + DF3.DEFECTS + DF4.DEFECTS]
HELDOUT = [d['id'] for d in DF5.DEFECTS]
CURRICULUM_REHEARSAL = ['E3', 'N1', 'N2', 'S2', 'B2', 'R1', 'K1', 'G2']
HELDOUT_REHEARSAL = ['X2', 'K4', 'G3', 'X4']
TARGETS = ['bag', 'bimap', 'calendar', 'graph', 'lease', 'ledger', 'log', 'lru', 'memo', 'pq', 'registry', 'stats',
           'stock', 'ttl', 'window']
ARMS = {'loop_v3': ('loop_v3', 'g1'), 'analogy_g1': ('analogy', 'g1'), 'analogy_g2': ('analogy', 'g2'),
        'dream_online': ('dream_online', 'g1'), 'enum': ('enum', None)}
QUESTIONS = {'P1': ('analogy_g1', 'loop_v3', 'GENESIS_SPACE_BEATS_BUILDER_RULES', 'BUILDER_RULES_BEAT_GENESIS_SPACE'),
             'P2': ('analogy_g2', 'analogy_g1', 'INVENTOR_IMPROVED', 'INVENTOR_WORSE'),
             'P3': ('analogy_g2', 'dream_online', 'GENESIS_SPACE_BEATS_BUILDER_GRAMMAR',
                    'BUILDER_GRAMMAR_BEATS_GENESIS_SPACE')}
SECONDARY = (('analogy_g2', 'loop_v3'), ('analogy_g2', 'enum'))
JOB_SEEDS = (11, 12, 13)
SEEDS = {'detect1': 21, 'probe1': 22, 'learn2': 23, 'probe2': 24, 'controls': 25}
JOB_VERSION = 2
BUDGET = 300
DREAM_BUDGET = 1000
PROBE_BUDGET = 200
SEARCH_SEED = 2
FAULT_AT = 700
SLICE_S = 6600
TIMEOUT = 1500
BLOCKED = ('FileNotFoundError', 'PermissionError', 'OSError')
RESEARCH_MUST_FAIL = ('read hidden tests (own view)', 'read defect catalogue (own view)',
                      'read any defect catalogue (own view)',
                      'read reference models (own view)', 'read hidden tests (repository path)',
                      'read repository history', 'write the Judge', 'write the Judge (repository path)',
                      'write the Supervisor policy', 'write the verifier (repository path)',
                      'create a file in the source tree', 'write /tmp')
EXECUTOR_MUST_FAIL = ('read hidden tests (own view)', 'read defect catalogue (own view)',
                      'read any defect catalogue (own view)', 'write the Judge',
                      'write the Supervisor policy', 'create a file in the source tree', 'write /tmp')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sign_test(a_only, b_only):
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    """Holm-adjusted p-values for a dict name -> p."""
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


class Pause(Exception):
    pass


class Rows:
    def __init__(self, path, deadline=None):
        self.path = path
        self.rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
        self.done = {r['key'] for r in self.rows}
        self.deadline = deadline

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


def _store(vault_dir, name):
    p = Path(vault_dir) / name
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _counts(vault_dir):
    ts = _store(vault_dir, 'transforms.jsonl')
    return {s: sum(t['status'] == s for t in ts) for s in ('candidate', 'admitted', 'rejected')}


def run_episode(work, rows, key, phase, kind, name, seed, arm, budget=BUDGET, vault_dir=None, vault_copy=None):
    """One obstacle, isolated. `vault_dir`: the research plane's own directory, shared (Genesis's library grows in
    it); `vault_copy`: a directory whose files are copied into a private vault (a frozen library)."""
    if key in rows.done:
        return next(r for r in rows.rows if r['key'] == key)
    if rows.deadline is not None and time.time() > rows.deadline:
        raise Pause(key)
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
    t_before = _counts(vault_dir)
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
           'patch': (rec.get('patch') or {}).get('name'), 'transform': rec.get('transform'),
           'lifted': rec.get('lifted', []), 'transforms_before': t_before, 'transforms_after': _counts(vault_dir),
           'source_changed': after != before, 'proposals': krec.get('proposals'),
           'evaluations': st.get('synthesise', {}).get('evaluations'),
           'first_solution': st.get('synthesise', {}).get('first_solution'),
           'repertoire': st.get('synthesise', {}).get('repertoire'),
           'total_cpu_s': (krec.get('cpu_s') or {}).get('total'), 'wall_s': krec.get('wall_s'),
           'research_uid': rec.get('uid'), 'exit': krec.get('exit'),
           'promoted_file_is_component': (krec.get('decision') or {}).get('file') in (None, str(job.file))}
    rows.add(row, (rec, krec), after if after != before else None)
    return row


def freeze(src, dst):
    if not dst.exists():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*.tmp'))


def test_vault(out, gen):
    """Generation 2's vault (the retained repairs, rules and beliefs of the whole cycle) with the transformations of
    the given generation: the arms differ in their transformations only."""
    d = out / f'test_vault_{gen}'
    if not d.exists():
        shutil.copytree(out / 'genesis_g2', d)
        mine = out / f'genesis_{gen}' / 'transforms.jsonl'
        if mine.exists():
            shutil.copy(mine, d / 'transforms.jsonl')
        else:
            (d / 'transforms.jsonl').unlink(missing_ok=True)
    return d


def analyse(all_rows, iso, heldout, g1, g2, deriver):
    rows_ = list(all_rows)
    isolation_ok = isolation_passes(iso)
    controls = [r for r in rows_ if r['phase'] == 'controls']
    controls_ok = len(controls) == 2 * len(TARGETS) and all(control_passes(r) for r in controls)

    def phase(p):
        return [r for r in rows_ if r['phase'] == p]
    admitted1 = [t for t in g1 if t['status'] == 'admitted']
    admitted2 = [t for t in g2 if t['status'] == 'admitted']
    gen = {
        'curriculum': len(phase('detect1')),
        'unsolved_by_v3': sum(not repaired(r) for r in phase('detect1')),
        'dreams': len(phase('dream1')), 'dreams_repaired': sum(repaired(r) for r in phase('dream1')),
        'learn2': len(phase('learn2')), 'learn2_repaired': sum(repaired(r) for r in phase('learn2')),
        'lifted_g1': sum(1 for t in g1 if t.get('generation') == 1),
        'admitted_g1': len(admitted1),
        'lifted_g2': sum(1 for t in g2 if t.get('generation') == 2 and not t.get('derived')),
        'derived_g2': sum(1 for t in g2 if t.get('derived')),
        'admitted_g2_total': len(admitted2),
        'admitted_in_g2': sorted(t['id'] for t in admitted2 if t['id'] not in {u['id'] for u in admitted1}),
        'admitted': [{k: t[k] for k in ('id', 'edit', 'subs', 'generation', 'derived', 'admitted_by')}
                     | {'source': t['provenance'].get('family') or t['provenance'].get('derived_from_families')}
                     for t in admitted2],
        'probes': {p: {'probes': len(phase(p)), 'with_candidates': sum(1 for r in phase(p) if r['evaluations']),
                       'admissions': sum(1 for r in phase(p) if r['transform'] and r['transform']['after'] == 'admitted'
                                         and r['transform']['before'] != 'admitted'),
                       'false_repairs': sum(r['false_repair'] for r in phase(p))} for p in ('probe1', 'probe2')},
        'deriver_beliefs': deriver,
        'cpu_s': round(sum(r['total_cpu_s'] or 0 for r in rows_ if r['phase'] in (
            'detect1', 'dream1', 'probe1', 'learn2', 'probe2')), 2)}
    p3 = {(r['name'], r['seed'], r['key'].rsplit('/', 1)[1]): r for r in rows_ if r['phase'] == 'test'}
    obstacles = [(d, s) for d in heldout for s in JOB_SEEDS if p3[(d, s, 'loop_v3')]['interrupted_at'] is not None]
    per_arm = {}
    for arm in ARMS:
        rs = [p3[(d, s, arm)] for d, s in obstacles]
        per_arm[arm] = {'obstacles': len(rs), 'repaired': sum(repaired(r) for r in rs),
                        'false_repairs': sum(r['false_repair'] for r in rs),
                        'by_transform': sum(1 for r in rs if repaired(r) and (r['patch'] or '').startswith('transform ')),
                        'evaluations': sum(r['evaluations'] or 0 for r in rs),
                        'total_cpu_s': round(sum(r['total_cpu_s'] or 0 for r in rs), 2)}

    def pair(x, y):
        a = sum(1 for d, s in obstacles if repaired(p3[(d, s, x)]) and not repaired(p3[(d, s, y)]))
        b = sum(1 for d, s in obstacles if repaired(p3[(d, s, y)]) and not repaired(p3[(d, s, x)]))
        return a, b, sign_test(a, b)
    questions, raw = {}, {}
    for q, (x, y, win, lose) in QUESTIONS.items():
        a, b, p = pair(x, y)
        raw[q] = p
        questions[q] = {'arm': x, 'against': y, f'{x}_only': a, f'{y}_only': b, 'p': round(p, 5)}
    adj = holm(raw)
    for q, (x, y, win, lose) in QUESTIONS.items():
        a, b = questions[q][f'{x}_only'], questions[q][f'{y}_only']
        questions[q]['p_holm'] = round(adj[q], 5)
        questions[q]['verdict'] = win if a > b and adj[q] < 0.05 else lose if b > a and adj[q] < 0.05 else \
            'NO_DIFFERENCE_SHOWN'
    secondary = {}
    for x, y in SECONDARY:
        a, b, p = pair(x, y)
        secondary[f'{x}_vs_{y}'] = {f'{x}_only': a, f'{y}_only': b, 'p': round(p, 5)}
    reach = sorted(f'{d}/{s}' for d, s in obstacles for arm in ('analogy_g1', 'analogy_g2')
                   if repaired(p3[(d, s, arm)]) and (p3[(d, s, arm)]['patch'] or '').startswith('transform ')
                   and not repaired(p3[(d, s, 'loop_v3')]))
    if not isolation_ok:
        verdict = 'ISOLATION_FAILED'
    elif not controls_ok:
        verdict = 'CONTROLS_FAILED'
    else:
        verdict = 'SPACE_INVENTED' if admitted2 else 'NO_SPACE_INVENTED'
    return dict(verdict=verdict, isolation_ok=isolation_ok, controls_ok=controls_ok, generations=gen,
                obstacles=len(obstacles), per_arm=per_arm, questions=questions, secondary=secondary,
                invented_reach=sorted(set(reach)),
                promotions_outside_component=sum(not r.get('promoted_file_is_component', True) for r in rows_))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    rehearse = '--rehearse' in argv
    out.mkdir(parents=True, exist_ok=True)
    assert sha256(ROOT / 'src/genesis/repairkernel/defects5.py') == DEFECTS5_SHA256, 'the sealed catalogue changed'
    assert sorted(TG.KERNEL_SOURCES) == TARGETS
    assert os.geteuid() == 0, 'the kernel runs as root (it starts the isolated parties)'
    curriculum = CURRICULUM_REHEARSAL if rehearse else CURRICULUM
    heldout = HELDOUT_REHEARSAL if rehearse else HELDOUT
    work = Path('/home/claude/work/scratch-foundry') / ('b20r185-rehearsal' if rehearse else 'b20r185')
    work.mkdir(parents=True, exist_ok=True)
    genesis = work / 'genesis-research'                 # the research plane's own directory: Genesis's library
    genesis.mkdir(exist_ok=True)
    t0 = time.time()
    rows = Rows(out / 'rows.jsonl', deadline=t0 + SLICE_S)
    try:
        return _run(out, rehearse, curriculum, heldout, work, genesis, rows, t0)
    except Pause as e:
        print(f'paused before {e} after {round(time.time() - t0)} s; run again to go on', flush=True)
        return 3


def _run(out, rehearse, curriculum, heldout, work, genesis, rows, t0):
    meta = {'study': 'B20_R185', 'rehearsal': rehearse, 'script_sha256': sha256(__file__),
            'defects5_sha256': DEFECTS5_SHA256, 'job_version': JOB_VERSION, 'budget': BUDGET,
            'dream_budget': DREAM_BUDGET, 'probe_budget': PROBE_BUDGET, 'arms': ARMS, 'job_seeds': JOB_SEEDS,
            'seeds': SEEDS, 'search_seed': SEARCH_SEED, 'curriculum': curriculum, 'heldout_used': heldout,
            'commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                     text=True).stdout.strip()}
    iso_path = out / 'isolation.json'
    if not iso_path.exists():
        iso_path.write_text(json.dumps(FD.isolation_report(work / 'isolation-vault'), indent=1))
    iso = json.loads(iso_path.read_text())

    # generation 1
    unsolved = []
    for did in curriculum:
        r = run_episode(work, rows, f'detect1/{did}', 'detect1', 'defect', did, SEEDS['detect1'], 'v3learn',
                        vault_dir=genesis)
        if not repaired(r):
            unsolved.append(did)
    still = []
    for did in unsolved:
        r = run_episode(work, rows, f'dream1/{did}', 'dream1', 'defect', did, SEEDS['detect1'], 'dream',
                        budget=DREAM_BUDGET, vault_dir=genesis)
        if not repaired(r):
            still.append(did)
    for did in curriculum:
        run_episode(work, rows, f'probe1/{did}', 'probe1', 'defect', did, SEEDS['probe1'], 'probe_t',
                    budget=PROBE_BUDGET, vault_dir=genesis)
    freeze(genesis, out / 'genesis_g1')
    # generation 2
    for did in still:
        run_episode(work, rows, f'learn2/{did}', 'learn2', 'defect', did, SEEDS['learn2'], 'analogy', vault_dir=genesis)
    for did in curriculum:
        run_episode(work, rows, f'probe2/{did}', 'probe2', 'defect', did, SEEDS['probe2'], 'probe_t2',
                    budget=PROBE_BUDGET, vault_dir=genesis)
    freeze(genesis, out / 'genesis_g2')
    vaults = {g: test_vault(out, g) for g in ('g1', 'g2')}
    # controls and the test, with the libraries frozen
    for t in TARGETS:
        for kind in ('clean', 'fault'):
            run_episode(work, rows, f'controls/{kind}-{t}', 'controls', kind, t, SEEDS['controls'], 'analogy',
                        vault_copy=vaults['g2'])
    for did in heldout:
        for s in JOB_SEEDS:
            for label, (arm, gen) in ARMS.items():      # the arm's label is the key's last part
                run_episode(work, rows, f'test/{did}/{s}/{label}', 'test', 'defect', did, s, arm,
                            vault_copy=vaults[gen] if gen else None)
    g1 = _store(out / 'genesis_g1', 'transforms.jsonl')
    g2 = _store(out / 'genesis_g2', 'transforms.jsonl')
    deriver = json.loads((out / 'genesis_g2' / 'deriver.json').read_text()) \
        if (out / 'genesis_g2' / 'deriver.json').exists() else {}
    result = dict(meta, **analyse(rows.rows, iso, heldout, g1, g2, deriver), wall_s=round(time.time() - t0, 1))
    (out / 'result.json').write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: result[k] for k in ('verdict', 'generations', 'obstacles', 'per_arm', 'questions',
                                             'secondary', 'invented_reach')}, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
