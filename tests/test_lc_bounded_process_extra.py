import os
import sys
import tempfile
import time
import unittest
from gap_engine.kernel.lean_custody.bounded_process import execute

class BoundedCaptureExtra(unittest.TestCase):
    def test_large_stream_terminates_quickly(self):
        t=time.monotonic()
        r=execute([sys.executable,'-c',"import os; [os.write(1,b'x'*65536) for _ in range(100000)]"], '/',timeout=5,limit=1024)
        self.assertEqual(r['status'],'OUTPUT_LIMIT')
        self.assertLess(time.monotonic()-t,3)
        self.assertEqual(r['stdout'],b'')
    def test_both_streams_captured(self):
        r=execute([sys.executable,'-c',"import os;os.write(1,b'hello');os.write(2,b'err')"], '/',timeout=3)
        self.assertEqual((r['status'],r['stdout'],r['stderr']),('EXIT',b'hello',b'err'))
    def test_exact_limit(self):
        r=execute([sys.executable,'-c',"import os;os.write(1,b'1234')"], '/',timeout=3,limit=4)
        self.assertEqual(r['status'],'EXIT')
    def test_one_byte_over_limit(self):
        r=execute([sys.executable,'-c',"import os;os.write(2,b'12345')"], '/',timeout=3,limit=4)
        self.assertEqual(r['status'],'OUTPUT_LIMIT')
    def test_timeout(self):
        r=execute([sys.executable,'-c',"import time;time.sleep(3)"], '/',timeout=.1)
        self.assertEqual(r['status'],'TIMEOUT')
    def test_no_unbounded_temp_files(self):
        import inspect
        from gap_engine.kernel.lean_custody import bounded_process
        self.assertNotIn('TemporaryFile',inspect.getsource(bounded_process))

if __name__=='__main__': unittest.main()
