# B20_R42 record: registry v2 and the generated-rows reference wired into the custodian path (opt-in; built for review, not adopted)

- **Run by:** the builder. This is engineering only, with no study and no new hosts. Nothing is
  adopted.
  - No adopted rule, config entry, frozen package or descriptor id changes.
  - Requests v3 and v4 and every receipt schema keep their meaning.
- **Commit:** the B20_R42 commit.

## Why

B20_R41 found E1d READY_FOR_REVIEW: E1's frozen candidate beats an exact MIP given four times its
budget, on calibrated dense planted settings scored by the generated-rows reference. A real run,
or even a same-operator rehearsal, needs the custodian to do three things:
1. run a registry-v2 MIP baseline;
2. select it as a comparator on its SELECT panel;
3. score with the generated-rows reference and keep its certificates in custody.

B20_R39 and B20_R40 built these pieces without wiring them. This step wires them in, opt-in only,
so that the reviewer's choice is to adopt or decline reviewed code, not to commission new code.

## What changed

**`src/genesis/candidate_registry.py` (new).** One entry point for both registries, chosen by the
descriptor's schema.
- A v1 descriptor takes exactly the v1 path.
- The exact-baseline policy: `EXACT_BASELINE_KINDS` is `milp-highs-v1`. It applies only under a
  rule listed in `EXACT_BASELINES_BY_RULE`, today the DRAFT `e1-hard-v3-draft` alone.

**`kernel/receipts.py`.** Adds `REQUEST_V5`, a v4 request plus a closed `reference` field. Its
receipt stays scientific receipt v4, which binds the request, route included, by hash.

**`custodian.py`:**
- **v5 validation.** Arms through the dispatcher, and the route checked by `reference_problems`:
  a closed route name, a known and intact theory package by digest, and bounded limits.
- **Evaluation.** Arms run through the dispatcher.
- **Reference.** `reference_options` asks for the named route, and refuses a domain that cannot
  honour it.
- **Comparator selection.** `select_comparator` accepts an exact v2 baseline only under a rule that
  names it. The calibration is now loaded before the baselines are checked.

**`domains.py`.** The triangle-free adapter offers the generated-rows reference
(`_rows_reference`), with the custody bundle persisted into the evaluation's evidence store. The C4
adapter refuses it. Small hosts keep exact search.

**`discovery/generated_certify.py`:**
- `known_package(digest)`, which checks the package's integrity and that its rows derive from
  CHECKED statements only;
- `reference_record`, the reference with its bundle unwritten. `reference` is unchanged in
  behaviour.

**`calibration.py`.** Adds `SELECTION_RULE_E1_HARD_V3_DRAFT`, equal to B20_R41's rule (checked by a
test), in `DRAFT_RULES_BY_NAME`, so that `record_problems` can check a record that uses it.
- It is **not** in `RULES` or `RULES_BY_NAME`.
- Using it needs a study adoption in `configs/dev_calibration.json`, which is the reviewer's
  decision.

**`cli.py`.** `descriptor_request_bundle(..., reference=...)` freezes a v5 request.

**Unchanged on purpose:** `candidates.py`, `candidates_v2.py` and `candidate_kinds/milp_highs.py`.
Their text is part of descriptor identities. So the frozen E1/E1b ids and the B20_R41 MIP ids are
kept.

## Tests

`tests_genesis/test_wiring_v5.py` (11).

**Dispatcher:**
- v1 descriptors take the v1 path, with identical problems;
- v2 descriptors take the v2 path;
- unknown descriptors, and a context passed to v2, are refused;
- the exact-baseline policy holds per rule.

**Schema:**
- v5 takes v2 arms, and v4 still does not;
- a v4 request with a `reference` field, or a v5 request without one, is refused;
- the route is closed: twelve kinds of bad route are refused;
- reference options follow the request version, and the C4 adapter refuses the route;
- the draft rule checks records but is not adopted, and it equals B20_R41's rule.

**Reference:**
- on K8, the rows reference gives 16, with a bundle that replays checker-only;
- small hosts keep exact search;
- C4 and an unknown package are UNSUPPORTED.

**End to end** (fixture keys, synthetic calibration record):
- under the adopted rule `e1-hard-v2`, the custodian refuses the MIP as a comparator;
- under the draft rule, it selects among the DSL and MIP baselines;
- registration refuses a v4 request with a v2 arm;
- a v5 evaluation runs the v2 arm in runc, with 6 optima by the rows route and their bundles in
  custody. The judge agrees, and there is no second draw.

**Regression:** the full `tests_genesis` suite passes with the change.

## Open

**B20R40-OPEN-1 and B20R35-OPEN-1** are updated: the wiring exists, opt-in. Adopting it is the
reviewer's decision, together with B20R41-OPEN-1. That means:
- the rule `e1-hard-v3-draft`;
- a study adoption;
- the package;
- the checker identities;
- the MIP as a comparator.

**Next:** an E1d DRAFT package and a same-operator rehearsal through this path, in a throwaway
copy where the draft rule is adopted for the rehearsal only.
