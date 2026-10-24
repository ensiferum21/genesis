#!/usr/bin/env python3
"""Create the repository's research queue (`research_queue.json`, `autonomy/queue.py`) as it stood on 24 Oct 2026,
19:00 SGT, if it does not exist. After that the file is the state: update it through `autonomy.queue.Queue`."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy.queue import Queue  # noqa: E402


def build(path):
    q = Queue(path)
    if q.doc['directions']:
        raise SystemExit(f'{path} exists; update it through autonomy.queue.Queue')
    S = 'scripts/'
    q.add('B20_R130', 'Choice, instrument and interpretation separated', line='causal-science', priority=9,
          committed=True, resources={'cpu0_hours': 1.5}, script=S + 'b20r130_choice_instrument_interpretation.py',
          output='evidence/choice_instrument_interpretation_b20r130', preregistered='f812701', status='running',
          unlocks=['global-interpretation'])
    q.add('B20_R133', 'The Problem Compiler against the specialists (existing reductions executed)', line='compiler',
          priority=8, committed=True, resources={'cpu0_hours': 1.25}, script=S + 'b20r133_problem_compiler.py',
          output='evidence/problem_compiler_b20r133', preregistered='e8bc181', unlocks=['compiler-validated'])
    q.add('B20_R131', 'The cascade on a real case: dormant R129 rules against R130\'s interpretation',
          line='capability-graph', priority=7, committed=True, depends_on=['B20_R130'],
          resources={'cpu0_hours': 1.0}, script=S + 'b20r131_cascade.py', output='evidence/cascade_b20r131',
          preregistered='22385f7', unlocks=['cascade-value'],
          notes='needs R130 recorded (its record test is the trigger\'s evidence)')
    q.add('B20_R132', 'The four bottlenecks of invention: headroom, expressiveness, search, evaluation',
          line='engine-invention', priority=6, committed=True, resources={'cpu0_hours': 5.7},
          script=S + 'b20r132_invention_bottleneck.py', output='evidence/invention_bottleneck_b20r132',
          unlocks=['invention-bottleneck-diagnosed'], notes='preregistration after its development look')
    q.add('B20_R128', 'Improving the inventor (level 2), as preregistered', line='engine-invention', priority=5,
          committed=True, depends_on=['B20_R132'], resources={'cpu0_hours': 3.3},
          script=S + 'b20r128_improve_the_improver.py', output='evidence/improve_the_improver_b20r128')
    q.add('judge-v3-followup', 'Engine invention under a validated judge v3 (a new preregistered study)',
          line='engine-invention', priority=4, depends_on=['B20_R132'], requires=['judge-v3-validated'],
          notes='only if R132 validates v3 and the supervisor adopts it for the study')
    q.add('checkpoint', 'A fresh checkpoint with the release matrix (the last is B20_R118)', kind='operations',
          line='operations', priority=3, depends_on=['B20_R128'], resources={'cpu0_hours': 1.0})
    q.add('repr-language-build', 'A self-extending mathematical representation language (engineering, fixtures)',
          kind='build', line='representation', priority=6, notes='directive items 6-9; built on CPU 1 meanwhile')
    q.add('repr-language-study', 'First preregistered study of invented representations',
          line='representation', priority=2,
          depends_on=['repr-language-build', 'B20_R130', 'B20_R131', 'B20_R132', 'B20_R133', 'B20_R128'],
          unlocks=['representation-language'])
    q.add('reduction-invention', 'Genesis invents reductions between problem families (not only executes them)',
          line='compiler', priority=1, depends_on=['B20_R133'], requires=['representation-language'])
    q.add('B20_R134', 'The Difficulty Cartographer, redesigned with obstacles hidden from cheap statistics',
          line='diagnosis', priority=1)
    q.add('allocator-baselines', 'Omega-10: allocator regret against uniform, greedy and bandit baselines',
          line='operations', priority=1)
    for past, outcome in (('B20_R111', 'NOT_DEMONSTRATED'), ('B20_R112', 'NOT_DEMONSTRATED'),
                          ('B20_R115', 'NOT_DEMONSTRATED'), ('B20_R127', 'NOT_SHOWN')):
        q.record_past('engine-invention', past, outcome, False)
    q.diagnose('engine-invention', 'B20_R132', tags=['judge-v3-validated', 'invention-bottleneck-diagnosed'])
    q.record_past('causal-science', 'B20_R129', 'ADAPTIVE_SCIENTIST', True)
    q.save()
    return q


if __name__ == '__main__':
    print(build(ROOT / 'research_queue.json').summary())
