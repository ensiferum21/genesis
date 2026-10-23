# B20_R112 evidence: the inventor under contract v2: NOT_DEMONSTRATED; the judge released nothing

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r112_inventor_v2.py`, preregistered at `dd55c33`, committed through the index while
  B20_R108 ran.
- **Run:** alone on CPU 0, 912 s, on 23 Oct 2026 (18:26–18:41 SGT). `code_identity` `ba029f9f…`, the committed tree
  `dd55c33` (as B20_R111). B20_R113's files were kept out of the working tree.
- **The other core.** While it ran, the builder recorded B20_R111 (documents, one test run of a second).

| File | What |
|---|---|
| `hosts.json` | 12 fresh large hosts, 3 per cell, split by cell into A, B and C (4 each) |
| `references.json` | tfxw's value at 2 s on each host: the yardstick values are divided by |
| `trace.jsonl` | All 400 split evaluations of the search: split, normalised value, program digest |
| `summary.json` | The search's report (generations, evaluations, the judge's tau, releases), the program, its signature, the invention test and the verdict |
| `run.log` | The run |

## Result: NOT_DEMONSTRATED

**The search.**
- It ran 30 generations over 256 distinct programs and used all 400 split evaluations, so the patience stop was
  never reached.
- The judge's threshold, set from B − C differences over 4-host splits, was **0.028 of the reference value** (about
  2.8%). The judge received 19 submissions and **released none**.
- The best program on the worker's own data scored 0.9955 of the reference. The start program's confirmation score
  was 0.9945, and the best confirmation score of any submission was 0.9954. So the improvements were about 0.1%,
  far inside the judge's noise.
- The reported program is therefore the start program, `[descent, init]` on the `adjacent_3` representation:
  multistart descent, a reduced form of the T1 template (and of T5's statement kinds).

**The invention test** (B20_R111's held-out hosts, 2 s, against the prior-art champion T4):
- **5–18 (1 tie), p = 0.011: BEHIND_PRIOR_ART.**
- Mean 4,219.7 against 4,229.5.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| NOT_DEMONSTRATED | NOT_DEMONSTRATED |
| The contract releases one to three improvements and stops early | It released none and did not stop early. The judge's noise with 4 hosts per split (about 2.8% of the value) is larger than any difference between programs here (about 0.1–1%) |
| The program found is an annealing or plateau-search variant, NOT_DISTINGUISHABLE from or BEHIND the champion | Multistart descent; BEHIND |

## What it means

- **The improved judge was honest.** It would not certify differences of 0.1% that it could not tell from host
  noise. Without the contract, the same search would have reported its best training score as progress
  (B20_R103).
- **Honesty with 4-host confirmations costs all the power at this effect size.** Program differences in this language
  on these hosts are about the size of one host set's quirk, so the judge needs many more confirmation hosts, or
  programs that differ more.
- **Together with B20_R111:** neither the existing programs nor a fresh, contract-disciplined search produce
  anything better than a tuned annealing-then-descent written in the same language. The limit is the language and
  the effect sizes it allows, not the honesty of the search.
- **Next, for invention:** a richer language (moves at the scale the evidence points to: coarse-grained and cluster
  moves), and confirmation data sized to the effects sought.
