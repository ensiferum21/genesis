"""The repair vault (SR-b; `docs/OMEGA_SELF_REPAIR.md` §2.4): past obstacles and their verified repairs, retrieved by
failure signature.

An entry records what the obstacle looked like (its signature, `capture.signature`), the class of what was missing
(§2.3: 'ordering', 'guard', 'missing-capability', 'design'), the fix template that repaired it with its parameters,
the commits before and after, and the regression test that verifies it. The first four entries are the defects the
builder repaired by hand on 28-30 Oct 2026 (`docs/BLOCKING_DEFECTS.md`).

`retrieve(signature)` ranks entries by how much of the signature they share: the innermost repairable function and
file count most, then the exception chain, then the blanked source line. A retrieved entry is a candidate only; the
kernel verifier decides (§2.5). In SR-1 the vault is used leave-one-out on the real obstacles, so that retrieving a
defect's own repair never counts as repairing it.
"""
ENTRIES = (
    {'id': 'B20R158-TEMPLATE', 'class': 'guard',
     'signature': {'exceptions': ['OverflowError'], 'file': 'src/genesis/conjecture/abstraction.py',
                   'func': 'mutate', 'code': None},
     'template': 'clamp', 'params': {'what': 'slot values', 'range': '[lo, max_n]'},
     'before': 'ff9eada', 'after': 'f7803e3',
     'test': 'tests_genesis/test_conjecture_domain.py::test_template_genomes_stay_bounded'},
    {'id': 'B20R163-META', 'class': 'design',
     'signature': {'exceptions': [], 'file': 'src/genesis/frontier/meta.py', 'func': 'step', 'code': None},
     'template': None, 'params': {'note': 'a selection compared at unequal spend; not a local repair'},
     'before': '77d725d', 'after': '8610f69',
     'test': 'tests_genesis/test_frontier_meta.py::Suite'},
    {'id': 'B20R177-LIBRARY', 'class': 'missing-capability',
     'signature': {'exceptions': ['StopIteration', 'RuntimeError'], 'file': 'src/genesis/conjecture/library.py',
                   'func': '<genexpr>', 'code': 'return (k,) + tuple(next(it) for _ in s[0:])'},
     'template': 'propagate-dependency',
     'params': {'into': 'GammaLib.__init__', 'what': 'the derived operations its macros use'},
     'before': 'a7303de', 'after': '25eadb7',
     'test': 'tests_genesis/test_operations.py::Library::test_a_macro_with_a_derived_operation_expands_and_builds'},
    {'id': 'B20R177-SEEN', 'class': 'ordering',
     'signature': {'exceptions': ['KeyError'], 'file': 'src/genesis/conjecture/statement.py', 'func': 'score',
                   'code': 'return self._seen[key]'},
     'template': 'reorder', 'params': {'move': 'the clear', 'before': 'the store'},
     'before': '25eadb7', 'after': '75b5bac',
     'test': 'tests_genesis/test_wowii.py::ScoreMemo'},
)


def score(entry, sig):
    e = entry['signature']
    s = 0.0
    if sig.get('file') and e.get('file') == sig['file']:
        s += 2.0
        if e.get('func') == sig.get('func'):
            s += 2.0
    if e.get('exceptions') and sig.get('exceptions'):
        s += len(set(e['exceptions']) & set(sig['exceptions'])) / len(set(e['exceptions']) | set(sig['exceptions']))
    if e.get('code') and e.get('code') == sig.get('code'):
        s += 1.0
    return s


def retrieve(sig, exclude=(), entries=ENTRIES, minimum=1.0):
    """Entries sharing at least `minimum` of the signature, best first; `exclude` holds ids left out (SR-1's
    leave-one-out)."""
    ranked = sorted(((score(e, sig), e['id'], e) for e in entries if e['id'] not in exclude),
                    key=lambda x: (-x[0], x[1]))
    return [e for s, _, e in ranked if s >= minimum]
