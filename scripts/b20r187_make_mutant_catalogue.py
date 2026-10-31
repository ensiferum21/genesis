"""Write the seventh defect catalogue (`src/genesis/repairkernel/defects7.py`): a fresh draw of random mutants for SR-2d
(B20_R187, a third generation), by the fifth catalogue's rules with a new seed, new job seeds and 36 entries,
excluding every hand-written defect and every mutant of the fifth and sixth catalogues. Fixed here before the draw;
nothing is chosen by looking at the mutants. Run by the builder on CPU 1:

    python3 scripts/b20r187_make_mutant_catalogue.py OUT_EVIDENCE_DIR"""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r185_make_mutant_catalogue as MK  # noqa: E402
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects5 as DF5  # noqa: E402
from genesis.repairkernel import defects6 as DF6  # noqa: E402
from genesis.repairkernel import guard as GD  # noqa: E402
from genesis.repairkernel import mutants as MU  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

SEED = 20261187
JOB_SEEDS = (17, 18, 19)
N = 36
PREFIX = 'Z'


def excluded():
    return MK.hand_written_sources() | {(d['target'], c.source(d['id'], TG.KERNEL_SOURCES))
                                        for c in (DF5, DF6) for d in c.DEFECTS}


def examine(target, mutant, tmp):
    """Why the mutant is not a real obstacle on this draw's jobs, or None (the fifth catalogue's rule)."""
    src = TG.KERNEL_SOURCES[target]
    why = GD.check(src, mutant)
    if why:
        return 'guard: ' + why
    for s in JOB_SEEDS:
        job = BN.Job(Path(tmp) / f'{target}-{s}', target, s, source=mutant, version=2)
        if job.run()['status'] != 'failed':
            return f'job {s} not interrupted'
        if s == JOB_SEEDS[0]:
            args = (job.dir, target, s, job.n_ops, job.every)
            if VF.verify(*args, mutant)['accepted']:
                return 'the verifier accepts it'
            if not VF.verify(*args, src)['accepted']:
                return 'the verifier rejects the correct source on this job'
    return None


HEADER = '''"""The seventh defect catalogue (kernel side, sealed by this file's digest): a fresh draw of random mutants of
the fifteen components, all held out, for SR-2d (B20_R187). Written by `scripts/b20r187_make_mutant_catalogue.py` (seed
{seed}, job seeds {jobs}, the first {n} real obstacles of the shuffled mutants that are neither hand-written defects nor
the fifth or sixth catalogue's; `genesis.repairkernel.mutants`), on 31 Oct 2026, before B20_R187's code existed. No
defect was chosen by hand. `homologue` as in the fourth catalogue."""

DEFECTS = (
'''


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    seen = excluded()
    kept, log = [], []
    allm = MU.shuffled(TG.KERNEL_SOURCES, SEED)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (target, op, what, m) in enumerate(allm):
            if len(kept) == N:
                break
            why = 'an earlier catalogue defect' if (target, m) in seen else examine(target, m, Path(tmp) / str(i))
            log.append({'order': i, 'target': target, 'operator': op, 'what': what, 'kept': why is None, 'why': why})
            if why is None:
                old, new = MU.as_defect(TG.KERNEL_SOURCES[target], m)
                kept.append({'id': f'{PREFIX}{len(kept) + 1:02d}', 'split': 'heldout7', 'target': target, 'class': op,
                             'what': what, 'old': old, 'new': new})
    assert len(kept) == N, len(kept)
    body = ''.join('    ' + repr(d) + ',\n' for d in kept)
    text = HEADER.format(seed=SEED, jobs=JOB_SEEDS, n=N) + body + MK.FOOTER
    (ROOT / 'src/genesis/repairkernel/defects7.py').write_text(text)
    (out / 'selection.json').write_text(json.dumps({'seed': SEED, 'job_seeds': JOB_SEEDS, 'n': N,
                                                    'mutants': len(allm), 'examined': len(log), 'log': log},
                                                   indent=1))
    print(json.dumps({'mutants': len(allm), 'examined': len(log), 'kept': len(kept)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
