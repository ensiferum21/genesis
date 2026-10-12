"""Research budget authority and accounting (Repair B, finding B20-REVIEW-02).

In B20 the research loop (``learning/research.py::run``)
  * started its CPU clock after ``policy.reset`` (preparation was free),
  * checked the cap before choosing an action, so the last action could start with any
    positive remainder,
  * passed ``max(1, ceil(remaining))`` seconds to E, rounding a fractional remainder up
    to at least a whole second of extra prover CPU, and
  * accepted a successful proof even when it finished after the cap.
The recorded Huntington seed-204 comparison is fixed 1.01 s versus learned 1.93 s under
a nominal 1 s cap; every Sheffer run exceeded its 1.57 s cap as well.

This module is the replacement: one account per research campaign, opened before any
preparation, against a frozen :class:`StudyBudget`.

* In-process work (policy reset and choice, deciders, retrieval, feature construction,
  macro induction, curriculum synthesis) is measured with ``process_time_ns`` and
  charged to its category. If it pushes the account over the cap the account stops:
  nothing further is reserved, and the overrun is recorded, never hidden.
* External work is *reserved before launch*. A reservation is at most the remaining
  budget less the declared kill tolerance, and at least the admissible quantum. With no
  admissible quantum left the account stops with ``INSUFFICIENT_REMAINING_BUDGET``; a
  fractional remainder is never rounded up into extra credited work.
* The attempt runs under :func:`run_bounded`: its own session/process group, a
  per-attempt cgroup that meters the CPU of every descendant (cgroup v1 cpuacct or v2
  cpu.stat; a procfs process-group meter is the documented lower-bound fallback), an
  outer kill when the metered CPU reaches the reservation, a wall deadline, and an
  RLIMIT backstop. The measured CPU (not the reservation) is charged.
* Late-result rule (frozen in the budget): a result is credited only if the attempt
  exited by itself within its reserved CPU and wall time. A proof produced by an attempt
  that overran or was killed is kept as raw output but earns nothing.
* With a journal, every reservation and settlement is appended and fsynced. Reopening
  the journal charges every open reservation in full as ``INTERRUPTED`` (no free
  retries) and continues the attempt numbering.

Enforcement modes (frozen in the budget):
  PROVER_QUANTUM    the prover's own whole-second limit must fit inside the reservation
                    with the declared overhead (reservation >= 1 s + overhead).
  OUTER_SUPERVISED  the metered outer kill enforces the reservation on the whole process
                    tree, so a fractional reservation may launch; the prover's own limit
                    is rounded up, which earns nothing because a killed attempt is never
                    credited.

``grant_bridge`` connects the account to the store-backed ``kernel.authority.GrantLedger``:
the campaign's CPU is leased as a child grant and the settled total is charged to it, so
research cannot exceed the authority it was given.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import uuid

from ..common import digest

SCHEMA = 'genesis-research-budget-v1'
ACCOUNT_SCHEMA = 'genesis-research-account-v1'
CATEGORIES = ('preparation', 'policy', 'decider', 'retrieval', 'prover', 'checker', 'induction', 'curriculum',
              'training', 'amortized_training', 'evaluation', 'supervision')
CHARGING = ('FULL_COST', 'AMORTIZED')
ENFORCEMENT = ('PROVER_QUANTUM', 'OUTER_SUPERVISED')
LATE_RULES = ('NOT_CREDITED',)
STOP_REASONS = ('INSUFFICIENT_REMAINING_BUDGET', 'BUDGET_EXHAUSTED_IN_PROCESS', 'ATTEMPT_CAP', 'WALL_EXHAUSTED')
NS = 1_000_000_000


@dataclass(frozen=True)
class StudyBudget:
    """Frozen per-campaign limits. Every arm of a comparison gets an equal record."""
    cpu_ns: int
    wall_ns: int
    attempt_cpu_ns: int                      # per-attempt reservation cap (the prover's per-call budget)
    memory_bytes: int = 2 << 30
    max_attempts: int = 100_000
    concurrency: int = 1
    quantum_ns: int = NS                     # smallest prover limit (E takes whole CPU seconds)
    overhead_ns: int = 250_000_000           # declared reserve on top of the prover limit (start-up, output)
    tolerance_ns: int = 50_000_000           # measured kill tolerance, held back from the cap; never credited
    charging: str = 'FULL_COST'
    amortize_uses: int = 0                   # preregistered uses when charging == 'AMORTIZED'
    late_rule: str = 'NOT_CREDITED'
    enforcement: str = 'PROVER_QUANTUM'

    def __post_init__(self):
        for f in ('cpu_ns', 'wall_ns', 'attempt_cpu_ns', 'memory_bytes', 'max_attempts', 'concurrency',
                  'quantum_ns', 'overhead_ns', 'tolerance_ns', 'amortize_uses'):
            v = getattr(self, f)
            if type(v) is not int or v < 0:
                raise ValueError(f'{f} must be a non-negative integer')
        if self.charging not in CHARGING or self.late_rule not in LATE_RULES or self.enforcement not in ENFORCEMENT:
            raise ValueError('unknown charging policy, late-result rule or enforcement mode')
        if self.charging == 'AMORTIZED' and self.amortize_uses < 1:
            raise ValueError('amortized charging needs a preregistered number of uses')
        if self.concurrency != 1:
            raise ValueError('only sequential campaigns are supported (concurrency 1)')

    @classmethod
    def from_seconds(cls, cpu_s, *, attempt_s, wall_factor=4, **kw):
        """Campaign cap ``cpu_s``; each prover attempt may use ``attempt_s`` of prover CPU plus
        the declared overhead reserve (so the reservation is attempt_s + overhead)."""
        overhead = kw.pop('overhead_ns', 250_000_000)
        cpu_ns = int(round(cpu_s * NS))
        return cls(cpu_ns=cpu_ns, wall_ns=int(round(cpu_s * NS * wall_factor)) + 30 * NS,
                   attempt_cpu_ns=int(round(attempt_s * NS)) + overhead, overhead_ns=overhead, **kw)

    @property
    def admissible_ns(self):
        """Smallest reservation that may launch an attempt (see the module docstring)."""
        return self.quantum_ns + (self.overhead_ns if self.enforcement == 'PROVER_QUANTUM' else 0)

    def prover_limit_s(self, reservation_ns):
        if self.enforcement == 'PROVER_QUANTUM':
            return int((reservation_ns - self.overhead_ns) // NS)          # floor: never rounded up
        return max(1, int(math.ceil(reservation_ns / NS)))                # meter-enforced; earns nothing extra

    def record(self):
        return dict(asdict(self), schema=SCHEMA)

    def identity(self):
        return digest(self.record())


@dataclass
class Reservation:
    attempt_id: str
    category: str
    cpu_ns: int
    wall_ns: int
    prover_limit_s: int
    purpose: str


class Journal:
    """Append-only, fsynced JSON-lines journal of reservations and settlements."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def entries(self):
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                break          # a torn final line from a crash: ignore it, everything before is intact
        return out

    def append(self, entry):
        data = (json.dumps(entry, sort_keys=True) + '\n').encode()
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)


class Account:
    """One campaign's resource account. Not thread-safe (campaigns are sequential)."""

    def __init__(self, budget, *, label, journal=None, grant=None):
        if not isinstance(budget, StudyBudget):
            raise TypeError('budget must be a StudyBudget')
        self.budget, self.label = budget, label
        self.cpu = {c: 0 for c in CATEGORIES}
        self.wall = {c: 0 for c in CATEGORIES}
        self.attempts, self.open, self.events = [], {}, []
        self.seq = 0
        self.stop_reason = None
        self.overrun_ns = 0
        self.wall0 = time.monotonic_ns()
        self.grant = grant
        self.journal = Journal(journal) if journal else None
        if self.journal:
            self._recover()
            self._log({'type': 'OPEN', 'label': label, 'budget': budget.record(), 'budget_sha256': budget.identity()})

    # ------------------------------------------------------------ bookkeeping
    def _log(self, entry):
        entry = dict(entry, account=self.label)
        self.events.append(entry)
        if self.journal:
            self.journal.append(entry)

    def _recover(self):
        """Replay a journal left by an earlier process: settled attempts are restored, open
        reservations are charged in full as INTERRUPTED (never a free retry)."""
        reserved, settled = {}, set()
        for e in self.journal.entries():
            if e.get('account') != self.label:
                continue
            if e['type'] == 'OPEN' and e['budget_sha256'] != self.budget.identity():
                raise ValueError('journal belongs to a campaign with a different budget')
            if e['type'] == 'RESERVE':
                reserved[e['attempt_id']] = e
                self.seq = max(self.seq, int(e['attempt_id'].rsplit(':', 1)[1]) + 1)
            elif e['type'] == 'SETTLE':
                settled.add(e['attempt_id'])
                self.cpu[e['category']] += e['cpu_ns']
                self.wall[e['category']] += e['wall_ns']
                self.attempts.append(e['record'])
            elif e['type'] == 'CHARGE':
                self.cpu[e['category']] += e['cpu_ns']
                self.wall[e['category']] += e['wall_ns']
            elif e['type'] == 'STOP':
                self.stop_reason = e['reason']
        for aid, e in sorted(reserved.items()):
            if aid in settled:
                continue
            rec = {'attempt_id': aid, 'category': e['category'], 'purpose': e['purpose'], 'status': 'INTERRUPTED',
                   'termination': 'INTERRUPTED', 'reserved_cpu_ns': e['cpu_ns'], 'cpu_ns': e['cpu_ns'],
                   'wall_ns': 0, 'eligible': False, 'reason': 'interrupted before settlement: charged in full'}
            self.cpu[e['category']] += e['cpu_ns']
            self.attempts.append(rec)
            self.journal.append({'type': 'SETTLE', 'account': self.label, 'attempt_id': aid,
                                 'category': e['category'], 'cpu_ns': e['cpu_ns'], 'wall_ns': 0, 'record': rec})

    def cpu_total(self):
        return sum(self.cpu.values())

    def outstanding_ns(self):
        return sum(r.cpu_ns for r in self.open.values())

    def remaining_ns(self):
        return self.budget.cpu_ns - self.cpu_total() - self.outstanding_ns()

    def _stop(self, reason, **detail):
        if self.stop_reason is None:
            self.stop_reason = reason
            self._log({'type': 'STOP', 'reason': reason, **detail})

    def charge(self, category, cpu_ns, wall_ns=0, note=None):
        """Charge measured in-process work. An overrun stops the account and is recorded."""
        if category not in CATEGORIES:
            raise ValueError(f'unknown category {category}')
        cpu_ns, wall_ns = int(cpu_ns), int(wall_ns)
        self.cpu[category] += cpu_ns
        self.wall[category] += wall_ns
        self._log({'type': 'CHARGE', 'category': category, 'cpu_ns': cpu_ns, 'wall_ns': wall_ns, 'note': note})
        over = self.cpu_total() - self.budget.cpu_ns
        if over > 0:
            self.overrun_ns = max(self.overrun_ns, over)
            self._stop('BUDGET_EXHAUSTED_IN_PROCESS', overrun_ns=over, category=category)

    @contextmanager
    def measure(self, category, note=None):
        c0, w0 = time.process_time_ns(), time.monotonic_ns()
        try:
            yield
        finally:
            self.charge(category, time.process_time_ns() - c0, time.monotonic_ns() - w0, note)

    def precharge_training(self, training_cpu_ns):
        """Charge a trained component's cost under the frozen charging policy."""
        if self.budget.charging == 'FULL_COST':
            self.charge('training', training_cpu_ns, note='full training cost charged to this campaign')
        else:
            share = -(-int(training_cpu_ns) // self.budget.amortize_uses)       # ceiling division
            self.charge('amortized_training', share,
                        note=f'training {training_cpu_ns} ns amortized over {self.budget.amortize_uses} '
                             'preregistered uses')

    # ------------------------------------------------------------ external attempts
    def reserve(self, category, *, purpose, cpu_ns=None):
        """Reserve resources for one external attempt, or return None and stop."""
        if category not in CATEGORIES:
            raise ValueError(f'unknown category {category}')
        if self.stop_reason:
            return None
        if self.seq >= self.budget.max_attempts:
            self._stop('ATTEMPT_CAP')
            return None
        if time.monotonic_ns() - self.wall0 >= self.budget.wall_ns:
            self._stop('WALL_EXHAUSTED')
            return None
        # The declared kill tolerance is held back from the last reservation, so a metered kill's
        # latency stays inside the cap; a larger overshoot is recorded as an overrun, never credited.
        want = min(self.budget.attempt_cpu_ns if cpu_ns is None else int(cpu_ns),
                   self.remaining_ns() - self.budget.tolerance_ns)
        if want < self.budget.admissible_ns:
            self._stop('INSUFFICIENT_REMAINING_BUDGET', remaining_ns=self.remaining_ns(),
                       admissible_ns=self.budget.admissible_ns)
            return None
        limit_s = self.budget.prover_limit_s(want)
        wall = min(max(want * 3, want + 5 * NS), self.budget.wall_ns - (time.monotonic_ns() - self.wall0))
        if wall < want:
            self._stop('WALL_EXHAUSTED', remaining_wall_ns=wall)
            return None
        res = Reservation(f'{self.label}:{self.seq}', category, want, int(wall), int(limit_s), purpose)
        self.seq += 1
        self.open[res.attempt_id] = res
        self._log({'type': 'RESERVE', 'attempt_id': res.attempt_id, 'category': category, 'cpu_ns': want,
                   'wall_ns': res.wall_ns, 'prover_limit_s': res.prover_limit_s, 'purpose': purpose})
        return res

    def settle(self, res, *, cpu_ns, wall_ns, termination, status, meter, extra=None):
        """Charge the measured usage and decide eligibility under the frozen late-result rule."""
        if res.attempt_id not in self.open:
            raise ValueError('unknown or already settled reservation')
        del self.open[res.attempt_id]
        cpu_ns = int(cpu_ns) if cpu_ns is not None else res.cpu_ns    # unmeasured: charge the reservation
        wall_ns = int(wall_ns)
        reasons = []
        if termination != 'EXITED':
            reasons.append(f'attempt did not exit by itself ({termination})')
        if cpu_ns > res.cpu_ns:
            reasons.append(f'CPU {cpu_ns} ns exceeded the reservation {res.cpu_ns} ns')
        if wall_ns > res.wall_ns:
            reasons.append(f'wall {wall_ns} ns exceeded the reservation {res.wall_ns} ns')
        if meter.get('lower_bound'):
            reasons.append('CPU meter is a lower bound for this attempt')
        eligible = not reasons
        rec = {'attempt_id': res.attempt_id, 'category': res.category, 'purpose': res.purpose, 'status': status,
               'termination': termination, 'reserved_cpu_ns': res.cpu_ns, 'reserved_wall_ns': res.wall_ns,
               'prover_limit_s': res.prover_limit_s, 'cpu_ns': cpu_ns, 'wall_ns': wall_ns,
               'kill_overshoot_ns': max(0, cpu_ns - res.cpu_ns), 'meter': meter, 'eligible': eligible,
               'reason': '; '.join(reasons) or None, **(extra or {})}
        self.cpu[res.category] += cpu_ns
        self.wall[res.category] += wall_ns
        self.attempts.append(rec)
        self._log({'type': 'SETTLE', 'attempt_id': res.attempt_id, 'category': res.category, 'cpu_ns': cpu_ns,
                   'wall_ns': wall_ns, 'record': rec})
        over = self.cpu_total() - self.budget.cpu_ns
        if over > 0:
            self.overrun_ns = max(self.overrun_ns, over)
            self._stop('BUDGET_EXHAUSTED_IN_PROCESS', overrun_ns=over, category=res.category)
        return rec

    # ------------------------------------------------------------ export
    def record(self):
        statuses = {}
        for a in self.attempts:
            statuses[a['status']] = statuses.get(a['status'], 0) + 1
        out = {'schema': ACCOUNT_SCHEMA, 'label': self.label, 'budget': self.budget.record(),
               'budget_sha256': self.budget.identity(), 'cpu_ns_by_category': dict(self.cpu),
               'wall_ns_by_category': dict(self.wall), 'cpu_ns_total': self.cpu_total(),
               'within_cap': self.cpu_total() <= self.budget.cpu_ns, 'overrun_ns': self.overrun_ns,
               'stop_reason': self.stop_reason, 'attempts': len(self.attempts), 'attempt_statuses': statuses,
               'eligible_attempts': sum(a['eligible'] for a in self.attempts),
               'outstanding_reservations': sorted(self.open), 'attempt_records': list(self.attempts),
               'charged': 'all categories, including preparation, policy choice, deciders, retrieval, failed, '
                          'killed and interrupted attempts'}
        out['account_sha256'] = digest(out)
        return out


def grant_bridge(ledger, parent_grant, budget, *, purpose):
    """Lease the campaign's CPU from a store-backed GrantLedger (kernel.authority).
    Returns the child grant id; call ``settle_grant`` with the finished account."""
    return ledger.child(parent_grant, {'cpu_seconds': budget.cpu_ns / NS,
                                       'attempts': budget.max_attempts}, ['execute_sandboxed_code'], purpose=purpose)


def settle_grant(ledger, grant_id, account):
    rec = account.record()
    return ledger.charge(grant_id, rec['account_sha256'], cpu_seconds=rec['cpu_ns_total'] / NS,
                         attempts=rec['attempts'])


# ---------------------------------------------------------------- bounded execution

class _CgroupV1:
    kind = 'cgroup-v1-cpuacct'

    def __init__(self, name, base=Path('/sys/fs/cgroup')):
        self.dir = base / 'cpuacct' / 'genesis-research' / name
        self.dir.mkdir(parents=True)

    def enter(self, pid):
        (self.dir / 'cgroup.procs').write_text(str(pid))

    def usage(self):
        return int((self.dir / 'cpuacct.usage').read_text())

    def pids(self):
        return [int(x) for x in (self.dir / 'cgroup.procs').read_text().split()]

    def close(self):
        for _ in range(200):
            try:
                self.dir.rmdir()
                return
            except OSError:
                for p in self.pids():
                    try:
                        os.kill(p, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                time.sleep(0.01)


class _CgroupV2(_CgroupV1):
    kind = 'cgroup-v2-cpu.stat'

    def __init__(self, name, base=Path('/sys/fs/cgroup')):
        self.dir = base / 'genesis-research' / name
        self.dir.mkdir(parents=True)

    def usage(self):
        for line in (self.dir / 'cpu.stat').read_text().splitlines():
            k, v = line.split()
            if k == 'usage_usec':
                return int(v) * 1000
        raise RuntimeError('cpu.stat without usage_usec')


def _cgroup(name):
    base = Path('/sys/fs/cgroup')
    try:
        if (base / 'cpuacct').is_dir() and os.access(base / 'cpuacct', os.W_OK):
            return _CgroupV1(name, base)
        if (base / 'cgroup.controllers').exists() and os.access(base, os.W_OK):
            return _CgroupV2(name, base)
    except OSError:
        return None
    return None


def _procfs_group_cpu(pgid):
    """CPU (ns) of live members of a process group, including their reaped children."""
    tick = os.sysconf('SC_CLK_TCK')
    total = 0
    for d in os.listdir('/proc'):
        if not d.isdigit():
            continue
        try:
            raw = Path(f'/proc/{d}/stat').read_text()
        except OSError:
            continue
        fields = raw[raw.rindex(')') + 2:].split()
        if int(fields[2]) != pgid:
            continue
        total += sum(int(x) for x in fields[11:15])
    return total * (NS // tick)


def run_bounded(argv, *, cpu_ns, wall_ns, memory_bytes=2 << 30, env=None, cwd=None, poll_s=0.005,
                output_cap=16 << 20, label=None):
    """Run argv under an outer CPU and wall budget, metering every descendant.

    Returns {'termination': EXITED | CPU_BUDGET_KILLED | WALL_KILLED | RLIMIT_KILLED | START_FAILED,
             'exit_code', 'stdout', 'stderr', 'cpu_ns', 'wall_ns', 'meter': {...}}.
    """
    name = f'{label or "attempt"}-{os.getpid()}-{uuid.uuid4().hex[:10]}'.replace('/', '_').replace(':', '_')
    cg = _cgroup(name)
    hard_s = int(math.ceil(cpu_ns / NS)) + 1

    def pre():
        if cg is not None:
            cg.enter(os.getpid())
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (hard_s, hard_s))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    start = time.monotonic_ns()
    try:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=env if env is not None else {'PATH': '/usr/bin:/bin'}, cwd=cwd,
                             start_new_session=True, preexec_fn=pre, close_fds=True)
    except OSError as exc:
        if cg is not None:
            cg.close()
        return {'termination': 'START_FAILED', 'exit_code': None, 'stdout': '', 'stderr': type(exc).__name__,
                'cpu_ns': 0, 'wall_ns': time.monotonic_ns() - start,
                'meter': {'kind': cg.kind if cg else 'procfs-pgid', 'lower_bound': False}}
    bufs = {'stdout': bytearray(), 'stderr': bytearray()}

    def reader(stream, key):
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            room = output_cap - len(bufs[key])
            if room > 0:
                bufs[key].extend(chunk[:room])
    threads = [threading.Thread(target=reader, args=(p.stdout, 'stdout'), daemon=True),
               threading.Thread(target=reader, args=(p.stderr, 'stderr'), daemon=True)]
    for t in threads:
        t.start()

    def metered():
        if cg is not None:
            try:
                return cg.usage()
            except OSError:
                return None
        return _procfs_group_cpu(p.pid)

    def kill_all():
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        if cg is not None:
            for q in cg.pids():
                try:
                    os.kill(q, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    termination, peak, rusage_ns = 'EXITED', 0, 0
    status = None
    while True:
        pid, st, ru = os.wait4(p.pid, os.WNOHANG)
        if pid == p.pid:
            status, rusage_ns = st, int((ru.ru_utime + ru.ru_stime) * NS)
            break
        used = metered()
        if used is not None:
            peak = max(peak, used)
        if peak >= cpu_ns:
            termination = 'CPU_BUDGET_KILLED'
            kill_all()
        elif time.monotonic_ns() - start >= wall_ns:
            termination = 'WALL_KILLED'
            kill_all()
        if termination != 'EXITED':
            _, status, ru = os.wait4(p.pid, 0)
            rusage_ns = int((ru.ru_utime + ru.ru_stime) * NS)
            break
        time.sleep(poll_s)
    p.returncode = os.waitstatus_to_exitcode(status)
    wall = time.monotonic_ns() - start
    kill_all()                         # descendants that outlived the leader are not allowed to keep running
    for t in threads:
        t.join(timeout=5)
    for s in (p.stdout, p.stderr):
        s.close()
    if cg is not None:
        try:
            final = cg.usage()
        except OSError:
            final = peak
        cg.close()
        cpu, meter = max(final, peak, rusage_ns), {'kind': cg.kind, 'lower_bound': False}
    else:
        cpu = max(peak, rusage_ns)
        meter = {'kind': 'procfs-pgid+wait4', 'lower_bound': True,
                 'note': 'descendants that leave the process group or are reaped by another process are missed'}
    if termination == 'EXITED' and p.returncode < 0 and -p.returncode in (signal.SIGKILL, signal.SIGXCPU):
        termination = 'RLIMIT_KILLED'
    return {'termination': termination, 'exit_code': p.returncode, 'cpu_ns': cpu, 'wall_ns': wall,
            'stdout': bytes(bufs['stdout']).decode(errors='replace'),
            'stderr': bytes(bufs['stderr']).decode(errors='replace'), 'meter': meter}


__all__ = ['StudyBudget', 'Account', 'Reservation', 'Journal', 'run_bounded', 'grant_bridge', 'settle_grant',
           'CATEGORIES', 'ENFORCEMENT', 'SCHEMA', 'ACCOUNT_SCHEMA', 'NS']
