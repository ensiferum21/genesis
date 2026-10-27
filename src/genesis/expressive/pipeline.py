"""One generation of Daniel's pipeline over the engine language (X2, B20_R154; 27 Oct 2026, 14:33):

    ARA diagnoses the obstacle -> Genesis invents a structural repair -> the independent Judge verifies it ->
    the Consolidator preserves it -> Genesis resumes research with the improved workflow.

`generation` runs it once, with every step's evidence kept:
  1. **diagnose**: the ladder of `workflow` on the measures a study supplies (optional here: B20_R151 supplies them
     for the real workflow); a repair is attempted only where the diagnosis is EXPRESSIVENESS, unless the caller
     says otherwise;
  2. **invent**: Genesis's dev searches in Λ_k (`dev_search`, the research plane's own data) give the corpus;
     `library.learn` proposes the most compressive statement, one at a time;
  3. **verify**: each proposal goes to the language judge (`submit`, kernel side) as (Λ_k, Λ_k + s) with the claim;
     a refused statement's skeleton is excluded and the next best is proposed, up to `max_tries`;
  4. **preserve**: every decision goes to the consolidator (`consolidate`) when a vault is given;
  5. **resume**: the admitted statements make Λ_k+1; the corpus rewritten in it seeds the next generation.
Nothing here judges: the decision is the judge's verdict, which the research plane receives without its numbers.
"""
from ..candidate_kinds import mcx3 as K
from . import consolidate as C
from . import lambda1 as L1
from . import library as LL
from . import workflow as W


def generation(k, library, dev_search, submit, claim='search', max_new=2, max_tries=4, vault=None, measures=None,
               force=False, corpus=None):
    """Returns {'library', 'seeds', 'diagnosis', 'decisions', 'admitted', 'records'}."""
    out = {'generation': k, 'parent': library.version, 'decisions': [], 'admitted': [], 'records': []}
    if measures is not None:
        out['diagnosis'] = W.ladder(measures, seed=k)
        if out['diagnosis']['diagnosis'] != 'EXPRESSIVENESS' and not force:
            out.update(library=library, seeds=list(corpus or []))
            return out
    corpus = list(corpus) if corpus is not None else dev_search(library)
    texts = [c['prog'] if isinstance(c, dict) else c for c in corpus]
    exclude, tries, letter = set(), 0, 0
    while len(out['admitted']) < max_new and tries < max_tries:
        cand, rewritten, steps = LL.learn(texts, library, k=1, generation=k, exclude=exclude, first=letter)
        if not steps:
            break
        tries += 1
        letter += 1
        name = steps[0]['name']
        verdict = submit(library.to_json(), cand.to_json(), [name], claim, corpus)
        decision = dict(verdict, claim=claim)
        out['decisions'].append({'name': name, 'body': steps[0]['body'], **decision, 'step': steps[0]})
        if vault is not None:
            out['records'].append(C.consolidate(vault, library, cand, [name], decision, ledger_entry=tries))
        if verdict['admitted']:
            out['admitted'].append(name)
            library = cand
            texts = rewritten
            corpus = [dict(c, prog=t) if isinstance(c, dict) else t for c, t in zip(corpus, texts)]
        else:
            exclude.add(steps[0]['body'])
    out.update(library=library, seeds=corpus)
    return out


def expanded_seeds(seeds, library):
    """The seeds as kind configurations (calls expanded), for a search that does not know the library."""
    return [L1.config(s, library) if isinstance(s, dict) else K.render(L1.expand(L1.surface(s, library), library))
            for s in seeds]
