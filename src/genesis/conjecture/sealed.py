"""The sealed calibration set: the 68 candidate upper bounds on the Laplacian spectral radius of Brankov, Hansen and
Stevanovic (KERNEL SIDE; F2, `docs/OMEGA_FRONTIER.md` §6). The research plane never imports this module; a study
poses a bound to Genesis by its formula only, under an opaque id, and keeps the status here.

**Source paper.** V. Brankov, P. Hansen, D. Stevanovic, "Automated conjectures on upper bounds for the largest
Laplacian eigenvalue of graphs", Linear Algebra Appl. 414 (2006) 407-424 (GERAD G-2005-20). Bounds 1-32:
mu <= max_v f(d_v, m_v); 33-68: mu <= max over edges ij of f(d_i, m_i, d_j, m_j); d a degree, m the average degree
of the neighbours. The 2006 text itself was not available here (its DOI page is not reachable from this session);
the formulas are transcribed from later papers that restate them.

**Transcription sources** (read 27 Oct 2026 through a page-to-text tool, one bound at a time):
  S1  I. Damnjanovic, T. Ha, D. Stevanovic, "Upper bounds for the Laplacian spectral radius: Proofs and
      counterexamples", arXiv 2606.14550v1 (12 Jun 2026): the 36 bounds open before it (Tables 1-2).
  S2  L. Taieb, M. Roucairol, T. Cazenave, A. Harutyunyan, "Automated Refutation with Monte Carlo Search of Graph
      Theory Conjectures on the Maximum Laplacian Eigenvalue", LION 2025, LNCS 15744 (2026) 52-63,
      doi 10.1007/978-3-032-09156-7_4; Appendix B of the authors' PDF (all 68; the extraction flattens radicals).
  S3  M. Ghebleh, S. Al-Yakoob, A. Kanso, D. Stevanovic, "Reinforcement learning for graph theory, I.
      Reimplementation of Wagner's approach", arXiv 2403.18429v1 HTML and PDF, Appendix B (OCR-damaged; some labels
      shifted by one, so it is used only where its text matches another source's formula under the same number,
      or as noted).
  S4  A. Bouffard, J. Breen, "Reinforcement learning for graph theory: Parallelizing Wagner's approach", arXiv
      2509.01607v1 HTML (LaTeX): bounds 2, 3, 15, 28, 29, 31, 32, 36, 43, 49, 52-55, 57-60 (61 truncated).
  S5  google-deepmind/formal-conjectures issue #7282 (13 Oct 2026): the statement of bound 44.

**Tiers** (the sealing rule):
  A1  two sources give the same formula;
  A2  one source gives it exactly, a second is compatible except for an extraction artefact (a missing parenthesis,
      a stray character, a flattened or uncertain radical, an inferred root index), and the semantic checks of
      `scripts/f2_bhs_transcription.py` pass;
  B   one source only (semantic checks reported): descriptive use only, never in a primary test;
  X   sources disagree: excluded until the 2006 text is read.
Every formula is also checked by the script: it parses; a proved bound holds on every connected graph up to 7
vertices; the value at the regular point d = m = r is reported (2r is mu of every r-regular bipartite graph).

**Status** (as of S1, June 2026; the literature after it was searched on 27 Oct 2026, `docs/OMEGA_FRONTIER.md`
§6): 'refuted-2024' (S3, 30), 'refuted-2025' (S2, 2: 45 and 48), 'refuted-2026' (S1, 12), 'proved' (S1, 22;
23 equals 10), 'open' (44, 46).

**Held out for the proving test** (`docs/OMEGA_FRONTIER.md` §7b, family A): 18, 21, 24, 30, 40, the bounds whose only
known counterexamples are large equitable-partition constructions (158-352 vertices). They are not posed in F4 or
F5.
"""

PROVED = (1, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 23, 25, 26, 27, 33, 34, 35, 37, 38, 39, 42)
REFUTED_2024 = (2, 3, 15, 17, 28, 29, 31, 32, 36, 41, 43, 49, 50, 51, 52, 53, 54, 55, 57, 58, 59, 60, 61, 62, 63,
                64, 65, 66, 67, 68)
REFUTED_2025 = (45, 48)
REFUTED_2026 = (11, 13, 18, 19, 20, 21, 22, 24, 30, 40, 47, 56)
OPEN = (44, 46)
DUPLICATES = {23: 10}
PROVING_TEST_HOLDOUT = (18, 21, 24, 30, 40)

# number: (formula in expr's grammar, tier, sources, note)
BOUNDS = {
    1: ('sqrt(4*d^3/m)', 'A1', ('S1', 'S3'), 'S2 garbled'),
    2: ('2*m^2/d', 'A1', ('S2', 'S3', 'S4'), ''),
    3: ('m^2/d + m', 'A1', ('S2', 'S4'), ''),
    4: ('2*d^2/m', 'A1', ('S1', 'S2'), ''),
    5: ('d^2/m + m', 'A1', ('S1', 'S2'), ''),
    6: ('sqrt(m^2 + 3*d^2)', 'A1', ('S1', 'S2'), ''),
    7: ('d^2/m + d', 'A1', ('S1', 'S2'), ''),
    8: ('sqrt(d*(m + 3*d))', 'A1', ('S1', 'S2'), ''),
    9: ('(m + 3*d)/2', 'A1', ('S1', 'S2'), ''),
    10: ('sqrt(d*(d + 3*m))', 'A2', ('S1', 'S2'), 'S2 drops a closing parenthesis'),
    11: ('2*m^3/d^2', 'A1', ('S1', 'S2'), ''),
    12: ('sqrt(2*m^2 + 2*d^2)', 'A1', ('S1', 'S2'), ''),
    13: ('2*m^4/d^3', 'A2', ('S1', 'S2'), 'S2 has a stray character after d^3'),
    14: ('2*d^3/m^2', 'A1', ('S1', 'S2'), ''),
    15: ('sqrt(4*m^3/d)', 'A1', ('S2', 'S4'), ''),
    16: ('2*d^4/m^3', 'A1', ('S1', 'S2'), ''),
    17: ('root4(5*d^4 + 11*m^4)', 'A1', ('S2', 'S3'), ''),
    18: ('sqrt(2*m^3/d + 2*d^2)', 'A1', ('S1', 'S3'), 'S2 leaves the radical extent open'),
    19: ('root4(4*d^4 + 12*d*m^3)', 'A2', ('S1', 'S2'), 'the root index is inferred in both extractions; a square '
         'root would make the bound quadratic in the degrees'),
    20: ('(1/2)*sqrt(7*d^2 + 9*m^2)', 'A1', ('S1', 'S2'), ''),
    21: ('sqrt(d^3/m + 3*m^2)', 'A1', ('S1', 'S2'), ''),
    22: ('root4(2*d^4 + 14*d^2*m^2)', 'A2', ('S1', 'S2'), 'root index inferred in both extractions'),
    23: ('sqrt(d^2 + 3*d*m)', 'A1', ('S1', 'S2'), 'identical to bound 10 (S1)'),
    24: ('root4(6*d^4 + 10*m^4)', 'A2', ('S1', 'S2'), 'root index inferred in both extractions'),
    25: ('root4(3*d^4 + 13*d^2*m^2)', 'A2', ('S1', 'S2'), 'root index inferred in both extractions'),
    26: ('(1/2)*sqrt(5*d^2 + 11*d*m)', 'A1', ('S1', 'S2'), ''),
    27: ('sqrt((3*d^2 + 5*d*m)/2)', 'A2', ('S1', 'S2'), 'S2 reads sqrt(3d^2 + 5dm)/2; that reading is below mu(C4) = 4 '
         'at C4 and could not be a proved bound'),
    28: ('sqrt(4*m^4/d^2 + 2*d*m)', 'X', ('S4',), 'S2 reads sqrt(2*m^4/d^2 + 2*d*m): disagreement on a coefficient'),
    29: ('sqrt(m^2 + 3*m^3/d)', 'A1', ('S2', 'S4'), ''),
    30: ('m^3/d^2 + d^2/m', 'A1', ('S1', 'S2'), ''),
    31: ('4*m^2/(m + d)', 'A1', ('S2', 'S3', 'S4'), ''),
    32: ('sqrt(m^3*(m + 3*d))/d', 'A2', ('S4', 'S2'), 'S2 flattens the radical (the /d may read inside it)'),
    33: ('2*(di + dj) - (mi + mj)', 'A1', ('S1', 'S2'), 'S3 garbled: divides by (di + dj), which is at most 2'),
    34: ('2*(di^2 + dj^2)/(di + dj)', 'A1', ('S1', 'S2', 'S3'), ''),
    35: ('2*(di^2 + dj^2)/(mi + mj)', 'A1', ('S1', 'S2', 'S3'), ''),
    36: ('2*(mi^2 + mj^2)/(di + dj)', 'A1', ('S2', 'S3', 'S4'), ''),
    37: ('sqrt(2*(di^2 + dj^2))', 'A1', ('S1', 'S2'), 'S2 flags the radical extent as uncertain'),
    38: ('2 + sqrt(2*(di - 1)^2 + 2*(dj - 1)^2)', 'A1', ('S1', 'S2'), 'S2 flags the radical extent'),
    39: ('2 + sqrt(2*(di^2 + dj^2) - 4*(mi + mj) + 4)', 'A1', ('S1', 'S2'), 'S2 flags the radical extent'),
    40: ('2 + sqrt(2*((mi - 1)^2 + (mj - 1)^2) + (di^2 + dj^2) - (di*mi + dj*mj))', 'A2', ('S1', 'S2', 'S3'),
         'S2 flags the radical extent; S3 gives the same formula under label 39'),
    41: ('2 + (mi + mj) - (di + dj) + sqrt(2*(di^2 + dj^2) - 4*(mi + mj) + 4)', 'X', ('S2',),
         'S3 reads 2 + sqrt(2((mi-1)^2 + (mj-1)^2) + (di^2 + dj^2) - 4(mi + mj) + 4): disagreement'),
    42: ('sqrt(di^2 + dj^2 + 2*mi*mj)', 'A1', ('S1', 'S2'), ''),
    43: ('2 + sqrt(3*(mi^2 + mj^2) - 2*mi*mj - 4*(di + dj) + 4)', 'A1', ('S2', 'S3', 'S4'), ''),
    44: ('2 + sqrt(2*((di - 1)^2 + (dj - 1)^2 + mi*mj - di*dj))', 'A1', ('S1', 'S2', 'S3', 'S5'), ''),
    45: ('2 + sqrt((di - dj)^2 + 2*(di*mi + dj*mj) - 4*(mi + mj) + 4)', 'B', ('S2',),
         'S3 gives bound 46\'s formula under label 45'),
    46: ('2 + sqrt(2*(di^2 + dj^2) - 16*di*dj/(mi + mj) + 4)', 'A1', ('S1', 'S2', 'S3'), 'S3 labels it 45'),
    47: ('(2*(di^2 + dj^2) - (mi - mj)^2)/(di + dj)', 'A1', ('S1', 'S2', 'S3'), ''),
    48: ('2*(di^2 + dj^2)/(2 + sqrt(2*(di^2 + dj^2) - 4*(mi + mj) + 4))', 'B', ('S2',),
         'S3 illegible; S2 reports the path on 3 vertices as a counterexample'),
    49: ('2 + sqrt(2*(mi^2 + mj^2) + (di - dj)^2 - 4*(di + dj) + 4)', 'A1', ('S2', 'S4'), ''),
    50: ('2*(di^2 + dj^2 + mi*mj - di*dj)/(di + dj)', 'B', ('S2',), 'S3 has no legible formula'),
    51: ('2*(mi + mj) - 4*mi*mj/(di + dj)', 'B', ('S2',), 'S3 garbled'),
    52: ('2 + sqrt(sqrt(8*(mi^4 + mj^4) - 8*(di^2 + dj^2) + 4) - 4*(di + dj) + 6)', 'A2', ('S4', 'S2', 'S3'),
         'S2 and S3 flatten the nested radical'),
    53: ('2 + sqrt(sqrt(8*(mi^4 + mj^4) - 8*(di*mi + dj*mj) + 4) - 4*(di + dj) + 6)', 'A2', ('S4', 'S2', 'S3'),
         'S2 and S3 flatten the nested radical'),
    54: ('2 + sqrt(2*(mi^2 + mj^2) + (di*mi + dj*mj) - (di^2 + dj^2) - 4*(di + dj) + 4)', 'A1', ('S2', 'S4'),
         'S3 garbled'),
    55: ('2 + sqrt(3*(mi^2 + mj^2) - (di^2 + dj^2) - 4*(mi + mj) + 4)', 'A1', ('S2', 'S4'), ''),
    56: ('(di^2 + dj^2)*(mi + mj)/(2*di*dj)', 'A1', ('S1', 'S2', 'S3'), ''),
    57: ('2 + sqrt(2*(mi^2 + mj^2) - 8*(di^2 + dj^2)/(mi + mj) + 4)', 'A1', ('S2', 'S3', 'S4'), ''),
    58: ('2 + sqrt(2*(mi^2 + mi*mj + mj^2) - (di*mi + dj*mj) - 4*(di + dj) + 4)', 'A1', ('S2', 'S3', 'S4'), ''),
    59: ('(2*(mi^2 + mi*mj + mj^2) - (di^2 + dj^2))/(mi + mj)', 'A1', ('S2', 'S3', 'S4'), ''),
    60: ('2 + sqrt(2*(mi^2 + mi*mj + mj^2) - (di^2 + dj^2) - 4*(di + dj) + 4)', 'A1', ('S2', 'S3', 'S4'), ''),
    61: ('2*(mi^2 + mj^2)/(2 + sqrt(2*((di - 1)^2 + (dj - 1)^2)))', 'A1', ('S2', 'S3'), 'S4 truncated, compatible'),
    62: ('2 + sqrt(mi^2 + 4*mi*mj + mj^2 - 2*di*dj - 4*(di + dj) + 4)', 'A1', ('S2', 'S3'),
         'S3 lists 62 twice; one copy matches'),
    63: ('di + dj + mi + mj - 4*di*dj/(mi + mj)', 'A1', ('S2', 'S3'), ''),
    64: ('mi*mj*(di + dj)/(di*dj)', 'A1', ('S2', 'S3'), 'S3 also has a garbled duplicate'),
    65: ('(mi + mj)*(di*mi + dj*mj)/(2*mi*mj)', 'A1', ('S2', 'S3'), ''),
    66: ('(mi^2 + 4*mi*mj + mj^2 - (di*mi + dj*mj))/(di + dj)', 'A1', ('S2', 'S3'), ''),
    67: ('(mi + mj)*(di*mi + dj*mj)/(2*di*dj)', 'A1', ('S2', 'S3'), ''),
    68: ('2 + sqrt((mi - mj)^2 + 4*di*dj - 4*(mi + mj) + 4)', 'A1', ('S2', 'S3'), ''),
}


def kind(number):
    return 'vertex' if number <= 32 else 'edge'


def status(number):
    for name, group in (('proved', PROVED), ('refuted-2024', REFUTED_2024), ('refuted-2025', REFUTED_2025),
                        ('refuted-2026', REFUTED_2026), ('open', OPEN)):
        if number in group:
            return name
    raise KeyError(number)


def sealed(tiers=('A1', 'A2'), exclude=PROVING_TEST_HOLDOUT, distinct=True):
    """The bounds admitted for a primary test: {number: (formula, kind, status)}."""
    out = {}
    for k, (f, tier, _, _) in sorted(BOUNDS.items()):
        if tier in tiers and k not in exclude and not (distinct and k in DUPLICATES):
            out[k] = (f, kind(k), status(k))
    return out
