# B20_R25 evidence: ground-hint generator v1 vs v2 on identical E proof objects (DEV)

Builder-run engineering comparison. Nothing here is independently reviewed, and it licenses no
claim. Script: `scripts/b20r25_hint_ab.py`, committed before running in `db73275`. Its SHA-256
was sent to the user beforehand. Log: `run.log`, 1,490 s.

## What was compared

`fof_lean` hands Lean ground instances ("hints") for each E inference step, and Lean then
checks the step.
- **v1** is the generator as it ran up to B20_R24. It is kept verbatim.
- **v2** was ported from the B21 side branch. It matches superposition results to the
  conclusion after rewriting them towards a normal form under the other parents, matching
  modulo a commutativity parent. It hands the rule and commutativity instances to Lean, and it
  seeds matched overlaps first.

Hints are only instances given to Lean. A wrong hint can make a step fail, never make a false
step pass.

Each successor proof that used library lemmas was replayed twice, with its whole lemma chain:
once under v1 and once under v2, on the **same proof object**.

## Material

| System | Seed | Research | Library | Successor (of 15) | Chains replayed | Chain length |
|---|---|---|---|---|---|---|
| Wolfram's single axiom | 2026251 | 60 CPU s, fixed policy | 89 | 9 | 9 | 22–43 lemmas |
| Wolfram's single axiom | 2026252 | 60 CPU s, fixed policy | 88 | 10 | 10 | |
| Sheffer's basis (regression check) | 2026253 | 10 CPU s | 28 | 11 | 11 | 1–14 lemmas |

## Result

| System | Attempted | v1 THEOREM_CHECKED | v2 THEOREM_CHECKED | Paired: both / v2 only / v1 only / neither |
|---|---|---|---|---|
| Wolfram | 19 | **0** | **19** | 0 / 19 / 0 / 0 |
| Sheffer | 11 | 11 | 11 | 11 / 0 / 0 / 0 |

- **Wolfram.** Under v1, 18 replays failed with ELABORATION_ERROR (a step without hints that
  `grind` could not close) and one with RESOURCE_LIMIT. Under v2, all 19 check. Mean Lean time
  per chain was 46.0 s with v1 and 17.5 s with v2.
- **Regressions.** v2 has none: every Sheffer replay checks under both versions.
- **This pairs the B21 side-branch observation.** There, the bridge went from 0/11 to 11/11 on
  regenerated libraries. Here the comparison is on identical proof objects.

## Limits

- **Systems.** Two equational systems, on proofs from one research policy.
- **Theory.** v2 has no completeness guarantee: hint generation stays heuristic.
- **Default.** v2 is the default from this batch on. Earlier evidence keeps the hint version it
  ran with: replays recorded before this batch carry no `hints` field and ran v1.
