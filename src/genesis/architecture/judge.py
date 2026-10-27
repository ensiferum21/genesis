"""The judge harness for architecture claims (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §7; ARA-1). **Kernel side**:
research-plane modules never import this module (`tests_genesis/test_architecture_boundary.py`), and its digest is
pinned by a test, as `autonomy/feedback.py`'s is; a change to it is a human-gated amendment.

The harness holds the zoo's sealed seed. It opens environments (`open`), hands ARA a `View`, and judges what is
submitted to it:

  1. **Correctness**: the variant AG type-checks and keeps the incumbent's kernel (`graph.admissible`).
  2. **Reproducibility**: re-executed by the harness from the AG and the seed on a fresh view of the same dev split,
     it gives the same fitted policy and the same charges as the submitter reported.
  3. **Budget accounting**: the units the submitter spent through its view (introspection, diagnosis, synthesis and
     development evaluation, all counted by the view itself) are at most the matched budget.
  4. **The sealed decision**: on the sealed tasks (fresh draws from the sealed seed, never in any view), the
     variant's noise-free value minus the incumbent's, in units of the attainable range (oracle minus the best single
     option), is at least MATERIAL.
A promotion needs all four. The submitter receives the verdict and which check failed, never a sealed number; the
numbers go to the harness's ledger, which only the study reads after the run (with the planted key, `key`).
Controls (incumbent with the whole budget, tuning-only, blind rewrite) are submitted the same way, under their arm's
name, and judged by the same rule.
"""
import copy

from . import graph as G
from . import zoo as Z

MATERIAL = 0.05


class Harness:
    def __init__(self, sealed_seed):
        self._seed = sealed_seed
        self._envs = {}
        self._ledger = []

    def open(self, index, cls=None):
        """A fresh view of the index-th environment (each call a new view with its own unit count)."""
        if index not in self._envs:
            self._envs[index] = Z.environment(index, self._seed, cls)
        view = self._envs[index].view()
        return view

    def _env(self, index):
        return self._envs[index]

    def _range(self, env):
        best_single = max(env.value('sealed', [c] * len(env.graphs['sealed'])) for c in range(Z.K))
        return env.oracle('sealed') - best_single

    def sealed_value(self, index, policy):
        env = self._envs[index]
        return env.value('sealed', G.choose(policy, env.graphs['sealed']))

    def submit(self, index, arm, variant, claimed, units_spent, matched_units):
        """Judge a variant AG for environment `index`. `claimed` is the submitter's execution record of the variant
        on dev_a ({policy, charges, seed}); `units_spent` what it spent (its view's units and its sense units).
        Returns {promoted, failed}."""
        seed = claimed.get('seed', 0)
        env = self._envs[index]
        incumbent = env.incumbent
        rec = {'index': index, 'arm': arm, 'variant': copy.deepcopy(variant), 'class': G.classify(incumbent, variant),
               'units_spent': units_spent, 'matched_units': matched_units}
        failed = None
        why = G.admissible(incumbent, variant) if G.classify(incumbent, variant) != 'NONE' else None
        if why:
            failed = 'correctness: ' + why
        if failed is None:
            again = G.execute(variant, env.view(), 'dev_a', seed=seed)
            if again['policy'] != claimed.get('policy') or again['charges'] != claimed.get('charges'):
                failed = 'reproducibility: the re-execution differs from the claim'
        if failed is None and units_spent > matched_units + 1e-9:
            failed = f'budget: {units_spent} units against {matched_units} matched'
        inc = G.execute(incumbent, env.view(), 'dev_a', seed=seed)
        v_inc = self.sealed_value(index, inc['policy'])
        v_var = self.sealed_value(index, claimed['policy']) if claimed.get('policy') else v_inc
        rng = self._range(env)
        gain = (v_var - v_inc) / rng if rng > 1e-12 else 0.0
        if failed is None and not gain >= MATERIAL:
            failed = 'sealed: the gain is below MATERIAL'
        rec.update({'incumbent_value': v_inc, 'variant_value': v_var, 'oracle': env.oracle('sealed'),
                    'range': rng, 'gain': gain, 'promoted': failed is None, 'failed': failed,
                    'size': G.size_of(variant)})
        self._ledger.append(rec)
        return {'promoted': failed is None, 'failed': failed.split(':')[0] if failed else None}

    def ledger(self):
        """For the study, after the run: every submission with its sealed numbers."""
        return copy.deepcopy(self._ledger)

    def key(self, index):
        """For the study, after the run: the planted class and its location."""
        env = self._envs[index]
        return {'class': env.cls, 'location': Z.LOCATION[env.cls]}

    def oracle_key(self, index, seed=0):
        """The oracle-key arm (labelled; an upper reference): the planted remedy's sealed gain."""
        env = self._envs[index]
        r = G.execute(env.remedy(), env.view(), 'dev_a', seed=seed)
        inc = G.execute(env.incumbent, env.view(), 'dev_a', seed=seed)
        rng = self._range(env)
        gain = (self.sealed_value(index, r['policy']) - self.sealed_value(index, inc['policy']))
        return gain / rng if rng > 1e-12 else 0.0


__all__ = ['MATERIAL', 'Harness']
