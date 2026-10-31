"""Write the fifth defect catalogue (`src/genesis/repairkernel/defects5.py`) by random mutation, once, before any of
SR-2c's research code exists (B20_R185; `genesis.repairkernel.mutants`). The seed, the job seeds, the number of defects
and the rules are fixed here; nothing is chosen by looking at the mutants. Run by the builder on CPU 1:

    python3 scripts/b20r185_make_mutant_catalogue.py OUT_EVIDENCE_DIR

It writes `defects5.py` and, in OUT_EVIDENCE_DIR, `selection.json` (every mutant examined, in order, with why it was
kept or passed over)."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repairkernel import bench as BN  # noqa: E402
from genesis.repairkernel import defects as DF  # noqa: E402
from genesis.repairkernel import defects2 as DF2  # noqa: E402
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import defects4 as DF4  # noqa: E402
from genesis.repairkernel import guard as GD  # noqa: E402
from genesis.repairkernel import mutants as MU  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402
from genesis.repairkernel import verify as VF  # noqa: E402

SEED = 20261031
JOB_SEEDS = (11, 12, 13)
N = 24
PREFIX = 'Q'


def hand_written_sources():
    return {(d['target'], c.source(d['id'], TG.KERNEL_SOURCES)) for c in (DF, DF2, DF3, DF4) for d in c.DEFECTS}


def examine(target, mutant, tmp):
    """Why the mutant is not a real obstacle, or None."""
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


HEADER = '''"""The fifth defect catalogue (kernel side, sealed by this file's digest): random mutants of the fifteen
components, all held out, for SR-2c (B20_R185). Written by `scripts/b20r185_make_mutant_catalogue.py` (seed {seed}, job
seeds {jobs}, the first {n} real obstacles of the shuffled mutants; `genesis.repairkernel.mutants`), on 31 Oct 2026,
before any of SR-2c's research code existed. No defect was chosen by hand: the operators, the seed and the rules decide.
`homologue` as in the fourth catalogue (computed, not declared)."""

DEFECTS = (
'''

FOOTER = ''')
BY_ID = {d['id']: d for d in DEFECTS}


def source(defect_id, sources):
    d = BY_ID[defect_id]
    src = sources[d['target']]
    assert src.count(d['old']) == 1, defect_id
    return src.replace(d['old'], d['new'])


def homologue(defect_id, sources):
    """Whether every line the defect removed or changed appears verbatim (stripped) elsewhere in the defective source."""
    d = BY_ID[defect_id]
    bad = source(defect_id, sources)
    gone = [ln.strip() for ln in d['old'].split("\\n") if ln.strip() and ln not in d['new'].split("\\n")]
    rest = {ln.strip() for ln in bad.split("\\n")}
    return bool(gone) and all(g in rest for g in gone)
'''


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    seen = hand_written_sources()
    kept, log = [], []
    allm = MU.shuffled(TG.KERNEL_SOURCES, SEED)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (target, op, what, m) in enumerate(allm):
            if len(kept) == N:
                break
            why = 'a hand-written catalogue defect' if (target, m) in seen else examine(target, m, Path(tmp) / str(i))
            log.append({'order': i, 'target': target, 'operator': op, 'what': what, 'kept': why is None, 'why': why})
            if why is None:
                old, new = MU.as_defect(TG.KERNEL_SOURCES[target], m)
                kept.append({'id': f'{PREFIX}{len(kept) + 1:02d}', 'split': 'heldout5', 'target': target, 'class': op,
                             'what': what, 'old': old, 'new': new})
    assert len(kept) == N, len(kept)
    body = ''.join('    ' + repr(d) + ',\n' for d in kept)
    text = HEADER.format(seed=SEED, jobs=JOB_SEEDS, n=N) + body + FOOTER
    path = ROOT / 'src/genesis/repairkernel/defects5.py'
    path.write_text(text)
    (out / 'selection.json').write_text(json.dumps({'seed': SEED, 'job_seeds': JOB_SEEDS, 'n': N,
                                                    'mutants': len(allm), 'examined': len(log), 'log': log},
                                                   indent=1))
    print(json.dumps({'mutants': len(allm), 'examined': len(log), 'kept': [(d['id'], d['target'], d['class'])
                                                                          for d in kept]}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
