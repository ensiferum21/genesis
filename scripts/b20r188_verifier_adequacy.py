"""B20_R188 (WP-4 of `docs/OMEGA_WEAKNESSES_AND_BLUEPRINT.md`, weakness C1): how strong is the circle's verifier?

Every single-place mutant of the fifteen components (`genesis.repairkernel.mutants`, 437) is put through the kernel's
independent verifier (`repairkernel/verify.py`: boundary and guard, visible tests, hidden tests, fresh workloads, the
resource check, the resumed job) on a job of seed 51. A mutant the verifier rejects is killed. A mutant it accepts
survives. Each survivor then gets a long differential test against the reference models: 20 fresh workloads of 5,000
operations, with every observable result compared (`bench.execute`, check on). A divergence makes it a **verifier gap**:
a behavioural defect that the verifier passes. A survivor that never diverges is **possibly equivalent**: the mutation
may not change behaviour at all.

Reported: the kill counts per component and operator; the verifier's mutation score, killed / (killed + gaps); and the
list of gaps, each with the first divergence. There is no verdict to pass or fail: it is a measurement. Its use is the
blueprint's C1, that a gap may be closed only by adding a check that every correct source passes, by Daniel's decision.
Expected (the builder's guess, before the run): a mutation score above 0.9, with gaps concentrated in mutants the job
does not reach (constants in rarely taken branches).

Alone on CPU 0, resumable. Usage: b20r188_verifier_adequacy.py OUT [--rehearse] (`--rehearse`: the bag only)."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import mutants as MU  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

JOB_SEED = 51
DIFF_WORKLOADS = 20
DIFF_OPS = 5000
JOB_VERSION = 2
TARGETS = sorted(TG.KERNEL_SOURCES)
REHEARSAL_TARGETS = ['bag']


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def differential(target, mutant):
    """The first divergence of the mutant from the reference model over DIFF_WORKLOADS fresh workloads, or None."""
    for k in range(DIFF_WORKLOADS):
        rng = random.Random(f'adequacy|{target}|{k}')
        cargs, ckw = TG.make_args(target, rng)
        op_list = TG.ops(target, rng, DIFF_OPS)
        try:
            mod = BN.load_source(mutant, 'adequacy_mut', f'/adequacy/{target}.py')
            BN._limited(lambda: BN.execute(target, mod, cargs, ckw, op_list), 10 ** 7, f'/adequacy/{target}.py')
        except Exception as e:                                      # noqa: BLE001 - a mutant may raise anything
            return f'workload {k}: {type(e).__name__}: {str(e)[:160]}'
    return None


def examine(target, op, what, mutant, tmp):
    job = BN.Job(Path(tmp) / 'job', target, JOB_SEED, source=mutant, version=JOB_VERSION)
    first = job.run()
    v = VF.verify(job.dir, target, JOB_SEED, job.n_ops, job.every, mutant)
    row = {'target': target, 'operator': op, 'what': what, 'job_interrupted': first['status'] == 'failed',
           'accepted': bool(v['accepted']), 'failed_checks': sorted(k for k, c in v['checks'].items() if not c['ok'])}
    row['divergence'] = differential(target, mutant) if row['accepted'] else None
    row['class'] = ('killed' if not row['accepted'] else 'gap' if row['divergence'] else 'possibly-equivalent')
    return row


def analyse(rows):
    out = {'mutants': len(rows)}
    for key in ('target', 'operator'):
        table = {}
        for r in rows:
            t = table.setdefault(r[key], {'killed': 0, 'gap': 0, 'possibly-equivalent': 0})
            t[r['class']] += 1
        out[f'by_{key}'] = dict(sorted(table.items()))
    killed = sum(r['class'] == 'killed' for r in rows)
    gaps = [r for r in rows if r['class'] == 'gap']
    out['killed'] = killed
    out['gaps'] = len(gaps)
    out['possibly_equivalent'] = sum(r['class'] == 'possibly-equivalent' for r in rows)
    out['mutation_score'] = round(killed / (killed + len(gaps)), 4) if killed + len(gaps) else None
    out['gap_list'] = [{k: r[k] for k in ('target', 'operator', 'what', 'job_interrupted', 'divergence')} for r in gaps]
    out['killed_by_the_job_alone'] = sum(r['job_interrupted'] for r in rows)
    out['killed_beyond_the_job'] = sum(r['class'] == 'killed' and not r['job_interrupted'] for r in rows)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    rehearse = '--rehearse' in argv
    out.mkdir(parents=True, exist_ok=True)
    targets = REHEARSAL_TARGETS if rehearse else TARGETS
    rows_path = out / 'rows.jsonl'
    rows = [json.loads(x) for x in rows_path.read_text().splitlines() if x.strip()] if rows_path.exists() else []
    done = {(r['target'], r['what']) for r in rows}
    t0 = time.time()
    for t in targets:
        for op, what, m in MU.enumerate_mutants(t, TG.KERNEL_SOURCES[t]):
            if (t, what) in done:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                row = examine(t, op, what, m, tmp)
            with rows_path.open('a') as f:
                f.write(json.dumps(row) + '\n')
            rows.append(row)
    result = {'study': 'B20_R188', 'rehearsal': rehearse, 'script_sha256': sha256(__file__),
              'mutants_sha256': sha256(ROOT / 'src/genesis/repairkernel/mutants.py'),
              'verify_sha256': sha256(ROOT / 'src/genesis/repairkernel/verify.py'), 'targets': targets,
              'job_seed': JOB_SEED, 'diff_workloads': DIFF_WORKLOADS, 'diff_ops': DIFF_OPS,
              'commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                       text=True).stdout.strip(),
              **analyse(rows), 'wall_s': round(time.time() - t0, 1)}
    (out / 'result.json').write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ('mutants', 'killed', 'gaps', 'possibly_equivalent', 'mutation_score',
                                             'killed_beyond_the_job')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
