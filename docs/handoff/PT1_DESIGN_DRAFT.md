# PT-1 (B20_R159): the proving test, a design draft (NOT preregistered)

Written 28 Oct 2026, 01:25 SGT, for whoever preregisters PT-1 after F1–F5 have run (`docs/OMEGA_FRONTIER.md` §7b).
Nothing here has been run on family A or family B. It records what is built, what was decided, and what remains to
be decided, so that the preregistration can be written from it.

## What is decided

- **Daniel, 27 Oct 2026, 20:22 (the test):** five parts, scored separately; PROVED_OUT only if all five pass.
- **Daniel, 28 Oct 2026, 00:53 (part 1's mechanisms):** "Do the hardest so it proves it can find its way."
  - Only the two mechanisms that hand over nothing are allowed:
    - library learning over Γ (`conjecture/library.py`);
    - operators acting on Γ's own operations (`conjecture/operations.py`, the engine's `derive`).
  - Low-level block primitives and the repeated-row compressor are excluded. They may run afterwards only as
    labelled diagnostics and never count.

## What is built (all on `continuation-b20-rx`)

| Piece | Where |
|---|---|
| Family A: Laplacian bounds 18, 21, 24, 30 and 40, held out of F4 and F5 | `conjecture/sealed.py` (`PROVING_TEST_HOLDOUT`) |
| Family B: all 63 Graffiti statements (29 proved, 25 disproved, 9 open), posed as text | kernel side `conjecture/wowii.py` (evaluators, `TEXT`, `COUNTEREXAMPLES`, `verifier`); research plane `conjecture/statement.py`, `invariant_domain.py` |
| B's double kernel check | `invariants.py` (research plane) and `invariants_ref.py` (kernel side, no shared code); `wowii.verifier` needs both |
| Part 1's mechanisms | `conjecture/library.py`, `conjecture/operations.py`, `ConjectureDomain.learn` / `derive`, `Frontier.derive`, `FrontierPolicy` `p_derive` |
| Part 3: procedures from the engine's own log, including derivation lineages | `frontier/procedure.py` (`extract`) |
| Part 5's improved inventor | `frontier/procedure.py` (`ProcedurePolicy`) |
| The forbidden-concept audit | `conjecture/audit.py` |
| The engine's meta level (not part of PT-1, but available) | `frontier/meta.py` |

## A proposed design (to be argued over and fixed at preregistration)

**Arms.**
- **P0, the predecessor.** The Frontier's allocation with the starting representations only: no abstraction, no
  library learning, no derivation (`p_derive` 0).
- **G, Genesis.** The Frontier with abstraction (templates, then library learning) and derivation on (`p_derive`
  fixed in advance, for example 0.2, not tuned on A or B).
- Both run at the same total compute. The CPU and the evaluations are both reported.

**The inadequacy gate (on A, first).** P0 at the full budget certifies nothing in A. If it certifies something, A
is not unfamiliar: the test stops as INADEQUACY_GATE_FAILED and needs another family. It does not count as a pass.

**Part 1, a useful new representation (on A).** G creates a representation during its run (a derived operation set
or a library) that is absent from the starting set.
- *Useful* is decided by an ablation inside the run's budget: re-running G's best branch's method with and without
  that representation, at matched compute, must give certificates in A that the starting representations do not.
- The report names which mechanism produced it: the derivation lineage, or the library's pieces.

**Part 2, a nontrivial consequence (on A).**
- At least one exact refutation certificate for a bound in A that P0 did not refute, double checked:
  - Sturm up to n = 40;
  - the independent matrix-form check above that.
- The certificate is compared with the published counterexamples. A rediscovery counts for the test but is labelled.

**Part 3, the procedure.** `procedure.extract` on G's log, for the discovery of part 2. It must:
- name no problem and no representation it made;
- replay on A and reproduce the discovery.

**Part 4, independent use in B.**
- *The improved inventor:* `ProcedurePolicy` with the part 3 procedure, on B's 25 disproved and 9 open statements
  posed as text. It is given no B-specific change.
- *Its predecessor:* the same Frontier without the procedure, at matched compute.
- *Pass:* an exact certificate (`wowii.verifier`: both implementations) that the predecessor does not get.
- *Open statements:* a violation of an open statement would be a new result, and is reported as such after the
  double check.

**Part 5, the improved inventor beats its predecessor (on C).**
- C is fresh sealed tasks, chosen by the kernel and never seen. Candidates:
  - generated conjectures from F5's generator, on a new seed;
  - AutoGraphiX adjacency-spectrum conjectures, once transcribed.
- At matched TOTAL compute: the improved arm is charged the cost of discovering the procedure in A.
- Test: a paired one-sided test over tasks, with Holm across the test's claims.

**Validity.**
- The forbidden-concept audit of every research-plane module the test runs, and of the manifest's text.
- The NHP boundary tests and the relabelling audit.
- No certificate against a proved statement or bound. One would mean a transcription or verifier error, and makes
  the run INVALID.
- Pins at preregistration.

## Still open (decide before preregistering)

1. Budgets for each part (F4's timings give the scale: about 100,000 evaluations per bound).
2. `p_derive`, and the abstraction settings: fixed in advance from F3–F5's results, never tuned on A, B or C.
3. Family C: which source, how many tasks, and how they are sealed.
4. Part 1's usefulness ablation: its exact protocol, and how a representation is credited when several are created.
5. Part 4's statistic, if B's small counterexamples are found by both arms: the count of certificates, or time to
   the first one.
6. Whether derived operations should also act on Γ's sum-type operations (union, join) and on corona. Today only
   the product-type space is open to derivation.
