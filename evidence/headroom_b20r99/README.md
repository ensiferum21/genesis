# B20_R99 evidence: is there structure left where the searches stop? HEADROOM_UNSTRUCTURED

Builder-run on DEV (GV4; the headroom pilot of `docs/DISCOVERY_PLAN.md` §3). It licenses nothing.
- **Script:** `scripts/b20r99_headroom.py`, preregistered at `779831c` (SHA-256 `405412a7…d33c`).
- **Run:** alone on CPU 0, 2,099 s, on 23 Oct 2026 (08:32–09:07 SGT). `code_identity` `4efa194c…`, the committed
  tree (`cc7f4bb`).
- **The other core.** While it ran, the builder used CPU 1 lightly: compiling the max-cut engine of B20_R104 a few
  times, brute-force checks on 30 graphs of at most 13 vertices, unit tests of the graph families, and reading two
  PDFs. All of it was a few minutes of CPU in total, disclosed as possible cache contention.

| File | What |
|---|---|
| `hosts.json` | The 16 fresh hosts of `triangle_free_large_v1` (4 per cell; every recorded large-domain identity excluded) |
| `rows.jsonl` | Per host: 8 states (tfxw at 2 s and 10 s, hybrid-swap-v1 at 2 s and 10 s, the programs gen1, gen2, gen3 and gen2's control at 2 s), each with Part A (exchanges), Part B for tfxw's states (48 CP-SAT regions), Part C (gap pieces) |
| `summary.json` | The verdict, Q1, Q2, the descriptive tables, part B and part C totals, inputs and seeds |
| `run.log` | The run |

## Result: HEADROOM_UNSTRUCTURED

**Q1, headroom.**
- **tfxw's states:** 2 of 32 (6%) have local headroom. Both are 2 s states, both through Part B (one host with 1
  improving region, one with 3); no exchange of size 1 or 2 improves any tfxw state, and no 10 s state has an
  improving region.
- **The language programs' states:** 23 of 64 (36%) still have a (2,3)-exchange after descent with r = 1.
- Below 10% at tfxw but not at the programs, so the verdict is not NO_HEADROOM.

**Q2, structure.**
- **Anchors (r = 1):** the fitted recognizer (S-degree sum at most 66, a high host-degree ratio, host-degree
  difference at least 8) has held-out lift 11.1, above the null's 95th percentile (7.3), but held-out recall 0.22
  (11 of 51 improving anchors), under the 0.3 required: FAILS.
- **Regions:** 4 improving regions of 1,536 (1 in training), 3 held out: UNDERPOWERED.

So: headroom exists, but none of it is recognizable in the primitive grammar.

**Descriptive.**

| State | Mean value | With r=1 | With strict r=2 | Mean descent gain |
|---|---|---|---|---|
| tfxw@10 | 4,247.6 | 0 | 0 | 0 |
| tfxw@2 | 4,244.7 | 0 | 0 | 0 |
| hybrid@10 | 4,239.8 | 0 | 5 | 0.88 |
| hybrid@2 | 4,234.6 | 0 | 5 | 0.88 |
| gen3@2 | 4,234.7 | 6 | 5 | 2.19 |
| gen1@2 | 4,234.4 | 7 | 7 | 2.94 |
| gen2@2 | 4,233.6 | 7 | 5 | 2.31 |
| control@2 | 4,229.5 | 8 | 8 | 2.75 |

Each row has 16 states; mean values are over hosts of different sizes.

- **Part B (tfxw's 2 s and 10 s states):**
  - ball2: 1 IMPROVES, 382 PROVED_NONE, 129 UNKNOWN;
  - ball4: 1 IMPROVES, 143 PROVED_NONE, 368 UNKNOWN;
  - rand4: 2 IMPROVES, 205 PROVED_NONE, 305 UNKNOWN.

  Half the regions were left UNKNOWN at the deterministic time limit (2.0). UNKNOWN never counts as headroom.
- **Part C:** 484 pieces in the differences to each host's best state, 143 of them improving, 55 of those with at
  most 10 edges. The largest improving pieces have about 8,000 edges, nearly the whole state: the best states are
  globally different, not one local repair away.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| The programs' states show r = 1 headroom often (the swap, already known) | Yes: 6-8 of 16 states per program |
| hybrid-swap-v1 shows strict r = 2 exchanges on planted hosts and none on G(n, 0.5) | Yes: 5 of 16 states at each budget, all on planted hosts |
| tfxw shows no exchange headroom | Yes |
| ...and improving 4-balls on a minority of its 2 s states, fewer at 10 s, more often than random 4-sets | Partly: 2 of 16 states at 2 s, none at 10 s; but random 4-sets improved as often as balls (2 against 1 ball4, 1 ball2) |
| NO_HEADROOM unlikely | Yes |
| HEADROOM_UNSTRUCTURED slightly more likely than HEADROOM_STRUCTURED | HEADROOM_UNSTRUCTURED |

## What it means

- **Where the strongest search stops, nothing local is left.** tfxw's states admit no improving exchange of up to
  two edges, and almost no improving region of 2-4 vertices. The best states differ from each other globally.
- **The language programs leave a simple repair undone.** Their headroom is the (1,2)/(2,3) exchange, which a
  descent step already fixes; that is the swap the language left out (B20_R78), not a new concept.
- **No recognizable local structure.** The one candidate pattern (anchors near high host-degree imbalance)
  generalises in precision but misses most improving anchors.

Under the plan (§3.3), the discovery loop of §4 is not built on these hosts. One richer grammar may be tried once.
The route that the evidence points to is global: coarse-grained views that move whole groups at once. That is the
renormalisation and crossover direction already being tested on max-cut (B20_R104–R106).
