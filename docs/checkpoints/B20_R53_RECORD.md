# B20_R53 record: research-selection headroom on Wolfram's axiom at the hard settings (design pilot)

- **Built and run by:** the builder. DEV only; a design diagnostic with no claim.
- **Parent:** B20_R52 (`5e5ebd5`).
- **Setup commit:** `45ed113` (script SHA-256 `9349eea3…1dd72`).
- **Evidence:** `evidence/wolfram_headroom_b20r53/` (README, four seed files, summary, log).
- **Concurrency:** it ran on core 0 while checkpoint B20_R52's release matrix ran on core 1.

## Problem

GV4, and the equational target of GV6, need a setting where *which* research the system does changes the
successor (B20R9-OPEN-1; `handoff/gv6/README.md`, target 2).
- **Earlier pilots.** B20_R3, R6 and R9 found none on eight equational systems with 1 s attempts.
- **The open cell.** Wolfram's single axiom was at the floor there, and research is known to matter on it at
  B20's hard settings (10 s attempts; 0 → 8–12 of 15). Its selection headroom at those settings had never been
  measured.

## Implementation

`scripts/b20r53_wolfram_headroom.py` uses B20's hard rules unchanged, on fresh seeds 5301–5304.

**Libraries**, each evaluated on 15 targets:
- EMPTY;
- EXHAUST;
- ORACLE (optimistic);
- per cap (60 and 30 CPU-s): FIXED@cap, B20_R3's ORACLE@cap, and a descriptive GAP@cap;
- a REPEAT evaluation, to measure noise.

**GAP** is the GV6 draft's mapping of the transferred keep rule: keep a true conjecture only if E with the kept
lemmas cannot prove it in 1 s, then prove it in 10 s.

**Verdict rule**, fixed in the script: SELECTION_HEADROOM, WEAK_HEADROOM or NO_HEADROOM.

## Result: **NO_HEADROOM**

- **Selection headroom.** ORACLE@cap − FIXED@cap is 1, 0, 1, 0 at both caps, and the noise is 0.
- **Why the caps did not bind.** The fixed policy proves the whole pool (88–89 true equations) in 4.9–9.1 CPU-s:
  after the first, hard lemma, everything else takes milliseconds.
- **Research still matters.** EXHAUST − EMPTY is 11, 7, 11, 11.
- **The ceiling is the limit.** 3–8 of the 15 targets are proved by no pool library.

**GAP (descriptive).**
- **Kept.** 1–3 lemmas: commutativity on two seeds; s(s(X,X),s(X,X)) = X and two 4-node equations on the
  other two.
- **Score.** It equals ORACLE on every seed (12, 7, 13, 11) with about 2% of the oracle's library.
- **Against FIXED.** GAP − FIXED is +1, 0, +1, 0.
- **Cost.** Its research cost 16.5–29.5 CPU-s against FIXED's 4.9–9.1 s.

## Tests

`tests_genesis/test_wolfram_headroom.py` (9 tests: 6 design, 3 record):
- the verdict recomputes from the seed files;
- the material is what the script derives;
- the GAP lemmas are true;
- the caps did not bind.

## Limitations

- One prover, at 3 s per evaluation target and 8 premises.
- Pools of up to 5 nodes.
- 4 seeds, 15 targets each.
- The ORACLE is built from the evaluation targets themselves.
- It ran concurrently with the release matrix on the other core. The repeat evaluation found no noise.

## Consequence

- **No selection headroom on any of nine systems.** Wolfram at the hard settings joins the eight systems of
  B20_R3/R6/R9: choosing which pool lemmas to prove or keep has at most 1 of 15 headroom.
- **For GV4 (B20R9-OPEN-1).** GV4 still cannot be answered positively on this domain at pool scale.
- **For GV6.** The equational target can show transfer only if the transferred procedure reaches beyond the
  pool, into the ceiling. The keep rule's compression (1–3 lemmas, with no loss) suggests it could screen much
  larger conjecture sets cheaply. That is the question for B20_R54.

## Open

B20R9-OPEN-1 is updated: Wolfram at the hard settings has NO_HEADROOM for selection, and the ceiling is the limit.
