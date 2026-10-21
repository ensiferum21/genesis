# B20_R97 evidence: quality at equal time against the 13 MaxSAT champions on large hosts (DEV)

The research loop's first study. The adaptation cell composed the design, `genesis.autonomy.studygen` wrote it as
`scripts/b20r97_qet_large.py`, and `loop.preregister` committed it at `6b674d1` (SHA-256 `892b5a11…7d58`, sent to Daniel
before it ran; `docs/PREREGISTRATIONS.md`). Run alone on CPU 0 in one segment (5,148 s); `code_identity`
`937f733f…7d08`, the committed tree's. It stopped at its first preregistered look (19 of 56 hosts), where every
comparison it had to decide was decided. Builder-run; licenses nothing.

| File | What |
|---|---|
| `hosts.json` | the 56 fresh hosts in run order (planted_cluster and G(n, 0.5), n = 128 and 256; seeds 20269701-04); 16 earlier large-domain identities excluded |
| `rows.jsonl` | one row per host run: every arm's value, run status and metered CPU; the probe; the best known value; the certified bound, its method and its certificate's digest |
| `certificates/NNN.json.gz` | per host: the best known value's witness (bit mask over the host's sorted edges, and which arm found it) and the bound's certificate; `genesis.autonomy.qet.check_host_evidence` re-checks both |
| `looks.jsonl` | the look at 19 hosts: labels and the decision to stop |
| `summary.json` | labels, every comparison (mean difference, interval, verdict), mean scores, per-cell means (descriptive), validity, descriptor ids, the design and its digest |
| `run.log` | the run |

Recomputed independently from these files with separate code (own triangle check, own certificate check in integers,
own scoring and bootstrap): every witness and bound re-checks, the look's labels, the stop, validity and the final
labels match. Record: `docs/checkpoints/B20_R97_RECORD.md`; tests: `tests_genesis/test_autonomy.py::RecordB20R97` and
the preregistered `ProspectiveB20R97`.
