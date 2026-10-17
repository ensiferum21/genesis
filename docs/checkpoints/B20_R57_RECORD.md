# B20_R57 record: the transferred sum-free rows give certification utility on hosts hard for the conventional route

- **Built and run by:** the builder. DEV only; no claim.
- **Setup commit:** `a64952b` (script SHA-256 `df93867e…e1cf13`).
- **Evidence:** `evidence/sf_hard_certification_b20r57/`.

## Problem

B20_R56 found NO_CERTIFICATION_UTILITY on an unenriched sample. After the fact, the rows helped on hosts hard for
the conventional route. This study is the preregistered, hardness-enriched test, in the B20_R32 → R35 pattern.

## Implementation

A candidate-blind screen: route a alone for 20 s from the 10 s witness. It included 40 of 72 fresh candidates.
Both routes then ran 60 s each, as in B20_R56.
- **Primary verdict:** B20_R56's rule.
- **Secondary verdict, fixed in advance:** the certified upper bound at the budget.

## Result: **CERTIFICATION_UTILITY** and **BOUND_UTILITY**

- **Coverage.** c certified 22 and a 14, with 8/0 discordant (McNemar p 0.0039).
- **Time.** Wall saving +6.02 s per host [2.50, 9.88].
- **Bound.** The certified bound is lower by +6.875 [5.375, 8.475].
- **Soundness.** Everything is sound.
- **Search.** Median nodes fell from 520 to 121.

## Tests

`tests_genesis/test_sf_hard_certification.py` (4 design, 3 record).

## Consequence

GV6, second target. The procedure transfers (B20_R55). Its rows give a prospective, attributed certification
utility on the hosts where the conventional relaxation is the bottleneck (B20_R57), and none on an unenriched sample
(B20_R56). That is the same profile as C4 and as triangle-free (B20_R32 → R35). It survives Benjamini–Yekutieli at
q = 0.1 over 13 attempts.

## Open

B20R46-OPEN-1 and B20R35-OPEN-1 are updated. The reviewer's decisions stand: whether this target counts as
structurally different, and whether certification utility counts as "helps".
