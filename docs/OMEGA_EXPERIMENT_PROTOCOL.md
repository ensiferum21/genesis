# Genesis Ω: experiment protocol (master implementation contract §14, §18)

The protocol every Ω claim follows. It extends the batch protocol of `docs/HANDOVER.md` §3, which still applies.

1. **Preregistration.** One script per study. Its docstring states, before any run:
   - the question;
   - the worlds or instances, with fresh seed ranges disjoint from every other script's (a design test checks this);
   - the arms;
   - the primary measure;
   - the tests and their multiplicity correction (Holm across a primary family);
   - the verdict rule;
   - every development look (its seeds, which are never reused);
   - the expectation;
   - the cost.

   The script and its design tests are committed (through the index while another study runs) before it runs.
2. **Splits.** The roles are disjoint:
   - calibration worlds fit models and thresholds;
   - training splits (A) feed inventors;
   - the judge's splits (B, C) confirm only improvements beyond its measured noise (feedback contract v2);
   - validation chooses among candidates;
   - test is used once;
   - transfer uses a shifted family.

   Development looks use separate seeds.
3. **Matched budgets.** Arms get the same CPU or the same number of experiments or evaluations. Invention and search
   costs are reported (`search_cpu_s`, `arm_cpu_s`). Common random numbers apply where possible: the lab is drawn
   once per world, so every strategy sees the same outcomes.
4. **Baselines.** Strong baselines are required:
   - the established method from the literature (LLC for linear latent models; the MaxSAT Evaluation 2026 entrants;
     BLS and MCX for max-cut);
   - random;
   - a non-adaptive variant;
   - an oracle as a labelled reference (never counted as Genesis);
   - for invention, fresh search at matched compute, random retrieval, and a null trigger.
5. **Statistics.** Paired tests (Wilcoxon signed-rank with zeros dropped, or sign tests) per world or instance. Each
   test has its effect size. Non-inferiority uses a stated margin. Holm runs across the primary family; secondary
   tests are reported uncorrected and labelled so.
6. **Validity.** Every answer passes its checker. Budgets and target counts are checked. Replays must reproduce
   recorded runs (B20_R131 replays B20_R129's searches). A failed validity check makes the study INVALID.
7. **Record.** A record test recomputes the verdict and every label from the saved rows. Where possible it re-derives
   the inputs: worlds regenerate from seeds, models recalibrate, runs replay. Then come the evidence README (against
   the stated expectation), the batch rows, the ledgers, and a literature check for any record or novelty candidate.
8. **Claims.** Only "DEV; licenses nothing". A result's rung on the novelty ladder is stated:

   syntactic → behavioural → mechanistic → verified useful → transferred → literature-checked → reviewed.

   Nothing above "verified useful in scope" is claimed without that rung's evidence.
