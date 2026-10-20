# B20_R93 record (engineering): the adaptation cell

- **Asked by Daniel (20 Oct 2026):** "a problem we saw, then we were able to put it in words as a caveat, and from
  there we adapt and improve ourselves: this mechanism I want to adapt, so our system is like a cell", and "make sure
  it's extremely smart so that it is unbelievably smart without handholding at all".
- **Built by:** the builder. **No claim, rule, comparator or package changes.** The cell reads evidence and proposes
  and blocks designs; it never runs a study or decides a claim.
- **Prospective check preregistered with this record** (below): what the cell must conclude from B20_R92, which was
  still running when the cell's code was committed.

## What it is

`src/genesis/adaptation/` turns the loop "see a problem, name it as a caveat, adapt, improve" into a mechanism. Nobody
registers a study, labels a caveat or says what a study tried: the cell reads all of that from the evidence.

| Part | What it does | Modelled on |
|---|---|---|
| `discovery.py` | Finds every time-to-solution study under `evidence/` by its shape (a `summary.json` with a ladder, rows with `runs` and a `target`), its batch from the directory name, its date from git, the system's own arm by name, its competitors | sensing the environment |
| `receptors.py` | Twelve receptors on a study's evidence: floor effect, saturation, uncertified targets, unresolved verdicts, ablations without an effect, invalid run, interruption, a leading published solver left out (by publication date), budgets below the competitors' regime, instances at the model's cap, **a competitor that does not respond to its run time** (a dose-response check), **the system's method outperformed** (read from the rows, with the lost hosts' families and sizes). One **autoreceptor** senses the cell itself: its baseline catalog going stale after the field's yearly results | receptors; autoreceptors |
| caveats | A detection becomes a typed record with evidence, severity, a magnitude comparable across studies, and a subject (one arm that does not respond is a different weakness from another) | signal transduction |
| `responses.py` | For each caveat type, the adaptations that answer it, in order, each with a **dose** (how far a design goes towards it: four of nine missing solvers is 0.44; a 10 s budget against a 60 s regime from 2 s is log 5 / log 30) and a **noise band** (122 s of certification instead of 121 s is not an attempt). Responses that make an observation go away rather than explain it (leaving an arm out) are **last resorts**, ranked after every other however well they have scored: a competitor that does not respond is first probed at its home budget (if it then responds, its regime is longer than the ladder; if not, its harness is checked against its Evaluation run script) | gene expression; dose-response; diagnose before excising |
| `ledger.py` | One lineage per weakness, read in batch order. **An attempt is a change, not a state:** the cell compares the design of the study where the caveat was last seen with the later study's design. Outcomes: RESOLVED, IMPROVING (the magnitude fell below 90%), PERSISTENT, UNDERDOSED (a partial dose without effect), CHRONIC (two unanswered recurrences; severity raised once), CLEARED (quiet in two studies that could have shown it; no response credited), RELAPSE (the response that resolved it is charged). A response is retired after two full doses without effect. Every response's record (Laplace-smoothed) ranks it for the next choice. New weaknesses appearing in the same study as an attempt are reported as suspected side effects, not scored | bacterial chemotaxis compares the last second with the three before and responds to the difference (Segall, Block and Berg 1986); immune memory, clonal selection, apoptosis; a CAPA's verification of effectiveness (21 CFR 820.100: effective and without adverse effect; a failed check opens a new action referencing the old) |
| `metabolism.py` | A cost model fitted to the cell's own run logs (one overhead per run, the median over the studies) | metabolism |
| `design.py` | `design_of` reads what a study did; `compose` writes the next design: the best-ranked response that changes the design, for every open caveat, at the dose the latest evidence calls for; a response that cannot be carried out (a ladder below 1 ms) gives way to the next (first-hit times); long budgets only for the arms that can change the comparison (the system's method, arms that stand for leading solvers, matched by name, and new leading baselines); resumption and sequential stopping planned when the design is longer than a background window; a growth-limited budget (at most twice the most expensive study so far) | homeostasis; triage under an energy budget |
| triage | When the design is over budget, the least urgent deferrable adaptation is deferred (the smallest that fits, else the largest), with the cost stated; high-severity and chronic caveats are never deferred to save time (if they alone are too expensive, the plan says so and names the largest share) | the membrane |
| `capabilities.py` | What the code (the task model's cap, the pinned solver keys) and the evidence (what some study has demonstrably done) show the system can do; what a design needs beyond it becomes a work order | the unfolded-protein response: stop and build capacity before taking on more |
| `checkpoint.py` | A design passes only if every open caveat is answered at full dose by something new relative to the study that showed it, or deferred with a reason the membrane allows; the catalog is current; validity thresholds are no looser than canonical and the hosts are fresh | the cell-cycle checkpoint |

`scripts/b20r93_cell.py ROOT OUT` runs it and writes `caveats.json`, `ledger.json`, `cost_model.json`,
`capabilities.json`, `next_design.json`, `plan.json`, `checkpoint.json` and a readable `CAVEATS.md`; with
`--check DESIGN.json` its exit status gates a design (0 passes, 1 fails).

## Retrospective: the cell on B20_R70–B20_R90

**Disclosed:** the receptors' thresholds, the noise bands and the dose rules were set by the builder while reading
these studies (and an 18-host preview of B20_R92, below). Agreement with the hand-found caveats is therefore a
consistency check, not an independent test; the prospective check below is the test.

It found the six studies by itself (B20_R70, R75, R76, R77, R81, R90; the focal arms candidate, system, system,
engine, found, tfx). On B20_R90 it senses exactly the seven caveats found by hand: FLOOR_EFFECT (33 of 36 hosts at
0.05 s), SATURATION, UNCERTIFIED_TARGETS, INTERRUPTED, MISSING_BASELINE (the five 2026 leaders), REGIME_GAP (10 s
against 60 s), SIZE_CAP (n = 63). Its account of the history, inferred from the evidence alone:

- B20_R70: SATURATION, MISSING_BASELINE, REGIME_GAP and OUTPERFORMED (tabu more than twice as fast on 20 of 24 hosts)
  first seen.
- B20_R75: a new method did not help OUTPERFORMED (dsb more than twice as fast on 11 of 12); INVALID_RUN, SIZE_CAP,
  UNCERTIFIED_TARGETS and ARM_NOT_RESPONDING for HiGHS and BURER2002 first seen.
- B20_R76: the harness fix resolved INVALID_RUN; SATURATION, MISSING_BASELINE and REGIME_GAP became CHRONIC.
- B20_R77: the engine resolved OUTPERFORMED; dropping HiGHS resolved its non-response; BURER2002's cleared (quiet in
  two studies that ran it); more hosts resolved UNRESOLVED_VERDICT; SIZE_CAP CHRONIC.
- B20_R81: OUTPERFORMED relapsed (the builder's engine more than twice as fast as the self-found solver on 18 of 24
  hosts; the B20_R81 record says about five times), UNRESOLVED_VERDICT relapsed, UNCERTIFIED_TARGETS CHRONIC.
- B20_R90: acquiring four of the nine missing solvers (dose 0.44) and a 10 s budget (dose 0.47) were IMPROVING;
  tfx resolved OUTPERFORMED again; FLOOR_EFFECT first seen.

What it saw that had not been said by hand: **UNCERTIFIED_TARGETS is chronic because no study ever gave certification
more time** (121–122 s since B20_R75; the LP upper bounds were there throughout and did not resolve it), and HiGHS
did not respond to its run time in B20_R75.

Its cost model (overhead 0.3655 s per run, fitted to the six run logs) predicts each study's wall time within 9%
(B20_R70 3,467 s against 3,424; R75 2,674 / 2,570; R76 3,229 / 3,306; R77 5,414 / 5,475; R81 5,203 / 5,243; R90
12,121 / 11,160).

**Its proposal from B20_R90** answers all seven open lineages: a ladder down to 0.005 s, the five 2026 leaders, a
60 s home budget (for the method and the arms that stand for leading solvers only), certification 1.5 times longer,
quality at equal time on n = 128 and 256, sequential stopping. B20_R92, designed by hand, did the first two of these
(its ladder starts at 0.005 s and it includes the five leaders); the rest is the large-graph milestone the builder had
proposed separately. Estimated 41,878 s against a limit of 22,319 s: the cell reports that only high-severity and
chronic caveats are left (the 60 s budget is the largest share, 21,732 s) and does not defer them. Work orders: a
task model and engine beyond n = 63; quality at equal time; sequential stopping; a harness test at 0.005 s; budgets
beyond 10 s. B20_R90's own design fails the checkpoint (it repeats every weakness it showed); the proposal passes.

## Prospective check on B20_R92 (preregistered)

B20_R92 was running (18 of 36 hosts finished) when this record and the cell's code were committed. The builder ran the
cell once on those 18 hosts as a development look (no summary yet, so its labels and solver list were missing);
the statements below use that look where marked. When B20_R92 has finished and is committed, `scripts/b20r93_cell.py`
is run, unchanged, on the tree, with every study up to B20_R92. The cell passes this check if all of the following
hold, and each failure is recorded as such:

1. FLOOR_EFFECT@B20_R90 is RESOLVED by `extend_ladder_down` (seen in the look).
2. MISSING_BASELINE@B20_R70 is RESOLVED by `acquire_baseline` (B20_R92 includes all nine leading solvers).
3. REGIME_GAP@B20_R70 recurs without an attempt (B20_R92's longest budget is 10 s, as B20_R90's).
4. SATURATION, UNCERTIFIED_TARGETS and SIZE_CAP recur without an attempt and stay CHRONIC.
5. INTERRUPTED becomes CHRONIC (B20_R92 was interrupted again, with the same design; seen in the look).
6. ARM_NOT_RESPONDING[deepdistc] is first seen (in the look, DeepDist-c ended near 70% of the target on 10 of 18
   hosts at every run time from 0.005 to 2 s; the B20_R91 record noted its first phase is SAT-based search).
7. OUTPERFORMED does not fire on B20_R92.
8. The proposal after B20_R92 passes the checkpoint and B20_R92's own design does not; it keeps the 60 s budget and
   instances beyond n = 63 and adds a probe of DeepDist-c at its home budget.
9. The cost model fitted on B20_R70–R90 predicts B20_R92's wall time within 15%: its prediction from B20_R92's design
   (19 ladder arms, 3 seeds, 8 rungs, 8 arms at 10 s, B20_R90's certification time) is **18,763 s**; the observed time
   is the sum of the run log's segments (which counts the host rerun after each interruption twice).

## Outcome of the prospective check: all nine hold

B20_R92 finished (`c3af5a7`), the cell was merged unchanged (the concatenated digest of its script, modules and
catalog is still `b5254e60…317a`) and run once: `python3 scripts/b20r93_cell.py . evidence/adaptation_cell_b20r93
--today 2026-10-20`. The nine preregistered checks (`ProspectiveB20R92`) pass:

1. FLOOR_EFFECT@B20_R90 RESOLVED by `extend_ladder_down` (tfx at the shortest run time on 5 of 36 hosts).
2. MISSING_BASELINE@B20_R70 RESOLVED by `acquire_baseline` (dose 1.0: all nine leading solvers).
3. REGIME_GAP@B20_R70 recurs without an attempt (10 s again).
4. SATURATION, UNCERTIFIED_TARGETS and SIZE_CAP recur unanswered and stay CHRONIC.
5. INTERRUPTED CHRONIC (two unanswered recurrences; severity raised to medium).
6. ARM_NOT_RESPONDING[deepdistc] first seen.
7. OUTPERFORMED does not fire.
8. The proposal passes the checkpoint and B20_R92's own design does not; it keeps the 60 s budget and n = 128 and 256,
   and probes DeepDist-c at 60 s on 4 hosts.
9. Cost: predicted 18,763 s from B20_R70–R90; observed 17,626 s (the sum of the run log's segments): 6.4% off.

It also saw, unprompted, two things the prospective list did not name: **UNRESOLVED_VERDICT relapsed** (vbs_P), so it
proposes 1.5 times the hosts (54); and **COMPONENT_EFFECT_UNRESOLVED** (the five ablations), so it proposes a dedicated
ablation with twice the hosts. Its proposal now costs an estimated 68,473 s against its growth limit of 35,253 s;
only high-severity or chronic caveats are left, so it defers nothing and says the study should be split at the 60 s
budgets (35,847 s of the cost). Work orders: a task model and engine beyond n = 63, quality at equal time, sequential
stopping, the DeepDist-c probe, budgets beyond 10 s.

**Limits seen in this run, for the cell's next version (not changed: the version above is the preregistered one):**
it reads the size cap from the n <= 63 task model only (a large domain needs a per-domain cap); `more_hosts` adds
hosts to every family although only the planted family's VBS label is unresolved; and an unresolved ablation whose
estimates lean against the component (B20_R92: the stripped-down engines were faster on more hosts) should also
propose racing without that component, which the library cannot yet express.

## Tests

`tests_genesis/test_adaptation_cell.py` (34, and 9 prospective checks that run once B20_R92 is in the tree): discovery by shape and batch order; each receptor on synthetic studies
(the floor share, saturation, regime, size cap, publication dates, labels, a flat arm against an improving one and an
ablation, outperformed with native arms marked, the stale catalog); noise bands and partial doses; the ledger
(change versus state, IMPROVING and UNDERDOSED, RESOLVED then RELAPSE with the resolver charged, retirement after two
failures, CLEARED, exclusion, a method's identity, side effects, deterministic rebuild); composition (every open
caveat answered and the checkpoint passed while the base fails, escalation below the harness resolution, triage that
defers the smallest fitting medium caveat and never a high one, anticipation, work orders, arm-to-solver matching);
the membrane and the stale catalog; the cost model's fit; the command and its gate; and the record on the real
evidence up to B20_R90 (the studies, the seven caveats, the inferred history, the proposal against B20_R92's design,
the cost model within 15%).

## Files

`src/genesis/adaptation/` (`__init__`, `discovery`, `receptors`, `responses`, `ledger`, `metabolism`, `design`,
`capabilities`, `checkpoint`, `baselines.json`), `scripts/b20r93_cell.py`, `tests_genesis/test_adaptation_cell.py`.

Sources: J. E. Segall, S. M. Block, H. C. Berg, "Temporal comparisons in bacterial chemotaxis", PNAS 83(23):
8987–8991 (1986), https://doi.org/10.1073/pnas.83.23.8987; "A SMART approach to CAPA effectiveness checks",
Pharmaceutical Online (9 Mar 2020), quoting 21 CFR 820.100,
https://www.pharmaceuticalonline.com/doc/a-smart-approach-to-capa-effectiveness-checks-0001.
