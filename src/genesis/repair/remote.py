"""The research plane's end of the isolation boundary (`genesis.repairkernel.foundry` starts it): a job handle whose
every method is a request to the kernel or to the trial executor, and `main`, which runs one obstacle episode
(`loop.episode`) through it with the research plane's own vault.

Requests are JSON lines. The kernel answers in JSON; the executor in length-prefixed pickles, which are read with a
restricted unpickler that builds plain builtins only."""
import builtins
import io
import json
import os
import pickle
import struct
import sys

from . import loop as LP


class _Builtins(pickle.Unpickler):
    def find_class(self, module, name):
        if module == 'builtins' and name in ('set', 'frozenset'):
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f'refused: {module}.{name}')


class RemoteHandle:
    def __init__(self, kernel_in, kernel_out, exec_out, exec_in):
        self._kin, self._kout = kernel_in, kernel_out
        self._xout, self._xin = exec_out, exec_in
        hello = self._kernel({'op': 'hello'})
        self.repairable = list(hello['repairable'])
        self.validation = tuple(hello['validation'])

    def _kernel(self, q):
        self._kout.write((json.dumps(q) + '\n').encode())
        self._kout.flush()
        return json.loads(self._kin.readline())

    def _executor(self, q):
        self._xout.write((json.dumps(q) + '\n').encode())
        self._xout.flush()
        head = self._xin.read(8)
        if len(head) < 8:
            raise EOFError('the trial executor closed')
        (n,) = struct.unpack('>Q', head)
        out = _Builtins(io.BytesIO(self._xin.read(n))).load()
        if isinstance(out, dict) and 'error' in out:
            raise RuntimeError(out['error'])
        return out

    def run(self, resume=False):
        return self._kernel({'op': 'run', 'resume': resume})

    def source(self):
        return self._kernel({'op': 'source'})

    def visible_tests(self):
        return [tuple(t) for t in self._kernel({'op': 'visible_tests'})]

    def propose(self, patch):
        return self._kernel({'op': 'propose', 'patch': patch})

    def trial(self, seed=None, n=None, whole=False):
        meta = self._executor({'op': 'trial', 'seed': seed, 'n': n, 'whole': bool(whole)})
        tid = meta['id']

        def runner(src, steps=200000, observe=None):
            return self._executor({'op': 'call', 'id': tid, 'src': src, 'steps': steps, 'observe': observe})
        runner.cost = meta['cost']
        return runner

    def done(self, record):
        return self._kernel({'op': 'done', 'record': record})


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    to_kernel, from_kernel, to_exec, from_exec = (int(x) for x in argv[:4])
    vault_path, params = argv[4], json.loads(argv[5])
    handle = RemoteHandle(os.fdopen(from_kernel, 'rb'), os.fdopen(to_kernel, 'wb'), os.fdopen(to_exec, 'wb'),
                          os.fdopen(from_exec, 'rb'))
    vault = LP.Vault(vault_path)
    try:
        rec = LP.episode(handle, vault=vault, arm=params['arm'], budget=params['budget'], seed=params['seed'],
                         exclude_vault=tuple(params['exclude_vault']), repair_id=params['repair_id'])
    except Exception as e:                                          # noqa: BLE001 - reported, not hidden
        import traceback
        rec = {'outcome': 'research-error', 'error': f'{type(e).__name__}: {e}',
               'traceback': traceback.format_exc()[-2000:]}
    rec['uid'] = os.getuid()
    handle.done(rec)
    return 0


if __name__ == '__main__':
    sys.exit(main())
