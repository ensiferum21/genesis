"""B20_R153: `mcx3-v1`, mcx2 with a construct algebra (targets, ?-guards over observables, repeats, blocks).

The binary is rebuilt from the in-repository source and equals the pin. **Identity:** mcx2's unchanged source and
mcx3's, both built with a counting clock in place of the CPU clock (`tests_genesis/native/countclock.h`), give the
same output and the same trace (every exp call's clock reading and argument) on every mcx2 program of a battery, at
several levels, perturbation modes and pools; and the comparison sees a difference when there is one (two planted
mutants of mcx3). **Meaning of the constructs:** equivalences that hold clock reading for clock reading (a target
equal to the default, `B@c` and `b`, a block and `P1` before its items, a repeat and its unrolling, a guard that
always or never holds); test builds with MCX3_PROBE show where each operator acts, recompute each observable from
what it is made of, and show that the item after a guard runs exactly when the guard holds. **The canonical form
keeps the meaning:** a program and non-canonical writings of it run the same operators in the same states.
Programs and configurations are data, refused outside their grammar by the kind and the binary; constructs reach
the optimum of small graphs; it runs in the sandbox; the runner admits it as a max-cut kind."""
from itertools import product
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import candidates_maxcut as CM  # noqa: E402
from genesis import graphs_maxcut as GM  # noqa: E402
from genesis.candidate_kinds import mcx2 as K2  # noqa: E402
from genesis.candidate_kinds import mcx3 as K  # noqa: E402
from genesis.expressive import operators as OPS  # noqa: E402
from genesis.models_maxcut import MaxCutCandidateView, MaxCutTask  # noqa: E402
import b20r153_build_mcx3 as B  # noqa: E402

MCX2_PROGRAMS = ('B100 X I S2000 C', 'B1', 'b5 X I', 'B10 S50 M', 'B10 P3 H S20 R', 'B3 C', 'b1 I I X S5 C P2 M',
                 'b2 D', 'B5 L', 'B3 S10 L D X I', 'S5 P2 C B4 X', 'B2 S3 S4 M P2 P3 R D L')


def rand_edges(n, p, seed, weights=(-2, -1, 1, 3)):
    rng = random.Random(seed)
    return [(u, v, rng.choice(weights)) for u in range(n) for v in range(u + 1, n) if rng.random() < p]


def rand_task(n, p, seed, weights=(-1, 1)):
    return MaxCutTask(task_id=f't{seed}', n=n, edges=tuple(rand_edges(n, p, seed, weights)), family='test')


def brute(task):
    return max(GM.cut_edge_driven(task.edges, '0' + ''.join(bits)) for bits in product('01', repeat=task.n - 1))


def run(binary, n, edges, seed, ms, args):
    text = f'{n} {len(edges)} {seed} {ms}\n' + ''.join(f'{u} {v} {w}\n' for u, v, w in edges)
    r = subprocess.run([str(binary), *args], input=text, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


def raw(text, *args):
    return subprocess.run([K.BINARY, *args], input=text, capture_output=True, text=True, timeout=30)


class Builds:
    """The counting-clock test builds, made once per test run."""
    _dir = None

    @classmethod
    def get(cls):
        if cls._dir is None:
            cls._dir = Path(tempfile.mkdtemp(prefix='mcx3t-'))
            B.build_test(B.MCX2_SOURCE, cls._dir / 'mcx2t')
            B.build_test(B.SOURCE, cls._dir / 'mcx3t')
            B.build_test(B.SOURCE, cls._dir / 'mcx3p', probe=True)
        return cls._dir


def probe_lines(n, edges, seed, ms, prog, levels=4, pool=8):
    code, out, err = run(Builds.get() / 'mcx3p', n, edges, seed, ms, ['-prog', prog, '-levels', str(levels),
                                                                       '-pool', str(pool)])
    assert code == 0, err[-300:]
    return [l.split() for l in err.splitlines() if l.startswith(('op ', 'obs '))]


class Binary(unittest.TestCase):
    def test_the_build_is_deterministic_and_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = B.build(Path(d) / 'a'), B.build(Path(d) / 'b')
        self.assertEqual(a, b)
        self.assertEqual(a, K.BINARY_SHA256)
        self.assertEqual(K.binary_digest(), K.BINARY_SHA256)
        self.assertNotEqual(K.BINARY_SHA256, K2.BINARY_SHA256)

    def test_mcx2_is_untouched(self):
        self.assertEqual(K2.binary_digest(), K2.BINARY_SHA256)

    def test_refusals(self):
        ok = '2 1 1 10\n0 1 1\n'
        for prog in ('', 'X', 'B0', 'B', 'Q1', 'B1 S', 'B1X', 'B' + '9' * 10, 'B1 D2', 'L', '[ ]', '[ B1', 'B1 ]',
                     '[B1 X]', '*2 S3 B1', '*0 B1', '*2', 'b1@c', 'B1@', 'B1@9', 'B1@x', '?q<3 B1', '?f=3 B1', '?f<',
                     '?f<-1 B1', 'S0 B1', ' '.join(['B1'] * 513), '[ ' * 17 + 'B1' + ' ]' * 17, 'B1 kick(3)'):
            self.assertEqual(raw(ok, '-prog', prog).returncode, 2, prog)
        for prog in ('B1', ' '.join(['B1'] * 40), '[ ' * 15 + 'B1' + ' ]' * 15, 'B1@01234567 ?f>0 [ X@h ] *3 C@a'):
            self.assertEqual(raw(ok, '-prog', prog).returncode, 0, prog)
        for opt, val in (('-levels', '0'), ('-levels', '9'), ('-tmax', '0'), ('-L0hot', '2'), ('-pert', '3')):
            self.assertEqual(raw(ok, opt, val).returncode, 2, opt)
        self.assertEqual(raw('2 1 1 10\n0 0 1\n').returncode, 2)
        self.assertEqual(raw('3 2 1 10\n0 1 10000000\n0 2 10000000\n').returncode, 3)

    def test_default_program_and_output(self):
        r = raw('4 5 7 50\n0 1 1\n1 2 1\n2 3 1\n0 3 1\n0 2 -1\n')
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.split('\n')
        self.assertEqual(lines[0], 'o 4')
        self.assertIn(lines[1], ('v 0101', 'v 1010'))


class Identity(unittest.TestCase):
    """Every mcx2 program means the same in mcx3: same output and same trace under a counting clock."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Builds.get()
        rng = random.Random(153)
        cls.programs = list(MCX2_PROGRAMS) + [OPS.random_engine(rng, 'L0')['prog'] for _ in range(14)]
        cls.graphs = [(n, rand_edges(n, p, s)) for s, (n, p) in enumerate(((60, 0.12), (150, 0.05), (260, 0.03)))]
        cls.graphs.append((120, rand_edges(120, 0.06, 9, weights=(-1, 1))))
        cfgs = [{'levels': 4, 'pert': 2, 'pool': 8}, {'levels': 1, 'pert': 0, 'pool': 4},
                {'levels': 3, 'pert': 1, 'pool': 16}, {'levels': 8, 'pert': 2, 'pool': 4}]
        cls.configs = [dict(K.DEFAULT, **c) for c in cfgs]
        for _ in range(2):
            cls.configs.append({k: rng.choice(v) for k, v in K.SPACE.items()})

    def args(self, prog, cfg):
        return K2.arguments(dict(cfg, prog=prog))

    def battery(self, other, programs=None):
        diffs, runs, calls = 0, 0, 0
        for i, prog in enumerate(programs or self.programs):
            for j, cfg in enumerate(self.configs):
                n, E = self.graphs[(i + j) % len(self.graphs)]
                for seed in (1, 2 + i):
                    a = run(self.dir / 'mcx2t', n, E, seed, 4, self.args(prog, cfg))
                    b = run(other, n, E, seed, 4, self.args(prog, cfg))
                    self.assertEqual(a[0], 0, a[2][-200:])
                    runs += 1
                    diffs += a != b
                    calls += int(a[2].split()[2])
        return diffs, runs, calls

    def test_mcx2_programs_are_identical_in_mcx3(self):
        diffs, runs, calls = self.battery(self.dir / 'mcx3t')
        self.assertEqual(diffs, 0)
        self.assertGreater(runs, 300)
        self.assertGreater(calls, 100 * runs)           # the traces are not trivial

    def test_the_comparison_sees_a_planted_difference(self):
        src = B.SOURCE.read_text()
        extra_clock = src.replace("            if (i > 0 && out_of_time()) break;\n            G *h = rp[slot[2 * lv[i]]].g;",
                                  "            if (out_of_time()) break;\n            G *h = rp[slot[2 * lv[i]]].g;", 1)
        reversed_x = src.replace("        for (int i = 0; i < nl; i++) {\n            int l = lv[i];\n            if (l + 1 >= NL)",
                                 "        for (int i = nl - 1; i >= 0; i--) {\n            int l = lv[i];\n            if (l + 1 >= NL)", 1)
        self.assertNotEqual(extra_clock, src)
        self.assertNotEqual(reversed_x, src)
        with tempfile.TemporaryDirectory() as d:
            for name, text, progs in (('m1', extra_clock, ['B5 L X I', 'b3 L D']), ('m2', reversed_x, ['B5 X I', 'B100 X I S2000 C'])):
                f = Path(d) / f'{name}.c'
                f.write_text(text)
                B.build_test(f, Path(d) / name)
                diffs, runs, _ = self.battery(Path(d) / name, progs)
                self.assertGreater(diffs, runs // 3, name)


EQUIVALENT = [                                       # (program, its equivalent clock reading for clock reading)
    ('B5@a X', 'B5 X'), ('B5@0 X', 'b5 X'), ('B5@c X', 'b5 X'), ('B5@01234567 I', 'B5 I'), ('b3 X@a I@a D@a', 'b3 X I D'),
    ('b3 L@c C@c L@0', 'b3 L C L'), ('b3 M@h H@h R@h', 'b3 M H R'), ('b3 X@0123 M@3', 'b3 X M'),
    ('b3 [ X I ] C', 'b3 P1 X I C'), ('b3 *2 X C', 'b3 P1 X X C'), ('b2 *3 [ X I ]', 'b2 P1 P1 X I P1 X I P1 X I'),
    ('b2 *2 *2 I', 'b2 P1 P1 I I P1 I I'), ('b2 ?t<10000000 [ X I ] C', 'b2 P1 P1 X I C'),
    ('b2 ?t<0 [ X I ] C', 'b2 P1 P1 C'), ('b2 ?d<0 X I', 'b2 P1 P1 I'), ('b2 ?d<1001 X I', 'b2 P1 X I'),
    ('b2 ?f>1000000 X I', 'b2 P1 P1 P1 I'), ('b2 ?f<1000000 X I', 'b2 P1 P1 X I'), ('b2 ?s<0 M H', 'b2 P1 P1 H'),
    ('*1 b4 X', 'P1 b4 X'), ('b2 [ S9 X ] I', 'b2 P1 S9 X I'),
]


class Constructs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Builds.get()

    def test_equivalent_programs_run_identically(self):
        graphs = [(80, rand_edges(80, 0.1, 3)), (180, rand_edges(180, 0.04, 4))]
        for (a, b), (n, E), seed in product(EQUIVALENT, graphs, (1, 5)):
            ra = run(self.dir / 'mcx3t', n, E, seed, 4, ['-prog', a, '-levels', '4', '-pool', '8'])
            rb = run(self.dir / 'mcx3t', n, E, seed, 4, ['-prog', b, '-levels', '4', '-pool', '8'])
            self.assertEqual(ra[0], 0, (a, ra[2][-200:]))
            self.assertEqual(ra, rb, (a, b))

    def test_targets_act_where_they_say(self):
        n, E = 60, rand_edges(60, 0.1, 6)
        prog = 'B1@13 X@0 I@h D@26 L@a C@1 M@c H@0257 R@a b1 B1 X I D L C M H R X@7 B1@h'
        for levels in (1, 4, 8):
            top = [l for l in probe_lines(n, E, 1, 40, prog, levels) if l[0] == 'op']
            items = prog.split()
            self.assertGreaterEqual(len(top), len(items))
            for got, tok in zip(top, items):
                op, _, tgt = tok.partition('@')
                op = op.rstrip('0123456789')
                tgt = tgt or K.DEFAULT_TARGET[op]
                want = (list(range(levels)) if tgt == 'a' else [0] if tgt == 'c' else [levels - 1] if tgt == 'h'
                        else [int(c) for c in tgt if int(c) < levels])
                self.assertEqual(got, ['op', op] + [str(l) for l in want], (levels, tok))

    def test_observables_are_what_they_are_made_of(self):
        n, E = 90, rand_edges(90, 0.08, 7)
        lines = probe_lines(n, E, 3, 6, 'b2 ?d<1001 X ?s<10000000 I ?t<10000001 D ?f<2000 M', levels=4, pool=8)
        seen, fs = set(), []
        for l in lines:
            if l[0] != 'obs':
                continue
            o, v = l[1], int(l[2])
            seen.add(o)
            if o == 'd':
                k, elites = int(l[3]), l[4:]
                self.assertEqual(len(elites), k)
                if k < 2:
                    self.assertEqual(v, 0)
                    continue
                total, pairs = 0.0, 0
                for i in range(k):
                    for j in range(i + 1, k):
                        h = sum(a != b for a, b in zip(elites[i], elites[j]))
                        total += min(h, n - h)
                        pairs += 1
                self.assertEqual(v, int(total / pairs / n * 1000.0))
                self.assertLessEqual(v, 500)
            elif o == 's':
                best, cuts = int(l[3]), [int(x) for x in l[4:]]
                self.assertEqual(len(cuts), 8)
                self.assertEqual(v, int((max(cuts) - min(cuts)) * 1e6 / max(1, abs(best))))
                self.assertLessEqual(max(cuts), best)
            elif o == 't':
                self.assertGreaterEqual(v, 0)
            else:
                fs.append(v)
        self.assertEqual(seen, {'d', 's', 't', 'f'})
        self.assertEqual(fs, sorted(fs))
        self.assertTrue(0 <= fs[0] and fs[-1] <= 1000 and fs[-1] > 800, fs[-5:])

    def test_the_item_after_a_guard_runs_exactly_when_it_holds(self):
        n, E = 120, rand_edges(120, 0.05, 8)
        decided = {(o, h): 0 for o in 'dstf' for h in (True, False)}
        for d, s, t in ((10, 50000, 50), (22, 100000, 400), (60, 140000, 800)):     # thresholds low to high
            bound = {'d': ('>', d, 'X'), 's': ('<', s, 'I'), 't': ('>', t, 'D'), 'f': ('<', 500, 'M')}
            lines = probe_lines(n, E, 2, 8, f'b2 ?d>{d} X ?s<{s} I ?t>{t} D ?f<500 M')
            for i, l in enumerate(lines[:-1]):
                if l[0] != 'obs':
                    continue
                o, v = l[1], int(l[2])
                cmp, k, op = bound[o]
                holds = v < k if cmp == '<' else v > k
                self.assertEqual(lines[i + 1][:2] == ['op', op], holds, (o, v, lines[i + 1]))
                decided[o, holds] += 1
        self.assertTrue(all(decided.values()), decided)


def decanon(prog, rng):
    """A non-canonical writing of a canonical program with the same meaning (the inverse of `canonical`'s rewrites)."""
    def item(x):
        k = x[0]
        if k == 'op':
            op, arg, tgt = x[1], x[2], x[3]
            r = rng.random()
            if op == 'b' and r < 0.3:
                return ('op', 'B', arg, rng.choice(('c', '0')))
            if tgt is None and op != 'b' and r < 0.3:
                return ('op', op, arg, K.DEFAULT_TARGET[op])
            if tgt == 'c' and op != 'b' and r < 0.5:
                return ('op', op, arg, '0')
            x = ('op', op, arg, tgt)
        elif k == '[':
            x = ('[', lst(x[1]))
        elif k == '*':
            n, body = x[1], item(x[2])
            if n % 2 == 0 and n > 2 and rng.random() < 0.5:
                return ('*', 2, ('*', n // 2, body))
            x = ('*', n, body)
        if k not in K.GUARDS and rng.random() < 0.2:
            return ('[', (x,))
        if k not in K.GUARDS and rng.random() < 0.1:
            return ('*', 1, x)
        return x

    def lst(xs):
        out = [item(x) for x in xs]
        if len(out) >= 2 and rng.random() < 0.4:              # wrap an unguarded run that does not end in a guard
            i = rng.randrange(len(out))
            for j in range(len(out), i + 1, -1):
                if (i == 0 or out[i - 1][0] not in K.GUARDS) and out[j - 1][0] not in K.GUARDS:
                    out[i:j] = [('[', tuple(out[i:j]))]
                    break
        return tuple(out)
    return lst(prog)


class Canonical(unittest.TestCase):
    def test_grammar(self):
        self.assertEqual(K.parse('B100 X I S2000 C'), (('op', 'B', 100, None), ('op', 'X', None, None),
                                                       ('op', 'I', None, None), ('S', 2000), ('op', 'C', None, None)))
        cases = {'B5@c X@a M@h L@c': 'b5 X M L', '*2 *3 B1': '*6 B1', 'B1@3210 X@01234567': 'B1@0123 X',
                 '[ [ B1 X ] ]': 'B1 X', '[ B1 S2 ] C': '[ B1 S2 ] C', 'S3 [ C ] b1': 'S3 C b1',
                 'S3 [ C M ] b1': 'S3 [ C M ] b1', 'b1 [ S5 ]': 'b1 [ S5 ]', '*1 [ b2 ]': 'b2',
                 'B5@0 *1 X [ I ] [ D L ] S3 [ C M ] ?f>500 [ R ]': 'b5 X I D L S3 [ C M ] ?f>500 R'}
        for text, canon in cases.items():
            self.assertEqual(K.render(K.canonical(K.parse(text))), canon, text)
        for bad in ('', 'X I', 'B0', 'B100001', 'S0 B1', 'B1 X3', 'P B1', 'Z1 B1', 7, 'B1 D2', 'B1 L1', '[ ] B1',
                    '*2 ?f<5 B1', 'B1 *1001 X', 'B1 ?f<1001', 'B1 ?s<1000001', 'b1@h', 'B01', 'B1 kick'):
            with self.assertRaises(ValueError, msg=bad):
                K.statements(bad)

    def test_canonical_is_idempotent_and_undoes_rewriting(self):
        rng = random.Random(7)
        for _ in range(400):
            g = OPS.random_engine(rng, 'L1')
            for _ in range(rng.randint(0, 6)):
                g = OPS.mutate(g, rng, 'L1')
            p = K.parse(g['prog'])
            self.assertEqual(K.canonical(p), p)
            self.assertEqual(K.render(K.parse(K.render(p))), g['prog'])
            q = decanon(p, rng)
            self.assertEqual(K.canonical(q), p, K.render(q))

    def test_canonical_keeps_the_meaning(self):
        rng = random.Random(11)
        n, E = 100, rand_edges(100, 0.07, 12)
        checked = compared = 0
        while checked < 25:
            g = OPS.random_engine(rng, 'L1')
            for _ in range(4):
                g = OPS.mutate(g, rng, 'L1')
            if '?f' in g['prog']:
                continue                                  # f reads the clock, which a rewriting shifts
            p = K.parse(g['prog'])
            q = decanon(p, rng)
            if q == p:
                continue
            same = lambda ls: [['op', 'B'] + l[2:] if l[:2] == ['op', 'b'] else l for l in ls]    # b is B@c
            a = same(probe_lines(n, E, 4, 30, g['prog']))
            b = same(probe_lines(n, E, 4, 30, K.render(q)))
            m = min(len(a), len(b))
            self.assertGreaterEqual(m, 3)
            compared += m
            self.assertEqual(a[:m], b[:m], (g['prog'], K.render(q)))
            checked += 1
        self.assertGreater(compared, 25 * 20)

    def test_lambda0_is_mcx2(self):
        rng = random.Random(3)
        progs = list(MCX2_PROGRAMS) + [OPS.random_engine(rng, 'L0')['prog'] for _ in range(50)]
        for t in progs:
            self.assertTrue(K.is_lambda0(K.parse(t)), t)
            self.assertEqual(K2.render(K2.statements(t)), t)
            self.assertIsNone(K.check_config(dict(K.DEFAULT, prog=t)))
        for t in ('b1 X@h', '[ b1 X ] I', '*2 b1', 'b1 ?f<5 X', ' '.join(['b1'] * 33)):
            self.assertFalse(K.is_lambda0(K.parse(t)), t)


class Kind(unittest.TestCase):
    def test_configuration_is_data(self):
        self.assertIsNone(K.check_config(K.DEFAULT))
        self.assertEqual(K.DEFAULT, K2.DEFAULT)
        self.assertEqual(K.SPACE, K2.SPACE)
        self.assertIsNone(K.check_parameters('maxcut_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        self.assertIn('canonical', K.check_config(dict(K.DEFAULT, prog='B5@c X')))
        self.assertIn('canonical', K.check_config(dict(K.DEFAULT, prog='B100  X')))
        self.assertIn('prog', K.check_config(dict(K.DEFAULT, prog='X')))
        self.assertIn('named statement', K.check_config(dict(K.DEFAULT, prog='b1 kick(3)')))
        self.assertIn('levels', K.check_config(dict(K.DEFAULT, levels=5)))
        self.assertIsNotNone(K.check_parameters('triangle_free_large_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        with mock.patch.object(K, 'BINARY_SHA256', '0' * 64):
            self.assertIn('pinned', K.check_parameters('maxcut_v1', {'cpu_seconds': 1.0, 'config': K.DEFAULT}))
        self.assertEqual(K.arguments(K.DEFAULT), K2.arguments(K2.DEFAULT))

    def test_constructs_reach_small_optima(self):
        progs = ('B100 X I S2000 C', 'b3 ?f<500 [ X I ] ?f>499 [ C M ]', 'B2@h *3 [ b1 D ] ?d<20 R@a',
                 'b2 ?s>100 [ X@0 L ] ?t>50 C@a', 'B1@01 *2 I@h S30 [ M H ]', 'b4 [ S9 R ] X@a L@c')
        for seed in range(4):
            t = rand_task(10 + seed, 0.5, seed, weights=(-2, -1, 1, 3))
            opt = brute(t)
            view = MaxCutCandidateView(n=t.n, edges=t.edges)
            for prog, levels in product(progs, (1, 3)):
                cfg = dict(K.DEFAULT, prog=K.render(K.canonical(K.parse(prog))), levels=levels, pool=4)
                out = K.solve(view, {'cpu_seconds': 0.05, 'config': cfg}, 0.05, seed)
                self.assertEqual(out['value'], opt, (seed, prog, levels))
                self.assertEqual(GM.cut_edge_driven(t.edges, out['side']), opt)

    def test_runs_in_the_sandbox(self):
        t = rand_task(16, 0.4, 11)
        cfg = dict(K.DEFAULT, prog='b3 ?f<500 [ X I ] *2 C@a')
        d = CM.build_descriptor('mcx3-v1', {'cpu_seconds': 1.0, 'config': cfg}, cpu_seconds=1.0)
        self.assertIn('candidate_kinds/native/mcx3.c', d['implementation'])
        r = CM.run(t, d, seed=987654321, expected_id=d['descriptor_id'], isolation='runc')
        self.assertEqual((r['status'], r['meter']), ('SUCCESS', 'cgroup'), r)
        self.assertEqual(r['result']['value'], brute(t))
        self.assertLess(r['cpu_ns'], 1.6e9)

    def test_membership(self):
        self.assertTrue(CM.is_maxcut_kind('mcx3-v1'))
        self.assertTrue(CM.is_maxcut_kind('mcx2-v1'))


if __name__ == '__main__':
    unittest.main()
