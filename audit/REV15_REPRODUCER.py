"""Benign negative regression: no sealed tasks, no external code or private data."""
import json
from gap_engine.adapters.induction.theory import Theory, Equation
from gap_engine.adapters.induction.checker import LemmaStore, CheckError
from gap_engine.adapters.induction.adapter import InductionWorld
from gap_engine.kernel.sealed import SealedStore

th = Theory.default()
store = LemmaStore(th)
store.verify('L', Equation(('Z',),('Z',)), {'rule':'rewrite','left':[],'right':[]})
false = Equation(('Z',),('S',('Z',)))
world = InductionWorld('audit', th, store, ['L'], [], {'DEV':[false], 'SELECT':[], 'CONFIRM':[]}, SealedStore())
result={'baseline':world.run_library([], 'DEV', 1).tolist()}
store.lemmas['L']=false
try:
    result['forged_public_lemma']=world.run_library([], 'DEV', 1).tolist()
except Exception as exc:
    result['forged_public_lemma']={'blocked':type(exc).__name__, 'reason':str(exc)}
store.lemmas['L']=Equation(('Z',),('Z',))
world.theory=th.copy()
world.theory.defs['plus'][0].rhs=('S',('?', 'y'))
world.tasks['DEV']=[Equation(*th.parser().parse_eq('plus Z Z = S Z'))]
try:
    result['detached_theory']=world.run_library([], 'DEV', 1).tolist()
except Exception as exc:
    result['detached_theory']={'blocked':type(exc).__name__, 'reason':str(exc)}
print(json.dumps(result,sort_keys=True))
