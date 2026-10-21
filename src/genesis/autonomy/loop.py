"""The research loop (B20_R96): propose, check, preregister, run in slices, record, rescan.

    propose(root, batch, today)    the cell reads every study, composes the next design; studygen writes the script
    preregister(root, script)      commit the script and append it to docs/PREREGISTRATIONS.md; returns its SHA-256
    run(root, script, out)         run alone on one core; a study pauses before the background limit and resumes
                                   from its rows, so `run` repeats until it finishes (or `max_slices` runs out)

Each step leaves a record; none edits a checker, threshold, scorer or the evaluator (the membrane). The builder (and
Daniel) see every preregistration: `preregister` prints the hash, which is sent before `run` starts.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _cell(root, today, budget_s=None):
    from ..adaptation import capabilities, metabolism
    from ..adaptation.checkpoint import check
    from ..adaptation.design import compose, vbs_contributors
    from ..adaptation.discovery import discover
    from ..adaptation.ledger import rebuild
    catalog = json.loads((Path(root) / 'src/genesis/adaptation/baselines.json').read_text())
    profiles = discover(root)
    led, seen, studies = rebuild(profiles, root, catalog)
    model = metabolism.fit(studies)
    caps = capabilities.scan([v['design'] for v in seen.values()])
    base = seen[profiles[-1].study]['design']
    design, plan = compose(led, base, catalog, model, budget_s=budget_s, contributors=vbs_contributors(studies[-1]),
                           caps=caps, today=today)
    return design, plan, check(design, led, catalog=catalog, today=today), led


def _why(plan, led):
    parts = []
    for key, resp in plan['chosen'].items():
        if key == 'ANTICIPATED_INTERRUPTION':
            parts.append('the design is longer than a background window, so it pauses and resumes and stops when '
                         'decided')
            continue
        e = led.open().get(key, {})
        parts.append(f"{key} ({e.get('status', '?')}, last seen in {e.get('study', '?')}) is answered by {resp}")
    if plan.get('over_budget'):
        parts.append('the whole design is over the cell\'s cost limit, so its budgets are staged: '
                     + plan['over_budget'])
    return '; '.join(parts) + '.'


def propose(root, batch, today=None, title=None):
    from . import studygen
    today = today or datetime.date.today().isoformat()
    design, plan, chk, led = _cell(root, today)
    if not chk['pass']:
        raise RuntimeError(f'the cell\'s own design fails its checkpoint: {chk}')
    sd = studygen.qet_design(design, plan, root, batch)
    name = f'b20r{batch}_qet_large.py'
    path = Path(root) / 'scripts' / name
    expectation = ('The adaptation cell predicts that this design resolves SATURATION and SIZE_CAP (instances where '
                   'values, not only times, separate the methods) and narrows UNCERTIFIED_TARGETS (a certified bound '
                   'per host). From the development looks (B20_R94: on one G(256, 0.5) host the system\'s method at '
                   '1-3 s found more than every champion at 30 s), the builder expects FOCAL_BETTER_THAN_EVERY_CHAMPION '
                   'and FOCAL_BETTER_THAN_VBS at the main budget, and the method at a tenth of the budget also better '
                   'than the VBS on the dense hosts; on the planted hosts, where the dense half is small, the margin '
                   'is smaller and EQUIVALENT is possible against the strongest champions.')
    studygen.write_script(sd, path, title=title or 'quality at equal time against the MaxSAT champions on large hosts',
                          why=_why(plan, led), expectation=expectation)
    proposal = {'batch': batch, 'script': str(path.relative_to(root)), 'design': sd, 'cell_design': design,
                'plan': plan, 'checkpoint': chk, 'today': today}
    (Path(root) / 'scripts' / f'b20r{batch}_qet_large.proposal.json').write_text(
        json.dumps(proposal, indent=1, sort_keys=True, default=str) + '\n')
    return proposal


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preregister(root, script, message):
    """Commit the script (and its proposal) and append a line to docs/PREREGISTRATIONS.md; returns the SHA-256."""
    root = Path(root)
    digest = sha256(script)
    ledger = root / 'docs' / 'PREREGISTRATIONS.md'
    if not ledger.exists():
        ledger.write_text('# Preregistrations written by the research loop\n\n| Script | SHA-256 | Date |\n|---|---|---|\n')
    rel = Path(script).resolve().relative_to(root.resolve())
    with ledger.open('a') as fh:
        fh.write(f'| `{rel}` | `{digest}` | {datetime.date.today().isoformat()} |\n')
    files = [str(rel), str(ledger.relative_to(root))]
    prop = Path(script).with_suffix('.proposal.json')
    if prop.exists():
        files.append(str(prop.resolve().relative_to(root.resolve())))
    subprocess.run(['git', '-C', str(root), 'add', *files], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Claude', '-c', 'user.email=noreply@anthropic.com',
                    'commit', '-q', '-m', f'{message}\n\n  {rel}  sha256 {digest}\n\n'
                    'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n'
                    'Claude-Session: https://claude.ai/code/session_01FE1KQN96fx3NqLs2hyu3Ka'], check=True)
    return digest


def run(root, script, out, max_slices=1, core=0):
    """Run the study in slices; returns 0 when it finished, 3 when it paused after `max_slices` slices."""
    for _ in range(max_slices):
        r = subprocess.run(['taskset', '-c', str(core), sys.executable, str(script), str(out)], cwd=str(root))
        if r.returncode != 3:
            return r.returncode
    return 3
