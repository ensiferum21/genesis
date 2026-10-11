"""World-step research loop (spec §26.3) over a public DEV panel.

    for epoch in campaign:
        gaps      = diagnose_failures(active_worlds, evidence)
        proposals = propose_world_actions(gaps)
        selected  = research_market.allocate(proposals, budget)
        receipts  = execute_bounded(selected)          # macros, under leased grants
        checked   = checker_service.verify(receipts)   # witnesses, SAT/DRAT bounds
        update_causal_models(checked)                  # market calibration
        update_pareto_ecology(checked)
        retire_and_compress_low_value_worlds()
        if meta_gap_detected(): record_meta_gap_hypothesis()

Every macro run is stored as a replayable IR program; every checked result is
an evidence node; per-task claims are promoted only as far as the kernel
allows (WITNESS_VALID, OPTIMALITY_CHECKED). Everything here is public DEV
work: no utility, improver or novelty level can be reached by this loop.
"""
from pathlib import Path
import resource
import time

from pydantic import Field

from .common import atomic_write, canonical, code_identity, digest, utcnow
from .dsl import baseline_programs
from .graphs import universal_upper, components
from .kernel.authority import GrantLedger
from .kernel.evidence import EvidenceKernel, PromotionRejected
from .kernel.wording import require_clean
from .macros import barrier_escape, gap_engine, local_to_global
from .ir import Interpreter, Value
from .market import Calibration, MarketPolicy, Proposal, allocate, should_stop
from .models import StrictModel, SolverProgram, Limits
from .panels import make_hard_panel
from .research import Ecology, propose
from .store import Store


class LoopConfig(StrictModel):
    schema_version: str = 'genesis-world-loop-v1'
    seed: int = 20261013
    domain: str = 'c4_host_v2'
    tasks: int = Field(default=6, ge=1, le=64)
    epochs: int = Field(default=3, ge=1, le=16)
    cpu_budget_per_epoch: float = Field(default=60.0, gt=0)
    verify_seconds: int = Field(default=30, ge=1, le=600)
    limits: Limits = Field(default_factory=lambda: Limits(cpu_seconds=10))
    market: MarketPolicy = Field(default_factory=MarketPolicy)


class _BestView:
    """Read-through view of per-task bounds; the store is the only source of truth."""

    def __init__(self, store):
        self.s = store

    def __getitem__(self, task_id):
        return self.s.state(f'best:{task_id}')


def _cpu():
    me = resource.getrusage(resource.RUSAGE_SELF); ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return me.ru_utime + me.ru_stime + ch.ru_utime + ch.ru_stime


class ResearchLoop:
    def __init__(self, root, config=None):
        root = Path(root)
        fresh = not (root / 'campaign.sqlite3').exists()
        self.s = Store(root)
        if fresh:
            self.config = config or LoopConfig()
            self.s.save('loop_config', 'resolved', self.config.model_dump(mode='json'))
            self.s.set_state('source_hash', code_identity(Path(__file__).resolve().parents[2])['sha256'])
        else:
            row = self.s.db.execute("SELECT object_hash FROM entities WHERE kind='loop_config'").fetchone()
            self.config = LoopConfig.model_validate_json(canonical(self.s.get(row[0])))
        from .verification.tools import tool, ToolUnavailable
        anchors = {}
        try:
            anchors[tool('drat-trim')['sha256']] = 'pinned drat-trim'
        except ToolUnavailable:
            pass
        self.k = EvidenceKernel(self.s, anchors=anchors)
        self.g = GrantLedger(self.s)
        self.source = self.s.state('source_hash')

    def close(self):
        self.s.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # ---------- helpers ----------
    def _verifiers(self):
        from .verification.tools import tool
        graphs = Path(__file__).with_name('graphs.py').read_bytes()
        self.k.register_verifier('dual-predicates', digest(graphs.decode()))
        try:
            t = tool('drat-trim')
            self.k.register_verifier('drat-trim', t['sha256'])
        except Exception:
            pass

    def _record_macro(self, name, result):
        pid = digest(result['program'])
        self.s.save('ir_program', pid, result['program'])
        return pid

    # ---------- the loop ----------
    def run(self):
        cfg = self.config
        if self.s.state('loop_phase') == 'COMPLETE':
            return self.refreshed_summary()
        self._verifiers()
        root_grant = self.g.root_grant({'cpu_seconds': cfg.cpu_budget_per_epoch * cfg.epochs * 1.5,
                                        'wall_seconds': cfg.cpu_budget_per_epoch * cfg.epochs * 6,
                                        'attempts': 100000, 'output_bytes': 1 << 30, 'paid_api_usd': 0},
                                       {'execute_fixed_dsl'}, issuer='loop-config')
        tasks, panel_stats = make_hard_panel(cfg.seed, cfg.tasks, cfg.domain, 'DEV',
                                             certify=False)
        for t in tasks:
            self.s.save('task', t.task_id, t.model_dump(mode='json'))
        self.s.save('panel', 'dev', {'tasks': [t.task_id for t in tasks], **panel_stats})
        eco = Ecology(cap=8, scope=f'loop-{cfg.seed}')
        worlds = {}
        for name, prog in baseline_programs().items():
            wid = eco.birth(prog); worlds[wid] = {'name': name, 'program': prog}
        for t in tasks:
            if self.s.state(f'best:{t.task_id}') is None:
                self.s.set_state(f'best:{t.task_id}', {'lower': 0, 'upper': universal_upper(t)['value'],
                                                       'status': 'BOUNDS_ONLY', 'witness_node': None})
        best = _BestView(self.s)
        calibration = Calibration()
        recent_classes, history, open_streak = [], [], {t.task_id: 0 for t in tasks}
        self.s.set_state('loop_phase', 'RUNNING')
        for epoch in range(cfg.epochs):
            eco.next_epoch()
            epoch_grant = self.g.child(root_grant, {'cpu_seconds': cfg.cpu_budget_per_epoch * 1.5,
                                                    'attempts': 10000}, {'execute_fixed_dsl'},
                                       purpose=f'epoch-{epoch}')
            open_tasks = [t for t in tasks if best[t.task_id]['status'] != 'OPTIMALITY_CHECKED']
            # 1. diagnose
            diagnoses = {}
            for wid, w in list(worlds.items()):
                if eco.worlds[wid].state == 'RETIRED' or not open_tasks:
                    continue
                t = open_tasks[0]
                rows = [{'optimum': best[x.task_id]['upper'], 'value': best[x.task_id]['lower'],
                         'family': x.family, 'status': 'SUCCESS'} for x in open_tasks]
                g = gap_engine(t, w['program'], rows, limits=cfg.limits)
                self._record_macro('gap_engine', g)
                diagnoses[wid] = g
            # 2. propose
            proposals = []
            for t in open_tasks:
                b = best[t.task_id]; gap = max(0, b['upper'] - b['lower'])
                for wid, w in worlds.items():
                    if eco.worlds[wid].state == 'RETIRED':
                        continue
                    rep = diagnoses.get(wid, {}).get('representation_sensitive', False)
                    proposals.append(Proposal(proposal_id=f'e{epoch}-{wid[:8]}-{t.task_id}-escape', kind='barrier_escape',
                                              structural_class='exact_representation', world=wid,
                                              expected_progress=gap * 0.8, info_gain=1.0 if rep else 0.5,
                                              future_capability=0.2, option_value=0.1,
                                              expected_cost=float(cfg.verify_seconds) / 3))
                    if len(components(t)) > 1:
                        proposals.append(Proposal(proposal_id=f'e{epoch}-{wid[:8]}-{t.task_id}-l2g',
                                                  kind='local_to_global', structural_class='decomposition',
                                                  world=wid, expected_progress=gap * 0.3, info_gain=0.3,
                                                  future_capability=0.2, option_value=0.2, expected_cost=2.0))
                    proposals.append(Proposal(proposal_id=f'e{epoch}-{wid[:8]}-{t.task_id}-search', kind='search',
                                              structural_class='greedy_search', world=wid,
                                              expected_progress=gap * 0.2, info_gain=0.1, future_capability=0.1,
                                              option_value=0.0, expected_cost=1.0))
            stop, why = should_stop(proposals, cfg.market, calibration=calibration)
            if stop or not proposals:
                history.append({'epoch': epoch, 'stopped': True, 'reason': why if proposals else 'no open tasks'})
                break
            # 3. allocate
            selected, decision = allocate(proposals, cfg.cpu_budget_per_epoch, cfg.market, calibration=calibration,
                                          recent_classes=recent_classes)
            self.s.save('market_decision', decision['decision_id'], decision)
            # 4-5. execute + verify
            by_id = {t.task_id: t for t in tasks}
            realized = []
            for p in selected:
                task = by_id[p.proposal_id.rsplit('-', 1)[0].split('-', 2)[2]]
                w = worlds[p.world]
                self.g.require(epoch_grant, 'execute_fixed_dsl', attempts=1)
                c0 = _cpu()
                before = best[task.task_id]['lower'], best[task.task_id]['upper']
                if p.kind == 'barrier_escape':
                    res = barrier_escape(task, w['program'], seeds=(epoch, epoch + 1),
                                         verify_seconds=cfg.verify_seconds, limits=cfg.limits, custody=self.s)
                    lower, upper = res['escape_value'], res['upper']
                    certified = res['certified']
                elif p.kind == 'local_to_global':
                    res = local_to_global(task, w['program'], limits=cfg.limits)
                    lower, upper, certified = res.get('value', 0), best[task.task_id]['upper'], False
                else:
                    ir = Interpreter(cfg.limits, max_actions=4, seed=epoch)
                    goal = ir.invoke('FORMALIZE', [Value('RawTask', task.model_dump(mode='json'))])
                    receipt = ir.invoke('EXECUTE', [goal, Value('Program', w['program'])])
                    value = receipt.data.get('result', {}).get('value', 0)
                    res = {'status': receipt.data['status'], 'program': {'nodes': ir.trace},
                           'witness': [list(e) for e in receipt.data.get('result', {}).get('selected', ())]}
                    lower, upper, certified = value, best[task.task_id]['upper'], False
                used = max(0.0, _cpu() - c0)
                self.g.charge(epoch_grant, digest(res.get('program', {})), cpu_seconds=round(used, 6), attempts=1)
                pid = self._record_macro(p.kind, res) if 'schema' in res.get('program', {}) else None
                self._update_evidence(task, lower, upper, certified, pid, p.kind,
                                      certificate=res.get('certificate'), witness=res.get('witness'))
                after = best[task.task_id]['lower'], best[task.task_id]['upper']
                progress = (after[0] - before[0]) + (before[1] - after[1])
                calibration.observe(p, max(0, progress), used)
                realized.append({'proposal': p.proposal_id, 'kind': p.kind, 'progress': progress, 'cpu': round(used, 3),
                                 'ir_program': pid})
                recent_classes.append(p.structural_class)
            # 6. ecology update and retirement
            for wid in worlds:
                if eco.worlds[wid].state != 'ACTIVE':
                    continue
                mine = [r for r in realized if r['proposal'].split('-')[1] == wid[:8]]
                eco.observe(wid, (sum(r['progress'] for r in mine), -sum(r['cpu'] for r in mine)),
                            {'actions': len(mine)})
            frontier = eco.frontier()
            for wid in worlds:
                if eco.worlds[wid].state == 'DORMANT' and wid not in frontier:
                    eco.retire(wid, 'dominated on the epoch Pareto frontier; lessons kept in ledger')
            # 7. meta-gap detection (hypothesis only)
            meta = []
            for t in tasks:
                if best[t.task_id]['status'] != 'OPTIMALITY_CHECKED':
                    open_streak[t.task_id] += 1
                    if open_streak[t.task_id] >= 2:
                        meta.append(t.task_id)
            history.append({'epoch': epoch, 'selected': len(selected), 'realized': realized,
                            'frontier': frontier, 'calibration_error': calibration.error(),
                            'meta_gap_candidates': meta, 'decision': decision['decision_id']})
            self.s.save('loop_epoch', str(epoch), history[-1])
        summary = self._summary(tasks, best, history, eco, calibration)
        self.s.set_state('loop_summary', summary)
        self.s.set_state('loop_phase', 'COMPLETE')
        atomic_write(self.s.root / 'reports' / 'world_loop.md', self._report(summary).encode(), overwrite=True)
        atomic_write(self.s.root / 'reports' / 'world_loop.json', canonical(summary), overwrite=True)
        return summary

    def _update_evidence(self, task, lower, upper, certified, program_id, kind, *, certificate=None, witness=None):
        state = dict(self.s.state(f'best:{task.task_id}'))
        task_sha = self.s.put(task.model_dump(mode='json'))  # the problem itself, content-addressed
        improved = False
        if lower > state['lower'] and not (witness and len(witness) == lower):
            state['custody_gap'] = f'lower bound {lower} reported without its witness; not recorded'
            lower = state['lower']
        if lower > state['lower']:
            run = self.k.record('execution_receipt', {'task': task.task_id, 'macro': kind, 'ir_program': program_id},
                                route='genesis.campaign', source_hash=self.source, verdict='VALID',
                                effects=['UNCHECKED_PROPOSAL', 'USES_DEV_DATA'])
            payload = {'schema': 'genesis-witness-check-v2', 'task': task.task_id, 'task_sha256': task_sha,
                       'witness': witness, 'value': lower}
            check = self.k.record('witness_check', payload, parents=[run],
                                  route='genesis.campaign', source_hash=self.source, verdict='VALID',
                                  verifier='dual-predicates')
            claim = f'lower:{task.task_id}:{lower}'
            problem = {'task_sha256': task_sha, 'value': lower, 'claim': 'lower_bound'}
            self.k.create_claim(claim, self.k.math_statement(problem), 'this finite host only', [check],
                                problem=problem)
            self.k.promote(claim, 'math', 'WITNESS_VALID')
            state.update(lower=lower, witness_node=check); improved = True
        if certified and (upper < state['upper'] or (upper == lower and state['status'] != 'OPTIMALITY_CHECKED')):
            parent = state.get('witness_node')
            if certificate is None or parent is None or state['lower'] != lower:
                # No certificate in custody: the bound is not recorded as evidence (R-03).
                state['custody_gap'] = 'certified bound without a custody-held certificate; not recorded'
            else:
                method = self.s.get(certificate)['upper']['method']
                bound = self.k.record('bound_state', {'schema': 'genesis-bound-state-v2', 'task': task.task_id,
                                                      'task_sha256': task_sha, 'lower': lower, 'upper': upper,
                                                      'gap': upper - lower, 'lower_evidence': parent,
                                                      'certificate_bundle': certificate},
                                      parents=[parent], route='genesis.verification.sat',
                                      source_hash=self.source, verdict='VALID',
                                      verifier='drat-trim' if method == 'SAT_DRAT' else 'host-edge-count')
                state['upper'] = upper
                state['certificate'] = certificate
                if upper == state['lower']:
                    claim = f'optimum:{task.task_id}:{upper}'
                    problem = {'task_sha256': task_sha, 'value': upper, 'claim': 'optimum'}
                    self.k.create_claim(claim, self.k.math_statement(problem), 'this finite host only', [bound],
                                        problem=problem)
                    try:
                        self.k.promote(claim, 'math', 'OPTIMALITY_CHECKED')
                        state['status'] = 'OPTIMALITY_CHECKED'
                    except PromotionRejected as exc:
                        state['promotion_rejected'] = exc.args[0]
        self.s.set_state(f'best:{task.task_id}', state)
        return improved

    def refreshed_summary(self):
        """The stored summary with every task status re-derived from the evidence kernel now,
        so a revocation after the run is visible (B14 round 3, F9)."""
        summary = dict(self.s.state('loop_summary'))
        tasks = {}
        for tid, v in summary['tasks'].items():
            claim = f"optimum:{tid}:{v.get('upper')}"
            try:
                level = self.k.levels(claim)['math']
            except KeyError:
                level = None
            status = v.get('status')
            if status == 'OPTIMALITY_CHECKED' and level != 'OPTIMALITY_CHECKED':
                status = 'OPTIMALITY_REVOKED_OR_UNVERIFIABLE'
            tasks[tid] = dict(v, status=status)
        summary.update(tasks=tasks, optimality_checked=sum(v['status'] == 'OPTIMALITY_CHECKED' for v in tasks.values()),
                       invalidated_claims=self.k.invalidated_claims(), refreshed_utc=utcnow())
        return summary

    def _summary(self, tasks, best, history, eco, calibration):
        final = {t.task_id: self.s.state(f'best:{t.task_id}') for t in tasks}
        return {'schema': 'genesis-world-loop-summary-v1', 'config': self.config.model_dump(mode='json'),
                'tasks': {k: {kk: v.get(kk) for kk in ('lower', 'upper', 'status')} for k, v in final.items()},
                'optimality_checked': sum(v.get('status') == 'OPTIMALITY_CHECKED' for v in final.values()),
                'epochs': history, 'calibration': calibration.snapshot(), 'calibration_error': calibration.error(),
                'worlds': {wid: {'state': w.state, 'metrics': list(w.metrics)} for wid, w in eco.worlds.items()},
                'invalidated_claims': self.k.invalidated_claims(),
                'evidence_ceiling': 'math up to OPTIMALITY_CHECKED per finite host; utility DEV_ONLY at most',
                'promotion_allowed': False, 'completed_utc': utcnow()}

    def _report(self, summary):
        lines = ['# World-step research loop (public DEV)', '',
                 f"Hosts with a certified optimum: {summary['optimality_checked']} of {len(summary['tasks'])}.", '',
                 '| Task | Lower | Upper | Status |', '|---|---:|---:|---|']
        for tid, v in summary['tasks'].items():
            lines.append(f"| {tid} | {v['lower']} | {v['upper']} | {v['status']} |")
        lines += ['', '## Epochs', '']
        for e in summary['epochs']:
            if e.get('stopped'):
                lines.append(f"- epoch {e['epoch']}: stopped ({e['reason']})")
            else:
                lines.append(f"- epoch {e['epoch']}: {e['selected']} actions funded, calibration error "
                             f"{e['calibration_error']}, open-task streaks {len(e['meta_gap_candidates'])}")
        lines += ['', 'Bounds are per finite host. Utility measurements are development-only; '
                  'no improver, transfer or novelty claim is made.', '']
        return require_clean('\n'.join(lines), {'math': 'OPTIMALITY_CHECKED', 'utility': 'DEV_ONLY',
                                                 'causality': 'NOT_TESTED', 'improver': 'NOT_TESTED',
                                                 'novelty': 'UNKNOWN', 'replication': 'NONE'})
