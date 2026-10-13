# B20_RX1 record: recovery branch after a second workspace loss

- **Branch:** `recovery-b20r1-partial`.
- **Prepared:** 13 October 2026.
- **Run by:** the builder. Nothing here is independently reviewed.
- **Status:** a partial base, not the canonical line.

## Why this branch exists

The workspace was reset again on 13 Oct 2026. The user rewound the conversation, said "Run them", and then "Continue". The B20_R11 checkpoint zip, which holds the canonical source history R1–R11, was not re-attached, and neither was the R3–R5 patch.

The R6–R11 patches cannot apply without R3–R5, and part of the R3–R5 code was never in the session log at all. So the canonical history could not be rebuilt faithfully. Re-implementing R3–R11 would produce a different history with re-run evidence, which the user has not asked for. That option was offered in chat.

This branch carries only work that does not depend on R3–R11, built on the part of the history that could be rebuilt exactly.

## The base

| Commit(s) | What | Fidelity |
|---|---|---|
| `97fb233` | B20, from the B20 checkpoint bundle | exact |
| `cca66c6`, `fed5684`, `d242988`, `f764063` | R1 repairs A–D (`git am` of the R1 patch) | **identical hashes** to the canonical commits |
| `2bfad58` | R1 `test_learning` fix, re-applied from the session log (canonical `72e429f`) | same content, new hash |
| `387c0fe`, `36f0dcd`, `69c837e` | CRPD-1, CRPD-2a, CRPD-3 (R2 patch), applied on f764063 instead of 972dbb6 | same content, new hashes |

Missing relative to B20_R11:
- **R1 records and obstruction evidence:** `708351c`, `972dbb6`.
- **The rest of R2:** H02 exit E3, lineage, candidates and records.
- **R3–R5, R6–R11:** all of it.
- **The checkpoint record:** `69f9613`.

## Decisions used

The user gave these on 13 Oct 2026, before the rewind; they were confirmed and not withdrawn:
- **E1:** time-matched baselines and the centred power model (a statistician's sign-off is still needed).
- **GV4:** graph construction as the domain.
- **CRPD-2b:** Go, time-boxed, reverted with a record if it fails.

## Work on this branch

### CRPD-2b: workspace pin revision and the Lean-checked C4 pair-count bound

Commits `61cd54a` and `bcd13e2`.

**Pin.** Two import roots were added:
- `Mathlib.Algebra.BigOperators.Group.Finset.Sigma`;
- `Mathlib.Algebra.Order.BigOperators.Ring.Finset`.

The Mathlib and dependency commits are unchanged. Modules went from 699 to 910. The source identity changed from `a3a7569b` to `7f5bcfa1`, and the artifact identity is now `be8f86a8`.

A new hash-chained `toolchain/FORMAL_WORKSPACE_HISTORY.jsonl` records each revision's reason, decision and build identities. It is checked by `build_formal_workspace.py check`, which before this had no record of pin changes.

**Checked statements** (`invention/pair_count.py`), stated over the repository definitions with builder-written recipes. These are known results.
- `pair_count_c4`: sum over v of C(deg v, 2) ≤ C(n, 2).
- `c4_quadratic_bound`: 4|S|² ≤ n²(n−1) + 2n|S|. This is `graphs.universal_upper`'s inequality.

Both are CHECKED, using allowed axioms only, and the package replays from its sources.

**Certificate method.** Bundle v2 gains `PAIR_COUNT_LEAN`:
- custody of the theory package;
- replay recomputes the bound from n and replays the package;
- the checker identity is revocable.

**Results.**
- **K3, K4 and K5:** `OPTIMALITY_CHECKED` without SAT.
- **K6, K7 and 4 dense hosts:** `BOUNDS_CHECKED`, each with a gap of 1. SAT/DRAT confirms the witness optimum on all of them.

**Earlier evidence.** It keeps its recorded identity. All earlier formal packages replay under the new pin: 151 of 152 formal tests pass. The one failure needed the missing R1 evidence and passes once that is regenerated (below).

### W23: fault-tolerant reasoning

Commit `d170012`; the Lean route is tested in `tests_formal/test_pair_count.py`.

`verification/reliability.py` implements:
- **Routes** with declared failure factors.
- **Diversity:** two routes count as independent only if they share neither implementation nor trust base.
- **Verdicts:** AGREE, CORRELATED, UNSETTLED or DISAGREE.
- **Quarantine:** stored as Store entities with inputs, outcomes and candidate causes drawn from a closed vocabulary.
- **Adjudication:** names the faulty route(s), one cause, stored evidence beyond the outcomes, and the adjudicator. It is recorded as an intervention.
- **No majority vote.**

Routes exist for motif-freeness (enumeration, bitsets, Lean kernel `decide`) and for the exact optimum (two Python optimizers, CaDiCaL + drat-trim). The existing graph checker guards still fail closed, and now carry both results and the input (`graphs.CheckerDisagreement`).

### W22: derived primitives

Commits `dd6fb7e` (code), `ab9a40f` (setup) and `f69d2e6` (evidence).

`primitives.py` implements:
- **Data-only contracts** whose reference expansions use accepted MRDL operations only.
- **Native implementations** only from a trusted table, each with its source digest pinned.
- **Licensing** always goes through the expansion.
- **Conformance testing.**
- **A fresh comparison** under a rule committed beforehand.
- **Versioned registries:** a cognitive-kernel digest, historical replay and migration checks.
- **Trace mining.**

**DEV result:** none of the four starting primitives is a capability gain.
- Three are renamed macros (NOT_A_CAPABILITY_GAIN): with conformance charged, they save less than half the CPU.
- One is REJECTED: its native code reaches beyond the 256-node language cap on 20 of 28 fresh hosts.

There is no DEV trace corpus of MRDL expressions, so mining is tested only on a fixture.

### H06 (s15.1): preserved search failures

Commit `e2d620c`. Proof-search attempts now keep the tactic text and that candidate's own Lean error lines.

### B20_R13: graph-construction headroom pilot (GV4)

Commit `01e92e8`, with the rules fixed before running.

The script was restored verbatim from the session log. The only change is that `e1_exposure()` now computes the 145 E1 hosts itself; `handoff/e1/exposure_hosts_to_exclude.json` is byte-identical to B20_R11's.

The lost run's B20_R12 SELECT-rehearsal hosts (drawn with `os.urandom`) cannot be named. The B20_R12 redo must therefore exclude this pilot's hosts.

**Result** (commit `ceeb673`): **NO_HEADROOM in all 7 settings.** All 4,160 runs completed and 0 witnesses were invalid.

- The cheapest fixed improver ties the oracle in every setting.
- The per-host ceiling over all configurations is at most 0.38 edges per host above it, against a minimum useful effect of 0.5.
- Selection and held-out rankings agree (rank correlation 0.94–0.99).

Configuration choice is saturated in graph construction, as it was on the equational systems. That makes four DEV pilots without research-policy headroom.

### B20_R14: optimum-gap probe (after the RX1 checkpoint)

Commits `331825f` (setup) and `01c38e6` (result). The probe certified the optimum on the 112 R13 held-out hosts (LP dual + SAT/DRAT, 60 s per host) and compared it with R13's per-host best over all configurations.

| Settings | Verdict | Optimum − per-host best |
|---|---|---|
| S2 tf n30 p.3 | ROOM_TO_OPTIMUM | **1.31** |
| S3 tf n40 p.2 | ROOM_TO_OPTIMUM | 0.56 |
| S7 c4 n30 | unsettled (11/16 hosts certified) | 1.36 on the certified hosts |
| S1 (the E1 family), S4, S6 | AT_CEILING | 0.19–0.31 |
| S5 | unsettled | — |

**Reading.** In graph construction the headroom is capability: better methods could earn it. It is not selection: picking among the existing configurations cannot. The comparison is not cost-matched.

**For E1:** the result supports the harder-family option. **For GV4:** it points to a design where research produces new methods, on S2-, S3- and S7-like families.

### User decisions, 13 Oct 2026 (second set)

- **R11 history:** independent work only (no rebuild).
- **GV4:** capability study design.
- **E1:** harder host family, once B20_R12 can be redone.

### B20_RX3 and RX3b: GV4 capability pilot and its replication

Commits `0dec3f6` (setup), `f2badd0`, `76aa47d` (replication setup) and `723c13d`. Rules fixed before running.

**Design.** Builder-written LP- and SAT-guided construction methods (`discovery/construct.py`) were added to the R13 menu.
- **Budget:** 2.0 CPU s per host, child processes included.
- **Research budget:** the same for every improver.
- **Families:** fresh S2-, S3- and S7-like.

**Result.** DEPLOYABLE_CAPABILITY_HEADROOM in all 3 settings, in both the first run and the fresh-seed replication:

| Setting | First run | Replication | 90% interval (replication) |
|---|---|---|---|
| C1 | +1.25 | +0.88 | [0.50, 1.25] |
| C2 | +0.75 | +0.63 | [0.31, 0.94] |
| C3 | +0.81 | +1.38 | [1.00, 1.75] |

**What it does and does not show.**
- Random proposals over the enlarged space do not reliably find the good methods; successive halving does.
- The methods are builder-written, so this shows the value of the method space, not that research can invent the methods.

**Design draft.** `handoff/gv4/README.md` (DRAFT) sets out the GV4 study these pilots point to, and what blocks it.

### H06 design probe (no study, nothing committed as evidence)

On 24 calibrated DEV hosts per domain, the motif hypergraph is essentially one component:
- **C4 hosts:** 96% of edges in the largest component, 4% in no motif.
- **Triangle hosts:** 90% and 9%.

So exact decomposition into independent motif components, and the free-edge kernel, would barely shrink the hard instances. A structural method for s16.3 has to come from elsewhere: symmetry, dominance rules, or a different family.

### Recovery-only commit

Commit `5b2c735` regenerates the R1 obstruction-custody evidence: 12 of 12 OPTIMALITY_CHECKED, matching the original run. It exists so the formal suite has the bundles on this branch. **Drop it when porting.**

## Porting onto the canonical line

Once `GENESIS_COMPLETION_CHECKPOINT_B20_R11.zip` is available:

```
git clone genesis/source-history.bundle genesis-work && cd genesis-work
git checkout continuation-b20-repairs                     # at 69f9613 (B20_R11 recorded)
git am -3 B20_RX1_recovery.patch                          # every commit after 69c837e on this branch
# then skip the RECOVERY-ONLY commit (git am --skip at that patch) and rerun the release matrix
```

None of the files these commits modify (`graphs.py`, `domains.py`, `certificates.py`, `soundness.py`, `codegree.py`, `formal_research/workspace.py`, `search.py`, `build_formal_workspace.py`, `FORMAL_WORKSPACE.json`) is changed by the available R6–R11 patches. R3–R5 cannot be checked from here; `git am -3` will stop on any conflict.

`handoff/e1/exposure_hosts_to_exclude.json` is byte-identical to R11's, so it merges cleanly. Records for this branch are in this new file only.

## Open items from this branch

| ID | Item | Needs |
|---|---|---|
| B20RX-OPEN-1 | The canonical history B20_R3–R11 is not in this workspace. B20_R12 (E1 under the user's decisions) was done in the lost run and must be redone; its code is recoverable from the session log. | the R11 zip, or the user's go to re-implement |
| B20RX-OPEN-2 | The CRPD-2b pin revision and the pair-count package. | reviewer acceptance (pin change, builder-written known results) |
| B20RX-OPEN-3 | W23 is not yet wired into the custodian or evidence-kernel promotion path; this needs the R5+ custodian. Code cannot check whether two operators are independent. | the canonical line; external review |
| B20RX-OPEN-4 | W22: no machine-proposed primitive with prospective utility yet, and no DEV trace corpus. | a corpus from real representation research |
| B20RX3-OPEN-1 | GV4: the capability effect (LP- and SAT-guided methods, builder-written) replicates. The study must let improvers *produce* the methods (`handoff/gv4/README.md`). It needs a candidate kind and H08 lineages from the canonical line, plus statistician and custodian. | canonical history; external parties |
| B20R13-OPEN-1 | GV4: choosing among existing configurations leaves no headroom in graph construction either (4 pilots in total). B20_R14 shows capability headroom on harder families: S2 at 1.31, S3 at 0.56 and S7 at 1.36 edges per host below the certified optimum. A study should let research produce new methods (LP- or SAT-guided construction, representations beyond the menu) at matched budgets on such families. | the user's design decision |
| B20RX-OPEN-5 | H06 s16.3: decomposition and free-edge kernel have no headroom on the calibrated families (design probe). | a different structural method or family |

## Claim ceiling

Engineering and DEV diagnostics only. Known mathematical results were Lean-checked as tools. No sealed task was run. Better-improver remains UNESTABLISHED.
