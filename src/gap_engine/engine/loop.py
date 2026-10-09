"""The Gap Engine v2 campaign on a reality adapter: U1-U5 wired together under the kernel.

Each step the U5 scheduler picks one intervention:
  admit     U1 fingerprints + U2 dropout on DEV, then Gate J on the strongest bundles
  harvest   U3 hindsight harvesting of verified byproducts into the candidate pool
  procedure U4 discovery procedure (with certified precondition) on failed DEV tasks
  explore   theory exploration (conjecture generation) on the cluster with most progress
  dream     U3 dream cycle; the new ranker generation is promoted only through G1
Reward = change in DEV tasks solved by the accepted library, plus half the change in
"potential" (DEV solved by the library plus the ranker's top-k pool lemmas), per unit cost.
All spend goes through one BudgetBroker; every admission cites a ledgered gate decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..adapters.induction.adapter import InductionWorld
from ..adapters.induction.terms import symbols
from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.gates import GateJ, Library
from ..kernel.ledger import Ledger
from ..u1.fingerprint import measure_fingerprints
from ..u2.design import DropoutConfig, run_dropout
from ..u3.dream import default_ranker, dream_cycle, select_top
from ..u3.harvest import harvest
from ..u4 import dsl
from ..u4.features import goal_features
from ..u4.procedures import BUILTIN, run
from ..u5.scheduler import Scheduler, StopAuditor, clusters_of
from .readiness import AdmissionReadinessBuffer

ARMS = ["admit", "harvest", "procedure", "explore", "dream"]

THEME_ORDER = ["rot", "qrev", "rev", "mult", "sum", "take", "drop", "len", "replicate", "incall",
               "double", "half", "minus", "max", "min", "app", "plus"]


def theme_of(eq) -> str:
    syms = set(symbols(eq.lhs)) | set(symbols(eq.rhs))
    for t in THEME_ORDER:
        if t in syms:
            return t
    return "other"


@dataclass
class CampaignResult:
    accepted: list[str]
    history: list[float]
    potential: list[float]
    steps: list[dict]
    spent: float
    stops: int
    dr_values: dict
    budget_report: dict
    generations: list[dict] = field(default_factory=list)


class Campaign:
    def __init__(self, world: InductionWorld, budget: float, seed: int, policy: str = "u5",
                 ledger: Ledger | None = None, dropout_cfg: DropoutConfig | None = None,
                 procedure_contracts: dict | None = None, k_potential: int = 10, enable: tuple = tuple(ARMS),
                 round_policy: str = "fixed", focus_size: int | None = None, prior_ranker=None,
                 focus_rotation: str = "none", rotate_after: int = 2, explore_share: float = 0.25,
                 admission_strategy: str = "select_split"):
        """round_policy: "fixed" (run-1/2 behaviour: rounds capped at 60 runs) or "power" (U5
        sizes each round from the co-inclusions the design needs). focus_size: dropout over
        the ranker's top-M candidates only. prior_ranker: a proposer generation carried over
        from earlier campaigns (U3); G1 still decides every later promotion.
        focus_rotation: "none" (round-2 behaviour, a fixed top-M) or "rotate" (post-round-2:
        candidates tested in `rotate_after` focused rounds without FDR-surviving evidence are
        retired from the focus, and `explore_share` of the focus is drawn at random from the
        rest of the pool)."""
        if focus_rotation not in ("none", "rotate"):
            raise ValueError(f"unknown focus_rotation {focus_rotation!r}")
        if admission_strategy not in ("select_split", "dev_build_full_select", "power_aware_devbuffer"):
            raise ValueError(f"unknown admission_strategy {admission_strategy!r}")
        self.admission_strategy = admission_strategy
        self.focus_rotation = focus_rotation
        self.rotate_after = int(rotate_after)
        self.explore_share = float(explore_share)
        self._null_rounds: dict[str, int] = {}
        self._retired: set[str] = set()
        # exploration draws come from their own stream, so "rotate" and "none" share every
        # other random draw (dropout designs, gate seeds) for the same campaign seed
        self.focus_rng = np.random.default_rng([seed, 7177])
        self.w = world
        self.ledger = ledger if ledger is not None else Ledger()
        self.broker = BudgetBroker.from_policy(budget, self.ledger, name=f"v2-{policy}")
        self.library = Library(self.ledger)
        self.library.admit_base(world.base_ids, {}, "lesion starting library")
        self.gate = GateJ(world, self.broker, self.ledger, alpha=0.05, reps=1)
        self.readiness_buffer = AdmissionReadinessBuffer(world, self.library, self.gate, self.ledger) if admission_strategy == "power_aware_devbuffer" else None
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.policy = policy
        self.cfg = dropout_cfg or DropoutConfig(tau=10, delta=2, min_tasks=2, fdr_q=0.10, mode="auto")
        self.ranker = prior_ranker if prior_ranker is not None else default_ranker(world)
        self.round_policy = round_policy
        self.focus_size = focus_size
        self.contracts = procedure_contracts or {}
        self.k_pot = k_potential
        self.enable = [a for a in ARMS if a in enable]
        self.sched = Scheduler(self.enable, self.ledger, np.random.default_rng(seed + 1))
        self.auditor = StopAuditor(self.ledger, np.random.default_rng(seed + 2))
        self.clusters = clusters_of(world.tasks["DEV"], theme_of)
        self.history: list[float] = []
        self.potential: list[float] = []
        self.steps: list[dict] = []
        self.generations: list[dict] = []
        self._rr = 0

    # ------------------------------------------------------------------ measurement
    def measure(self) -> tuple[float, float]:
        try:
            self.broker.charge("measure", 2.0, purpose="progress measurement")
        except BudgetExceeded:
            return (self.history[-1] if self.history else 0.0, self.potential[-1] if self.potential else 0.0)
        a = float(self.w.run_library([], "DEV", 1).sum())
        top = select_top(self.w, self.ranker, self.k_pot)
        p = float(self.w.run_library(top, "DEV", 1).sum())
        return a, p

    def failed_dev(self, cluster: str | None = None) -> list[int]:
        if getattr(self, "_fail_cache", None) is None:
            y = self.w.run_library([], "DEV", 2)
            self._fail_cache = [i for i in range(len(y)) if not y[i]]
        idx = self._fail_cache
        if cluster and cluster in self.clusters:
            members = set(self.clusters[cluster])
            idx = [i for i in idx if i in members]
        return list(idx)

    def pick_cluster(self) -> str:
        """Learning-progress choice: clusters whose failed count fell recently score highest;
        ties and flat clusters are broken toward clusters with more failures left."""
        self._fail_cache = None
        best, best_v = None, -1.0
        prev = getattr(self, "_prev_fail", {})
        cur = {}
        for c in self.clusters:
            f = len(self.failed_dev(c))
            cur[c] = f
            lp = abs(prev.get(c, f) - f)
            v = (2.0 * lp + 0.1 * f) * (1.0 + 0.3 * self.rng.random()) if f else -1.0
            if v > best_v:
                best, best_v = c, v
        self._prev_fail = cur
        return best or "other"

    # ------------------------------------------------------------------ interventions
    def do_admit(self) -> None:
        if self.round_policy == "power":
            return self._admit_power()
        n = len(self.w.pool)
        p_plain = min(0.5, self.cfg.target_size / max(1, n))
        proposals = None
        R_cap = int(min(60, self.broker.remaining * 0.35))
        if R_cap < 12:
            raise BudgetExceeded("no budget for a dropout round")
        if p_plain ** 2 * R_cap < self.cfg.min_joint:
            fps = measure_fingerprints(self.w, self.broker, self.seed)
            proposals = fps.pair_proposals(cap=80)
        rd = run_dropout(self.w, self.broker, int(self.rng.integers(1 << 30)), self.cfg, proposals=proposals,
                         max_runs=R_cap)
        if rd is None:
            return
        cands = sorted([b for b in rd.bundles if b.evidence.fdr_rejected], key=lambda b: b.evidence.pvalue)
        from .admission import admit_proposals
        props = [(b.members, b.evidence.pvalue, b.kind) for b in cands]
        gate_seed = int(self.rng.integers(1 << 20))
        if self.readiness_buffer is not None:
            if self.readiness_buffer.offer(props):
                self.readiness_buffer.try_admit(gate_seed)
        else:
            admit_proposals(self.w, self.library, self.gate, props, gate_seed,
                            strategy=self.admission_strategy)

    def _focus_set(self, pool: list[str]) -> list[str]:
        """The candidates a focused round may include."""
        M = int(self.focus_size)
        if self.focus_rotation == "none":
            return select_top(self.w, self.ranker, M)
        ranked = select_top(self.w, self.ranker, len(pool))
        fresh = [c for c in ranked if c not in self._retired]
        if len(fresh) < M:                      # everything has been tried: start a new pass
            self.ledger.append("u5.focus_reset", {"retired": len(self._retired), "pool": len(pool)})
            self._retired.clear()
            self._null_rounds.clear()
            fresh = ranked
        n_explore = int(round(self.explore_share * M))
        head = fresh[:M - n_explore]
        rest = fresh[M - n_explore:]
        if n_explore and rest:
            pick = self.focus_rng.choice(len(rest), size=min(n_explore, len(rest)), replace=False)
            head = head + [rest[i] for i in sorted(pick)]
        return head

    def _admit_power(self) -> None:
        """Power-sized round: choose plain or blocked design and the number of runs from the
        expected co-inclusions per candidate pair (>= cfg.min_joint) and a floor of 60 runs for
        single effects; never more than 60% of the remaining budget."""
        import math
        pool = list(self.w.pool)
        if not pool:
            return
        eligible = np.ones(len(pool), bool)
        focused = bool(self.focus_size and len(pool) > self.focus_size)
        if focused:
            top = set(self._focus_set(pool))
            eligible = np.array([c in top for c in pool])
        n_el = int(eligible.sum())
        unit = self.w.library_eval_cost(int(self.cfg.target_size))
        # Experimental readiness policy reserves enough for at least one complete
        # DEV-build/full-SELECT/CONFIRM gate instead of spending it all on dropout.
        gate_reserve = (self.readiness_buffer.minimum_gate_reserve()
                        if self.readiness_buffer is not None else 0.0)
        available = max(0.0, self.broker.remaining - gate_reserve)
        R_avail = int(0.6 * available / unit)
        if R_avail < 20:
            raise BudgetExceeded("no budget for a power-sized round")
        p_plain = min(0.5, self.cfg.target_size / max(1, n_el))
        proposals = None
        if p_plain ** 2 * R_avail >= self.cfg.min_joint:
            R_need = max(60, math.ceil(self.cfg.min_joint / p_plain ** 2))
        else:
            fps = measure_fingerprints(self.w, self.broker, self.seed,
                                       members=[i for i in range(len(pool)) if eligible[i]])
            proposals = [pr for pr in fps.pair_proposals(cap=80) if eligible[pr[0]] and eligible[pr[1]]]
            K = max(1, len(proposals))
            q = min(self.cfg.q_max, (self.cfg.block_target / 2.0) / K)
            R_need = max(60, math.ceil(self.cfg.min_joint / q))
        R = int(min(R_need, R_avail))
        if R < 20:
            raise BudgetExceeded("round too small after fingerprints")
        rd = run_dropout(self.w, self.broker, int(self.rng.integers(1 << 30)), self.cfg, proposals=proposals,
                         eligible=eligible, max_runs=R)
        self.ledger.append("u5.round", {"policy": "power", "eligible": n_el, "R_need": R_need, "R": R,
                                        "mode": None if rd is None else rd.design.mode,
                                        "rotation": self.focus_rotation,
                                        "retired": len(self._retired)})
        if rd is None:
            return
        cands = sorted([b for b in rd.bundles if b.evidence.fdr_rejected], key=lambda b: b.evidence.pvalue)
        if self.focus_rotation == "rotate" and focused:
            # Candidates that were in focus and appear in no FDR-surviving bundle accumulate a
            # "tested without evidence" count; after `rotate_after` such rounds they leave the
            # focus so the next-ranked candidates get tested (round-2 diagnosis: a frozen top-40).
            hit = {m for b in cands for m in b.members}
            for i, c in enumerate(pool):
                if eligible[i] and c not in hit:
                    self._null_rounds[c] = self._null_rounds.get(c, 0) + 1
                    if self._null_rounds[c] >= self.rotate_after:
                        self._retired.add(c)
        from .admission import admit_proposals
        props = [(b.members, b.evidence.pvalue, b.kind) for b in cands]
        gate_seed = int(self.rng.integers(1 << 20))
        if self.readiness_buffer is not None:
            if self.readiness_buffer.offer(props):
                self.readiness_buffer.try_admit(gate_seed)
        else:
            admit_proposals(self.w, self.library, self.gate, props, gate_seed,
                            strategy=self.admission_strategy)

    def do_harvest(self) -> None:
        harvest(self.w, self.broker, seed=int(self.rng.integers(1 << 20)))

    def _ctx(self):
        lib = self.w._library([])
        return dsl.ResearchContext(self.w.theory, self.w.store, lib, self.broker, fuel=self.w.solver.fuel,
                                   seed=int(self.rng.integers(1 << 20)))

    def do_procedure(self, cluster: str) -> None:
        fails = self.failed_dev(cluster)[:6]
        lib = self.w._library([])
        for t in fails:
            eq = self.w.tasks["DEV"][t]
            feats = goal_features(self.w.theory, eq, lib, fuel=self.w.solver.fuel)
            chosen = None
            for name, (prog, pre) in self.contracts.items():
                if pre is None or pre(feats):
                    chosen = prog
                    break
            prog = chosen or BUILTIN["lemma_calculation"]
            ctx = self._ctx()
            run(prog, ctx, eq, max_cost=1.5)
            for lid in ctx.new_lemmas:
                self._add_to_pool(lid, "procedure")

    def do_explore(self, cluster: str) -> None:
        idx = self.clusters.get(cluster) or [0]
        eq = self.w.tasks["DEV"][idx[0]]
        ctx = self._ctx()
        conjs = dsl.op_conjecture(ctx, eq, max_size=5)
        conjs = [c for c in conjs if self.w.screen_reason(c.text()) is None]
        dsl.op_prove(ctx, conjs, limit=10)
        for lid in ctx.new_lemmas:
            self._add_to_pool(lid, "explore")

    def _add_to_pool(self, lid: str, source: str) -> bool:
        """Every lemma a campaign creates enters the pool through the world's single screen
        (sealed near-duplicates and held-out gate tasks are refused). Round 2's
        `do_procedure` skipped this; the review found it admitted a sealed theorem."""
        if lid in self.w.pool or lid in self.w.accepted_extra or lid in self.w.base_ids:
            return False
        why = self.w.screen_reason(self.w.statement(lid))
        if why is not None:
            self.ledger.append("pool.refused", {"source": source, "reason": why})
            return False
        self.w.pool.append(lid)
        return True

    def do_dream(self) -> None:
        if len(self.w.pool) < 20 or self.broker.remaining < 100:
            return
        gen = f"gen{len(self.generations) + 1}"
        new, rec, _ = dream_cycle(self.w, self.ranker, self.broker, self.ledger, seed=int(self.rng.integers(1 << 20)),
                                  k=self.k_pot, label_runs=20, gen_id=gen)
        self.generations.append(rec.model_dump())
        self.ranker = new

    # ------------------------------------------------------------------ loop
    def eligible(self) -> list[str]:
        """Interventions whose preconditions hold now (cost and state), so the scheduler
        never spends measurement budget on an arm that cannot act."""
        out = []
        for a in self.enable:
            if a == "dream" and (len(self.w.pool) < 20 or self.broker.remaining < 100):
                continue
            if a == "admit" and self.broker.remaining * 0.35 < 12:
                continue
            if (a == "admit" and self.readiness_buffer is not None
                    and self.round_policy == "power"
                    and self.broker.remaining - self.readiness_buffer.minimum_gate_reserve() < 20):
                continue
            out.append(a)
        return out

    def choose(self, eligible):
        if self.policy == "u5":
            return self.sched.choose(eligible)
        if self.policy == "round_robin":
            a = eligible[self._rr % len(eligible)]
            self._rr += 1
            return a, False, 1.0
        a = eligible[int(self.rng.integers(len(eligible)))]
        return a, True, 1.0 / len(eligible)

    def run(self, max_steps: int = 40) -> CampaignResult:
        a0, p0 = self.measure()
        self.history.append(a0)
        self.potential.append(p0)
        tried: list[str] = []
        for step in range(max_steps):
            if self.broker.remaining < 6:
                break
            eligible = self.eligible()
            if not eligible:
                break
            arm, rnd, prop = self.choose(eligible)
            cluster = self.pick_cluster()
            before = self.broker.used
            try:
                getattr(self, f"do_{arm}")(*(() if arm in ("admit", "harvest", "dream") else (cluster,)))
            except BudgetExceeded:
                pass
            self._fail_cache = None
            a, p = self.measure()
            cost = max(self.broker.used - before, 1e-6)
            reward = (a - self.history[-1]) + 0.5 * (p - self.potential[-1])
            self.history.append(a)
            self.potential.append(p)
            if self.policy == "u5":
                self.sched.record(arm, rnd, prop, cost, reward, cluster)
            tried.append(arm)
            self.steps.append({"step": step, "arm": arm, "cluster": cluster, "cost": cost, "reward": reward,
                               "solved": a, "potential": p, "pool": len(self.w.pool),
                               "accepted": len(self.w.accepted_extra)})
            if self.policy == "u5" and self.sched.should_stop(self.history):
                rec = self.auditor.stop("campaign", tried[-6:], {k: v for k, v in self.sched.dr_report().items()},
                                        "a new lemma whose fingerprint overlaps the unsolved DEV tasks")
                if not rec.audited:
                    break
        return CampaignResult(list(self.w.accepted_extra), self.history, self.potential, self.steps,
                              self.broker.used, len(self.auditor.stops), self.sched.dr_report(),
                              self.broker.report(), self.generations)
