"""Recognising an obstacle (the obstacle loop's step 1, SR-a; `docs/OMEGA_SELF_REPAIR.md` §2).

A failed run leaves a Python traceback in its slice log. `parse` turns the last traceback into a `Failure`: the
exception's type and message, and the frames, each with its file relative to the repository (whatever worktree the
run used), its line, its function and its source line. Chained tracebacks ("The above exception was the direct cause
of the following exception", "During handling of the above exception") are kept as `causes`, oldest first, because
the cause often names the fault (B20R177-LIBRARY's StopIteration under the RuntimeError).

`signature(failure)` is what a past repair is retrieved by: the exception types of the chain, and the innermost
frame in a repairable module (its file, function and source line, with literals blanked). `where(path)` puts a file
on one side of the boundary of §3:
  * 'protected': the Judge, the kernel and custody, the checkers and verifiers, the sealed sets and held-out data,
    the kernel side of the planted worlds and the zoo, the run scripts and every study script, the tests, the data and
    the evidence. Genesis never repairs these; an obstacle inside one is escalated to the Supervisor;
  * 'repairable': the research plane's modules listed in REPAIRABLE;
  * 'outside': anything else (the standard library, third-party packages, unlisted modules): not repaired either.
The rule is default-deny: a file is repairable only if listed.
"""
import re

PROTECTED = (
    'src/genesis/autonomy/feedback.py', 'src/genesis/architecture/judge.py', 'src/genesis/architecture/zoo.py',
    'src/genesis/kernel/', 'src/genesis/judge.py', 'src/genesis/custodian.py', 'src/genesis/custody_records.py',
    'src/genesis/verification/', 'src/genesis/release_bundle.py', 'src/genesis/eligibility.py',
    'src/genesis/exposure.py',
    'src/genesis/decision_record.py', 'src/genesis/domains.py', 'src/genesis/gset.py',
    'src/genesis/conjecture/sealed.py', 'src/genesis/conjecture/verify.py', 'src/genesis/conjecture/wowii.py',
    'src/genesis/conjecture/invariants_ref.py', 'src/genesis/conjecture/audit.py',
    'src/genesis/frontier/manifest.py', 'src/genesis/frontier/world.py',
    'src/genesis/repair/',                       # the loop may not repair itself (its verifier least of all)
    'scripts/', 'tests_genesis/', 'data/', 'evidence/',
)
REPAIRABLE = (
    'src/genesis/frontier/', 'src/genesis/conjecture/', 'src/genesis/architecture/', 'src/genesis/senses/',
    'src/genesis/expressive/', 'src/genesis/representation/', 'src/genesis/objects/',
)
_FILE = re.compile(r'^  File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>.+)$')
_CHAIN = ('The above exception was the direct cause of the following exception:',
          'During handling of the above exception, another exception occurred:')
_ROOTS = re.compile(r'^.*?/((?:src|scripts|tests_genesis)/.*)$')


def relative(path):
    """The file relative to its repository, whatever worktree or clone the run used."""
    m = _ROOTS.match(path)
    return m.group(1) if m else path


def where(path):
    rel = relative(path)
    if any(rel == p or (p.endswith('/') and rel.startswith(p)) or rel.startswith(p + '/') for p in PROTECTED):
        return 'protected'
    if any(rel.startswith(p) for p in REPAIRABLE):
        return 'repairable'
    return 'outside'


def _one(lines):
    """One traceback block -> (frames, exception type, message)."""
    frames, i = [], 0
    while i < len(lines):
        m = _FILE.match(lines[i])
        if m:
            code = lines[i + 1].strip() if i + 1 < len(lines) and lines[i + 1].startswith('    ') else ''
            rel = relative(m.group('file'))
            frames.append({'file': rel, 'line': int(m.group('line')), 'func': m.group('func'), 'code': code,
                           'side': where(rel)})
        i += 1
    last = [x for x in lines if x and not x.startswith(' ') and not x.startswith('Traceback')]
    head = last[-1] if last else ''
    exc, _, msg = head.partition(':')
    return frames, exc.strip(), msg.strip()


def parse(text):
    """The last (chained) traceback in `text` as a Failure dict, or None if there is none."""
    lines = text.splitlines()
    starts = [i for i, x in enumerate(lines) if x.startswith('Traceback (most recent call last):')]
    if not starts:
        return None
    # walk back over a chain: each link is introduced by one of _CHAIN two lines before its "Traceback"
    first = len(starts) - 1
    while first > 0 and any(lines[starts[first] - 2].strip() == c for c in _CHAIN if starts[first] >= 2):
        first -= 1
    blocks = []
    for k in range(first, len(starts)):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        block = lines[starts[k]:end]
        while block and (not block[-1].strip() or block[-1].strip() in _CHAIN):
            block = block[:-1]
        blocks.append(_one(block))
    frames, exc, msg = blocks[-1]
    return {'exception': exc, 'message': msg, 'frames': frames,
            'causes': [{'exception': e, 'message': m, 'frames': f} for f, e, m in blocks[:-1]]}


def _blank(code):
    code = re.sub(r"'[^']*'|\"[^\"]*\"", "''", code)
    return re.sub(r'\b\d+(\.\d+)?\b', '0', code)


def innermost(failure, side='repairable'):
    """The innermost frame on `side` of the boundary, over the chain (the causes first: they are deeper)."""
    for block in [c for c in failure['causes']] + [failure]:
        inner = [f for f in block['frames'] if f['side'] == side]
        if inner:
            return inner[-1]
    return None


def signature(failure):
    """What a past repair is retrieved by: the chain's exception types and the innermost repairable frame."""
    f = innermost(failure)
    return {'exceptions': [c['exception'] for c in failure['causes']] + [failure['exception']],
            'file': f['file'] if f else None, 'func': f['func'] if f else None,
            'code': _blank(f['code']) if f else None}


def escalate(failure):
    """Whether the obstacle is the Supervisor's: its innermost Genesis frame is protected, or nothing in it is
    repairable."""
    rep, prot = innermost(failure, 'repairable'), innermost(failure, 'protected')
    if rep is None:
        return True
    if prot is None:
        return False
    # the deepest frame of the innermost block decides: a fault raised inside a protected module is not Genesis's
    for block in [c for c in failure['causes']] + [failure]:
        sides = [f['side'] for f in block['frames'] if f['side'] in ('repairable', 'protected')]
        if sides:
            return sides[-1] == 'protected'
    return False
