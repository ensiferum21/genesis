# B20_R97 record: the loop's first study; the system's engine finds more than all 13 MaxSAT champions at equal time on large hosts (DEV)

- **Run by:** the builder, on DEV; licenses nothing; changes no package, rule or comparator. The design is the
  adaptation cell's; `genesis.autonomy.studygen` wrote the script and `loop.preregister` committed it at `6b674d1`
  (`scripts/b20r97_qet_large.py`, SHA-256 `892b5a11…7d58`, sent to Daniel before it ran), unchanged. Setup and the
  rehearsal before preregistration: `B20_R96_RECORD.md`, "Setup of B20_R97".
- Alone on CPU 0, one segment (5,148 s); `code_identity` `937f733f…7d08`. Evidence `evidence/qet_large_b20r97/`;
  recomputed independently (match, including every witness and certificate).

## Result

On fresh hosts with 128 and 256 vertices (planted clusters and G(n, 0.5)), given the same 10 s, the system's engine
(`tfxw-v1` in B20_R95's frozen configuration) finds larger triangle-free subgraphs than each of the 13 champions of
the MaxSAT Evaluations 2024 and 2026, and than their per-host best. The study stopped at its first preregistered look
(19 of 56 hosts), where every comparison it had to decide was decided.

Anytime score (the Evaluation's: best known cost + 1 over cost + 1), the engine minus each arm, paired over 19 hosts,
interval at level 1 − 0.1/3, margin 0.002:

| Against | Mean difference | Interval | Verdict |
|---|---|---|---|
| DeepDist | +0.0129 | [+0.0094, +0.0168] | better |
| PASMaxSAT-c | +0.0152 | [+0.0097, +0.0228] | better |
| SPB-MaxSAT-c-FPS, NuWLS-c-2026-UB, Aperture-IBI, SGAT-NuWLS-c, Aperture-GBG, Aperture-KBG, NuWLS-c-IBR, TT-Open-WBO-Inc | +0.024 to +0.028 | lower ends +0.015 to +0.019 | better |
| Aperture | +0.0442 | [+0.0324, +0.0593] | better |
| NuWLS-c-2026 | +0.2008 | [+0.1061, +0.2976] | better (see limits) |
| DeepDist-c | +0.3882 | [+0.3773, +0.3985] | better (see limits) |
| **their per-host best (VBS)** | **+0.0102** | **[+0.0062, +0.0149]** | **better** |
| the engine at **1 s** against the VBS at 10 s | +0.0091 | [+0.0050, +0.0138] | better |

The engine is strictly best on 17 of 19 hosts and tied with the best champion on 2 (planted, n = 128). In edges,
against the best champion on each host: G(256, 0.5) +155 to +216 (a subgraph about 2% larger); G(128, 0.5) +9 to +29;
planted n = 256 +15 to +34; planted n = 128 0 to +2.

**Ablations (the cell's dedicated ablation).** Against the frozen configuration, each of these is **equivalent within
the margin**:

| Arm | Mean difference | Interval |
|---|---|---|
| B20_R89's configuration (previous generation) | +0.00059 | [+0.00009, +0.00128] |
| no crossover | +0.00017 | [−0.00020, +0.00051] |
| no relinking and no restarts | −0.00016 | [−0.00060, +0.00020] |
| the engine's first design (DEFAULT) | +0.00020 | [−0.00045, +0.00091] |

Descent warm starts only and no parallel tempering are already the frozen configuration's choices (B20_R95), so those
two ablations give no arm. At 10 s on these hosts, configuration hardly matters: what wins is the engine's core
(tightness-guided swaps, least-tight kicks, the work lists), not its nature- and physics-inspired operators. This is
the third study in a row where those operators show no measurable effect (B20_R92 unresolved, B20_R95 small margins).

**Probe.** DeepDist-c at its home budget (60 s) on the first four hosts: 742, 1,193, 2,321 and 3,611 edges, 40–63% of
the best known value, barely more than at 10 s (720, 1,174, 2,268, 3,595): NO_RESPONSE.

**Validity.** No failed run among 365 (361 and the four probes); median metered CPU at the 10 s budget 10.16–10.32 s for every arm.

**Certified bounds.** Every host has one, re-checked from its certificate: the clique packing on 15 hosts, the
triangle packing on the four G(256, 0.5) hosts (the clique LP did not finish in 60 s). Gap between the best known
value and the bound: mean 10.8%, from 0.8% (planted, n = 128) to 20% (G(256, 0.5)). How close anything is to the
optimum on the dense hosts is not known.

## Against the expectation stated before running

| Expected | Found |
|---|---|
| FOCAL_BETTER_THAN_EVERY_CHAMPION | yes |
| FOCAL_BETTER_THAN_VBS | yes |
| on planted hosts a smaller margin, equivalence with the strongest possible there | smaller on planted n = 128 (two ties; per-cell means 1.0 against the VBS's 0.9987); not on planted n = 256 |
| at a tenth of the budget: better than the VBS, or unresolved | better |
| the extra arms: NO_MEASURABLE_EFFECT for most | all four |

The expectation was written before the rehearsal, which showed the same direction on four dev-only hosts (disclosed in
the script).

## The prospective check on the cell (preregistered with the study): 8 of 8 hold

`ProspectiveB20R97`: the cell discovers B20_R97 last as a study of quality at equal time; senses no interruption; no
size cap; no saturation; uncertified targets (mean gap 0.108); the home regime still missing; its next design asks for
the 60 s budget; and studygen's cost estimate is within a quarter of the observed time (5,448 s predicted for 19 hosts
and the probes, 5,148 s observed: 5.8% high). Item 2 held trivially: the study ran in one segment, so the receptor's
new handling of planned pauses was not exercised by real data.

## What the cell made of it (unchanged cell, `evidence/adaptation_cell_b20r97/`)

- **Closed:** SATURATION (by quality at equal time on larger instances), SIZE_CAP (extend_domain), INTERRUPTED
  (sequential stopping).
- **Still open:** REGIME_GAP (chronic: 10 s here, the champions' home regime is 60 s); UNCERTIFIED_TARGETS (chronic;
  no attempt credited, because this study gave the bound 60 s per host, less certification time than B20_R92's
  122 s);
  COMPONENT_EFFECT_UNRESOLVED (improving: the receptor counts a decided null as a caveat, so it now reads "no
  component shown to help"); ARM_NOT_RESPONDING[deepdistc] (persistent after the probe).
- **Next design, without being told:** it escalates DeepDist-c from probing to a **harness check** (work order: "check
  how deepdistc is run against its Evaluation run script and fix what differs"), keeps the 60 s budget, more hosts,
  longer certification and a dedicated ablation; 44,016 s against its limit of 35,253 s, so it stages again.
- **Its reading attributes the ablation to `ablation_on_harder_instances`**, not to the dedicated ablation it chose:
  the study decided the ablations by equivalence at 19 hosts, fewer than B20_R92's, and the cell infers attempts from
  what a design did, not from what it was asked.
- **Two things it got wrong, found reading its output (engineering, next):**
  1. Stale work orders: "extend_domain" (its capability scan reads only the small domain's cap of 63) and "budgets up
     to 60 s" (it does not count the 60 s probes as long runs).
  2. It did not notice NuWLS-c-2026 collapsing on every 256-vertex host (40–52% of the best known value, against
     97–100% at n = 128): the quality-at-equal-time receptors sense an arm that does not respond only through probes.

## Limits

- DEV, builder-run, one machine, one seed per arm and host, 19 hosts (the preregistered stop), n ≤ 256, two families.
  No independent replication.
- The champions are general MaxSAT solvers on the standard encoding (one soft clause per edge, one hard clause per
  triangle). The engine is specific to this problem. A specialised method beating general ones on its home problem is
  expected in kind; the finding is that it does so against all 13, at a tenth of the time against their per-host best,
  and by subgraphs about 2% larger on dense 256-vertex hosts.
- 10 s is not the champions' home regime (their anytime track gives 60 and 300 s). At 30 s the champions gain
  (B20_R94's development look); the 60 s stage is the cell's next request.
- **DeepDist-c and NuWLS-c-2026** end near half the best value on large hosts, which is not what either does in the
  Evaluation. A harness or encoding difference at scale is not excluded. Their margins above are not evidence about
  those solvers until the harness check the cell asks for is done; the VBS comparison does not depend on them (the
  per-host best comes from DeepDist, PASMaxSAT-c and others).
- Best known values come from every arm, including five runs of the system's method, so the anytime score's reference
  is set mostly by the system; that is the Evaluation's rule (best known from all solvers) and it favours whoever
  runs most.
- Bounds are certified but loose on dense hosts.

## Tests

`tests_genesis/test_autonomy.py`: `RecordB20R97` (5: the preregistered script and design unchanged, the labels and
the stop follow from the rows, validity, every witness and bound re-check, the hosts fresh by exposure identity) and
`ProspectiveB20R97` (8, preregistered before the run).

**Amendment (B20_R98).** The harness check this record asked for found NOT_THE_HARNESS. Our harness reads the solver's
own best model, and none of the following changes the value: pipe or file input, the sandbox, the stop signal, or 60 s
instead of 10 s. DeepDist-c's and NuWLS-c-2026's low values here are their own search on these instances, so the
margins above stand as what they do here. B20_R98 also saw the controls end 3% lower at 10 s on the G(256, 0.5) host
than in this study (machine speed at the edge of the budget), so 10 s comparisons on that family should allow for a 3%
band (`evidence/harness_check_b20r98/`).

