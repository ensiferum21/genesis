# B20_R25 record: ground-hint generator v2 for the Lean replay of E proofs, paired against v1

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim.
- **Commits:** `db73275` (setup: code, tests and script, committed before the run; the script's
  SHA-256 was sent to the user beforehand, because GitHub was not linked) and the result commit
  that follows it.
- **Evidence:** `evidence/hint_ab_b20r25/` (see its README).

## Why

`fof_lean.replay` checks an E proof object in Lean, one inference at a time. Each step gets ground
instances of its parents ("hints"), and `grind` closes it. On Wolfram's single axiom, many steps
have the form rw(…rw(spm(A, B), C)…), often with ordered rewriting by a derived commutativity
law. The v1 generator found no instances for them.

The work was done on a side branch built on plain B20 while the R-line was elsewhere
(`side-b21-equational`, `710d26d`, kept in the history bundle and not canonical). There, the
repair took a Lean bridge from 0/11 to 11/11 replays, but on regenerated libraries. This batch
ports the repair and pairs the comparison.

## What changed

- **`fof_lean.HINT_VERSIONS = ('v1', 'v2')`, with `HINTS = 'v2'` the default.** v1 (`_overlaps_v1`,
  `_ground_hints_v1`) is the generator as it ran up to B20_R24, kept verbatim. v2 adds four
  things:
  - superposition results matched to the conclusion;
  - those results rewritten towards a normal form under the other parents, by size-decreasing
    rules with matching modulo a commutativity parent (`_rules`, `_commutative`, `_match_c`,
    `_rewrite_path`);
  - the rule and commutativity instances used, handed to Lean;
  - matched overlaps seeded before blind enumeration.
- **Replay records carry the hint version** (`hints`).
- **Soundness is unchanged.** Hints are only instances handed to Lean, which checks every step:
  a wrong hint can make a step fail, never make a false step pass.
- **Implementation identities are unchanged.** No candidate kind's implementation identity
  includes `fof_lean.py`, so no frozen descriptor changes.

## Result (DEV, identical proof objects)

| System | Chains | v1 checked | v2 checked | v2 only | v1 only |
|---|---|---|---|---|---|
| Wolfram's single axiom (2 seeds) | 19 (22–43 lemmas) | 0 | **19** | 19 | 0 |
| Sheffer's basis (regression check) | 11 (1–14 lemmas) | 11 | 11 | 0 | 0 |

Under v1, 18 Wolfram chains failed with ELABORATION_ERROR and one with RESOURCE_LIMIT. Mean
Lean time per Wolfram chain fell from 46.0 s to 17.5 s.

## Tests

`tests_formal/test_hint_versions.py`:
- the versions and their default;
- v2 finds hints that v1 misses on a real failing step;
- v2's hints really are refuting instances (congruence closure);
- commutativity matching records its swaps;
- rewrite rules are size-decreasing;
- the evidence contract.

The suites that replay E proofs in Lean (`test_ghost_census`, `test_learning`) pass under the v2
default.

## Open

B20R25-OPEN-1: v2 is heuristic, with no completeness guarantee. It was measured on two
equational systems with one research policy.
