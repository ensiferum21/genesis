"""The trial executor (kernel side, run unprivileged by `foundry` in its own mount namespace): it runs the research
plane's candidate sources on workloads against the reference models and answers pass, crash or divergence.

Requests come from the research plane as JSON lines (never unpickled):
  {"op": "trial", "seed": s, "n": n}   -> {"id", "cost"}: a runner for the job's failing segment (seed null) or for a
                                          fresh workload of n <= MAX_OPS operations from the research plane's seed;
  {"op": "call", "id", "src", "steps", "observe"} -> the runner's result (`bench.make_runner`).
Answers go back as length-prefixed pickles of plain builtins. A candidate the static guard refuses is not run."""
import json
import os
import pickle
import random
import struct
import sys

from . import bench as BN
from . import targets as TG

MAX_OPS = 5000
MAX_STEPS = 10 ** 6


def _send(f, obj):
    data = pickle.dumps(obj, protocol=4)
    f.write(struct.pack('>Q', len(data)) + data)
    f.flush()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    spec_fd, req_fd, resp_fd = (int(x) for x in argv[:3])
    with os.fdopen(spec_fd, 'rb') as f:
        spec = pickle.load(f)                       # the kernel's own data
    target, filename, original = spec['target'], spec['filename'], spec['original']
    runners = []
    with os.fdopen(req_fd, 'rb') as req, os.fdopen(resp_fd, 'wb') as resp:
        for line in req:
            try:
                q = json.loads(line)
                if q.get('op') == 'trial':
                    seed = q.get('seed')
                    if seed is None and q.get('whole'):
                        sp = spec['whole']
                        r = BN.make_runner(target, filename, sp['cargs'], sp['ckw'], sp['ops'], sp['start'],
                                           sp['state'], original)
                    elif seed is None:
                        sp = spec['failing']
                        r = BN.make_runner(target, filename, sp['cargs'], sp['ckw'], sp['ops'], sp['start'],
                                           sp['state'], original)
                    else:
                        if not isinstance(seed, (str, int)):
                            raise ValueError('a seed is a string or an integer')
                        n = min(MAX_OPS, max(1, int(q.get('n') or 200)))
                        rng = random.Random(f'trial|{target}|{seed}')
                        cargs, ckw = TG.make_args(target, rng)
                        r = BN.make_runner(target, filename, cargs, ckw, TG.ops(target, rng, n), 0, None, original)
                    runners.append(r)
                    _send(resp, {'id': len(runners) - 1, 'cost': r.cost})
                elif q.get('op') == 'call':
                    r = runners[int(q['id'])]
                    steps = min(MAX_STEPS, int(q.get('steps') or 200000))
                    observe = 'full' if q.get('observe') == 'full' else None
                    _send(resp, r(str(q['src']), steps=steps, observe=observe))
                else:
                    _send(resp, {'error': 'unknown request'})
            except (ValueError, KeyError, IndexError, TypeError) as e:
                _send(resp, {'error': f'{type(e).__name__}: {e}'})
    return 0


if __name__ == '__main__':
    sys.exit(main())
