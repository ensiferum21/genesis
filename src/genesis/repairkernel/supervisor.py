"""The Supervisor's promotion policy for repairs (kernel side; `docs/OMEGA_SELF_REPAIR.md` §3). Predefined, not
learned: a repair is promoted only if the independent verifier accepted it and the policy's scope allows automatic
promotion; otherwise it waits for a human. Promotion keeps the previous source (rollback) and logs a record."""
import datetime
import re
import json
from pathlib import Path

POLICY = {
    'required': ('boundary', 'visible', 'hidden', 'fresh', 'resume'),
    'automatic_scopes': ('testbed',),          # the sandboxed testbed; the repository's own modules need a human
}


def decide(verdict, scope):
    missing = [c for c in POLICY['required'] if not verdict.get('checks', {}).get(c, {}).get('ok')]
    if missing:
        return {'promote': False, 'why': f'checks failed: {missing}'}
    if scope not in POLICY['automatic_scopes']:
        return {'promote': False, 'why': 'pending: this scope needs the human Supervisor', 'pending': True}
    return {'promote': True, 'why': 'every required check passed; automatic scope'}


def promote(path, new_source, verdict, scope, log_path, repair_id):
    """Apply the repair under the policy: back up the old source, write the new one, log the decision."""
    path = Path(path)
    d = decide(verdict, scope)
    rec = {'time': datetime.datetime.now().isoformat(timespec='seconds'), 'repair': repair_id, 'file': str(path),
           'scope': scope, 'decision': d}
    if d['promote']:
        safe = re.sub(r'[^A-Za-z0-9_.-]+', '-', str(repair_id))
        backup = path.with_name(path.name + '.before-' + safe)
        backup.write_text(path.read_text())
        path.write_text(new_source)
        rec['backup'] = str(backup)
    with Path(log_path).open('a') as f:
        f.write(json.dumps(rec) + '\n')
    return rec


def rollback(rec):
    if rec.get('backup'):
        Path(rec['file']).write_text(Path(rec['backup']).read_text())
        return True
    return False
