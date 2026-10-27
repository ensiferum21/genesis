"""The engine-invention workflow as an Architecture Graph, and ARA's loss ladder over it (X2, B20_R154;
`docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §3, `docs/OMEGA_ARCHITECTURE_INVENTION.md` §2, §4).

**The graph.** Four typed nodes: `language` (Λ0, or Λ1 with a library version), `search` (a registered search and its
budget), `evaluator` (the data it decides on, and the judge if any) and `output` (the closed kernel: what is returned
is checked on fresh graphs). `check` refuses a malformed graph; `classify` says what kind of change one graph is from
another, in ARA's classes: a different language is LANGUAGE, a different search or evaluator STRUCTURAL, a different
budget or size TUNING, the output never changes.

**The ladder** (ARA's rule, `architecture/diagnose.py`, with the engine workflow's stand-ins). Per truth graph, the
values (gain over the reference) of:

| Stand-in | What it is |
|---|---|
| A | the workflow as it is |
| S_exact | its language and search, its choice made on exact evaluation (no judge, larger splits) |
| C_cur | its language under the ceiling search (`expressive.judge.SEARCHES['ceiling']`), exactly evaluated |
| C_rich | the richest available language under the ceiling search |
| O | the attainable: the reference engine at ten times the budget |

    expressiveness = C_rich - C_cur    -> the language node
    search         = C_cur - S_exact   -> the search node
    evaluation     = S_exact - A       -> the evaluator node
    residual       = O - C_rich        -> not reached by any language available

Each term has a bootstrap interval over the graphs; the diagnosis lists the terms whose lower bound exceeds MATERIAL
times the attainable range (O's mean gain), largest first; NONE when the range's interval reaches zero or no term is
material; AMBIGUOUS when the top two are not separated. These are B20_R132's instruments and B20_R151's factorial
put into ARA's form; a study supplies the values (`measures`), this module only decides.

**The next step** (Daniel's pipeline, 27 Oct 2026, 14:33): EXPRESSIVENESS -> grow the language (`library.learn`, then
the language judge, then the consolidator); SEARCH -> a stronger search (a STRUCTURAL rewrite of the search node);
EVALUATION -> a finer evaluator; NONE -> no structural repair is indicated.
"""
import random
import statistics

MATERIAL = 0.05
BOOT = 1000
TERMS = ('expressiveness', 'search', 'evaluation', 'residual')
LOCATE = {'expressiveness': 'language', 'search': 'search', 'evaluation': 'evaluator', 'residual': None}
NEXT = {'EXPRESSIVENESS': 'grow the language: library learning, the language judge, the consolidator',
        'SEARCH': 'a stronger search: a structural rewrite of the search node',
        'EVALUATION': 'a finer evaluator: more graphs or repeats, or a finer judge',
        'NONE': 'no structural repair is indicated', 'AMBIGUOUS': 'measure the top two terms apart'}
ROLES = ('language', 'search', 'evaluator', 'output')


def make(language='L1', library=None, search='inventor', evals=240, size=4, judge=None):
    return {'schema': 'genesis-engine-workflow-v1',
            'nodes': {'language': {'lang': language, 'library': library},
                      'search': {'name': search, 'evals': evals},
                      'evaluator': {'size': size, 'judge': judge},
                      'output': {'check': 'fresh graphs'}}}


def check(wf):
    """[problems]; empty when the graph is well formed."""
    out = []
    n = wf.get('nodes', {}) if isinstance(wf, dict) else {}
    if set(n) != set(ROLES):
        return [f'the nodes are {ROLES}']
    if n['language'].get('lang') not in ('L0', 'L1'):
        out.append('language: L0 or L1')
    if n['language'].get('lang') == 'L0' and n['language'].get('library'):
        out.append('Λ0 has no library')
    if n['search'].get('name') not in ('inventor', 'ceiling'):
        out.append('search: inventor or ceiling')
    if not isinstance(n['search'].get('evals'), int) or n['search']['evals'] < 1:
        out.append('search: a positive budget')
    if not isinstance(n['evaluator'].get('size'), int) or n['evaluator']['size'] < 1:
        out.append('evaluator: a positive size')
    if n['output'] != {'check': 'fresh graphs'}:
        out.append('the output is the closed kernel')
    return out


def classify(old, new):
    """ARA's class of the change from one workflow to another."""
    if check(old) or check(new):
        raise ValueError('malformed workflow')
    a, b = old['nodes'], new['nodes']
    if a['output'] != b['output']:
        raise ValueError('the output is the closed kernel')
    if a['language'] != b['language']:
        return 'LANGUAGE'
    if a['search']['name'] != b['search']['name'] or a['evaluator']['judge'] != b['evaluator']['judge']:
        return 'STRUCTURAL'
    if a != b:
        return 'TUNING'
    return 'NONE'


def _boot(diffs, seed):
    rng = random.Random(f'boot|{seed}')
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOT))
    return means[int(0.025 * BOOT)], means[int(0.975 * BOOT) - 1]


def ladder(measures, seed=0):
    """measures: {stand-in: [gain per truth graph]} for A, S_exact, C_cur, C_rich, O (the same graphs, in order)."""
    need = ('A', 'S_exact', 'C_cur', 'C_rich', 'O')
    if set(measures) != set(need) or len({len(v) for v in measures.values()}) != 1:
        raise ValueError(f'measures for {need} on the same graphs')
    m = measures
    pairs = {'expressiveness': ('C_rich', 'C_cur'), 'search': ('C_cur', 'S_exact'),
             'evaluation': ('S_exact', 'A'), 'residual': ('O', 'C_rich')}
    terms, diffs = {}, {}
    for t, (hi, lo) in pairs.items():
        d = [x - y for x, y in zip(m[hi], m[lo])]
        diffs[t] = d
        terms[t] = {'value': statistics.mean(d), 'ci': _boot(d, f'{seed}|{t}'), 'node': LOCATE[t]}
    rng_ci = _boot(m['O'], f'{seed}|range')
    attainable = statistics.mean(m['O'])
    threshold = MATERIAL * attainable
    material = sorted((t for t in TERMS if t != 'residual' and terms[t]['ci'][0] > threshold and rng_ci[0] > 0),
                      key=lambda t: -terms[t]['value'])
    if not material:
        diagnosis = 'NONE'
    elif len(material) > 1 and _boot([a - b for a, b in zip(diffs[material[0]], diffs[material[1]])],
                                     f'{seed}|top')[0] <= 0:
        diagnosis = 'AMBIGUOUS'
    else:
        diagnosis = material[0].upper()
    return {'terms': terms, 'attainable': attainable, 'range_ci': rng_ci, 'threshold': threshold,
            'material': material, 'diagnosis': diagnosis, 'next': NEXT[diagnosis],
            'locate': LOCATE.get(diagnosis.lower())}
