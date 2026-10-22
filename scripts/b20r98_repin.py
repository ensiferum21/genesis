#!/usr/bin/env python3
"""B20_R98 (engineering): pins of external tools cover what the tool is, not where or when it was installed.

    PYTHONPATH=src python3 scripts/b20r98_repin.py [--wheel WHEEL]     every pinned tool's digest against its pin

**The defect, found when the tools were rebuilt in a new container (22 Oct 2026).** Two pins depended on the build
environment rather than on the tool:
  * `cpsat-v1` pinned the installed OR-Tools tree by a digest over every file. pip writes
    `*.dist-info/direct_url.json` with the absolute path the wheel was installed from, and `RECORD` lists it. The
    pinned wheel (SHA-256 `ebd5aea0…3c9a`), installed from another folder, gave 336 library files byte-identical to the
    wheel's members and a tree digest `4e6f0f66…` against the pin `fb5ef9ac…`: only pip's metadata differed. B20_R76's
    "a reinstall gives the same digest" held only for a reinstall from the same folder.
  * Aperture (2024, `maxsat-anytime-v1`) and Aperture 2026 (`maxsat-anytime-2026-v1`) embed a build stamp: one
    string `date; uname` output ("Thu Oct 22 22:07:48 +08 2026 Linux vm 6.18.44-fc-v140 x86_64"), written by their
    bundled SAT solvers' configure scripts. B20_R87 recorded that a rebuild differs in these bytes only. Rebuilt from
    the pinned sources, both differ from their pins; a search of the original build window (20 Oct 2026, 03:00-08:00
    UTC, each second) found no stamp that reproduces the old pin (the host name or kernel string must differ too).
    The other nine solver binaries rebuilt byte-identical to their pins.

**The repair.**
  * `cpsat.tree_digest` leaves out pip's install-time metadata (`direct_url.json`, `INSTALLER`, `REQUESTED`, `RECORD`
    in `*.dist-info`); `cpsat.wheel_digest(WHEEL)` computes the same digest from the wheel's own members, so the pin
    is a function of the pinned wheel alone. New pin `2010e03a…e47a` (from the tree and from the wheel alike).
  * `maxsat.binary_digest` (used by both MaxSAT kinds and the large kind) zeroes a build stamp (`maxsat.STAMP`: a
    `date` line followed by `Linux …`) and, when there is one, the GNU build-id note (a hash the linker computes over
    the binary, stamp included) before hashing. Binaries without a stamp hash exactly as before, so nine pins are
    unchanged. The two Aperture pins are the masked digests of the 22 Oct rebuilds; a second rebuild of each into
    another directory, 40-50 minutes later, differed from the first in 23 and 25 bytes (the stamp's clock digits and
    the 20-byte build-id) and gives the same masked digest. **Disclosed:** that the 22 Oct Aperture binaries equal
    B20_R87's outside those bytes rests on B20_R87's recorded rebuild check (22 bytes); the original binaries are not
    available here to compare.

**Identity.** The repair changes `cpsat.py`, `maxsat.py` and `maxsat2026.py`, hence the identity of every descriptor of
`cpsat-v1`, `maxsat-anytime-v1`, `maxsat-anytime-2026-v1` and `maxsat-anytime-large-v1`. As B20_R67 did for its core
edit, evidence is never rewritten: record tests of evidence recorded before B20_R98 compare the ids and digests they
recorded with `pre_r98_id` and the PRE_R98 constants, which accept exactly the descriptor this code builds with the
three files as they were before B20_R98, and nothing else.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import digest  # noqa: E402

# The three kind files as they were before B20_R98 (unchanged from B20_R92's commit 9602505 for the MaxSAT kinds and
# from B20_R76's 7e9d822 for cpsat.py, through commit ee298c9); every descriptor recorded before B20_R98 hashes these.
PRE_R98_FILES = {'candidate_kinds/cpsat.py': 'fb724423e9a8ca82422decdb24b08eb7efb175f669c875e82aae7cc3f3c791bd',
                 'candidate_kinds/maxsat.py': '0320d4775674d97434bce669be6fd5328de89e34cae7ceee053b031739172b73',
                 'candidate_kinds/maxsat2026.py': '549cd6e8f5f14972f70bc5e1b211cbbb5ef1330f8d1b6a796d18e2f9b914e904'}
PRE_R98_TREE_SHA256 = 'fb5ef9ac7eddfbf80c9e27678df204400c6f913d41c500f24a50f9f4996d67f9'
PRE_R98_BINARY_SHA256 = {'aperture': 'd2d8155ede698f5615466990bd6f067080624bbe4c605abb052e0fe49a74c45d',
                         'aperture-2026': '0fb72956e3c9c41c31626910b6b0ef26fc47f01d361d0e421b3f1100dec4b511'}


def pre_r98_id(desc):
    """The id a descriptor built by this code had before B20_R98: the same body with the pre-R98 digests of whichever
    of the three files its identity holds; a descriptor holding none of them is unchanged."""
    impl = desc.get('implementation', {})
    if not set(impl) & set(PRE_R98_FILES):
        return desc['descriptor_id']
    body = {k: v for k, v in desc.items() if k != 'descriptor_id'}
    body['implementation'] = dict(impl, **{f: h for f, h in PRE_R98_FILES.items() if f in impl})
    return digest(body)


def report(wheel=None):
    from genesis.candidate_kinds import cpsat as K, maxsat as MS, maxsat2026 as M26
    out = {'cpsat': {'tree': K.tree_digest(), 'pin': K.SOTA_TREE_SHA256}}
    if wheel:
        out['cpsat']['from_wheel'] = K.wheel_digest(wheel)
    for mod in (MS, M26):
        for k, s in mod.SOLVERS.items():
            out[k] = {'binary': s['binary'], 'digest': MS.binary_digest(s['binary']), 'pin': s['sha256']}
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    wheel = argv[argv.index('--wheel') + 1] if '--wheel' in argv else None
    r = report(wheel)
    print(json.dumps(r, indent=1))
    ok = r['cpsat']['tree'] == r['cpsat']['pin'] and r['cpsat'].get('from_wheel', r['cpsat']['pin']) == r['cpsat']['pin']
    ok &= all(v['digest'] == v['pin'] for k, v in r.items() if k != 'cpsat')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
