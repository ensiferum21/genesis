"""The autonomy layer (B20_R96): the parts that let Genesis run its own research loop, properly.

Daniel (21 Oct 2026): make the system more powerful, let it "recursively but properly improve and discover and make
itself better", and "use novel ways to solve the system issues". The adaptation cell (B20_R93) senses weaknesses and
proposes the next design; until now the builder turned each design into a study. These modules close that loop and
widen what is improved, each against a published failure mode of self-improving systems:

  * `archive`: a quality-diversity archive (MAP-Elites, Mouret and Clune 2015) of solver configurations over cells
    of host family, size and budget, with several objectives and a Pareto front; weaker entries stay as stepping
    stones and parents are drawn as in the Darwin Gödel Machine (performance, and fewer children), so search does not
    collapse onto one winner;
  * `adversary`: an evolutionary search over host-generator parameters for hosts where the system does worst against
    the champions or its own bound (co-evolving problems with solvers, as POET does), feeding the cell;
  * `qet`: the generic quality-at-equal-time study runner (fresh hosts, every arm in the sandbox, the MaxSAT
    Evaluation's anytime score, paired bootstrap against a margin, Bonferroni-split interim looks that stop when
    decided, certified bounds, time slices under the session's background limit);
  * `studygen`: turns a cell design into a preregistered study script (the design embedded, seeds drawn fresh and
    checked against every earlier script, the runner pinned by the tree's identity);
  * `loop`: propose, check, preregister, run in slices, record, rescan.

The membrane holds at every level: the loop cannot edit checkers, thresholds, scorers or its own evaluator; every
study is preregistered (script committed and its hash sent) before it runs; hosts are fresh; selection never sees a
sealed panel; negative results are recorded.
"""
