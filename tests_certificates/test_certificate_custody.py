"""R-03 regression: original proof artifacts survive the world loop and replay without the solver.

Acceptance (roadmap §3.3): export a real certified world-loop result; remove
solver access; verify the original certificate and witness from the bundle
alone. Missing or altered proof objects must block the corresponding status.
Requires the pinned drat-trim and CaDiCaL (the producer runs only while the
loop runs). Missing tools are a failure here, not a skip.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from genesis.common import canonical
from genesis.release_bundle import build_bundle, verify_bundle
from genesis.store import Store
from genesis.verification.tools import tool
from genesis.worldstep import LoopConfig, ResearchLoop

SRC = Path(__file__).resolve().parents[1] / 'src'


def rewrite(bundle, out, change):
    """change(files: dict name->bytes, base) mutates the file map; MANIFEST is re-hashed consistently."""
    with zipfile.ZipFile(bundle) as zin:
        names = zin.namelist(); base = names[0].split('/')[0] + '/'
        files = {n: zin.read(n) for n in names}
    change(files, base)
    manifest = json.loads(files[base + 'MANIFEST.json'])
    manifest['files'] = {n[len(base):]: hashlib.sha256(v).hexdigest() for n, v in files.items()
                         if n != base + 'MANIFEST.json'}
    files[base + 'MANIFEST.json'] = canonical(manifest)
    with zipfile.ZipFile(out, 'w') as zout:
        for n, v in files.items():
            zout.writestr(n, v)


class CertificateCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tool('cadical'); tool('drat-trim')  # raise (fail, not skip) if the pinned tools are absent
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = Path(cls.tmp.name)
        cls.loop = cls.d / 'loop'
        with ResearchLoop(cls.loop, LoopConfig(tasks=2, epochs=2, cpu_budget_per_epoch=20, verify_seconds=20)) as l:
            cls.summary = l.run()
        cls.bundle = cls.d / 'release.zip'
        build_bundle(cls.loop, cls.bundle)
        # A toolchain directory holding only the checker: the producer is not reachable.
        cls.checker_only = cls.d / 'checker_only_toolchain'
        drat = Path(tool('drat-trim')['path'])
        (cls.checker_only / 'drat-trim').mkdir(parents=True)
        shutil.copy2(drat, cls.checker_only / 'drat-trim' / 'drat-trim')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def verify_without_solver(self, bundle):
        code = ('import json,sys\nfrom genesis.verification.tools import tool,ToolUnavailable\n'
                'try:\n    tool("cadical"); solver="AVAILABLE"\nexcept ToolUnavailable:\n    solver="UNAVAILABLE"\n'
                'from genesis.release_bundle import verify_bundle\n'
                'r=verify_bundle(sys.argv[1]);r["solver"]=solver;print(json.dumps(r))\n')
        proc = subprocess.run([sys.executable, '-c', code, str(bundle)], capture_output=True, text=True, timeout=600,
                              env={'PYTHONPATH': str(SRC), 'PATH': '/usr/bin:/bin', 'HOME': str(self.d),
                                   'GENESIS_TOOLCHAIN': str(self.checker_only), 'GENESIS_CHECKER_ONLY': '1'})
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        return json.loads(proc.stdout)

    def test_world_loop_bound_states_reference_their_evidence(self):
        self.assertGreaterEqual(self.summary['optimality_checked'], 1)
        with Store(self.loop) as s:
            bounds = [s.get(s.get(h)['payload_hash']) for (h,) in
                      s.db.execute("SELECT object_hash FROM entities WHERE kind='evidence_node'")
                      if s.get(h)['kind'] == 'bound_state']
            self.assertTrue(bounds)
            for b in bounds:
                self.assertEqual(b['schema'], 'genesis-bound-state-v2')
                cert = s.get(b['certificate_bundle'])
                self.assertEqual(cert['upper']['method'], 'SAT_DRAT')
                self.assertTrue(s.get_bytes(cert['upper']['cnf_sha256']))
                self.assertTrue(s.get_bytes(cert['upper']['proof_sha256']))
                self.assertEqual(cert['lower']['value'], b['lower'])
            # IR program records carry immutable references to the certificates they produced.
            refs = {a for (h,) in s.db.execute("SELECT object_hash FROM entities WHERE kind='ir_program'")
                    for n in s.get(h)['nodes'] for a in n.get('artifacts', [])}
            self.assertTrue({b['certificate_bundle'] for b in bounds} <= refs)

    def test_bundle_alone_replays_with_the_solver_removed(self):
        result = self.verify_without_solver(self.bundle)
        self.assertEqual(result['solver'], 'UNAVAILABLE')
        self.assertTrue(result['ok'], result['problems'])
        self.assertTrue(result['certificate_replays'])
        for r in result['certificate_replays']:
            self.assertEqual((r['status'], r['lower'], r['upper']), ('OPTIMALITY_CHECKED', 'VALID', 'VALID'))

    def _proof_names(self):
        with zipfile.ZipFile(self.bundle) as z:
            base = z.namelist()[0].split('/')[0] + '/'
            certs = [json.loads(z.read(n)) for n in z.namelist() if '/certificates/bundle_' in n]
        return base, [c['upper']['proof_sha256'] for c in certs]

    def test_missing_proof_object_blocks_optimality(self):
        base, proofs = self._proof_names()

        def drop(files, base):
            for p in proofs:
                files.pop(base + f'objects/sha256/{p}')

        out = self.d / 'missing.zip'
        rewrite(self.bundle, out, drop)
        result = self.verify_without_solver(out)
        self.assertFalse(result['ok'])
        self.assertTrue(any('event rebuild' in p or 'does not license' in p or 'replay' in p
                            for p in result['problems']), result['problems'])

    def test_altered_proof_object_blocks_optimality(self):
        base, proofs = self._proof_names()

        def corrupt(files, base):
            # Replace the proof bytes under the same name (a producer that swaps the object).
            name = base + f'objects/sha256/{proofs[0]}'
            files[name] = files[name].replace(b' 0\n', b' 1 0\n', 1)

        out = self.d / 'altered.zip'
        rewrite(self.bundle, out, corrupt)
        result = self.verify_without_solver(out)
        self.assertFalse(result['ok'])

    def test_checker_only_mode_refuses_to_run_the_producer(self):
        from genesis.verification.sat import solve
        from genesis.verification.tools import ToolUnavailable
        os.environ['GENESIS_CHECKER_ONLY'] = '1'
        try:
            with self.assertRaises(ToolUnavailable):
                solve(b'p cnf 1 1\n1 0\n')
        finally:
            os.environ.pop('GENESIS_CHECKER_ONLY')


if __name__ == '__main__':
    unittest.main()
