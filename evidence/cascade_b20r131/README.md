# B20_R131: the cascade on a real case (DEV; NO_VERIFIED_TRIGGER)

Preregistered at `22385f7` (`scripts/b20r131_cascade.py`); run alone on CPU 0 from a clean worktree of `68e24c0`,
24 Oct 2026, 20:32:54-20:49:13 SGT (16 min). Record test: `tests_genesis/test_cascade_study.py::RecordB20R131`.

**Verdict: NO_VERIFIED_TRIGGER, by the preregistered protocol.** B20_R130 did not show the global interpretation
better (T_interpretation NO_DIFFERENCE), so the "global interpretation" CapabilityRecord was never verified, no rule
was reactivated, and the primary test (reactivated against fresh) was not run. The null trigger and the comparators
ran as registered.

| Arm (24 evaluations each) | Winner | Test mean (200 fresh worlds; F1 at 4 and 8) | CPU |
|---|---|---|---|
| fresh search (seeded with eig, dec, hybrid, decf, decfall) | `sum decfall` (its own seed) | 0.4959 | 149.8 s |
| random retrieval from the archive | `sum sqrt(decfall)·pf²·min(pf,1)²` | 0.5023 | 75.4 s |
| null trigger (B20_R129's scientist, unchanged) | `sum decfall` | 0.4959 | 0 |
| eig (reference) | eig | 0.4498 | 0 |

**Overhead (directive item 3).**
- The archive: B20_R129's four searches replayed exactly (every winner and judged score reproduced), and 1,310
  distinct rules from 1,968 evaluations stored dormant, each with an inferred `failed_due_to` edge. This took
  158.9 s of CPU, once.
- Reactivation cost nothing here, because no reactivation took place.
- The vault: 1,314 artifacts and 6,558 events, LOCAL_HASH_CHECKED, packed as `vault.tar.xz`. The record restores
  and verifies it.

**Exploratory (not preregistered; descriptive).** These are paired Wilcoxon tests on the test worlds:
- random retrieval against fresh search: NO_DIFFERENCE (p 0.38, 55 non-zero differences);
- fresh, null and random each beat eig (p 1.9e-5, 1.9e-5 and 9.1e-6).

The fresh search found nothing better than its best seed in 24 evaluations.

**What it means.**
- A capability that is not verified cannot be a trigger: the gate held.
- Nothing is learned about the cascade's value, because the trigger condition never occurred.
- The architecture lesson is recorded in `docs/OMEGA_ARCHITECTURE_INVENTION.md` §1.1 and §11: reactivation is an
  intervention with controls, never assumed causal.

**Limitation found.** `Vault.opportunities` does not itself check that its trigger is verified. In this study, the
gate is the study's own check on B20_R130's verdict. The CapabilityRecord contract is stated in
`docs/OMEGA_CAPABILITY_GRAPH.md`; enforcing it inside the vault is an open engineering item.

Status: DEV; licenses nothing.
