# B20_RX2 record: GV4 capability pilots and the harder E1 family (recovery branch)

- **Parent:** checkpoint B20_RX1, commit `3456797`, SHA-256 `e107304a…ec0f`.
- **Branch:** `recovery-b20r1-partial`, a partial base. See `B20_RX1_RECORD.md` for the base, how to port this onto the canonical line, and every open item.
- **Run by:** the builder, on DEV. Nothing here is independently reviewed.
- **User decisions, 13 Oct 2026 (second set):** independent work only; GV4 capability study design; harder host family for E1.

| Batch | Commits | Result |
|---|---|---|
| B20_R14 optimum-gap probe | `331825f`, `01c38e6` | the R13 portfolio is 0.6–1.4 edges per host below the certified optimum on harder families (S2, S3, S7) and at the ceiling on S1 (the E1 family), S4 and S6 |
| B20_RX3 capability pilot | `0dec3f6`, `f2badd0` | builder-written LP/SAT-guided components (`discovery/construct.py`, CPU charged including child processes) give DEPLOYABLE_CAPABILITY_HEADROOM in all 3 settings: +0.75 to +1.25 |
| B20_RX3b replication | `76aa47d`, `723c13d` | replicated on fresh seeds: +0.63 to +1.38, every 90% interval above 0. Also the GV4 design DRAFT (`handoff/gv4/README.md`) |
| B20_RX4 E1 calibration | `7b8a57e`, `4b1c2fc` | harder E1 family **n30 p0.35**: the candidate is +4.9 edges per host over the strongest time-matched baseline (12/0/0), with room to the optimum |
| B20_RX5 proposal pilot | `7adbece`, `f100eea` | NO_PROPOSAL_HEADROOM: once the components exist, good compositions are plentiful. GV4 reduces to component invention (s15.3, W22) |

**New tests:** `tests_certificates/test_construct.py` (4).

**Claim ceiling.** Engineering and DEV diagnostics only. No sealed task was run. Better-improver remains UNESTABLISHED. E1 remains a DRAFT design until the B20_R12 redo on the canonical line.
