# Genesis Ω: capability graph and reactivation policy (master implementation contract §8, §18)

The graph lives in the vault: edges between artifacts, or from an artifact to a tag naming a prerequisite or
capability.

**Triggers.** A CapabilityRecord artifact declares what it `unlocks` (tags). It becomes a trigger once it is
`verified`, which needs an EvidenceRecord naming a recorded study and its record test.

**Opportunities** (`Vault.opportunities(trigger, fuel)`):
- The candidates are artifacts that are currently `dormant` and have a `failed_due_to` edge to a tag the trigger
  unlocks.
- They are ranked by the edge's stored score (ties by ID), and at most `fuel` are returned.
- An artifact already `reactivated_by` this trigger is excluded: an unchanged condition is never retried.

**Reactivation** (`Vault.reactivate`):
- It sets the artifact to `exploratory` and adds a `reactivated_by` edge.
- The re-test result is annotated by the caller. Reproducible results lead on to `verified` only through evidence.
- A failed reactivation stays archived with its updated reason.

**Cascades** (`Vault.cascade(triggers, retest, fuel, depth)`):
- Breadth-first.
- A trigger runs once (seen set).
- At most `fuel` artifacts per trigger and `depth` levels.
- New capabilities produced by re-tests enqueue as further triggers.

**Controls, required for any claim that reactivation adds value:**
- a null trigger, which unlocks nothing and must reactivate nothing;
- random retrieval from the archive at the same fuel;
- a fresh search at the same compute;
- no reactivation.

The value measured is verified quality per total compute, never the number of nodes generated.

**The first real test is B20_R131** (preregistered `22385f7`):
- B20_R129's ~1,300 evaluated acquisition rules are archived as dormant, with an inferred `failed_due_to →
  tag:interpretation` edge (confidence 0.5).
- If B20_R130 verifies the global interpretation, it is the trigger.
- Reactivated rules are compared with a fresh search, random retrieval and the null trigger, on 200 fresh worlds.
