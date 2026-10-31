"""Restore-verify a Genesis completion checkpoint (zip): every manifest entry's digest and size, no member outside the
manifest, the history bundle clones to the recorded commit and tree, and the bundle's tracked files equal the archived
tree byte for byte. Usage: python3 -I restore_verify.py ZIP OUT_JSON"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def main(zpath, out):
    zpath = Path(zpath)
    data = zpath.read_bytes()
    res = {'zip': zpath.name, 'zip_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    with zipfile.ZipFile(zpath) as z:
        names = set(z.namelist())
        manifest = json.loads(z.read('genesis/CHECKPOINT_MANIFEST.json'))
        record = json.loads(z.read('genesis/CHECKPOINT_RECORD.json'))
        bad = [p for p, m in manifest.items()
               if p not in names or hashlib.sha256(z.read(p)).hexdigest() != m['sha256'] or len(z.read(p)) != m['bytes']]
        res['manifest_entries'] = len(manifest)
        res['manifest_mismatches'] = bad
        res['unlisted_members'] = sorted(names - set(manifest) - {'genesis/CHECKPOINT_MANIFEST.json'})
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'h.bundle').write_bytes(z.read('genesis/source-history.bundle'))
            subprocess.run(['git', 'clone', '-q', str(d / 'h.bundle'), str(d / 'clone')], check=True)
            subprocess.run(['git', '-C', str(d / 'clone'), 'checkout', '-q', record['commit']], check=True)
            head = subprocess.run(['git', '-C', str(d / 'clone'), 'rev-parse', 'HEAD', 'HEAD^{tree}'],
                                  capture_output=True, text=True, check=True).stdout.split()
            res['commit_ok'] = head[0] == record['commit']
            res['tree_ok'] = head[1] == record['tree']
            tracked = subprocess.run(['git', '-C', str(d / 'clone'), 'ls-files', '-z'], capture_output=True,
                                     check=True).stdout.decode().split('\0')
            tracked = [t for t in tracked if t]
            archived = {p[len('genesis/'):] for p in manifest
                        if p not in ('genesis/source-history.bundle', 'genesis/CHECKPOINT_RECORD.json')}
            res['files_tracked'] = len(tracked)
            res['files_archived'] = len(archived)
            mism = []
            for t in tracked:
                p = d / 'clone' / t
                if p.is_symlink() or not p.is_file():
                    continue
                if t in archived and p.read_bytes() != z.read('genesis/' + t):
                    mism.append(t)
            res['archive_vs_clone_mismatches'] = mism
            res['tracked_not_archived'] = sorted(t for t in tracked if t not in archived
                                                 and (d / 'clone' / t).is_file())
    res['record'] = {k: record.get(k) for k in ('batch', 'commit', 'tree', 'created_utc', 'parent_checkpoint')}
    tr = record.get('test_report') or {}
    res['matrix'] = {'total_ran': tr.get('total_ran'), 'total_skipped': tr.get('total_skipped'),
                     'all_ok': tr.get('all_ok'), 'suites': {s['suite']: s['ran'] for s in tr.get('suites', [])}}
    res['ok'] = (not bad and not res['unlisted_members'] and res['commit_ok'] and res['tree_ok'] and not mism
                 and not res['tracked_not_archived'] and bool(tr.get('all_ok')))
    Path(out).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res[k] for k in ('ok', 'manifest_entries', 'commit_ok', 'tree_ok', 'files_tracked',
                                          'files_archived', 'matrix')}))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
