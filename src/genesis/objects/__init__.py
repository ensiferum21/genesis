"""Research objects: one typed, executable, bounded unit for everything Genesis can invent or improve
(`docs/OMEGA_RECURSIVE_INVENTION.md` §3; Daniel's architecture of 24 Oct 2026, 20:31).

  * `types`: the type registry (base types with validators, constructors; new types as data);
  * `kinds`: the kind registry (senses, instruments, compositions, representations, methods, strategies, improvers,
    ... and kinds Genesis registers itself, as data);
  * `core`: the research-object record, its validation, `run` (types, preconditions, the executor under fuel,
    postconditions, a record of the run), and storage in the vault;
  * `executors`: the registered interpreters (never `eval`), including adapters for the existing languages and the
    improver.
Research plane: nothing here imports the protected kernel (`test_omega_boundary`).
"""
