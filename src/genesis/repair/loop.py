"""The obstacle loop (research plane; `docs/OMEGA_SELF_REPAIR.md` §2; the Foundry's first milestone): an interrupted
job's failure, taken from recognition to a resumed job and retained knowledge, with no human edit.

`episode(handle, ...)`:
  1. **recognise**: the job's failure is parsed (`capture`); an obstacle in a protected module, or no repairable file,
     is escalated to the Supervisor and nothing is changed;
  2. **reproduce**: the failing segment, from the job's last checkpoint, is re-run on the current source; a failure
     that does not reproduce is escalated;
  3. **diagnose**: the causal obstacle model (`obstacle`) chooses trials by expected information per operation,
     observes them through the probe (coverage, conserved laws), and updates its posterior over causes; laws mined
     from the passing trials, broken first in some method, add evidence;
  4. **regression test**: the smallest failing trial found, with the law it broke, becomes the repair's regression test;
  5. **synthesise**: clonal selection with annealing (`synth.Search`) over the operators, at the suspected methods
     first, law-restoring edits and the vault's suggested operator kinds before the rest;
  6. **test in isolation**: the patch is run on new module objects against fresh trials of the loop's own seeds;
  7-8. **propose**: the patch goes to the kernel (`handle.propose`, once per obstacle): the independent verifier, in
     another process, with checks the loop never sees, then the Supervisor's predefined policy, which promotes it and
     keeps the old source for rollback. The loop learns only whether it was accepted, which checks failed, and
     whether it was promoted;
  9. **resume**: the interrupted job continues from its checkpoint with the promoted source;
  10. **retain**: the repair, its evidence, its regression test and its hunk (the changed lines with a line of context
     either side) go to the vault (a JSON-lines file). The next episode retrieves two things from it: the hunks that
     apply verbatim to its own source, ranked by how closely the failure's signature matches (a recurring obstacle:
     the same defect in another job or another copy of the component), tried first; and the operator kinds that
     worked for the same evidence, which order the rest of the search (transfer to unfamiliar obstacles).
`arm` selects the comparators of the benchmark: 'loop' (all of the above, version 2: the mined laws are evidence for
localisation and sources of law-restoring candidates, never a reason to reject a candidate, because laws mined from a
defective component can encode the defect (B20_R178: S3, S4); and the search widens from the suspected methods to the
whole file, ordered by the posterior, and runs until its budget is spent, because a wrong focus must not end it (W1)),
'loop_v1' (the loop as B20_R178 ran it, frozen: the strong predecessor), 'loop_v2' (the loop as B20_R180 ran it,
frozen); 'loop' is version 3 (after B20_R180): candidates are ordered by the posterior of the line they change, then
by the vault's operator kinds (version 2 let the kinds override the posterior), and the invented operators
(`synth.inventions`: symmetry completion, vestigial calls, dimensional offsets) come after the law-restoring edits,
at the focus and then, widening, everywhere; among passing patches it prefers, in order, one that empties no attribute
outside `__init__`, one that holds no more state than the original on the passing trials, one that keeps the mined
laws on the whole workload, then the cheapest and smallest; 'nolocal' (no diagnosis: every function,
operators shuffled), 'random' (random single and double edits anywhere, no selection), 'enum' (conventional
generate-and-validate: every single edit of the file in source order, no diagnosis, no selection), 'retrieval' (the
vault's suggestions only). Every arm gets the same budget of candidate evaluations and the same verifier."""
import ast
import json
from pathlib import Path
import random
import time

from . import analogy as AN
from . import capture as CP
from . import invent as IV
from . import obstacle as OB
from . import probe as PR
from . import synth as SY

MAX_TRIALS = 14
CONFIRM_SEEDS = ('confirm-a', 'confirm-b')


def kind_of(name):
    """The operator kind of an edit's name ('retrieve <id>: <edit>' is the retrieved edit's kind)."""
    if not name:
        return None
    if name.startswith('retrieve ') and ': ' in name:
        name = name.split(': ', 1)[1]
    return name.split()[0]


def law_kind(law):
    if not law:
        return 'none'
    if ' is None or ' in law:
        return 'coherence'
    if law.startswith('positions'):
        return 'positions'
    if law.startswith(('set(', 'len(')) and '<=' not in law:
        return 'pairing'
    if '<=' in law:
        return 'bound'
    return 'other'


class Vault:
    """Repair knowledge, retained across episodes (JSON lines)."""

    def __init__(self, path):
        self.path = Path(path) if path else None
        self.entries = []
        if self.path and self.path.exists():
            self.entries = [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]

    def hunks(self, src, signature=None, exclude=()):
        """[(name, patched source)] for the retained hunks that apply verbatim to `src` (exactly once), the closest
        failure signatures first."""
        out = []
        for e in self.entries:
            h = e.get('hunk')
            if e.get('id') in exclude or not h or src.count(h['before']) != 1:
                continue
            sig = e.get('signature') or {}
            score = 0
            if signature:
                score = (sig.get('exceptions') == signature.get('exceptions')) + \
                    (sig.get('func') == signature.get('func')) + (sig.get('code') == signature.get('code'))
            out.append((-score, len(out), f"retrieve {e.get('id')}: {e.get('edit')}",
                        src.replace(h['before'], h['after'])))
        out.sort()
        seen, res = set(), []
        for _, _, name, patched in out:
            if patched not in seen:
                seen.add(patched)
                res.append((name, patched))
        return res

    def suggest(self, evidence, exclude=()):
        """Operator kinds ranked by how often they repaired obstacles with the same evidence."""
        count = {}
        for e in self.entries:
            if e.get('id') in exclude:
                continue
            match = (e['evidence'].get('law_kind') == evidence.get('law_kind')) + \
                (e['evidence'].get('exception') == evidence.get('exception'))
            if match:
                count[e['operator']] = count.get(e['operator'], 0) + match
        return sorted(count, key=lambda k: -count[k])

    def retain(self, entry):
        self.entries.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a') as f:
                f.write(json.dumps(entry, default=str) + '\n')


def hunk(a, b, context=1):
    """The changed block between sources a and b, with `context` lines either side: {'before', 'after'}."""
    x, y = a.split('\n'), b.split('\n')
    i = 0
    while i < min(len(x), len(y)) and x[i] == y[i]:
        i += 1
    j = 0
    while j < min(len(x), len(y)) - i and x[-1 - j] == y[-1 - j]:
        j += 1
    lo = max(0, i - context)
    return {'before': '\n'.join(x[lo:len(x) - j + context]), 'after': '\n'.join(y[lo:len(y) - j + context])}


def _lines_and_methods(src):
    tree = ast.parse(src)
    lines, method = set(), {}
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef):
            for st in ast.walk(f):
                if isinstance(st, ast.stmt) and not isinstance(st, ast.FunctionDef):
                    lines.add(st.lineno)
                    method[st.lineno] = f.name
    return lines, method


def _visible(src, tests, filename):
    import types
    bad = 0
    for _, code in tests:
        try:
            mod = types.ModuleType('visible_mod')
            exec(compile(src, filename, 'exec'), mod.__dict__)
            exec(code, {'mod': mod})
        except Exception:                                           # noqa: BLE001
            bad += 1
    return bad


PROBE_T = ('probe_t', 'probe_t2', 'probe_t3')           # SR-2c, SR-2d: probes of candidate transformations
DIAG = ('loop', 'loop_v1', 'loop_v2', 'loop_v3', 'dream', 'dream_online', 'v3learn', 'analogy') + PROBE_T
V3 = ('loop', 'loop_v3', 'dream', 'dream_online', 'v3learn', 'analogy')
V2PLUS = V3 + ('loop_v2',)
LEARN_T = {'v3learn': 1, 'dream': 1, 'analogy': 2}       # arms that lift their verified repairs into transformations
PER_TRANSFORM = 12                                      # a probe's candidates per transformation, most suspected first


def episode(handle, vault=None, arm='loop', budget=300, seed=0, exclude_vault=(), repair_id='repair', trial_key=None,
            family=None):
    """`trial_key` (default: repair_id) names the diagnosis trials' seeds: a benchmark gives every arm the same key
    for the same obstacle, so that arms that diagnose see the same experiments (common random numbers). `family` names
    the obstacle's family (its defect), for the leave-one-out of rule invention.

    Version 4 ('loop') is version 3 ('loop_v3', frozen) plus the rules Genesis invented and the verifier admitted
    (`invent.Library`, in the vault's directory), applied after the builder's inventions. 'dream' is version 3 plus the
    grammar of statements (`invent.dream_edits`), at the focus and then everywhere; when its patch is verified, the
    patch is abstracted into candidate rules (`invent.abstract`) and kept. 'dream_online' is the same search without
    the learning (the benchmark's control: does a learned rule beat searching the grammar directly?). 'probe' tries
    only candidate rules from other families, in the order the inventor believes in (`invent.Inventor`); a verified
    repair admits the rule that made it.

    SR-2c (`analogy`): 'v3learn' is version 3 that lifts its verified repairs into transformations
    (`analogy.lift`; 'dream' does too); 'analogy' is version 3 plus the admitted transformations' candidates, after
    version 3's own (as 'dream' adds the grammar's), and lifts what it repairs; 'probe_t' tries only candidate
    transformations of other families, at the suspected methods, the inventor's believed derivations first
    (`analogy.Deriver`); 'probe_t2' first derives new candidates from the admitted first-generation transformations
    (`analogy.derive`); 'probe_t3' (SR-2d) from every admitted transformation of the first two generations, as the
    third."""
    tk = repair_id if trial_key is None else trial_key
    lib = inv = tl = dv = None
    if vault is not None and vault.path is not None:
        lib = IV.Library(vault.path.parent / 'rules.jsonl')
        inv = IV.Inventor(vault.path.parent / 'inventor.json')
        tl = AN.Transforms(vault.path.parent / 'transforms.jsonl')
        dv = AN.Deriver(vault.path.parent / 'deriver.json')
    t0 = time.process_time()
    rec = {'arm': arm, 'repair': repair_id, 'steps': {}}
    first = handle.run(resume=True)
    if first['status'] == 'done':
        rec['outcome'] = 'no-obstacle'
        return rec
    failure = CP.parse(first['traceback'], repairable=handle.repairable)
    rec['failure'] = {'exception': failure['exception'], 'message': failure['message'][:160],
                      'signature': CP.signature(failure)}
    if CP.escalate(failure, validation=handle.validation, repairable_exists=bool(handle.repairable)):
        rec['outcome'] = 'escalated'
        rec['why'] = 'the fault is in a protected module, or nothing is repairable'
        return rec
    src0 = handle.source()
    filename = handle.repairable[0]
    rep = handle.trial()
    r0 = rep(src0)
    rec['steps']['reproduce'] = r0
    if r0['status'] == 'pass':
        rec['outcome'] = 'escalated'
        rec['why'] = 'the failure did not reproduce'
        return rec
    lines, method_of = _lines_and_methods(src0)
    model = OB.ObstacleModel(repair_id, rec['failure'], lines, method_of)
    ob = PR.Observation(rep(src0, observe='full'))
    model.update(rep.cost, ob.lines, True, 'reproducer')
    failing, passing = [(rep, ob)], []
    trial_runs = []
    rng = random.Random(f'{repair_id}|{seed}')
    if arm in DIAG:
        for k in range(MAX_TRIALS):
            if model.done() and len(passing) >= 2:
                break
            n = model.next_length() if len(passing) >= 1 else min(OB.LENGTHS)
            run = handle.trial(seed=f'loop|{tk}|{seed}|{k}', n=n)
            res = run(src0, observe='full')
            o = PR.Observation(res)
            failed = res['status'] != 'pass'
            model.update(n, o.lines, failed, f'trial {k} (n={n})', cost=run.cost)
            (failing if failed else passing).append((run, o))
            trial_runs.append({'n': n, 'failed': failed})
        laws = PR.mine([o for _, o in passing])
        breaks = [PR.first_break(o, laws) for _, o in failing]
        brk = next((b for b in breaks if b), None)
        if brk:
            model.boost_method(brk[0], brk[1])
        rec['laws'] = [n for n, _ in laws]
        rec['law_break'] = brk
    else:
        for k in range(4):                                  # the comparators get trials too, for negative selection
            run = handle.trial(seed=f'loop|{tk}|{seed}|{k}', n=100)
            res = run(src0, observe='full')
            o = PR.Observation(res)
            (failing if res['status'] != 'pass' else passing).append((run, o))
        brk, laws = None, []
    obstacle = model.summary()
    rec['steps']['diagnose'] = {'trials': trial_runs, 'operations': model.record['cost'],
                                'uncertainty_bits': obstacle['uncertainty_bits'],
                                'top_causes': obstacle['competing_causes'][:4], 'methods': obstacle.get('methods')}
    smallest = min(failing, key=lambda fo: fo[0].cost)[0]
    rec['steps']['regression_test'] = {'trial_operations': smallest.cost, 'law': brk[1] if brk else None}
    tests = handle.visible_tests()
    evidence = {'exception': failure['exception'], 'law_kind': law_kind(brk[1] if brk else None)}
    suggested = vault.suggest(evidence, exclude=exclude_vault) if vault else []
    retrieved = vault.hunks(src0, rec['failure']['signature'], exclude=exclude_vault) if vault else []

    # Every arm but the frozen 'loop_v1' checks a candidate on the job's whole workload from its start, not only from
    # the last checkpoint: the saved state may have been corrupted by the defect (a stale cache, a wrong index), and
    # then no repair passes from it (B20_R180's job version 2; the kernel rolls the resume back to a sound checkpoint).
    target_run = rep if arm == 'loop_v1' else handle.trial(whole=True)
    base_work = {}

    def work(src):
        """The component's work (line events) on the trials that passed before: a patch that only hides the defect by
        doing far more (recomputing what a cache should keep) costs more, the metabolic price of a repair."""
        return sum(run(src)['steps'] for run, _ in passing[:3])

    def storage(src):
        """The most the component holds (its containers' total length at any method return) on the passing trials:
        a patch that hides the defect by never letting go of anything (a bound deleted, a removal skipped) holds
        more. Version 3 only."""
        most = 0
        for run, _ in passing[:3]:
            o = PR.Observation(run(src, observe='full'))
            for _, st in o.returns:
                most = max(most, sum(len(v) for v in st.values() if isinstance(v, (list, dict, set, tuple))))
        return most
    grows = {}

    def evaluate(src):
        r = smallest(src)
        if r['status'] != 'pass':
            frac = (r.get('op') or 0) / max(1, r.get('of') or 1)
            return 60 + 40 * (1 - frac), False
        e = 0.0
        rr = target_run(src, observe='full' if laws and arm == 'loop_v1' else None)
        o = PR.Observation(rr)
        if rr['status'] != 'pass':
            frac = (rr.get('op') or 0) / max(1, rr.get('of') or 1)
            return 50 + 30 * (1 - frac), False
        still = sum(1 for run, _ in failing if run(src)['status'] != 'pass')
        e += 30 * still / max(1, len(failing))
        broken = sum(1 for run, _ in passing if run(src)['status'] != 'pass')
        e += 50 * broken                                         # negative selection: do not attack "self"
        e += 20 * _visible(src, tests, filename)
        if arm == 'loop_v1' and laws and PR.first_break(o, laws):
            e += 3
        if e == 0 and passing:
            if 'w' not in base_work:
                base_work['w'] = max(1, work(src0))
            extra = work(src) / base_work['w'] - 1
            metabolic[src] = max(0.0, extra)
            if arm in V3:
                if 's' not in base_work:
                    base_work['s'] = storage(src0)
                grows[src] = storage(src) > 1.5 * base_work['s'] + 4
        return e, e == 0

    if arm in DIAG:
        methods, mass = model.ranked_methods()
        focus, acc = [], 0.0
        for m in methods:
            focus.append(m)
            acc += mass[m]
            if acc >= 0.8 or len(focus) >= 3:
                break
        if brk and brk[0] not in focus:
            focus.insert(0, brk[0])
        top_lines = [ln for ln in model.ranked_lines()[:8]]
        repertoire = []
        if brk:
            repertoire += SY.law_repairs(src0, brk[0], brk[1])
        local_lines = SY.local_edits(src0, focus_lines=top_lines, focus_funcs=set(focus))
        local_funcs = SY.local_edits(src0, focus_funcs=set(focus))
        trans = SY.transplants(src0, focus)
        rest = [x for x in local_lines + trans + local_funcs if x not in repertoire]

        def kind_rank(x):
            return suggested.index(kind_of(x[0])) if kind_of(x[0]) in suggested else len(suggested)

        def line_post(x):
            return model.post.get(_first_changed_line(src0, x[1]) + 1, 0.0)
        if arm in PROBE_T:                                  # SR-2c: candidate transformations of other families only
            if arm == 'probe_t2' and tl is not None:
                tl.add(AN.derive([t for t in tl.admitted() if t.get('generation') == 1]))
            if arm == 'probe_t3' and tl is not None:
                tl.add(AN.derive([t for t in tl.admitted() if t.get('generation') in (1, 2)], generation=3))
            first, later = [], []
            for t in (dv.order(tl.candidates(family), src0, set(focus)) if tl is not None else []):
                cs = sorted(AN.apply_transform(t, src0, set(focus)), key=lambda x: -line_post(x))
                first += cs[:PER_TRANSFORM]
                later += cs[PER_TRANSFORM:]
            repertoire, rest = first + later, []
        if arm in V3:                                       # v3: the posterior first, the vault's kinds second
            rest.sort(key=lambda x: (-round(line_post(x), 6), kind_rank(x)))
            repertoire += SY.inventions(src0, set(focus))
            if arm == 'loop' and lib is not None:           # v4: the rules Genesis invented, the trusted first
                for r in lib.admitted():
                    repertoire += IV.apply_rule(r, src0)
            if arm in ('dream', 'dream_online'):
                dream = IV.dream_edits(src0, set(focus))
                rest += inv.order_dream(dream) if (arm == 'dream' and inv is not None) else dream
            if arm == 'analogy' and tl is not None:         # SR-2c: Genesis's own transformations, after v3's
                mine = [x for t in tl.admitted() for x in AN.apply_transform(t, src0, set(focus))]
                rest += sorted(mine, key=lambda x: -line_post(x))
        elif suggested and arm not in PROBE_T:
            rest.sort(key=kind_rank)
        repertoire = (repertoire if arm in PROBE_T else retrieved + repertoire) + rest
        mut_funcs = set(focus) if arm not in PROBE_T else None
        generations = 8 if arm not in PROBE_T else 0
        if arm in V2PLUS:                                   # widen: the rest of the file, most suspected lines first
            have = {x[1] for x in repertoire}
            wide = [x for x in SY.local_edits(src0) + SY.transplants(src0, sorted(set(method_of.values())))
                    + (SY.inventions(src0) if arm in V3 else [])
                    + (IV.dream_edits(src0) if arm in ('dream', 'dream_online') else [])
                    + ([y for t in tl.admitted() for y in AN.apply_transform(t, src0)]
                       if arm == 'analogy' and tl is not None else []) if x[1] not in have]
            wide.sort(key=lambda x: -line_post(x))
            repertoire += wide
            generations = 60
    elif arm == 'nolocal':
        repertoire = SY.local_edits(src0) + SY.transplants(src0, list(method_of.values()))
        rng.shuffle(repertoire)
        mut_funcs = None
        generations = 8
    elif arm == 'random':
        singles = SY.local_edits(src0) + SY.transplants(src0, sorted(set(method_of.values())))
        rng.shuffle(singles)
        repertoire = []
        for name, s in singles:
            repertoire.append((name, s))
            if rng.random() < 0.5:                                  # and a random second edit on top
                more = SY.local_edits(s)
                if more:
                    n2, s2 = rng.choice(more)
                    repertoire.append((f'{name} + {n2}', s2))
        mut_funcs = None
        generations = 0
    elif arm == 'enum':
        repertoire = SY.local_edits(src0) + SY.transplants(src0, sorted(set(method_of.values())))
        repertoire.sort(key=lambda x: _first_changed_line(src0, x[1]))
        mut_funcs = None
        generations = 0
    elif arm == 'probe':                                            # candidate rules of other families only
        repertoire = []
        for r in (inv.order(lib.candidates(family), src0) if lib is not None else []):
            repertoire += IV.apply_rule(r, src0)
        mut_funcs = None
        generations = 0
    else:                                                           # 'retrieval'
        all_edits = SY.local_edits(src0) + SY.transplants(src0, sorted(set(method_of.values())))
        repertoire = retrieved + [x for x in all_edits if kind_of(x[0]) in suggested]
        mut_funcs = None
        generations = 0

    def mutate(src, r):
        funcs = mut_funcs
        if arm in V2PLUS and len(search.history) >= 8:      # after 8 generations, mutate anywhere
            funcs = None
        pool = SY.local_edits(src, focus_funcs=funcs)
        if funcs:
            pool += SY.transplants(src, sorted(funcs))
        elif arm in V2PLUS:
            pool += SY.transplants(src, sorted(set(method_of.values())))
        return r.choice(pool) if pool else None

    metabolic = {}
    search = SY.Search(src0, evaluate, budget=budget, seed=seed, generations=generations)
    solutions, srec = search.run(repertoire, mutate)
    # among patches that pass everything visible, the cheapest to run, then the smallest (Occam)
    # (version 3 first prefers a patch that destroys no accumulated state (one that empties an attribute outside
    # __init__ makes the defect vanish by forgetting, the classic degenerate repair: conservation of information), then
    # one that holds no more than the original on the passing trials (a deleted bound: conservation of resources),
    # then one that keeps the mined laws on the whole workload (a tie-break: a law mined from the defective component
    # may encode the defect, so it never vetoes a patch, B20_R178))
    breaks = {}
    if arm in V3 and laws and len(solutions) > 1:       # mined laws as a tie-break among solutions, never a veto
        for p in solutions:
            breaks[p[2]] = PR.first_break(PR.Observation(target_run(p[2], observe='full')), laws) is not None
    solutions.sort(key=lambda p: ((arm in V3 and SY.annihilates(src0, p[2]) > 0), grows.get(p[2], False),
                                  breaks.get(p[2], False),
                                  round(metabolic.get(p[2], 0.0), 2) > 0.05, SY.changed_lines(src0, p[2]),
                                  metabolic.get(p[2], 0.0)))
    rec['steps']['synthesise'] = dict(srec, repertoire=len(repertoire), suggested=suggested, retrieved=len(retrieved))
    if not solutions:
        rec['outcome'] = 'not-repaired'
        rec['cpu_s'] = round(time.process_time() - t0, 2)
        model.record['intervention'] = None
        rec['obstacle'] = model.record
        return rec
    energy, name, patch, _ = solutions[0]
    confirm = []
    for cs in CONFIRM_SEEDS:
        run = handle.trial(seed=f'{cs}|{repair_id}', n=300)
        confirm.append(run(patch)['status'])
    rec['steps']['isolated_test'] = {'fresh_trials': confirm, 'ok': all(c == 'pass' for c in confirm)}
    rec['patch'] = {'name': name, 'changed_lines': SY.changed_lines(src0, patch), 'diff': _diff(src0, patch),
                    'extra_work': round(metabolic.get(patch, 0.0), 3), 'alternatives': len(solutions)}
    model.record['intervention'] = name
    model.record['predicted_effect'] = 'the failing segment and the failing trials pass; trials that passed still do'
    model.record['missing_capability'] = _capability(name, brk)
    rec['obstacle'] = model.record
    if not rec['steps']['isolated_test']['ok']:
        rec['outcome'] = 'rejected-in-isolation'
        rec['cpu_s'] = round(time.process_time() - t0, 2)
        return rec
    answer = handle.propose(patch)
    tid = name.split()[1] if name.startswith('transform ') else None
    if tid and tl is not None:
        before = (tl.get(tid) or {}).get('status')
        accepted = bool(answer.get('accepted')) and bool(answer.get('promoted'))
        tl.record(tid, accepted, family, false_repair=not answer.get('accepted') and bool(answer.get('failed_checks')))
        after = (tl.get(tid) or {}).get('status')
        if arm in PROBE_T and dv is not None:
            dv.learn(tl.get(tid), admitted=after == 'admitted' and before != 'admitted')
        rec['transform'] = {'id': tid, 'before': before, 'after': after}
    rid = name.split()[1] if name.startswith('rule ') else None
    if rid and lib is not None:
        before = (lib.get(rid) or {}).get('status')
        accepted = bool(answer.get('accepted')) and bool(answer.get('promoted'))
        lib.record(rid, accepted, family, false_repair=not answer.get('accepted') and bool(answer.get('failed_checks')))
        after = (lib.get(rid) or {}).get('status')
        if arm == 'probe' and inv is not None:
            inv.learn(lib.get(rid)['level'], admitted=after == 'admitted' and before != 'admitted')
        rec['rule'] = {'id': rid, 'before': before, 'after': after}
    rec['steps']['verify'] = {'accepted': answer.get('accepted'), 'failed_checks': answer.get('failed_checks')}
    if not answer.get('accepted'):
        rec['outcome'] = 'false-repair' if answer.get('failed_checks') else 'verifier-error'
        rec['why'] = answer.get('why')
        rec['cpu_s'] = round(time.process_time() - t0, 2)
        return rec
    rec['steps']['promote'] = {'promoted': answer.get('promoted'), 'why': answer.get('why')}
    if not answer.get('promoted'):
        rec['outcome'] = 'verified-pending'
        rec['cpu_s'] = round(time.process_time() - t0, 2)
        return rec
    resumed = handle.run(resume=True)
    rec['steps']['resume'] = {'status': resumed['status'], 'from_op': resumed.get('started'), 'to_op': resumed['op']}
    rec['outcome'] = 'repaired' if resumed['status'] == 'done' else 'repaired-but-failed-again'
    if vault is not None and rec['outcome'] == 'repaired':
        vault.retain({'id': repair_id, 'operator': kind_of(name), 'edit': name, 'evidence': evidence,
                      'hunk': hunk(src0, patch),
                      'signature': rec['failure']['signature'], 'law': brk[1] if brk else None,
                      'missing_capability': model.record['missing_capability'],
                      'regression_test': rec['steps']['regression_test'], 'verified': True})
        rec['retained'] = True
        if arm == 'dream' and lib is not None and not name.startswith('rule '):
            # Genesis meets an obstacle its rules did not solve, the dream found a verified repair: lift it into rules
            new = lib.add(IV.abstract(src0, patch, {'episode': repair_id, 'family': family, 'edit': name,
                                                    'missing_capability': model.record['missing_capability']}))
            rec['invented'] = [r['id'] for r in new]
            if inv is not None and name.startswith('dream '):
                inv.learn_production(IV.production(name), True)
        if arm in LEARN_T and tl is not None and not name.startswith(('transform ', 'rule ')):
            new = tl.add(AN.lift(src0, patch, {'episode': repair_id, 'family': family, 'edit': name,
                                               'generation': LEARN_T[arm]}))
            rec['lifted'] = [t['id'] for t in new]
    rec['cpu_s'] = round(time.process_time() - t0, 2)
    return rec


def _first_changed_line(a, b):
    for i, (x, y) in enumerate(zip(a.split('\n'), b.split('\n'))):
        if x != y:
            return i
    return 10 ** 6


def _capability(name, brk):
    k = kind_of(name)
    if k == 'restore':
        return 'invalidation of a cache when what it caches changes' if brk and ' is None or ' in brk[1] else \
            'a paired update keeping two containers consistent'
    return {'transplant': 'an operation a sibling method performs and this one lacks',
            'move': 'the order of two state changes', 'delete': 'a statement that should not be there',
            'compare': 'the right comparison (a bound or a membership test)', 'copy': 'a copy instead of an alias',
            'uncopy': 'an alias instead of a copy', 'pop': 'the right end of a container',
            'bool': 'the right flag', 'int': 'the right constant', 'name': 'the right function',
            'arith': 'the right arithmetic'}.get(k, k)


def _diff(a, b):
    import difflib
    return '\n'.join(x for x in difflib.unified_diff(a.split('\n'), b.split('\n'), 'before', 'after', lineterm='',
                                                     n=1))
