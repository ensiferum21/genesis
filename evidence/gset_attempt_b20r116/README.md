# B20_R116 evidence: five minutes on each Gset instance not yet reached: 7 of 21 reached; 40 of 54 over all runs; no record

Builder-run on DEV (the open-record track). It licenses nothing; no record claim.
- **Script:** `scripts/b20r116_gset_attempt.py`, preregistered at `018dff2` (committed through the index while
  B20_R113 ran, before its result).
- **Run:** alone on CPU 0, on 23 Oct 2026, in two parts:
  - 20:19–21:03 SGT, 8 instances (G14–G29), until the container restarted mid-instance (G30, whose unfinished run
    left no row);
  - 21:05–22:12 SGT, resumed from G30. The study is resumable per instance with one seed per instance, so the
    interruption changes nothing but G30's start time.
- **Code identity:** `f67a43b5…`, the committed tree `018dff2`. B20_R117's files were committed through the index
  only and kept out of the working tree.
- **The other core.** While it ran, the builder recorded B20_R115 (documents, a 4 s record-test run, one worktree
  identity hash), and wrote and tested B20_R117's benchmark and B20_R118's design (unit tests of under a second each).

| File | What |
|---|---|
| `plan.json` | The 21 instances (computed at the start from B20_R106, R109, R110 and R113), their best earlier values, and the configuration per class |
| `rows.jsonl` | One 300 s run per instance: class, configuration, value with its witness cut (re-checked by the domain's two checkers), metered CPU, descriptor |
| `summary.json` | Instances reaching the best known value, gaps, gains over the best earlier value, record candidates, validity |
| `run.log` | Both parts |

**Configurations, by the preregistered rule:** B20_R105's 10 s choices for random and toroidal graphs (no torus was
left), and B20_R108's renormalisation configuration for planar graphs, because B20_R113's Part A was RENORM_BETTER.

## Result

- **7 of the 21 reach the best known value:** G19, G25, G29, G30, G37, G39, G52.
- **Over all of Genesis's recorded runs, its engine now reaches the 2012-13 best known values on 40 of the 54 Gset
  instances.** It exceeds none: **no record candidate.**
- The run improved on the best earlier Genesis value on 10 instances, matched it on 7 and was below it on 4.
  Mean fraction of the best known value: 0.99933.

| Instance | Class | Best known | 300 s | Best earlier |
|---|---|---|---|---|
| G14 | planar | 3,064 | 3,063 | 3,063 |
| G15 | planar | 3,050 | 3,049 | 3,049 |
| G19 | planar ±1 | 906 | **906** | 905 |
| G22 | random | 13,359 | 13,358 | 13,358 |
| G24 | random | 13,337 | 13,336 | 13,336 |
| G25 | random | 13,340 | **13,340** | 13,334 |
| G26 | random | 13,328 | 13,327 | 13,324 |
| G29 | random ±1 | 3,405 | **3,405** | 3,404 |
| G30 | random ±1 | 3,413 | **3,413** | 3,412 |
| G31 | random ±1 | 3,309 | 3,308 | 3,308 |
| G35 | planar | 7,686 | 7,675 | 7,685 |
| G36 | planar | 7,679 | 7,662 | 7,673 |
| G37 | planar | 7,690 | **7,690** | 7,686 |
| G38 | planar | 7,687 | 7,676 | 7,679 |
| G39 | planar ±1 | 2,408 | **2,408** | 2,406 |
| G41 | planar ±1 | 2,405 | 2,397 | 2,404 |
| G42 | planar ±1 | 2,481 | 2,472 | 2,472 |
| G51 | planar | 3,848 | 3,847 | 3,846 |
| G52 | planar | 3,851 | **3,851** | 3,849 |
| G53 | planar | 3,850 | 3,849 | 3,848 |
| G54 | planar | 3,852 | 3,851 | 3,851 |

Bold: at the best known value. "Best earlier" is the best of every earlier recorded Genesis run (several seeds and
budgets), so a single 300 s run can fall below it.

**Validity:** median metered CPU 1.00 of the 300 s budget; no failed run.

**The 14 still below** (best over all runs): one below on G14, G15, G22, G24, G26, G31, G35, G41, G51, G53 and G54;
further on G36 (6), G38 (8) and G42 (9), all 2,000-vertex planar instances.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| About a third of the remaining instances reach their best known value | 7 of 21, a third |
| Most of the random ones one or two below | 3 of 7 random instances reached; the other four are one below |
| Few of the larger planar ±1 ones | One of the three (G39) |
| No RECORD_CANDIDATE | None |

## What it means

- **Five minutes closes a third of what remained.** Most instances still below are one unit short.
- **On the 2,000-vertex planar instances, more time with this configuration is not reliably better.** Three of
  them (G35, G36, G41) ended 7–10 below B20_R113's 60 s runs, while G37 and G39 reached their best known values. One
  seed per instance and budget cannot separate time from luck here. The renormalisation configuration restarts every
  2,000 attractors, was chosen at 10 s, and may not be the right one at 300 s. A record attempt on these instances
  would need several seeds and a configuration chosen at the long budget.
- **The open-record track stands at 40 of 54 matched and none beaten** against the 2012-13 values. Beating a value
  would also need a check against the literature after 2013, which may have raised some of them.
