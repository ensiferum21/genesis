# B20_R75 record: the state-of-the-art comparison is INVALID_CPU_DELIVERY (a seed-range defect in the BURER2002 kind)

- **Run by:** the builder. DEV only.
- **Setup:** `fc8f950`, amended before any arm ran at `1f04796` (n80 → n63: the task model caps n at 63; the first
  run stopped while drawing hosts). Script SHA-256 `c2c1e54d…2f2b`, sent before the run. Alone, pinned, 2,570 s.
- **Evidence:** `evidence/sota_b20r75/`.

## Result: **INVALID_CPU_DELIVERY**

BURER2002's median CPU at 0.5 s was 0.166 s (threshold 0.45 s). Cause, found after the run: MQLib accepts seeds only
in 0..65535; `mqlib-v1` passed seeds modulo 2^31; MQLib exited with a usage error, and the kind returned an empty
witness instead of failing. All 180 BURER2002 runs scored 0. The preregistered validity check caught it, so no
primary verdict is read.

Descriptive (the five valid arms): simulated bifurcation fastest (median TTS 0.1 s at n60, 0.25 s at n63); the
system's engine 1.2 s at both sizes, ahead of the frozen candidate at n63 (3.0 s; 75th percentile 24 s); tabu fast
where it succeeds but unsolved on 2–3 hosts per size; HiGHS never within 2 s and, with 60 s, proved no host
optimal. The system's checked certification route certified 6 of 12 hosts within 120 s.

## Consequence

- `mqlib-v1` is fixed in B20_R76 (seed modulo 65,536; a non-zero exit or unparseable output now fails the run) with a
  test at a large seed; B20_R76 repeats the comparison on fresh hosts, with CP-SAT added.
- A lesson for the protocol: a kind that wraps an external program must fail loudly, never return an empty answer;
  and kind tests must use seeds of the size studies use.

## Tests

`tests_genesis/test_sota.py`: Design (5); Record (3).
