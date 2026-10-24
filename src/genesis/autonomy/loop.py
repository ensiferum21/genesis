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


def _why(plan, led, sd=None):
    """The cell's reasons, each with how the study `sd` carries it out (`studygen.implementation`)."""
    from . import studygen
    how = studygen.implementation(sd) if sd else {}
    parts = []
    for key, resp in plan['chosen'].items():
        if key == 'ANTICIPATED_INTERRUPTION':
            parts.append('the design is longer than a background window, so it pauses and resumes and stops when '
                         'decided')
            continue
        e = led.open().get(key, {})
        here = f' (here: {how[resp]})' if resp in how else ''
        parts.append(f"{key} ({e.get('status', '?')}, last seen in {e.get('study', '?')}) is answered by {resp}{here}")
    if plan.get('over_budget'):
        cost = studygen.estimate_seconds(sd) if sd else None
        parts.append('the cell\'s whole design is over its cost limit, so its budgets are staged: '
                     + plan['over_budget']
                     + (f"; this study, staged, is estimated at {cost['all_hosts_s']} s if it runs every host"
                        if cost else ''))
    return '; '.join(parts) + '.'


def propose(root, batch, today=None, title=None, disclosure=None):
    """The next study: writes scripts/b20r{batch}_qet_large.py (and its .proposal.json) and returns the proposal.
    `disclosure`: what the builder looked at before preregistering (rehearsals, development looks), stated in the
    script."""
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
                   '1-3 s found more than every champion at 30 s), the builder expects '
                   'FOCAL_BETTER_THAN_EVERY_CHAMPION '
                   'and FOCAL_BETTER_THAN_VBS at the main budget; on the planted hosts, where the dense half is small, '
                   'the margin is smaller and equivalence with the strongest champions is possible there (visible in '
                   'the per-cell means, which carry no label). At a tenth of the budget (short_vs_vbs): '
                   'FOCAL_BETTER_THAN_VBS or UNRESOLVED; the dense n256 hosts should carry it, while on the others a '
                   'run of a tenth of the time may fall short of the champions\' best.')
    if sd.get('extra'):
        expectation += (' For the extra arms (' + ', '.join(e['arm'] for e in sd['extra']) + '): '
                        'NO_MEASURABLE_EFFECT expected for most. In B20_R95\'s final round the frozen configuration, '
                        'DEFAULT and B20_R89\'s were within 0.0007 of anytime score of each other at 1 and 5 s, a third '
                        'of the margin, and in B20_R96\'s development look the iterated search after the warm starts '
                        'hardly changed the best on dense hosts; a component that matters would show as HELPS.')
    studygen.write_script(sd, path, title=title or 'quality at equal time against the MaxSAT champions on large hosts',
                          why=_why(plan, led, sd), expectation=expectation, disclosure=disclosure)
    proposal = {'batch': batch, 'script': str(path.relative_to(root)), 'design': sd, 'cell_design': design,
                'plan': plan, 'checkpoint': chk, 'today': today}
    (Path(root) / 'scripts' / f'b20r{batch}_qet_large.proposal.json').write_text(
        json.dumps(proposal, indent=1, sort_keys=True, default=str) + '\n')
    return proposal


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


IDENTITY = ('Genesis research loop', 'genesis-research-loop@localhost')


def preregister(root, script, message, identity=IDENTITY, trailers=()):
    """Commit the script (and its proposal) and append a line to docs/PREREGISTRATIONS.md; returns the SHA-256.
    The commit is the research loop's own (IDENTITY); an operator who runs the loop may add attribution `trailers`
    (Genesis Ω contract: no assistant identity is part of the runtime; docs/OMEGA_NO_LLM_AUDIT.md)."""
    root = Path(root)
    digest = sha256(script)
    ledger = root / 'docs' / 'PREREGISTRATIONS.md'
    if not ledger.exists():
        ledger.write_text('# Preregistrations written by the research loop\n\n'
                          '| Script | SHA-256 | Date |\n|---|---|---|\n')
    rel = Path(script).resolve().relative_to(root.resolve())
    with ledger.open('a') as fh:
        fh.write(f'| `{rel}` | `{digest}` | {datetime.date.today().isoformat()} |\n')
    files = [str(rel), str(ledger.relative_to(root))]
    prop = Path(script).with_suffix('.proposal.json')
    if prop.exists():
        files.append(str(prop.resolve().relative_to(root.resolve())))
    subprocess.run(['git', '-C', str(root), 'add', *files], check=True)
    body = f'{message}\n\n  {rel}  sha256 {digest}\n' + (('\n' + '\n'.join(trailers)) if trailers else '')
    subprocess.run(['git', '-C', str(root), '-c', f'user.name={identity[0]}', '-c', f'user.email={identity[1]}',
                    'commit', '-q', '-m', body], check=True)
    return digest


def run(root, script, out, max_slices=1, core=0):
    """Run the study in slices; returns 0 when it finished, 3 when it paused after `max_slices` slices."""
    for _ in range(max_slices):
        r = subprocess.run(['taskset', '-c', str(core), sys.executable, str(script), str(out)], cwd=str(root))
        if r.returncode != 3:
            return r.returncode
    return 3
