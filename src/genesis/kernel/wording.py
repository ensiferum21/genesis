"""Evidence wording gate (spec §7.4, §21.2).

Reports are generated from evidence records; this linter is the backstop that
rejects prose asserting more than the granted levels allow. A phrase is allowed
when negated nearby ("no", "not", "never", "unestablished", ...), so honest
limitation statements pass. UPPER_SNAKE status tokens are ignored.
"""
import re

NEGATIONS = re.compile(r"\b(no|not|never|none|without|unestablished|unconfirmed|unsupported|cannot|isn't|"
                       r"aren't|wasn't|nor|neither|zero|false|unproven|absent|pending|requires?|needs?|until)\b",
                       re.I)

# (pattern, axis, minimum level that licenses it, explanation)
RULES = [
    (r'\b(?:we\s+)?(?:have\s+)?(?:proved|proven|proves|prove)\b', 'math', 'THEOREM_CHECKED',
     'proof language needs a formally checked theorem'),
    (r'\btheorem\b', 'math', 'THEOREM_CHECKED', 'theorem language needs a formally checked theorem'),
    (r'\b(?:is|are|was|were)\s+(?:the\s+)?optimal\b|\bproved\s+optimal\b|\boptimality\b', 'math',
     'FINITE_CERTIFIED', 'optimality needs certified matching bounds'),
    (r'\bgenerali[sz](?:es|ed|ation|e)\b|\btransfers?\b(?!\s+(?:panel|domain|task|experiment|wins|diagnostic))',
     'utility', 'CONFIRMED_TRANSFER', 'generalisation/transfer needs confirmed transfer'),
    (r'\bconfirmed\b|\bstatistically significant\b|\bsignificantly\s+(?:better|improv)', 'utility',
     'CONFIRMED_SAME_DOMAIN', 'confirmation language needs a clean prospective evaluation'),
    (r'\bcaus(?:es|ed|ally|al\s+effect)\b|\bbecause\s+of\s+the\s+(?:change|modification)\b', 'causality',
     'ABLATION_SUPPORTED', 'causal language needs ablation support'),
    (r'\bnovel\b|\bnew\s+discovery\b|\bdiscovered\s+a\s+new\b|\bfirst\s+known\b', 'novelty',
     'EXTERNALLY_CHECKED_NOVEL', 'novelty needs an external priority check'),
    (r'\brecursive(?:ly)?\s+self[- ]improv\w*\b|\bbetter\s+improver\b|\bself[- ]improving\b', 'improver',
     'MULTIGEN_CONFIRMED', 'self-improvement language needs multi-generation confirmation'),
    (r'\breplicated\b|\bindependently\s+reproduced\b', 'replication', 'EXTERNAL_REPRODUCTION',
     'replication language needs external reproduction'),
]
ORDER = {
    'math': ['UNCHECKED', 'EXECUTABLE', 'WITNESS_VALID', 'FINITE_CERTIFIED', 'THEOREM_CHECKED', 'OPTIMALITY_CHECKED'],
    'utility': ['NOT_TESTED', 'DEV_ONLY', 'CONFIRMED_SAME_DOMAIN', 'CONFIRMED_TRANSFER'],
    'causality': ['NOT_TESTED', 'CORRELATED', 'ABLATION_SUPPORTED', 'PLACEBO_CONTROLLED'],
    'improver': ['NOT_TESTED', 'SAME_DOMAIN_CONFIRMED', 'CROSS_DOMAIN_CONFIRMED', 'MULTIGEN_CONFIRMED'],
    'novelty': ['UNKNOWN', 'REDISCOVERY', 'VARIANT', 'CANDIDATE_NOVEL', 'EXTERNALLY_CHECKED_NOVEL'],
    'replication': ['NONE', 'INTERNAL_INDEPENDENT', 'EXTERNAL_REPRODUCTION'],
}
STATUS_TOKEN = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b')
CODE = re.compile(r'`[^`]*`')
# External statements quoted as sources are not claims of this run: "[cited: ...]".
CITED = re.compile(r'\[cited:[^\]]*\]', re.I)
# "no ghost found" may never sit next to proof language (§21.2).
GHOST_AS_PROOF = re.compile(r'no[_ ]ghost[_ ]found[^.]{0,60}\b(?:proved|proven|proof|holds)\b', re.I)


def _licensed(levels, axis, minimum):
    have = levels.get(axis, ORDER[axis][0])
    if axis == 'math' and have not in ORDER['math']:
        return False
    if axis == 'math' and minimum == 'FINITE_CERTIFIED':
        return ORDER['math'].index(have) >= ORDER['math'].index('FINITE_CERTIFIED')
    return ORDER[axis].index(have) >= ORDER[axis].index(minimum)


def lint(text, levels):
    """Return a list of violations; empty means the prose is within its evidence."""
    violations = []
    if GHOST_AS_PROOF.search(text):
        violations.append({'phrase': GHOST_AS_PROOF.search(text).group(0), 'why': 'no ghost found is not proof'})
    for raw_sentence in re.split(r'(?<=[.!?])\s+(?![^\[]*\])|\n+', text):
        sentence = CITED.sub(' ', CODE.sub(' ', STATUS_TOKEN.sub(' ', raw_sentence)))
        for pattern, axis, minimum, why in RULES:
            for m in re.finditer(pattern, sentence, re.I):
                window = sentence[max(0, m.start() - 60):m.start()]
                if NEGATIONS.search(window) or NEGATIONS.search(sentence[m.end():m.end() + 25]):
                    continue
                if not _licensed(levels, axis, minimum):
                    violations.append({'phrase': m.group(0), 'sentence': raw_sentence.strip()[:200], 'why': why})
    return violations


def require_clean(text, levels):
    problems = lint(text, levels)
    if problems:
        raise ValueError('report exceeds its evidence: ' + '; '.join(f"{p['phrase']!r} ({p['why']})"
                                                                     for p in problems[:5]))
    return text
