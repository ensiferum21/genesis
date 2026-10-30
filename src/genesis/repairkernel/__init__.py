"""The obstacle loop's kernel side (`docs/OMEGA_SELF_REPAIR.md` §3, §7): the testbed of state-management components
with sealed planted defects (`targets`, `bench`, `defects`), the static guard on candidate sources (`guard`), the
independent repair verifier with hidden tests (`verify`), the Supervisor's promotion policy with rollback
(`supervisor`), the trial executor (`executor`) and the driver that runs the research plane and the executor in
isolation and decides what comes back (`foundry`). The research plane (`genesis.repair`) never imports this package
and cannot read it; Genesis may not repair it (`capture.PROTECTED`)."""
