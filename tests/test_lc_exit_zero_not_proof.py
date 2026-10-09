"""Independent negative regression for GEN-AUD-012 reintroduction."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from gap_engine.kernel.lean_custody import real_lean_gate

class ExitZeroNotProof(unittest.TestCase):
    def test_mocked_zero_exit_never_claims_proof(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);project=root/'project';project.mkdir()
            manifest=root/'manifest.json';manifest.write_text('pinned')
            binary=root/'lean';binary.write_bytes(b'executable')
            exe_hash=hashlib.sha256(binary.read_bytes()).hexdigest()
            man_hash=hashlib.sha256(manifest.read_bytes()).hexdigest()
            output={'status':'EXIT','exit_code':0,'stdout':b'', 'stderr':b'', 'stdout_bytes':0,'stderr_bytes':0}
            with patch('gap_engine.kernel.lean_custody.real_lean_gate.shutil.which',return_value=str(binary)), \
                 patch('gap_engine.kernel.lean_custody.replay_package.audit',return_value={'verified':True}), \
                 patch('gap_engine.kernel.lean_custody.bounded_process.execute',return_value=output):
                r=real_lean_gate.run(project,exe_hash,man_hash,manifest)
            self.assertFalse(r['proof_replayed'])
            self.assertFalse(r['promotion_allowed'])
            self.assertEqual(r['status'],'DEV_LEAN_EXIT_ZERO_UNTRUSTED')
            self.assertEqual(r['evidence']['exit_code'],0)
    def test_old_unsafe_status_not_present(self):
        from inspect import getsource
        self.assertNotIn("out['proof_replayed']=p['exit_code']==0",getsource(real_lean_gate.run))
