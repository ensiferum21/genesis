"""The adaptation cell (B20_R93): how Genesis notices its own weaknesses and turns them into its next study.

Daniel (20 Oct 2026): "a problem we saw, then we were able to put it in words as a caveat, and from there we adapt and
improve ourselves: this mechanism I want to adapt, so our system is like a cell", and "make sure it's extremely smart
... without handholding at all". Until B20_R93 that loop ran through the builder and Daniel reading results. This
package makes it a mechanism that needs no one to register a study, label a caveat or say what was tried:

  * discovery (`discovery.py`): finds every time-to-solution study in the evidence and how to read it (its batch,
    date, the system's own arm and its competitors);
  * receptors (`receptors.py`): each senses one kind of weakness in a study's evidence: a floor effect, saturation,
    uncertified targets, unresolved verdicts, ablations without an effect, an invalid run, an interruption, a
    stronger published solver left out, budgets below the competitors' regime, instances at the model's size cap, a
    competitor that does not respond to its run time (a dose-response check), the system's method outperformed;
    and one autoreceptor that senses the cell itself: its knowledge of the field going stale;
  * signal transduction: a detection becomes a typed caveat with evidence, severity, magnitude and subject;
  * gene expression (`responses.py`): a library maps each caveat type to adaptations of the next study's design,
    each with a dose (how far a design goes towards it) and a noise band;
  * immune memory (`ledger.py`): one lineage per weakness, read in batch order; an attempt is a change between the
    study that showed the weakness and a later one (chemotaxis: compare with the past, not the state), with outcomes
    RESOLVED, IMPROVING, PERSISTENT, UNDERDOSED, CHRONIC, CLEARED and RELAPSE; responses that keep failing are
    retired (apoptosis) and every response's record ranks it for the next choice (clonal selection);
  * metabolism (`metabolism.py`): a cost model fitted to the cell's own earlier runs;
  * homeostasis and triage (`design.compose`): the next design answers every open caveat with the best-ranked
    response that changes something, at the dose the latest evidence calls for, gives long budgets only to arms that
    can change the comparison, plans for interruption before it happens, and under a growth-limited budget defers
    only what the membrane allows;
  * capabilities and work orders (`capabilities.py`): what the design needs that the system cannot do yet;
  * membrane and cell-cycle checkpoint (`responses.MEMBRANE`, `checkpoint.py`): what no adaptation may do, and the
    gate a design must pass before preregistration.

What the cell does not do: decide claims, change packages, or run studies. It senses, remembers, proposes and blocks;
the builder (and the reviewer) still decide, preregister and run.
"""
