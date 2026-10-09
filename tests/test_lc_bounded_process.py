import sys, unittest
from gap_engine.kernel.lean_custody.bounded_process import execute
class BoundedTests(unittest.TestCase):
    def test_normal(self):
        x=execute([sys.executable,'-c',"print('ok')"],'/tmp')
        self.assertEqual(x['status'],'EXIT');self.assertEqual(x['stdout'],b'ok\n')
    def test_failure(self):
        x=execute([sys.executable,'-c','import sys;sys.exit(9)'],'/tmp')
        self.assertEqual(x['exit_code'],9)
    def test_overflow(self):
        x=execute([sys.executable,'-c',"print('a'*100)"],'/tmp',limit=10)
        self.assertEqual(x['status'],'OUTPUT_LIMIT');self.assertEqual(x['stdout'],b'')
    def test_timeout(self):
        x=execute([sys.executable,'-c','import time;time.sleep(3)'],'/tmp',timeout=.05)
        self.assertEqual(x['status'],'TIMEOUT')
    def test_invalid_bounds(self):
        with self.assertRaises(ValueError):execute([sys.executable],'/tmp',timeout=0)
if __name__=='__main__':unittest.main()
