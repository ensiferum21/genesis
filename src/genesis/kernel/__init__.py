"""Immutable evidence microkernel (spec §3).

Modules here must not import research, campaign, DSL or IR code: the kernel
decides what evidence licenses, and it must not depend on the components whose
outputs it judges. `tests_genesis/test_architecture_boundaries.py` enforces this.
"""
