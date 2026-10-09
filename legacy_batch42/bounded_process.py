"""DEV process runner: bounded pipe capture, deadline, process-group teardown.
Not a sandbox: child processes may evade process groups; use a cgroup for production.
"""
import os
import selectors
import signal
import subprocess
import time

LIMIT = 1048576


def execute(argv, cwd, timeout=120, limit=LIMIT):
    if not (0 < timeout <= 600 and isinstance(limit, int) and not isinstance(limit, bool) and 0 < limit <= LIMIT):
        raise ValueError('invalid resource bounds')
    proc = subprocess.Popen(argv, cwd=cwd, env={'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent'},
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                            close_fds=True)
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    sizes = {'stdout': 0, 'stderr': 0}
    status = 'EXIT'
    deadline = time.monotonic() + timeout
    sel = selectors.DefaultSelector()
    try:
        for name, pipe in (('stdout', proc.stdout), ('stderr', proc.stderr)):
            os.set_blocking(pipe.fileno(), False)
            sel.register(pipe, selectors.EVENT_READ, name)
        while sel.get_map() or proc.poll() is None:
            if time.monotonic() >= deadline:
                status = 'TIMEOUT'
                break
            events = sel.select(timeout=min(0.05, max(0, deadline-time.monotonic())))
            for key, _ in events:
                name = key.data
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    sel.unregister(key.fileobj)
                    continue
                sizes[name] += len(chunk)
                if sizes[name] > limit:
                    status = 'OUTPUT_LIMIT'
                    break
                buffers[name].extend(chunk)
            if status != 'EXIT':
                break
    finally:
        if status != 'EXIT' or proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        sel.close()
        proc.stdout.close()
        proc.stderr.close()
    return {'status': status, 'exit_code': proc.returncode,
            'stdout': bytes(buffers['stdout']) if status == 'EXIT' else b'',
            'stderr': bytes(buffers['stderr']) if status == 'EXIT' else b'',
            'stdout_bytes': sizes['stdout'], 'stderr_bytes': sizes['stderr']}
