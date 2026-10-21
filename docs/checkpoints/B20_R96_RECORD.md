# B20_R96 record (engineering): the autonomy layer, and new answers to the system's chronic caveats

- **Asked by Daniel (21 Oct 2026):** make the system more powerful, let it "recursively but properly improve and
  discover and make itself better", add the six things proposed (close the loop; several objectives and an archive;
  invented operators; an adversary; an improver that improves itself; transfer), "and also use novel ways to solve the
  system issues".
- **Built by:** the builder. **No claim, rule, comparator or package changes; every existing identity unchanged**
  (tfxw-v1, the maxsat kinds and registry v2 untouched; B20_R92's descriptors still rebuild). Overview:
  `docs/AUTONOMY.md`.

## What was built

| Part | What it does | State |
|---|---|---|
| `autonomy/studygen.py`, `autonomy/loop.py` | the cell's design becomes a preregistered study script (fresh seeds checked against every script, the design embedded); the loop commits it, appends `docs/PREREGISTRATIONS.md`, returns the hash (sent before running), runs it in slices and resumes | built, tested; first use: B20_R97 |
| `autonomy/qet.py` | the generic quality-at-equal-time study: every arm in runc, the Evaluation's anytime score, paired bootstrap against a margin, Bonferroni-split interim looks that stop when decided, a certified bound per host, pause before the background limit | built, tested end to end on a tiny design |
| `autonomy/archive.py` | quality-diversity archive (MAP-Elites) over family × size × budget cells; objectives mean, worst cell, scaling with n, elite cells; Pareto front; parents drawn by performance and fewer children (Darwin Gödel Machine) | built, tested; used from B20_R98 |
| `candidate_kinds/tfxw2.py`, `native/tfxw2.c` | `tfxw-v2`: late acceptance, great deluge, record-to-record travel, population annealing, heavy-tailed (Lévy) kick counts, a removal rule; tfxw-v1's search when the new keys are at their first values | built, verified (70 runs of a build that recomputes every structure each iteration), pinned `9e674217…eab9` |
| `autonomy/adversary.py` | (mu + lambda) evolution over host-generator parameters for the hosts where the system does worst | built, tested on a synthetic hardness; used from B20_R98 |
| cell v2 (`adaptation/`) | reads studies of quality at equal time (discovery, five receptors, their designs, VBS contributors), per-domain size caps, `extra_` comparisons as ablations | built, tested; the preregistered v1 results unchanged (all 43 cell tests pass) |
| `bounds_large.py` | a certified bound from a fractional **Mantel clique packing** (below) | built, tested |
| GV4: an improver that improved itself against a frozen one | design only (next) | not built |
| GV6: the stack, unchanged, on another problem class | not started | — |

## The system's chronic caveats, and the new answers

- **UNCERTIFIED_TARGETS** (chronic since B20_R75). For any subgraph F and triangle-free H, |E(H) ∩ E(F)| ≤ ex(F, K3),
  and ex(K_k, K3) = ⌊k²/4⌋ (Mantel). With clique weights y_C covering each edge at most once,
  |E(H)| ≤ m − Σ y_C (e(C) − ⌊k²/4⌋): triangles certify one removed edge per three, large cliques nearly one per two,
  which is what dense hosts need. The weights come from a linear program (HiGHS interior point) with **column
  generation** (cliques grown against the edge duals while their reduced cost is positive; Gilmore and Gomory 1961),
  then rounded to integers and re-checked exactly; each host gets the better of this and B20_R94's triangle packing.
  Development looks (dev-only hosts, 60 s): G(128, 0.5) 2,455 against the triangle bound's 2,794 (best known about
  2,310: gap 6%); planted n128 1,203 against 1,422 (best about 1,170: 3%); planted n256 5,526 against 5,601. **Limit:**
  on G(256, 0.5) the first LP does not finish in 60 s and the triangle bound (about 25% above the best known) is
  used; a first-order packing solver is the next step there.
- **INTERRUPTED** (chronic since B20_R81): studies pause between hosts before the background limit and resume from
  their rows; interim looks end a study when it is decided.
- **SATURATION and SIZE_CAP**: the large domain (B20_R94) with quality at equal time; the adversary to look for the
  hosts where the system does worst.
- **COMPONENT_EFFECT_UNRESOLVED**: each generation of the engine is compared with the previous one on hosts where
  configurations can differ.
- **ARM_NOT_RESPONDING (DeepDist-c)**: a probe at its home budget.
- **Over the cost limit**: budgets staged (10 s, then 60 s), sequential stopping.

## Development looks (disclosed; dev-only hosts drawn with Python's `random`, seeds no study uses)

- **tfxw-v2's new operators at 5 s** (B20_R95's configuration with each operator switched on; two seeds): on G(256,
  0.5) and G(400, 0.5) every variant ended at exactly the same values as the base (8,900 and 8,897; 21,560 and 21,531
  or 21,534); on a planted n256 host within 1-6 edges of it either way. On dense hosts at this budget the answer comes
  from the warm starts and the first local search; the iterated search after them hardly changes the best. That is
  where better operators have room, and what the archive and the operator search are for.
- **The bound** (above).

## Tests

`tests_genesis/test_autonomy.py` (13): the bound (valid against brute force, Mantel's value on cliques, tighter than the
triangle packing on a dense host, the best-bound choice, tampering refused), the archive (elites, Pareto front,
parents, round trip, mutation inside the space), the adversary, the quality-at-equal-time study end to end (labels,
probes, bounds, resume, pause) and its labels on synthetic rows, the study generator (fresh seeds, the embedded design
round-trips), tfxw-v2's space, and the cell reading a study of quality at equal time (discovery, receptors, design,
caps, saturation).

## Setup of B20_R97 (the loop's first study; preregistered with this addendum)

The study generator's first proposal, read before preregistering it, did not do everything it said, and the cell would
have misread the study it was about to run. Fixed first (engineering; no checker, threshold or scorer changed):

- **Ablations.** The cell asked for a dedicated ablation with more power (COMPONENT_EFFECT_UNRESOLVED), the
  generated docstring said so, and studygen's own docstring promised the frozen configuration without each component;
  the code compared only the previous generation. It now adds B20_R92's ablations of the frozen configuration
  (`no_cross`, `no_relink_restart`; `no_dsb` and `no_pt` give no arm because B20_R95's configuration already has
  them off) and the engine's first design (`tfxw-v1` DEFAULT), and such a study does not stop before those
  comparisons are decided (`decide`, in `qet`'s docstring). Without that, interim stopping on the champions alone
  could have ended the ablation at 19 hosts, fewer than the 48 the cell asked for.
- **What the script says.** Each of the cell's reasons now states how this study carries it out (the 60 s home
  budget, for example, is left for the next study), with a cost estimate (`studygen.estimate_seconds`) and what the
  builder looked at before preregistering (`disclosure`).
- **The cell's reading of pauses.** The interruption receptor counted every restart in a run log as an
  interruption; a study that pauses on purpose and resumes, the answer to INTERRUPTED, would have been read as a new
  case of it. A start that follows a planned pause no longer counts (no earlier run log has one, so no earlier reading
  changes; the 43 cell tests pass).
- **Evidence that re-checks.** Rows carried only the bound's digest and no witness. Each host now keeps the best
  value's witness (a bit mask over the host's edges) and the bound's certificate in `certificates/<host>.json.gz`;
  `qet.check_host_evidence` re-checks both from the data.
- **Descriptive per-cell means** (family and size) in the summary, carrying no label.
- **A prospective check on the cell** (`tests_genesis/test_autonomy.py::ProspectiveB20R97`, eight items, declared as
  a non-mandatory skip until B20_R97 is in the tree): what the cell must conclude when it reads the study, and whether
  the generator's cost estimate is within a quarter of the observed time.
- **A rehearsal** of the study's own code path (runc, every arm, the bound, the kept evidence) on four dev-only hosts
  before preregistration, reported below and disclosed in the script.
