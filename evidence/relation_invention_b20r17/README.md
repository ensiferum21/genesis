# B20_R17: a machine-generated representation outside the menu (s15.3, W10). Verdict: NO_UTILITY_AFTER_COST

- **Script:** `scripts/b20r17_relation_invention.py`. It was committed and pushed as `14c77be` before it ran; rules and verdicts are in its docstring.
- **Generator:** `src/genesis/invention/relations.py`.
- **Run:** 13 Oct 2026, 351 s, with nothing else running. DEV only; it licenses no claim.

## Part A: generation and checking (`package.json`, `part_a.json`)

The generator enumerated every non-empty oriented relation over k ≤ 3 classes (16 for k = 2, 512 for k = 3). It kept the exactly triangle-free-sound, inclusion-maximal ones, and reduced them to one representative per class-relabelling orbit after removing unused classes:

| Decoder | Relation (class of u → class of v, u < v) | Equals | Image (Lean) | Triangle-free soundness (Lean) |
|---|---|---|---|---|
| `rel2_0110` | 0→1, 1→0 | `cross_2` = `adjacent_2` | CHECKED | CHECKED |
| `rel3_01021020` | 0→1, 0→2, 1→0, 2→0 | `adjacent_3` | CHECKED | CHECKED |
| `rel3_011220` | 0→1, 1→2, 2→0 (the oriented 3-cycle) | **none: NEW** | CHECKED | CHECKED |

- **Semantics.** Every obligation is a Lean theorem over the repository definitions, checked with the pinned toolchain and allowed axioms only, through `formal_research.loop`. The builder-written recipe is `class-triple-decide`: a decided statement over Fin k triples, then instantiation.
- **Transport.** The image theorem says the decoder returns a subset of the host. The soundness theorem says it is triangle-free for every host and encoding. So every decoded encoding is a valid witness; repair keeps it valid, and the checker re-validates every witness.
- **Novelty against the menu.** `rel3_011220` reads the host orientation, which none of the four menu decoders' relations do after reduction. It is generated, not renamed.
- **Construction cost** (charged): 64.3 CPU s. The Lean checker's own cgroup report was 44.3 s; the larger value is charged.

## Part B: prospective DEV utility (`part_b.json`, `part_b_rows.json`, `hosts.json`)

- **Hosts:** fresh DEV hosts of B20_R13's S2 (erdos n30 p0.3) and S3 (erdos n40 p0.2), 8 SELECT and 16 EVAL per setting. Every triangle-free host named in the B20_R13–RX5 evidence, and every E1 host, was excluded.
- **Budget:** every arm had 1.0 CPU s per host (measured means 1.00, 1.00, 1.01). The matched arm had 1.64 s, which is 1.0 s plus the 64.3 s construction cost amortised over 100 hosts.

**SELECT totals** (16 hosts):

| Arm | Total |
|---|---|
| new `rel3_011220` | 1706 |
| menu `adjacent_3` | 1714 (chosen) |
| menu `cross_2` | 1712 |
| menu `adjacent_2` | 1712 |
| menu `ordered_2` | 1599 |
| `low_cycle_tm` | 1716 (chosen) |
| `multistart_tm` | 1686 |
| `exchange_tm` | 1662 |

**EVAL** (32 hosts; new minus the other arm, edges per host):

| Comparison | Mean | 90% interval | S2 / S3 | Wins / ties / losses | Passes (≥ 0.5, lower bound > 0) |
|---|---|---|---|---|---|
| new − menu (`adjacent_3`) | +0.19 | [−0.03, 0.44] | +0.06 / +0.31 | 7 / 21 / 4 | no |
| new − conventional (`low_cycle_tm`) | −0.03 | [−0.41, 0.34] | +0.81 / −0.88 | 9 / 9 / 14 | no |
| new − matched (menu with +0.64 s) | +0.16 | [−0.06, 0.41] | +0.06 / +0.25 | 6 / 22 / 4 | no |

## Reading

The acceptance in s15.3 has three parts:
- **Checked semantics:** met.
- **A valid decoder and transport path:** met.
- **Prospective utility after construction cost:** not met.

The generated decoder is about as good as the best menu decoder: most hosts tie, and the difference is well under the 0.5 minimum useful effect. It neither beats nor loses to the conventional time-matched baseline overall; that comparison differs by setting.

The result is preserved as NO_UTILITY_AFTER_COST. Under the declared policy, relational decoders at k ≤ 3 are retired as a source of utility on these settings. Any next family (for example a versioned k ≤ 4 expansion, partitions/quotients, or decompositions) is a new, separately preregistered step, and every attempt counts.
