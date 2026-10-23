# B20_R111 evidence: the invention test: NOT_DEMONSTRATED

Builder-run on DEV (Daniel's request of 23 Oct 2026: "Genesis autonomously invented a fundamentally new algorithm —
not yet demonstrated; test this too"). It licenses nothing.
- **Script:** `scripts/b20r111_invention_test.py`, preregistered at `962f947`, committed through the index while
  B20_R108 ran.
- **Run:** alone on CPU 0, 1,810 s, on 23 Oct 2026 (17:56–18:26 SGT). `code_identity` `ba029f9f…`, the committed tree
  `dd55c33`. B20_R113's files were kept out of the working tree.
- **The other core.** While it ran, the builder recorded B20_R110 (documents, one test run of a second). It also
  wrote B20_R113's design and ran a 31 s check that B20_R113's graphs generate, which is possible cache contention for
  the in-process program runs.

| File | What |
|---|---|
| `hosts.json` | 32 fresh hosts of `triangle_free_large_v1`, 8 per cell (planted clusters and G(n, 0.5) at n = 128 and 256): 8 for tuning, 24 held out |
| `runs.jsonl` | Every run: 68 template variants on the tuning hosts; 8 tuned templates, 4 candidates and 2 builder engines on the held-out hosts |
| `summary.json` | Tuning scores, the tuned variants, the champion, the four tests, the verdict, held-out values and means, the candidates' SHA-256, the templates' signatures |
| `run.log` | The run |

## Result: NOT_DEMONSTRATED

**Prior art, tuned on 8 hosts.** Each template's best variant, with its mean gap below the best of all variants:

| Template | Best variant | Gap |
|---|---|---|
| **T4 annealing then descent (the champion)** | cross_2, 75% annealing | **0.11%** |
| T2 iterated local search | adjacent_2, kick 10 | 0.32% |
| T5 restarted annealing | cross_2 | 0.33% |
| T3 annealing | cross_2 | 0.33% |
| T1 multistart descent | cross_2 | 0.40% |
| T8 annealing, then plateau search | cross_2 | 0.79% |
| T7 forced-edge iterated local search | cross_2 | 1.14% |
| T6 plateau search | cross_2 | 1.40% |

**Test 1: the system's own programs against the prior-art champion** (24 held-out hosts, 2 s, alpha 0.05 / 4):

| Candidate | Wins–losses (ties) | p | Label |
|---|---|---|---|
| gen1 (B20_R79) | 6–14 (4) | 0.12 | NOT_DISTINGUISHABLE |
| gen2 (B20_R83) | 7–12 (5) | 0.36 | NOT_DISTINGUISHABLE |
| gen3 (B20_R85) | 4–17 (3) | 0.007 | **BEHIND_PRIOR_ART** |
| control (B20_R84) | 9–13 (2) | 0.52 | NOT_DISTINGUISHABLE |

No candidate beats prior art, so Test 2 (the core) did not run.

**Held-out means** (edges kept, 24 hosts):
- the builder's tfxw: 4,239.1;
- **T4: 4,229.5**;
- T3 4,228.0, the builder's hybrid-swap 4,227.7, T2 4,227.5;
- gen3 4,225.3, gen2 4,225.0, control 4,222.6;
- T5 4,219.8, gen1 4,219.8, T1 4,219.6;
- T8 4,199.0, T6 4,189.9, T7 4,184.7.

**Validity:** median CPU 1.00 of the budget for every program arm; 1.11 for tfxw (runc start-up metered); no invalid
edge set.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| NOT_DEMONSTRATED | NOT_DEMONSTRATED |
| T4/T8-like templates NOT_DISTINGUISHABLE from the candidates or ahead | T4, the champion, is ahead of every candidate on average. Three candidates are NOT_DISTINGUISHABLE; gen3 is BEHIND |
| All far behind the builder's tfxw | Yes: about 10 edges on average |

## What it means

- **The claim is not demonstrated.** The best of the system's autonomously found programs is not better than
  annealing followed by descent, a 1983-era recipe written in the same language and tuned with modest effort. One of
  them (generation 3) is worse.
- **This agrees with what came before.** Random programs of the language did as well as the search (B20_R80, R81).
  The generations do not compound (B20_R86). Where the strongest search stops, nothing local is left (B20_R99).
- **What the test now provides.** A standing bar any future invention claim must clear: preregistered prior art in
  the same language, equal tuning, held-out hosts, a significant win, and a core no template has, reviewed against
  the literature before anything is claimed. B20_R112 holds a fresh search, run under the improved feedback
  contract, to the same bar.
