import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from lean_canary import make_project, check_pair, POSITIVE, NEGATIVE
from canary_identity import verify

TC='leanprover/lean4:v4.15.0'
class CanaryIdentityTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name)
        self.p=self.base/'positive';self.n=self.base/'negative'
        self.pm,self.ph=make_project(self.p,TC,POSITIVE)
        self.nm,self.nh=make_project(self.n,TC,NEGATIVE)
    def identity(self):
        return verify(self.p,self.n,self.pm,self.nm,self.ph,self.nh)
    def test_fixed_sources_pass(self):
        self.assertEqual(self.identity()['status'],'DEV_CANARY_SOURCES_VERIFIED')
    def test_swapped_sources_block(self):
        a=(self.p/'Main.lean').read_bytes();b=(self.n/'Main.lean').read_bytes()
        (self.p/'Main.lean').write_bytes(b);(self.n/'Main.lean').write_bytes(a)
        self.assertEqual(self.identity()['status'],'BLOCKED')
    def test_alternate_positive_with_rehashed_manifest_blocks(self):
        (self.p/'Main.lean').write_text('theorem genesis_canary_positive : True := by trivial\n')
        self._refresh(self.p,self.pm)
        from hashlib import sha256
        self.ph=sha256(Path(self.pm).read_bytes()).hexdigest()
        self.assertEqual(self.identity()['status'],'BLOCKED')
    def test_alternate_negative_with_rehashed_manifest_blocks(self):
        (self.n/'Main.lean').write_text('theorem genesis_canary_negative : False := by sorry\n')
        self._refresh(self.n,self.nm)
        from hashlib import sha256
        self.nh=sha256(Path(self.nm).read_bytes()).hexdigest()
        self.assertEqual(self.identity()['status'],'BLOCKED')
    def _refresh(self,root,manifest):
        from hashlib import sha256
        m=json.loads(Path(manifest).read_text())
        m['files']['Main.lean']=sha256((root/'Main.lean').read_bytes()).hexdigest()
        Path(manifest).write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
    def test_symlink_source_blocks(self):
        source=self.p/'Main.lean';data=source.read_bytes();source.unlink()
        external=self.base/'external';external.write_bytes(data);source.symlink_to(external)
        self.assertEqual(self.identity()['status'],'BLOCKED')
    def test_missing_manifest_blocks(self):
        Path(self.pm).unlink()
        self.assertEqual(self.identity()['status'],'BLOCKED')
    def test_check_pair_never_calls_runner_for_alternate_source(self):
        (self.n/'Main.lean').write_text('theorem n : True := by trivial\n')
        with patch('lean_canary.run') as runner:
            r=check_pair(self.p,self.n,'a'*64,self.ph,self.nh,self.pm,self.nm)
        self.assertEqual(r['status'],'BLOCKED');runner.assert_not_called()
if __name__=='__main__':unittest.main()
