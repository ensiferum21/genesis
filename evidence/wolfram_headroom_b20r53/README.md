# B20_R53: research-selection headroom on Wolfram's axiom at the hard settings (design pilot, DEV)

- **Script:** `scripts/b20r53_wolfram_headroom.py`, preregistered in commit `45ed113`.
  SHA-256 `9349eea3196201cce7df74520490e71065f69f244ae8e5edfb2b1b991c41dd72`.
- **Run:** the builder, pinned to one core, 1,046 s in all. Checkpoint B20_R52 ran on the other core at the same
  time.
- **Status:** a design diagnostic. It licenses no claim and adopts nothing.

## Question

GV4 and the equational target of GV6 both need a setting where *which* research the system does changes the
successor. B20_R3, R6 and R9 found no such setting on eight equational systems with 1 s attempts. Wolfram's
single axiom sat at the floor there.

B20's hard follow-up showed that research matters on Wolfram's axiom with 10 s attempts: 60 s takes the successor
from 0 to 8–12 of 15. Selection headroom at those settings had never been measured.

## Result: **NO_HEADROOM**

Targets proved, of 15:

| Seed | EMPTY | EXHAUST | ORACLE | FIXED@60 | ORACLE@60 | GAP@60 | FIXED@30 | ORACLE@30 | GAP@30 | REPEAT |
|---|---|---|---|---|---|---|---|---|---|---|
| 5301 | 0 | 11 | 12 | 11 | 12 | 12 | 11 | 12 | 12 | 11 |
| 5302 | 0 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| 5303 | 1 | 12 | 13 | 12 | 13 | 13 | 12 | 13 | 13 | 12 |
| 5304 | 0 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |

- **Selection headroom.** ORACLE@cap − FIXED@cap is 1, 0, 1, 0 at both caps, mean 0.5. The rule needs a mean of
  at least 2. Evaluation noise (FIXED@60 against its repeat) was 0 on every seed.
- **Library headroom.** Research matters: EXHAUST − EMPTY is 11, 7, 11, 11.
- **Ceiling.** No library built from the pool proves 3–8 of the 15 targets (15 − EXHAUST is 4, 8, 3, 4).

## Why the caps did not bind

The fixed policy proved all 88–89 true pool equations in 4.9–9.1 CPU-s, well under the 30 and 60 s caps.
- **Easy pool after one key lemma.** After its first, hard lemma (7.8 s for commutativity on seeds 5301 and
  5304), every other pool equation is proved in milliseconds.
- **Different from B20's hard runs.** There a budget of 4.23 s was spent on that first conjecture. B20's 240 s
  attempt exhausted the pool.

The preregistered caps followed B20's 60 s research budget. They turned out to be non-binding, and FIXED@cap
equals EXHAUST on every seed.

## The GAP arm (descriptive)

GAP is the GV6 draft's mapping of the transferred keep rule: keep a true conjecture only if E with the lemmas kept
so far cannot prove it in 1 s; then prove it with 10 s.
- **Kept lemmas.** It kept 1–3 lemmas. On seeds 5301 and 5304 it kept commutativity, s(X,Y) = s(Y,X). On 5302
  and 5303 it kept s(s(X,X),s(X,X)) = X and two 4-node equations (sizes count operation nodes).
- **Discarded.** Every other true pool equation, 86–88 of them, was cheaply derivable.
- **Score.** GAP equals ORACLE on every seed: 12, 7, 13 and 11. ORACLE used 50–64 lemmas; GAP used 1–3, and
  FIXED 88–89.
- **Against FIXED.** GAP − FIXED is +1, 0, +1, 0.
- **Cost.** GAP's research cost 16.5–29.5 CPU-s against FIXED's 4.9–9.1 s: the cheap checks, plus the full
  attempt after each failed check.
- **Interpretation.** The keep rule compresses the library to its essential lemmas, about 2% of the oracle's
  size, with no loss. It cannot gain more than the selection headroom, and the headroom is at most 1 of 15.

## Consequence

This adds a ninth system to B20_R3/R6/R9's equational headroom pilots, and the first at hard settings. Choosing
which pool lemmas to prove or keep has at most 1 of 15 headroom here too.
- **What limits the successor.** The limit is the ceiling: targets that no pool library proves. Selection is not
  the limit.
- **Equational GV6 target.** A transferred procedure can matter here only if it reaches beyond the pool's
  lemmas, for example larger conjectures that the keep rule screens cheaply. That is the next design question
  (B20_R54).

## Files

- `seed_<n>.json`: the material (pool, development and evaluation statements, all now exposed), the libraries,
  per-target statuses, GAP's trajectory, and the exhaust outcomes.
- `summary.json`: the verdict and table.
- `run.log`: the log.

## Tests

`tests_genesis/test_wolfram_headroom.py` has 9 tests. The design tests check:
- the rules are B20's;
- the seeds are fresh and the material disjoint;
- ORACLE@cap is B20_R3's;
- the GAP arm's keep rule and its charging;
- the verdict rule.

The record tests check:
- the verdict recomputes from the seed files;
- the material is what the script derives;
- the GAP lemmas are true;
- the caps did not bind.
