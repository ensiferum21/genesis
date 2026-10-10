#!/usr/bin/env python3
"""R4: bytes in a bundle that verify_bundle accepts but never checks.

(a) CLAIMS.json is compared after json.loads (last duplicate key wins), not by bytes.
    A first occurrence of "effective_levels"/"ceiling" can carry any level. Readers
    with first-wins semantics, grep/less, and the project's own strict loader
    (genesis.common.load_json refuses duplicate keys) see something else.
(b) Any file named MANIFEST.json, in any directory, is exempt from the file-set,
    hash and stray-file checks (present = ... if p.name != 'MANIFEST.json').
(c) A final unterminated line of events.jsonl is silently dropped by the rebuild
    (record['partial_tail_dropped'] is ignored), so a shipped event the verifier
    never applied sits in the bundle.
(d) Zip entries outside the single release_* directory are ignored.
  PYTHONPATH=src python3 -W ignore audit/redteam_b14_round2/r4_bundle_parser_differentials.py
"""
import json
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r2  # noqa: E402
from genesis.common import canonical, code_identity, load_json  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.release_bundle import build_bundle, verify_bundle  # noqa: E402
from genesis.store import Store  # noqa: E402

TOP = {'causality': 'PLACEBO_CONTROLLED', 'improver': 'MULTIGEN_CONFIRMED', 'math': 'OPTIMALITY_CHECKED',
       'novelty': 'EXTERNALLY_CHECKED_NOVEL', 'replication': 'EXTERNAL_REPRODUCTION', 'utility': 'CONFIRMED_TRANSFER'}
d = Path(tempfile.mkdtemp())
with Store(d / 'c') as s:
    s.set_state('source_hash', code_identity(_r2.REPO)['sha256'])
    k = EvidenceKernel(s)
    run = k.record('execution_receipt', {'r': 1}, route='genesis.campaign', source_hash='c' * 64, verdict='VALID')
    w = k.record('witness_check', {'value': 7}, parents=[run], route='genesis.campaign', source_hash='c' * 64,
                 verdict='VALID', verifier='dual-predicates')
    k.create_claim('w', 'host H has a valid subgraph with 7 edges', 'host H', [w])
    k.promote('w', 'math', 'WITNESS_VALID')
build_bundle(d / 'c', d / 'honest.zip', report='')
print('honest verify ok:', verify_bundle(d / 'honest.zip')['ok'])


def dup_keys(files, manifest):
    text = files['CLAIMS.json'].decode()
    text = text.replace('"effective_levels":{', '"effective_levels":' + json.dumps(TOP, separators=(',', ':'))
                        + ',"effective_levels":{', 1)
    text = text.replace('"ceiling":{', '"ceiling":' + json.dumps(TOP, separators=(',', ':')) + ',"ceiling":{', 1)
    files['CLAIMS.json'] = text.encode()


_r2.rewrite_bundle(d / 'honest.zip', d / 'a.zip', dup_keys)
ra = verify_bundle(d / 'a.zip')
raw = _r2.bundle_file(d / 'a.zip', 'CLAIMS.json')
first = json.loads(raw, object_pairs_hook=lambda kv: {k: v for k, v in reversed(kv)})
try:
    (d / 'CLAIMS.json').write_bytes(raw); load_json(d / 'CLAIMS.json'); strict = 'accepted'
except ValueError as e:
    strict = f'rejected ({e})'
print('(a) verify ok:', ra['ok'], ra['problems'])
print('    first-wins reader sees:', first['claims'][0]['effective_levels']['math'], '| ceiling',
      first['ceiling']['utility'], '| genesis.common.load_json:', strict)
print('    grep:', 'OPTIMALITY_CHECKED' in raw.decode(), 'CONFIRMED_TRANSFER' in raw.decode())


def manifest_named(files, manifest):
    files['certificates/MANIFEST.json'] = canonical({'claim': 'w', 'math': 'OPTIMALITY_CHECKED', 'checker': 'drat-trim',
                                                     'verdict': 'VALID'})
    files['analysis_code/src/genesis/MANIFEST.json'] = b'{"anything": true}'


_r2.rewrite_bundle(d / 'honest.zip', d / 'b.zip', manifest_named)
with zipfile.ZipFile(d / 'b.zip') as z:  # rewrite_bundle lists every file in MANIFEST; drop them again
    names = z.namelist(); base = names[0].split('/')[0] + '/'
    content = {n: z.read(n) for n in names}
m = json.loads(content[base + 'MANIFEST.json'])
m['files'] = {k: v for k, v in m['files'].items() if not k.endswith('MANIFEST.json')}
content[base + 'MANIFEST.json'] = canonical(m)
with zipfile.ZipFile(d / 'b2.zip', 'w') as z:
    for n, v in content.items():
        z.writestr(n, v)
rb = verify_bundle(d / 'b2.zip')
print('(b) unlisted, unhashed certificates/MANIFEST.json shipped; verify ok:', rb['ok'], rb['problems'])

# (c) a real revocation event appended without its trailing newline
with Store(d / 'c') as s:
    before = (d / 'c' / 'events.jsonl').read_bytes()
    EvidenceKernel(s).revoke(w, 'witness checker bug', 'auditor')
    after = (d / 'c' / 'events.jsonl').read_bytes()
    new_objects = {p.name: p.read_bytes() for p in (d / 'c' / 'objects' / 'sha256').iterdir()}
tail = after[len(before):].split(b'\n')[0]          # ENTITY_COMMITTED evidence_revocation


def partial_tail(files, manifest):
    files['events.jsonl'] = files['events.jsonl'] + tail   # no trailing newline
    for h, v in new_objects.items():
        files.setdefault(f'objects/sha256/{h}', v)


_r2.rewrite_bundle(d / 'honest.zip', d / 'c.zip', partial_tail)
rc = verify_bundle(d / 'c.zip')
lines = _r2.bundle_file(d / 'c.zip', 'events.jsonl').decode().splitlines()
last = json.loads(lines[-1])['event']
print('(c) shipped events.jsonl lines:', len(lines), '| last line:', last['kind'],
      json.loads(new_objects[last['payload']])['kind'],
      '| verify ok:', rc['ok'], '| bundled math level still:',
      json.loads(_r2.bundle_file(d / 'c.zip', 'CLAIMS.json'))['claims'][0]['effective_levels']['math'])


def outside(path_in, path_out):
    with zipfile.ZipFile(path_in) as zin, zipfile.ZipFile(path_out, 'w') as zout:
        for n in zin.namelist():
            zout.writestr(n, zin.read(n))
        zout.writestr('CLAIMS.json', canonical({'claims': [{'claim_id': 'w', 'effective_levels': TOP}]}))


outside(d / 'honest.zip', d / 'd.zip')
rd = verify_bundle(d / 'd.zip')
print('(d) top-level CLAIMS.json outside release_*; verify ok:', rd['ok'])
ok = ra['ok'] and rb['ok'] and rc['ok'] and rd['ok']
print('ATTACK_SUCCEEDED' if ok else 'ATTACK_BLOCKED')
