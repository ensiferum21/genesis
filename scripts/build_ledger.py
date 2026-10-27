#!/usr/bin/env python3
"""Build the W01 requirements ledger (roadmap §7 W01, §17).

Sources: the frozen specification's table of contents (spec/GENESIS_FINAL_SPECIFICATION.txt,
every numbered section), the reviewer roadmap (defects R-01..R-04, gates GV0..GV8,
workstreams W01..W28, experiments E0..E7) and the 137-entry engine catalogue
(src/genesis/registry.py). Every row gets one disposition from the roadmap's set:

  IMPLEMENTED_AND_ACCEPTED           passed its required INDEPENDENT checks (none yet)
  IMPLEMENTED_BOUNDED_PENDING_AUDIT  narrow behaviour exists and is tested here; acceptance outstanding
  SHARED_IMPLEMENTATION              realized by another module, with an explicit mapping and tests
  RESEARCH_HYPOTHESIS                concrete mechanism exists; efficacy not established
  NOT_IMPLEMENTED                    no adequate executable implementation
  DEFERRED_EXTENSION                 outside the named release scope (only with Daniel's agreement)
  RETIRED_AFTER_TEST                 tested and rejected or superseded, with evidence
plus NOT_A_REQUIREMENT for headings and informative text.

Implementation, local execution, independent verification and scientific
efficacy are separate columns. Every test reference is checked to exist (file,
and class when given) and every code path to exist; a row is never satisfied by
its name alone. Run: python3 scripts/build_ledger.py  (writes ledger/ and docs/).
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

B, S, H, N, D, R_, I = ('IMPLEMENTED_BOUNDED_PENDING_AUDIT', 'SHARED_IMPLEMENTATION', 'RESEARCH_HYPOTHESIS',
                        'NOT_IMPLEMENTED', 'DEFERRED_EXTENSION', 'RETIRED_AFTER_TEST', 'NOT_A_REQUIREMENT')
DISPOSITIONS = {'IMPLEMENTED_AND_ACCEPTED', B, S, H, N, D, R_, I}

# ---------- specification rows ----------
# id: (disposition, scope, code, tests, remaining, external blockers, efficacy, workstream)
K = 'src/genesis/kernel/'
G = 'tests_genesis/'
SPEC = {
    '1': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '1.1': (I, 'informative principle', [], [], [], [], 'N/A', 'W01'),
    '1.2': (B, 'claim boundary enforced as evidence axes + wording gate; no autonomous-science claim is made',
            [K + 'evidence.py', K + 'wording.py'], [G + 'test_evidence_kernel.py::Wording'], [], [], 'N/A', 'W02'),
    '1.3': (I, 'informative (non-goals)', [], [], [], [], 'N/A', 'W01'),
    '1.4': (I, 'heading-level objectives; realized by the rows below', [], [], [], [], 'N/A', 'W01'),
    '2': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '2.1': (B, 'SystemVersion with all §2.1 fields', [K + 'version.py'], [G + 'test_research_runtime.py'], [], [], 'N/A', 'W01'),
    '2.2': (B, 'research state in the event-sourced store; atomic CAS/export, crash-tested at 14 points, verified backup/restore',
            ['src/genesis/store.py', 'src/genesis/backup.py', 'src/genesis/faults.py'],
            [G + 'test_store.py', G + 'test_crash_consistency.py::StoreCrashes', G + 'test_backup_restore.py'],
            [], ['second supported machine'], 'N/A', 'W04'),
    '2.3': (N, 'capability/reachability/improver-quality quantities are defined, not measured',
            [], [], ['measured reachability and improver-quality estimates'], [], 'NOT_TESTED', 'W21'),
    '2.4': (B, 'authority invariant: children cannot gain budget or permissions', [K + 'authority.py'],
            [G + 'test_authority.py'], [], [], 'N/A', 'W04'),
    '2.5': (B, 'research as typed IR programs over 16 primitives (graph wedge)', ['src/genesis/ir.py'],
            [G + 'test_macros_market.py::IR'], ['other domains'], [], 'N/A', 'W18'),
    '3': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '3.1': (B, 'identity, CAS, ledger, receipts, authority, certificate replay, evaluator isolation, release gate',
            ['src/genesis/store.py', K + 'evidence.py', 'src/genesis/custodian.py', 'src/genesis/sandbox.py',
             'src/genesis/release_bundle.py'],
            [G + 'test_store.py', G + 'test_export_revocation.py', 'tests_certificates/test_certificate_custody.py',
             'tests_sandbox/test_escape.py'], ['independent audit of the repaired kernel (GV0)'], [], 'N/A', 'W02'),
    '3.2': (B, 'trust root outside the research account; CIRCULAR_JUSTIFICATION; revoked verifiers retire',
            [K + 'roles.py', K + 'evidence.py'], [G + 'test_role_registry.py', G + 'test_evidence_kernel.py::TrustGraph',
                                                  G + 'test_redteam_b14.py::KernelFindings'],
            [], ['root key held by an external party'], 'N/A', 'W02'),
    '3.3': (I, 'informative rationale', [], [], [], [], 'N/A', 'W01'),
    '4': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '4.1': (B, 'sixteen primitives with typed overloads (graph wedge only)', ['src/genesis/ir.py'],
            [G + 'test_macros_market.py::IR'], ['useful semantics outside the graph wedge'], [], 'N/A', 'W18'),
    '4.2': (B, 'IR node records, traces, replay, artifact references', ['src/genesis/ir.py'],
            [G + 'test_macros_market.py::IR', 'tests_certificates/test_certificate_custody.py'], [], [], 'N/A', 'W18'),
    '4.3': (B, 'epistemic effects with propagation; speculative taint resolved only by passing checks',
            [K + 'evidence.py'], [G + 'test_evidence_kernel.py::MathPromotion'], [], [], 'N/A', 'W02'),
    '4.4': (B, 'MRDL bounded graph vocabulary; typed representation grammar with Lean-checked obligations (B18)',
            ['src/genesis/mrdl.py', 'src/genesis/invention/representations.py'],
            [G + 'test_graphs.py', 'tests_formal/test_invention.py', G + 'test_relations.py',
             'tests_formal/test_relation_invention.py', G + 'test_quotients.py', G + 'test_decompositions.py',
             'tests_formal/test_quotient_invention.py', 'tests_formal/test_decomposition_invention.py',
             G + 'test_cuts.py', 'tests_formal/test_relaxation_invention.py', G + 'test_cuts_c4.py',
             'tests_formal/test_c4_generator.py', G + 'test_cuts_sf.py', 'tests_formal/test_sf_generator.py'],
            ['a generated representation with prospective utility (B20_R17/R19 relational decoders, B20_R26 quotients, '
             'B20_R27 decompositions and B20_R31/R36 generated inequalities are Lean-checked; DEV construction '
             'utility after cost was not shown in any of the six attempts; B20_R46 transferred the inequality '
             'generator to C4-free subgraphs, Lean-checked, utility untested)'],
            [], 'N/A', 'W10'),
    '5': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '5.1': (B, 'task contracts for two graph domains through the DomainAdapter interface (parse, exposure identity, '
                'candidate/evaluator views, validity, score, certified reference, obligations, cost, families, replay); '
                'formalization is fixed, not faithful-formalization research',
            ['src/genesis/domains.py', 'src/genesis/models.py', 'src/genesis/graphs.py',
             'src/genesis/formal_research/lean_domain.py'],
            [G + 'test_domain_adapters.py', G + 'test_graphs.py', 'tests_formal/test_formal_research.py'],
            ['faithful formalization at scale (B19 W17 links a few claims with Lean and executable checks)'], [],
            'N/A', 'W05'),
    '5.2': (B, 'identifiability over a finite hypothesis set: indistinguishable methods (declared by checked theorems or '
                'identical per-task results) are collapsed and reported UNRESOLVED; EIG, KG*, top-two, fixed and random '
                'selection compared under equal budgets on DEV (B19)',
            ['src/genesis/discovery/active.py', 'scripts/b19_discovery.py', 'scripts/b19_active_v2.py'],
            ['tests_formal/test_discovery.py::ActiveSelection'],
            ['richer hypothesis spaces and interventions', 'a sealed comparison'], [], 'NOT_TESTED', 'W14'),
    '5.3': (B, 'gap diagnosis macro (gap_engine)', ['src/genesis/macros.py'], [G + 'test_macros_market.py::Macros'],
            [], [], 'NOT_TESTED', 'W13'),
    '5.4': (B, 'bounded world ecology over solver programs', ['src/genesis/research.py', 'src/genesis/worldstep.py'],
            [G + 'test_macros_market.py::WorldLoop'], [], [], 'NOT_TESTED', 'W12'),
    '5.5': (B, 'construction (witness search) and obstruction (SAT/DRAT upper bounds, exact LP dual certificates with '
                'Lean-checked inequality validity) in one loop',
            ['src/genesis/verification/sat.py', 'src/genesis/macros.py', 'src/genesis/discovery/obstruction.py'],
            ['tests_certificates/test_sat_certificates.py', 'tests_certificates/test_certificate_custody.py',
             'tests_formal/test_discovery.py::LPCertificates'],
            [], [], 'N/A', 'W13'),
    '5.6': (B, 'certificate-first: optimality only with custody-held, replayed certificates',
            [K + 'evidence.py', 'src/genesis/verification/certificates.py'],
            ['tests_certificates/test_certificate_custody.py', G + 'test_redteam_b14.py::KernelFindings'], [], [],
            'N/A', 'W03'),
    '5.7': (B, 'sealed prospective evaluation protocol (request v3, anchor, custodian, receipts, preflight)',
            ['src/genesis/custodian.py', K + 'receipts.py', K + 'phases.py'],
            [G + 'test_external_custodian.py', G + 'test_phase_receipts.py', G + 'test_acceptance_regressions.py'],
            ['retention policy after confirmation'],
            ['independent custodian, fresh sealed pools', 'external time anchoring'], 'NOT_TESTED', 'W06'),
    '6': (I, 'heading; engine-level dispositions are in the catalogue rows', [], [], [], [], 'N/A', 'W01'),
}
for sid in ('6.1', '6.2', '6.3', '6.4', '6.5', '6.6', '6.7', '6.8', '6.9', '6.10'):
    SPEC[sid] = (I, 'engine family heading; see CAT-* rows for each named engine', [], [], [], [], 'N/A', 'W01')
SPEC.update({
    '7': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '7.1': (B, 'six orthogonal axes; effective levels re-derived on every read; only kernel-replayable evidence '
                '(re-run witness checks, replayed certificates, role-signed receipts) licenses a level',
            [K + 'evidence.py', K + 'replay_contracts.py'],
            [G + 'test_evidence_kernel.py', G + 'test_export_revocation.py', G + 'test_replay_contracts.py',
             G + 'test_b14_open4_contracts.py'],
            ['a Lean-package route for THEOREM_CHECKED; DEV rows bound to their execution evidence (B20R8-OPEN-1); '
             'contracts for every level exist since B20_R15 (exact, formal, DEV in B20_R8; causal, internal '
             'replication, priority in B20_R15)'], ['independent review of the B20_R8/R15 contracts'],
            'N/A', 'W02'),
    '7.2': (B, 'ghost semantics: no-ghost is never proof', ['src/genesis/macros.py', K + 'wording.py'],
            [G + 'test_macros_market.py::Macros', 'tests_formal/test_fol_ghosts.py'], [], [], 'N/A', 'W16'),
    '7.3': (B, 'BoundState v2 references lower witness check and a replayed certificate bundle',
            [K + 'evidence.py', 'src/genesis/worldstep.py'],
            ['tests_certificates/test_certificate_custody.py', G + 'test_evidence_kernel.py::MathPromotion'], [], [],
            'N/A', 'W03'),
    '7.4': (B, 'asserted wording derived per claim from its own effective levels (requested vs established); '
                'report.md generated from it; free prose checked at the floor',
            [K + 'wording.py', 'src/genesis/release_bundle.py'],
            [G + 'test_evidence_kernel.py::Wording', G + 'test_redteam_b14.py::F1BundleWholeObject',
             G + 'test_redteam_b14_round3.py::F8Vocabulary', G + 'test_external_review_b14.py::F01'],
            ['semantic contracts beyond generated math and committed statements'], [], 'N/A', 'W02'),
    '8': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '8.1': (B, 'c4_host_v2 with dual checkers, exact solvers <=24 edges, SAT/DRAT beyond; DEV-calibrated families '
                'with headroom (v1 panels: ceiling rate 1.0)',
            ['src/genesis/graphs.py', 'src/genesis/calibration.py', 'configs/dev_calibration.json'],
            [G + 'test_graphs.py', 'tests_certificates/test_sat_certificates.py', G + 'test_calibration.py'], [], [],
            'N/A', 'W05'),
    '8.2': (B, 'triangle_free_host_v1 transfer domain; DEV-calibrated family (round 2)',
            ['src/genesis/graphs.py', 'src/genesis/calibration.py', 'configs/dev_calibration.json'],
            [G + 'test_graphs.py', G + 'test_calibration.py'], ['a structurally more distant domain (E5)'], [],
            'NOT_TESTED', 'W05'),
    '8.3': (I, 'informative rationale', [], [], [], [], 'N/A', 'W01'),
    '9': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '9.1': (B, 'world = program + representation + lineage + metrics; explicit assumption worlds with checked '
                'consistency, implication, separation and transport (B18)',
            ['src/genesis/research.py', 'src/genesis/invention/worlds.py'],
            [G + 'test_research_runtime.py', 'tests_formal/test_invention.py'], [], [], 'N/A', 'W12'),
    '9.2': (B, 'Pareto promotion, dormancy and retirement records', ['src/genesis/research.py'],
            [G + 'test_macros_market.py::WorldLoop'], [], [], 'N/A', 'W12'),
    '9.3': (B, 'irreversibility as the market risk term', ['src/genesis/market.py'], [G + 'test_macros_market.py::Market'],
            [], [], 'N/A', 'W19'),
    '10': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '10.1': (B, 'component cover, transport, glue and re-check (local_to_global)', ['src/genesis/macros.py'],
             [G + 'test_macros_market.py::Macros'], ['learned covers'], [], 'NOT_TESTED', 'W13'),
    '10.2': (N, 'continuation', [], [], ['continuation engine'], [], 'NOT_TESTED', 'W13'),
    '10.3': (N, 'parameterized tractability and kernelization', [], [], ['FPT/kernelization engines'], [], 'NOT_TESTED',
             'W13'),
    '10.4': (S, 'approximation -> exact via greedy witness + SAT/DRAT completion; LP relaxation -> exact via exact '
                 'rational dual certificates and SAT/DRAT on the remaining gap (B19)',
             ['src/genesis/verification/sat.py', 'src/genesis/discovery/obstruction.py',
              'src/genesis/verification/lp_dual.py', 'src/genesis/verification/certificates.py'],
             ['tests_certificates/test_sat_certificates.py', 'tests_formal/test_discovery.py::LPCertificates',
              'tests_certificates/test_obstruction_custody.py'], [], [],
             'N/A', 'W13'),
    '11': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '11.1': (B, 'heterogeneous checks: dual predicates, SAT vs exhaustive, Lean comparator, model finder',
             ['src/genesis/graphs.py', 'src/genesis/verification/lean.py', 'src/genesis/modelfind.py'],
             ['tests_certificates/test_sat_certificates.py::AgreementWithExactSolvers', 'tests_formal/test_lean_checker.py',
              G + 'test_replay_contracts.py::FiniteCertified'],
             [], [], 'N/A', 'W23'),
    '11.2': (N, 'semantic parity syndromes', [], [], ['parity checks across representations'], [], 'NOT_TESTED', 'W23'),
    '11.3': (N, 'adaptive verification strength', [], [], ['risk-weighted verification policy'], [], 'NOT_TESTED', 'W23'),
    '12': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '12.1': (B, 'Modification records with hypothesis, prediction, rollback, authority_delta = 0',
             ['src/genesis/campaign.py'], [G + 'test_research_runtime.py'], [], [], 'N/A', 'W21'),
    '12.2': (B, 'DEV ablation/placebo controls; B19: factorial solver catalysis (removal, placebo, effort, conventional '
                 'alternative) and placebo/effort concept controls on fresh DEV tasks',
             ['src/genesis/evaluation.py', 'src/genesis/campaign.py', 'scripts/b19_discovery.py'],
             [G + 'test_research_runtime.py', 'tests_formal/test_discovery.py::Evidence',
              G + 'test_b14_open4_contracts.py::Causal'],
             ['a sealed catalysis study (E2)', 'registered interventions beyond the DSL program components (B20_R15 '
              'causal contract: signed ablation/placebo receipts whose arms replay as one registered intervention)'],
             [], 'NOT_TESTED', 'W15'),
    '12.3': (H, 'self-science loop exists on DEV; no supported causal gain', ['src/genesis/campaign.py'],
             [G + 'test_research_runtime.py'], ['prospective causal evidence'], [], 'UNESTABLISHED', 'W21'),
    '12.4': (B, 'better-improver test harness (sealed_improver_evaluation receipts, kernel rules); B20: DEV comparison of '
                 'learned vs fixed research policies over independent research runs (better-improver UNESTABLISHED)',
             [K + 'receipts.py', K + 'evidence.py', 'src/genesis/learning/research.py', 'scripts/b20_learning.py',
              'src/genesis/learning/partitions.py', 'src/genesis/learning/budget.py', 'src/genesis/learning/custody.py',
              'scripts/b20r3_e3_costaware.py', 'evidence/e3_costaware_b20r3/e3_summary.json',
              'scripts/b20r3_headroom_pilot.py', 'evidence/headroom_pilot_b20r3/README.md',
              'scripts/b20r6_family_search.py', 'evidence/family_search_b20r6/README.md',
              'scripts/b20r53_wolfram_headroom.py', 'evidence/wolfram_headroom_b20r53/README.md',
              'scripts/b20r54_wolfram_ceiling.py', 'evidence/wolfram_ceiling_b20r54/README.md',
              'scripts/b20r58_sf_pattern_selection.py', 'evidence/sf_pattern_selection_b20r58/README.md',
              'scripts/b20r60_gv4_fallback.py', 'handoff/gv4/FALLBACK_CLAIM_DRAFT.md'],
             [G + 'test_acceptance_regressions.py::RevocationAndTrust', 'tests_formal/test_learning.py',
              G + 'test_research_policy_v2.py', G + 'test_wolfram_headroom.py', G + 'test_wolfram_ceiling.py', G + 'test_sf_pattern_selection.py',
              G + 'test_gv4_fallback.py',
              'tests_formal/test_learning_partitions.py', G + 'test_research_resource_accounting.py',
              'tests_formal/test_successor_proof_custody.py'],
             ['a family with selection headroom (B20_R3 pilot: ORACLE - fixed <= 1 of 12 on six systems; the '
              'redesigned cost-aware policy is INFERIOR_DEV, 2W/3T/3L; B20_R53: Wolfram at the hard settings '
              'NO_HEADROOM, 1, 0, 1, 0 of 15; B20_R54: 6-node conjectures do not reach the ceiling, '
              'NO_CEILING_HEADROOM; B20_R58: sum-free pattern selection NO_HEADROOM; B20_R60: the fallback claim is '
              'drafted for the reviewer)', 'a sealed E3 study'],
             ['independent custodian; fresh panels'], 'UNESTABLISHED', 'W21'),
    '13': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '13.1': (N, 'minimal teaching sets', [], [], ['W20'], [], 'NOT_TESTED', 'W20'),
    '13.2': (N, 'critical periods and ordering', [], [], ['W20'], [], 'NOT_TESTED', 'W20'),
    '13.3': (N, 'teach, unteach, repair', [], [], ['W20'], [], 'NOT_TESTED', 'W20'),
    '14': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '14.1': (B, 'trace compilation (cognitive_compile) only', ['src/genesis/macros.py'],
             [G + 'test_macros_market.py::Macros'], ['higher compilation rungs'], [], 'NOT_TESTED', 'W18'),
    '14.2': (N, 'law ladder', [], [], ['W18'], [], 'NOT_TESTED', 'W18'),
    '14.3': (N, 'generative kernel objective', [], [], ['W22'], [], 'NOT_TESTED', 'W22'),
    '15': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '15.1': (B, 'trust tower: anchored pinned tools, circularity detection, revocation', [K + 'evidence.py', K + 'anchors.py'],
             [G + 'test_evidence_kernel.py::TrustGraph'], [], [], 'N/A', 'W22'),
    '15.2': (N, 'foundation lifting', [], [], ['external trust decision process'], ['external trust authority'],
             'NOT_TESTED', 'W22'),
    '15.3': (B, 'no self-certification: fixture grants never survive production paths; pins never arguments',
             [K + 'roles.py', K + 'evidence.py'],
             [G + 'test_acceptance_regressions.py::RevocationAndTrust', G + 'test_role_registry.py'], [], [], 'N/A', 'W02'),
    '16': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '16.1': (B, 'fixed engineering decisions (Python 3.13 locked with wheel-content fingerprints, SQLite single writer, '
                'CAS, Ed25519); supported platform as data with a host check',
             ['src/genesis/store.py', 'src/genesis/deployment.py', 'deployment/SUPPORTED_PLATFORM.json'],
             [G + 'test_store.py', G + 'test_deployment.py'], ['wheel download hashes (PyPI denied on the build host)'],
             ['registry access', 'second machine'], 'N/A', 'W04'),
    '16.2': (B, 'repository layout with kernel/research boundary enforced by test', [K + '__init__.py'],
             [G + 'test_architecture_boundaries.py'], [], [], 'N/A', 'W04'),
    '16.3': (B, 'campaign directory layout', ['src/genesis/store.py'], [G + 'test_store.py'], [], [], 'N/A', 'W04'),
    '16.4': (B, 'relational tables as a derived index from effective state', [K + 'index.py'],
             [G + 'test_relational_index.py', G + 'test_redteam_b14.py::KernelFindings'], [], [], 'N/A', 'W04'),
    '16.5': (B, 'hash-chained event envelope', ['src/genesis/store.py'], [G + 'test_store.py'], [], [], 'N/A', 'W04'),
    '16.6': (B, 'single-writer lock; WAL sidecars refused', ['src/genesis/store.py'],
             [G + 'test_matrix_classes.py::LoadAndConcurrency', G + 'test_store_recovery.py'], [], [], 'N/A', 'W04'),
    '17': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '17.1': (B, 'default limits enforced by DSL executor and OCI sandbox; root launcher enforces its own ceiling and budget',
             ['src/genesis/execution.py', 'src/genesis/sandbox.py', 'src/genesis/launcher.py'],
             ['tests_sandbox/test_escape.py::Resources', 'tests_sandbox/test_launcher.py::LauncherLifecycle'], [],
             ['containment must be re-run on a second supported host (R-04)'], 'N/A', 'W04'),
    '17.2': (B, 'profiles (commit/nightly/release matrix)', ['scripts/run_test_matrix.py'], [G + 'test_matrix_classes.py'],
             [], [], 'N/A', 'W04'),
    '17.3': (B, 'realized-CPU matching in the ladder and specialist arm; per-category resource account (discovery, '
                'inference per arm, verification, ground truth, memory; human time declared) and arm-fairness check '
                'recorded in sealed evidence and recomputed by the judge',
             ['src/genesis/ladder.py', 'src/genesis/resources.py', 'src/genesis/judge.py'],
             [G + 'test_ladder.py', G + 'test_resources.py'],
             ['independent audit of resource fairness (W07)'], [], 'N/A', 'W07'),
    '18': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '18.1': (B, 'split classes; CONFIRM labels are not sealing', ['src/genesis/models.py', 'src/genesis/custodian.py'],
             [G + 'test_custodian_registry.py'], [], [], 'N/A', 'W06'),
    '18.2': (B, 'exact, structural, elaborated, near-duplicate screening; oracle with query budget',
             [K + 'leakscan.py', 'src/genesis/exposure.py'], [G + 'test_leak_firewall.py', G + 'test_custodian_registry.py'],
             ['semantic equivalence beyond near duplicates (residual risk disclosed)'], [], 'N/A', 'W06'),
    '18.3': (I, 'historical evidence note (round-2 contamination stays invalidating)', [], [], [], [], 'N/A', 'W01'),
    '18.4': (B, 'claim ladder = evidence axes', [K + 'evidence.py'], [G + 'test_evidence_kernel.py'], [], [], 'N/A', 'W02'),
    '19': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '19.1': (B, 'Experiment A: corruption, mutation, rebuild, bundle verification, escape suite',
             ['src/genesis/store.py', 'src/genesis/release_bundle.py'],
             [G + 'test_matrix_classes.py', G + 'test_export_revocation.py', 'tests_sandbox/test_escape.py'],
             ['independent replay on a second host (E0); deployment/reproduce.py is ready for it'],
             ['second supported machine'], 'N/A', 'W04'),
    '19.2': (R_, 'Experiment B (Ghost Census kill gate): B13 KILL on its small DEV family (kept); B19 W16 diagnostic '
                 'on a 125-problem family of ten equational theories with Lean-replayed E proofs: RETIRE_NO_HEADROOM '
                 '(free true lemmas add nothing over the strongest baseline; the Ghost Census arms lose)',
             ['src/genesis/experiment_b.py', 'src/genesis/discovery/ghost_census.py'],
             ['tests_formal/test_fol_ghosts.py::ExperimentB', 'tests_formal/test_ghost_census.py'],
             ['a family where E needs lemmas (e.g. single-axiom systems)'], [], 'EFFECT_NOT_SUPPORTED', 'W16'),
    '19.3': (B, 'harness: campaign generations, custodian, receipts; B20_R7: sealed equational statement panels '
                 'generated by the custodian after freeze, frozen research successors run in the sandbox, every '
                 'claimed proof replayed in Lean by the custodian and again by the judge',
             ['src/genesis/campaign.py', 'src/genesis/custodian.py', 'src/genesis/learning/statement_panels.py',
              'src/genesis/learning/research_export.py'],
             [G + 'test_phase_receipts.py', G + 'test_statement_custody.py'], ['clean prospective Lean study'],
             ['independent custodian', 'a family with headroom (B20R3-OPEN-1)'], 'NOT_TESTED', 'W08'),
    '19.4': (B, 'harness only: transfer receipts and kernel rules', [K + 'receipts.py'],
             [G + 'test_acceptance_regressions.py'], ['E5'], ['independent custodian'], 'NOT_TESTED', 'W24'),
    '19.5': (B, 'kernel rules only; the custodian refuses improver evaluations until a lineage protocol exists',
             [K + 'receipts.py'], [G + 'test_acceptance_regressions.py'], ['E3', 'lineage protocol (B14-OPEN-3)'],
             ['independent custodian'], 'NOT_TESTED', 'W21'),
    '19.6': (B, 'kernel rules (consecutive, program-linked chains); B20_R4: campaigns write native research-lineage '
                 'records and the custodian accepts a generation request only for a transition in the qualifying chain',
             [K + 'receipts.py', 'src/genesis/lineage.py', 'src/genesis/campaign.py', 'src/genesis/custodian.py'],
             [G + 'test_evidence_kernel.py::Confirmation', G + 'test_redteam_b14.py::KernelFindings',
              G + 'test_campaign_lineage.py'], ['E4'],
             ['independent custodian'], 'NOT_TESTED', 'W21'),
    '20': (B, 'DSL baselines, CaDiCaL specialist under equal CPU, exact reference, ablation/placebo',
           ['src/genesis/ladder.py', 'src/genesis/dsl.py'], [G + 'test_ladder.py', G + 'test_dsl_equivalence.py'],
           ['frontier-model baseline (no model is used)'], [], 'N/A', 'W07'),
    '21': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '21.1': (B, 'evidence-derived reports with limitations', ['src/genesis/release_bundle.py', K + 'wording.py'],
             [G + 'test_redteam_b14.py::F1BundleWholeObject'], [], [], 'N/A', 'W02'),
    '21.2': (B, 'forbidden transformations rejected by the wording gate and stale-report refusal',
             [K + 'wording.py', 'src/genesis/release_bundle.py'], [G + 'test_export_revocation.py'], [], [], 'N/A', 'W02'),
    '22': (B, 'red-team catalogue: audit reproductions GI6-*, B14 R-01..R-03, three internal red-team rounds',
           ['audit/reproductions/r01_r02_b13.py', 'audit/redteam_b14_round3/README.md'],
           [G + 'test_gi6_legacy_paths.py', G + 'test_redteam_b14.py', G + 'test_redteam_b14_round2.py',
            G + 'test_redteam_b14_round3.py'],
           [], ['independent red team'], 'N/A', 'W02'),
    '23': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '23.1': (B, 'checkpoint policy: clean tree, matrix, record, manifest', ['scripts/make_checkpoint.py'],
             [G + 'test_matrix_classes.py'], [], [], 'N/A', 'W04'),
    '24': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '24.1': (I, 'informative list of unproven claims (kept visible in LIMITATIONS)', [], [], [], [], 'N/A', 'W01'),
    '24.2': (I, 'informative', [], [], [], [], 'N/A', 'W01'),
    '25': (B, 'design freeze: no new primitives; registry is data', ['src/genesis/registry.py'],
           [G + 'test_macros_market.py::Registry'], [], [], 'N/A', 'W22'),
    '26': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '26.1': (B, 'trial execution contract', ['src/genesis/campaign.py', 'src/genesis/execution.py'],
             [G + 'test_research_runtime.py'], [], [], 'N/A', 'W04'),
    '26.2': (B, 'evidence promotion through one licensing function', [K + 'evidence.py'],
             [G + 'test_evidence_kernel.py', G + 'test_acceptance_regressions.py'], [], [], 'N/A', 'W02'),
    '26.3': (B, 'world step', ['src/genesis/worldstep.py'], [G + 'test_macros_market.py::WorldLoop'], [], [], 'N/A', 'W12'),
    '26.4': (B, 'modification contract with authority_delta = 0', ['src/genesis/campaign.py'],
             [G + 'test_research_runtime.py'], [], [], 'N/A', 'W21'),
    '27': (B, 'Lean (sandboxed comparator, axiom audit), SAT/DRAT, exact, E prover (prover claims; THEOREM_CHECKED only '
              'after step-by-step Lean replay of the E proof object, B19)',
           ['src/genesis/verification/lean.py', 'src/genesis/verification/sat.py', 'src/genesis/verification/eprover.py',
            'src/genesis/formal_research/fof_lean.py'],
           ['tests_formal/test_lean_checker.py', 'tests_certificates/test_sat_certificates.py',
            'tests_formal/test_ghost_census.py::LeanReplay'],
           ['interval/numerical certificates'], [], 'N/A', 'W03'),
    '28': (B, 'provenance-bearing ingestion (pinned library verbatim; retrieved text as untrusted, screened data), exact '
              'quotes, notation resolution, Lean-checked and executable links, ambiguity records, adjudication queue, '
              'scoped novelty reports that never conclude novelty (B19)',
           ['src/genesis/literature.py', 'scripts/b19_literature.py', K + 'replay_contracts.py'],
           [G + 'test_literature.py', G + 'test_b14_open4_contracts.py::Priority'],
           ['broader ingestion (full texts, dated library snapshots); relations modulo the theory\'s laws (the B20_R15 '
            'priority contract relates statements syntactically)'], ['domain expert / priority reviewer'],
           'NOT_TESTED', 'W17'),
    '29': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '29.1': (N, 'software research (proposed DEFERRED_EXTENSION; needs Daniel\'s scope agreement)', [], [], ['W26'], [],
             'NOT_TESTED', 'W26'),
    '29.2': (N, 'empirical science (proposed DEFERRED_EXTENSION; needs scope agreement)', [], [], ['W27'],
             ['empirical operator'], 'NOT_TESTED', 'W27'),
    '29.3': (N, 'ML research (proposed DEFERRED_EXTENSION; needs scope agreement)', [], [], ['W25'],
             ['model/training resources'], 'NOT_TESTED', 'W25'),
    '30': (B, 'no network in generated code; credentials outside the sandbox', ['src/genesis/sandbox.py'],
           ['tests_sandbox/test_escape.py::Network'], [], [], 'N/A', 'W04'),
    '31': (B, '§31 checklist tracked in docs/REQUIREMENTS_AND_GAPS.md and this ledger', ['docs/REQUIREMENTS_AND_GAPS.md'],
           [G + 'test_ledger.py'], ['independent acceptance of each item'], ['auditor'], 'N/A', 'W01'),
    '32': (B, 'primitive contracts (graph wedge)', ['src/genesis/ir.py'], [G + 'test_macros_market.py::IR'],
           ['contracts for other domains'], [], 'N/A', 'W18'),
    '33': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '33.1': (B, 'signed scientific transitions bound to this campaign; envelope persisted before the phase; '
                 'verified phase re-derived from events with the same binding checks',
             [K + 'phases.py'], [G + 'test_phase_receipts.py', G + 'test_redteam_b14.py::F10SharedAcceptance',
                                 G + 'test_redteam_b14_round2.py::H1PhaseChain'], [], [], 'N/A', 'W04'),
    '33.2': (B, 'crash recovery from events.jsonl + CAS with quarantine; real-process crash injection at CAS write, '
                'commit, export, trial, freeze, generation commit, completion, request freeze, zip, custodian '
                'reservation/evaluation/signing/publication; campaign resume; custodian recover',
             ['src/genesis/store.py', 'src/genesis/faults.py', 'src/genesis/campaign.py', 'src/genesis/custodian.py'],
             [G + 'test_store_recovery.py', G + 'test_crash_consistency.py', G + 'test_redteam_b15.py'], [],
             ['independent review of the recovery semantics'], 'N/A', 'W04'),
    '34': (B, 'research market score, Pareto prefilter, diversity slot, calibration', ['src/genesis/market.py'],
           [G + 'test_macros_market.py::Market'], [], [], 'NOT_TESTED', 'W19'),
    '34.1': (B, 'stop-thinking rule', ['src/genesis/market.py'], [G + 'test_macros_market.py::Market'], [], [], 'N/A', 'W19'),
    '35': (B, 'leak scanner and contamination firewall', [K + 'leakscan.py'], [G + 'test_leak_firewall.py'], [], [],
           'N/A', 'W06'),
    '35.1': (B, 'canonicalization: alpha/structural, elaborated Lean fingerprints, graph WL+VF2', [K + 'leakscan.py'],
             [G + 'test_leak_firewall.py::Elaborated'], [], [], 'N/A', 'W06'),
    '36': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '36.1': (B, 'DomainAdapter interface: conformance suite for the graph adapters; the Lean statement adapter '
                '(B17) conforms with explicit UNSUPPORTED exact references and is not a sealed-receipt domain',
             ['src/genesis/domains.py', 'src/genesis/formal_research/lean_domain.py'],
             [G + 'test_domain_adapters.py', 'tests_formal/test_formal_research.py'], [], [], 'N/A', 'W05'),
    '36.2': (B, 'worked C4 flow = e2e walkthrough (re-run in B14: evidence/e2e_walkthrough_b14)',
             ['scripts/e2e_walkthrough.py', 'evidence/e2e_walkthrough_b14/final/walkthrough.json'], [], [], [], 'N/A', 'W05'),
    '36.3': (B, 'fixtures (hard panels, ladder answer key)', ['src/genesis/panels.py', 'src/genesis/ladder.py'],
             ['tests_certificates/test_hard_panels.py', G + 'test_ladder.py::AnswerKeyIntegrity'], [], [], 'N/A', 'W05'),
    '37': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '37.1': (B, 'Lean worker in sandbox for finite witness obligations; pinned Lean/Mathlib workspace (B17): '
                'pinned commits, import closure built offline without Lake cache, audited artifacts, mounted read-only',
             ['src/genesis/verification/lean.py', 'src/genesis/formal_research/workspace.py',
              'toolchain/FORMAL_WORKSPACE.json', 'toolchain/build_formal_workspace.py'],
             ['tests_formal/test_lean_checker.py', 'tests_formal/test_formal_research.py'],
             ['byte-identical workspace artifacts on a second machine'], [], 'N/A', 'W08'),
    '37.2': (B, 'trusted spec / untrusted proof / trusted check; axiom audit; leanchecker; module chains with '
                'per-binding statements, declaration extraction and dependency closure (B17)',
             ['src/genesis/verification/lean.py', 'src/genesis/formal_research/checker.py'],
             ['tests_formal/test_lean_checker.py::DefenceInDepth', 'tests_formal/test_formal_research.py::Acceptance',
              G + 'test_replay_contracts.py::TheoremChecked'],
             ['a Lean-package route (trusted statement modules such as the B17 theory package and the CRPD-2a '
              'codegree package) for THEOREM_CHECKED; B20_R8 covers equational custody'], [], 'N/A', 'W08'),
    '37.3': (B, 'theorem-memory rule with transitive revocation', [K + 'memory.py'],
             [G + 'test_leak_firewall.py::TheoremMemoryRule'], [], [], 'N/A', 'W06'),
    '38': (B, 'test and CI matrix; skips in release-blocking suites fail; clean-room reproduction driver',
           ['scripts/run_test_matrix.py', '.github/workflows/ci.yml', 'deployment/reproduce.py'],
           [G + 'test_matrix_classes.py', G + 'test_reproduce.py'], ['independent run on a second supported host (R-04)'],
           ['second machine'], 'N/A', 'W04'),
    '38.1': (B, 'seeded property loops under unittest', [G + 'test_store.py'], [G + 'test_store.py'],
             ['Hypothesis not installable here'], [], 'N/A', 'W04'),
    '39': (I, 'heading', [], [], [], [], 'N/A', 'W01'),
    '39.1': (B, 'resolved configuration', ['src/genesis/models.py'], [G + 'test_research_runtime.py'], [], [], 'N/A', 'W04'),
    '39.2': (B, 'CLI surface incl. verify-bundle exit status', ['src/genesis/cli.py'],
             [G + 'test_redteam_b14.py::F1BundleWholeObject'], [], [], 'N/A', 'W04'),
    '40': (B, 'walkthrough steps 1-13 with fixture roles (B14 re-run); step 14 not performed',
           ['scripts/e2e_walkthrough.py', 'evidence/e2e_walkthrough_b14/final/walkthrough.md'],
           [], [], ['external release authority for step 14'], 'N/A', 'W06'),
    '41': (H, 'meta-gap candidates recorded as hypotheses', ['src/genesis/worldstep.py'],
           [G + 'test_macros_market.py::WorldLoop'], ['primitive invention with prospective test'], [], 'UNESTABLISHED',
           'W22'),
    '41.1': (N, 'evidence that a primitive is genuinely new', [], [], ['W22'], ['independent semantic acceptance'],
             'NOT_TESTED', 'W22'),
    '42': (N, 'kernel minimization experiment', [], [], ['W22'], [], 'NOT_TESTED', 'W22'),
    '43': (B, 'replication bundle; verifier re-derives claims, files and certificates', ['src/genesis/release_bundle.py'],
           [G + 'test_export_revocation.py', G + 'test_redteam_b14.py::F1BundleWholeObject',
            'tests_certificates/test_certificate_custody.py'], [], ['independent replicator'], 'N/A', 'W03'),
    '44': (B, 'signed adjudication records for near duplicates', ['src/genesis/custodian.py'],
           [G + 'test_custodian_registry.py::PanelScreening'], ['expert-query optimizer'], ['domain expert'], 'N/A', 'W23'),
    '44.1': (N, 'optimal expert query', [], [], ['W23'], [], 'NOT_TESTED', 'W23'),
    '45': (B, 'threat model exercised by escape suite, audit reproductions and red-team regressions',
           ['src/genesis/sandbox.py'], ['tests_sandbox/test_escape.py', G + 'test_redteam_b14.py'], [],
           ['independent red team'], 'N/A', 'W04'),
    '46': (B, 'supported deployment: platform spec and host check, Python 3.13 lock, reproducible toolchain, role '
              'separation, recovery, reproduction driver (deployment/DEPLOYMENT.md); compute sizing not measured',
           ['deployment/SUPPORTED_PLATFORM.json', 'src/genesis/deployment.py', 'containers/Containerfile'],
           [G + 'test_deployment.py', G + 'test_reproduce.py'],
           ['pin image digest', 'second-machine matrix', 'compute sizing from measured runs'],
           ['registry access', 'second machine'], 'N/A', 'W04'),
    '47': (N, 'empirical-science adapter (proposed DEFERRED_EXTENSION; needs scope agreement)', [], [], ['W27'],
           ['empirical operator'], 'NOT_TESTED', 'W27'),
    '48': (B, 'completion labels assessed in docs; P0-P2 pending independent acceptance after R-01..R-03',
           ['docs/REQUIREMENTS_AND_GAPS.md'], [G + 'test_ledger.py'], ['GV0..GV7'], ['auditor', 'release authority'],
           'N/A', 'W01'),
})

ROADMAP = {
    'R-01': (B, 'signed evidence bound to the claim (kernel.receipts shared by all entry points); request facts '
                'checked against the campaign export', [K + 'receipts.py', 'src/genesis/custodian.py'],
             [G + 'test_acceptance_regressions.py', G + 'test_redteam_b14.py', G + 'test_redteam_b14_round2.py',
              G + 'test_redteam_b14_round3.py', G + 'test_external_custodian.py', G + 'test_redteam_b16.py'],
             [],
             ['independent source review (GV0)'], 'N/A', 'W02'),
    'R-02': (B, 'effective revocation in every export; verifier re-derives the bundle', ['src/genesis/release_bundle.py'],
             [G + 'test_export_revocation.py', G + 'test_redteam_b14.py::F1BundleWholeObject'], [],
             ['independent replay reviewer'], 'N/A', 'W02'),
    'R-03': (B, 'certificate custody and checker-only replay', ['src/genesis/verification/certificates.py'],
             ['tests_certificates/test_certificate_custody.py'], [], ['independent replay on another host'], 'N/A', 'W03'),
    'R-04': (B, 'supported platform spec + host check; one Python (3.13) across lock, pyproject, container and runtime; '
                'byte-reproducible tool builds with a gated pin-revision protocol; root launcher / unprivileged worker; '
                'crash-tested recovery; backup/restore; second-machine reproduction driver with deterministic '
                'reference results',
             ['src/genesis/deployment.py', 'src/genesis/launcher.py', 'toolchain/build_reproducible.sh',
              'toolchain/revise_pins.py', 'deployment/reproduce.py', 'containers/Containerfile'],
             [G + 'test_deployment.py', G + 'test_toolchain_revision.py', 'tests_sandbox/test_launcher.py',
              G + 'test_crash_consistency.py', G + 'test_backup_restore.py', G + 'test_reproduce.py',
              'tests_certificates/test_known_answers.py'],
             ['pinned image digest', 'wheel download hashes', 'reproduction on a second machine'],
             ['registry access', 'PyPI access', 'second machine and its operator'], 'N/A', 'W04'),
}
# Findings of the external B20 review (and one defect found while repairing them), B20_R1.
REVIEW = {
    'B20-REVIEW-01': (B, 'evaluation material globally disjoint from all research-visible material: one partition '
                         'builder with EXACT/ALPHA/INSTANCE/GENERALIZES screening, quarantine, explicit '
                         'INSUFFICIENT_DISTINCT_MATERIAL, frozen manifest, insertion screen on every route; the B20 '
                         'comparison stays contaminated (3 statements, 4 slots)',
                      ['src/genesis/learning/partitions.py', 'audit/review_b20/reproduce_b20_review.py',
                       'scripts/b20r_e3_fresh.py', 'evidence/e3_fresh_b20r/partition_evaluation.json'],
                      ['tests_formal/test_learning_partitions.py'],
                      [], ['independent source review (GV0)'], 'N/A',
                      'W19'),
    'B20-REVIEW-02': (B, 'research budget authority: account opened before preparation, every category charged, '
                         'reservations before launch, cgroup-metered outer kill, no rounding up, late results never '
                         'credited, interrupted reservations charged on restart, GrantLedger bridge',
                      ['src/genesis/learning/budget.py', 'src/genesis/learning/research.py',
                       'src/genesis/learning/macros.py'],
                      [G + 'test_research_resource_accounting.py'],
                      [], ['independent source review (GV0)'],
                      'N/A', 'W19'),
    'B20-REVIEW-03': (B, 'successor proof custody: run-bound lemma uids, per-target proof records, pure validators, '
                         'replay from custody only, prover-reported / checked / eligible kept apart',
                      ['src/genesis/learning/custody.py'], ['tests_formal/test_successor_proof_custody.py'],
                      ['checked coverage of every scored success in the fresh study'],
                      ['independent replay on another host'], 'N/A', 'W19'),
    'B20-REVIEW-04': (B, 'joint construction/obstruction custody: certificate bundle v2 with witness, exact LP '
                         'certificate and CNF/DRAT bytes; separate LP checker; kernel promotion and revocation; '
                         'custody-complete DEV re-run (new execution; B19 record unchanged)',
                      ['src/genesis/verification/lp_dual.py', 'src/genesis/verification/certificates.py',
                       'src/genesis/discovery/obstruction.py', 'scripts/b20r_obstruction_custody.py'],
                      ['tests_certificates/test_obstruction_custody.py'], [],
                      ['independent replay on another host'], 'N/A', 'W13'),
    'B20R-NEW-01': (B, "E's '%% SZS status ResourceOut' line was parsed as ERROR; timeouts are now RESOURCE_OUT "
                       '(labels only: B20 counted PROVED from THEOREM, so recorded scores are unaffected)',
                    ['src/genesis/verification/eprover.py'],
                    [G + 'test_research_resource_accounting.py::ProverStatus'], [], [], 'N/A', 'W19'),
}
GATES = {f'GV{i}': (N, t, [], [], [], b, 'NOT_TESTED' if i >= 2 else 'N/A', w) for i, t, b, w in (
    (0, 'trust repaired: R-01..R-04 closed, no critical evidence-integrity defect open',
     ['R-04 second-machine acceptance', 'independent source review'], 'W02'),
    (1, 'bounded platform accepted', ['independent release-matrix run', 'audited bundle'], 'W04'),
    (2, 'real formal discovery loop', ['independent replay of the B17 theory package',
                                       'conjectures and proofs beyond builder templates and rediscovery'], 'W08'),
    (3, 'useful verified discovery on fresh tasks', ['independent custodian', 'fresh panels',
                                                   'reviewer and statistician sign-off of e1-hard-v2 and the E1/E1b '
                                                   'DRAFTs (B20_R24: both READY_FOR_REVIEW on DEV; same-operator '
                                                   'rehearsals SUPPORTED, judge agrees)'], 'W13'),
    (4, 'better improver', ['independent search runs', 'sealed downstream evaluation'], 'W21'),
    (5, 'three compounding generations', ['fresh panels per transition'], 'W21'),
    (6, 'meaningful transfer to a structurally different domain', ['different formal domain'], 'W24'),
    (7, 'independent replication', ['another operator, host and keys'], 'W24'),
    (8, 'extended science validation', ['domain-specific studies'], 'W25'))}
WORKSTREAMS = {
    'W01': ('Requirements, status and specification reconciliation', B, ['scripts/build_ledger.py'], [G + 'test_ledger.py']),
    'W02': ('Evidence and release authority', B, [K + 'receipts.py', K + 'evidence.py'], [G + 'test_acceptance_regressions.py']),
    'W03': ('Certificate custody and independent replay', B, ['src/genesis/verification/certificates.py',
                                                             'src/genesis/verification/lp_dual.py'],
            ['tests_certificates/test_certificate_custody.py', 'tests_certificates/test_obstruction_custody.py']),
    'W04': ('Deployment, isolation, recovery and reproducibility', B,
            ['src/genesis/deployment.py', 'src/genesis/launcher.py', 'src/genesis/backup.py', 'src/genesis/faults.py',
             'deployment/reproduce.py', 'docs/OMEGA_NO_LLM_AUDIT.md', 'docs/OMEGA_ARCHITECTURE.md', 'docs/OMEGA_OPERATIONS.md'],
            [G + 'test_deployment.py', G + 'test_crash_consistency.py', G + 'test_backup_restore.py',
             'tests_sandbox/test_launcher.py', G + 'test_reproduce.py', G + 'test_no_llm.py', G + 'test_omega_boundary.py']),
    'W05': ('Domain contracts and calibration (B20_R12/R24: separately versioned study rules e1-hard-v1/v2; B20_R30: '
            'the calibration\'s 60 s certification limit and the evaluator\'s 600 s measured on the e1b family; B20_R33: '
            'an exact MIP baseline proves every e1b optimum within 0.36 CPU s; B20_R34: no MIP-hard certifiable setting '
            'within the 200-edge bound; B20_R38: E1 beyond the exact MIP in a dense regime certified by generated rows; '
            'B20_R41: E1d readiness under the DRAFT rule e1-hard-v3-draft, READY_FOR_REVIEW against HiGHS at 4x budget; '
            'B20_R43: E1d DRAFT package and a SUPPORTED same-operator rehearsal through the v5 path; '
            'B20_R44: registered ablation of the discovered representation, READY_FOR_REVIEW, null control clean; '
            'B20_R45: the ablation evaluation rehearsed through the v5 custody path, SUPPORTED; '
            'B20_R63: the advantage over HiGHS ends between 8x and 16x its budget, CROSSOVER_AT_8S; '
            'B20_R64: it grows with host size, holding at 64x at n60, ADVANTAGE_GROWS, DEV; '
            'B20_R66: the n60 lead replicates on fresh hosts and holds at 120x, REPLICATED_ADVANTAGE_THROUGH_120X, DEV; '
            'B20_R68: a standard max-cut tabu search ties the candidate on the calibrated settings and beats it at n60, '
            'E1D_MATCHES_DOMAIN_HEURISTIC, DEV; B20_R70: by time-to-solution the candidate is slower than simulated '
            'bifurcation and tabu search and scales worst, E1D_SLOWER_THAN_SOME, DEV; B20_R73: multiverse analysis, '
            '12 of 18 contrasts robust, B20_R68 Part B fragile)', B,
            ['src/genesis/domains.py', 'src/genesis/calibration.py', 'configs/dev_calibration.json',
             'evidence/certification_budget_b20r30/summary.json', 'evidence/strong_baseline_audit_b20r33/summary.json',
             'evidence/mip_hard_probe_b20r34/summary.json', 'evidence/dense_strong_baseline_b20r38/summary.json',
             'evidence/e1d_readiness_b20r41/summary.json', 'evidence/e1d_package_b20r43/summary.json',
             'evidence/e1d_ablation_b20r44/summary.json', 'evidence/e1d_ablation_rehearsal_b20r45/rehearsal_summary.json',
             'scripts/b20r63_e1d_crossover.py', 'evidence/e1d_crossover_b20r63/summary.json',
             'scripts/b20r64_e1d_scaling.py', 'evidence/e1d_scaling_b20r64/summary.json',
             'scripts/b20r66_e1d_n60.py', 'evidence/e1d_n60_b20r66/summary.json',
             'scripts/b20r68_e1d_domain_heuristic.py', 'evidence/e1d_domain_heuristic_b20r68/summary.json',
             'scripts/b20r70_tts_scaling.py', 'evidence/tts_scaling_b20r70/summary.json',
             'scripts/b20r73_multiverse.py', 'evidence/multiverse_b20r73/summary.json', 'src/genesis/compiler/bqp.py', 'src/genesis/compiler/families.py', 'src/genesis/compiler/backends.py', 'src/genesis/compiler/contracts.py', 'scripts/b20r133_problem_compiler.py', 'scripts/b20r135_invented_representations.py', 'evidence/invented_representations_b20r135/summary.json', 'docs/checkpoints/B20_R135_RECORD.md', 'docs/OMEGA_REPRESENTATION_LANGUAGE.md', 'src/genesis/representation/gadgets.py', 'src/genesis/representation/encodings.py', 'evidence/problem_compiler_b20r133/summary.json'],
            [G + 'test_domain_adapters.py', G + 'test_calibration.py', G + 'test_calibration_rules.py',
             G + 'test_certification_budget.py', G + 'test_strong_baseline_audit.py', G + 'test_mip_hard_probe.py',
             G + 'test_dense_strong_baseline.py', G + 'test_e1d_readiness.py', G + 'test_e1d_package.py',
             G + 'test_e1d_ablation.py', G + 'test_e1d_ablation_rehearsal.py', G + 'test_e1d_crossover.py',
             G + 'test_e1d_scaling.py', G + 'test_compiler.py', G + 'test_problem_compiler_study.py', G + 'test_invented_representations.py', G + 'test_representation_gadgets.py', G + 'test_representation_encodings.py', G + 'test_representation_families.py', G + 'test_representation_library.py', G + 'test_representation_processes.py']),
    'W06': ('Independent custody and preregistration (B20_R40: candidate registry v2 with per-kind identity and an '
            'exact-MIP baseline kind; B20_R42: wired opt-in through request v5 and a registry dispatcher, not adopted; '
            'B20_R67: the kind map moved out of the hashed core, a kind bound to its dispatched module, and a '
            'max-cut tabu domain-baseline kind; B20_R69: simulated-bifurcation and extremal-optimization kinds; '
            'B20_R71: the representation engine with physics move rules; B20_R72: they do not improve it, '
            'NO_GENERAL_IMPROVEMENT, DEV; B20_R74: MQLib BURER2002 as a pinned external baseline; B20_R75: the '
            'state-of-the-art comparison INVALID_CPU_DELIVERY, a kind defect caught by the validity check; B20_R76: '
            'CP-SAT installed from a supplied wheel as cpsat-v1, and the comparison with CP-SAT and the fixed '
            'BURER2002 UNRESOLVED; B20_R77: hybrid-swap-v1, a cut portfolio with (1,2)-swap local search, and its '
            'powered comparison with CP-SAT and BURER2002, ENGINE_BEATS_SOTA on DEV; B20_R78: a closed solver language, '
            'solver-program-v1 and a program search; B20_R79: the system searches for its own solver; B20_R80: a '
            'random-program control; B20_R81: the self-found solver against the builder engine and the tools; B20_R82: '
            'a library language so that generations compound; B20_R83-R86: three generations, a control and '
            'their test; B20_R104-R110, R113, R116: the max-cut engine mcx-v1 (breakout local search with an '
            'elite pool and population restarts), configured and tested on Gset; B20_R111, R112, R115: the '
            'invention test against preregistered prior art, NOT_DEMONSTRATED; B20_R132: why the system\'s own '
            'engines are never released, NOT_SHOWN, EXPRESSIVENESS in every class)', B,
            ['src/genesis/custody_records.py', 'src/genesis/custodian.py', 'src/genesis/decision_record.py',
             'src/genesis/candidates.py', 'src/genesis/judge.py', 'src/genesis/learning/statement_panels.py',
             'src/genesis/learning/research_export.py', 'src/genesis/candidates_v2.py',
             'src/genesis/candidate_kinds/milp_highs.py', 'docs/CANDIDATE_REGISTRY_V2.md',
             'src/genesis/candidate_registry.py', 'src/genesis/candidate_kinds/kinds.py',
             'src/genesis/candidate_kinds/maxcut_tabu.py', 'scripts/b20r67_refresh_v2_ids.py',
             'src/genesis/candidate_kinds/ising_dsb.py', 'src/genesis/candidate_kinds/maxcut_eo.py',
             'docs/PHYSICS_INSPIRED_PLAN.md', 'src/genesis/candidate_kinds/represent_search.py',
             'scripts/b20r72_represent_moves.py', 'evidence/represent_moves_b20r72/summary.json',
             'src/genesis/candidate_kinds/mqlib.py', 'scripts/b20r74_sota_tools.py',
             'scripts/b20r75_sota.py', 'evidence/sota_b20r75/summary.json',
             'src/genesis/candidate_kinds/cpsat.py', 'scripts/b20r76_sota.py', 'evidence/sota_b20r76/summary.json',
             'src/genesis/candidate_kinds/hybrid_swap.py', 'scripts/b20r77_engine_vs_sota.py',
             'evidence/engine_vs_sota_b20r77/summary.json', 'src/genesis/invention/solver_programs.py',
             'src/genesis/invention/solver_search.py', 'src/genesis/candidate_kinds/solver_program.py',
             'scripts/b20r79_program_search.py', 'evidence/program_search_b20r79/search_summary.json',
             'scripts/b20r80_random_program_control.py', 'evidence/random_program_control_b20r80/control_summary.json',
             'scripts/b20r81_self_found_solver.py', 'evidence/self_found_solver_b20r81/summary.json',
             'src/genesis/invention/solver_library.py',
             'src/genesis/invention/library_search.py', 'src/genesis/candidate_kinds/solver_library_program.py',
             'scripts/b20r83_generation_search.py', 'evidence/generation2_b20r83/summary.json',
             'evidence/generation2_control_b20r84/summary.json',
             'evidence/generation3_b20r85/summary.json',
             'evidence/generations_b20r86/summary.json',
             'scripts/b20r86_generations_eval.py', 'src/genesis/candidate_kinds/maxsat.py',
             'src/genesis/candidate_kinds/mqlib_heuristic.py', 'scripts/b20r87_maxsat_tools.py',
             'src/genesis/candidate_kinds/tfx.py', 'src/genesis/candidate_kinds/native/tfx.c',
             'scripts/b20r88_build_tfx.py', 'scripts/b20r89_configure_tfx.py', 'scripts/b20r90_beat_the_champions.py',
             'evidence/configure_tfx_b20r89/summary.json', 'evidence/beat_the_champions_b20r90/summary.json',
             'src/genesis/candidate_kinds/maxsat2026.py', 'scripts/b20r91_mse2026_tools.py', 'scripts/b20r92_vs_mse2026.py',
             'evidence/vs_mse2026_b20r92/summary.json', 'src/genesis/models_large.py',
             'src/genesis/graphs_large.py', 'src/genesis/candidates_large.py', 'src/genesis/candidate_kinds/tfxw.py',
             'src/genesis/candidate_kinds/native/tfxw.c', 'src/genesis/candidate_kinds/maxsat_large.py',
             'scripts/b20r94_build_tfxw.py', 'scripts/b20r95_configure_tfxw.py',
             'evidence/configure_tfxw_b20r95/summary.json', 'src/genesis/candidate_kinds/tfxw2.py',
             'src/genesis/candidate_kinds/native/tfxw2.c', 'scripts/b20r96_build_tfxw2.py', 'src/genesis/bounds_large.py',
             'scripts/b20r98_repin.py', 'scripts/b20r98_harness_check.py', 'evidence/harness_check_b20r98/summary.json',
             'scripts/b20r99_headroom.py', 'src/genesis/models_maxcut.py', 'src/genesis/graphs_maxcut.py',
             'src/genesis/candidates_maxcut.py', 'src/genesis/gset.py', 'src/genesis/candidate_kinds/mqlib_maxcut.py',
             'src/genesis/candidate_kinds/dsb_maxcut.py', 'data/gset/MANIFEST.json', 'data/gset/best_known.json',
             'scripts/b20r102_gset_standing.py', 'evidence/headroom_b20r99/summary.json',
             'src/genesis/candidate_kinds/mcx.py', 'src/genesis/candidate_kinds/native/mcx.c',
             'scripts/b20r104_build_mcx.py', 'scripts/b20r105_mcx_configure.py', 'scripts/b20r106_mcx_gset.py',
             'evidence/mcx_configure_b20r105/summary.json', 'evidence/mcx_configure_b20r105/configs.json',
             'evidence/gset_standing_b20r102/summary.json', 'scripts/b20r108_mcx_maturation.py',
             'evidence/mcx_gset_b20r106/summary.json', 'evidence/mcx_maturation_b20r108/summary.json',
             'evidence/mcx_maturation_b20r108/configs.json', 'scripts/b20r109_gset_replication.py',
             'evidence/gset_replication_b20r109/summary.json', 'scripts/b20r110_gset_long.py',
             'evidence/gset_long_b20r110/summary.json', 'scripts/b20r111_invention_test.py',
             'evidence/invention_test_b20r111/summary.json', 'scripts/b20r112_inventor_v2.py',
             'evidence/inventor_v2_b20r112/summary.json', 'scripts/b20r113_planar_renorm.py',
             'evidence/planar_renorm_b20r113/summary.json', 'src/genesis/invention/solver_programs_v2.py',
             'scripts/b20r115_language_v2.py', 'evidence/language_v2_b20r115/summary.json',
             'scripts/b20r116_gset_attempt.py', 'evidence/gset_attempt_b20r116/summary.json',
             'scripts/b20r123_gset_seeds.py', 'evidence/gset_seeds_b20r123/summary.json', 'src/genesis/candidate_kinds/mcx2.py', 'src/genesis/candidate_kinds/native/mcx2.c', 'scripts/b20r125_build_mcx2.py', 'src/genesis/autonomy/selfimprove.py', 'scripts/b20r127_self_invented_engine.py', 'evidence/self_invented_engine_b20r127/summary.json', 'scripts/b20r128_improve_the_improver.py', 'evidence/improve_the_improver_b20r128/summary.json', 'docs/checkpoints/B20_R128_RECORD.md', 'scripts/b20r132_invention_bottleneck.py', 'src/genesis/autonomy/contract_v3.py', 'evidence/invention_bottleneck_b20r132/summary.json', 'docs/checkpoints/B20_R132_RECORD.md', 'src/genesis/autonomy/process.py'],
            [G + 'test_evaluator_readiness.py', G + 'test_redteam_b16.py', G + 'test_candidate_adapters.py',
             G + 'test_candidate_custody.py', G + 'test_statement_custody.py', G + 'test_candidates_v2.py',
             G + 'test_wiring_v5.py', G + 'test_maxcut_tabu.py', G + 'test_physics_kinds.py',
             G + 'test_represent_search.py', G + 'test_mqlib_kind.py',
             G + 'test_cpsat_kind.py', G + 'test_sota.py', G + 'test_sota_v2.py',
             G + 'test_hybrid_swap.py', G + 'test_engine_vs_sota.py', G + 'test_solver_programs.py',
             G + 'test_program_search_study.py', G + 'test_self_found_solver.py', G + 'test_solver_library.py',
             G + 'test_generations.py', G + 'test_maxsat_kind.py', G + 'test_tfx_kind.py',
             G + 'test_beat_champions.py', G + 'test_maxsat2026_kind.py', G + 'test_vs_mse2026.py',
             G + 'test_large_domain.py', G + 'test_configure_tfxw.py', G + 'test_harness_check.py',
             G + 'test_headroom.py', G + 'test_maxcut_domain.py', G + 'test_gset_standing.py',
             G + 'test_mcx_kind.py', G + 'test_mcx_configure.py', G + 'test_mcx_gset.py',
             G + 'test_mcx_maturation.py', G + 'test_gset_replication.py', G + 'test_gset_long.py',
             G + 'test_invention_test.py', G + 'test_inventor_v2.py', G + 'test_planar_renorm.py',
             G + 'test_language_v2.py', G + 'test_gset_attempt.py', G + 'test_gset_seeds.py', G + 'test_mcx2_kind.py', G + 'test_selfimprove.py', G + 'test_self_invented_engine.py', G + 'test_improve_the_improver.py', G + 'test_invention_bottleneck.py', G + 'test_contract_v3.py', G + 'test_process_levels.py']),
    'W07': ('Statistics, fairness and decision rules', B,
            [K + 'analysis.py', 'src/genesis/power.py', 'src/genesis/judge.py', 'src/genesis/resources.py',
             'docs/STATISTICIAN_BRIEF.md', 'scripts/b20r61_statistician_brief.py', 'scripts/b20r62_power_rebind.py',
             'scripts/b20r65_unsupported_hosts.py', 'src/genesis/anytime.py'],
            [G + 'test_analysis_v2.py', G + 'test_evaluator_readiness.py', G + 'test_resources.py',
             G + 'test_statistician_brief.py', G + 'test_power_rebind.py', G + 'test_unsupported_hosts.py',
             G + 'test_anytime.py']),
    'W08': ('Lean and Mathlib research workspace', B,
            ['src/genesis/formal_research/workspace.py', 'src/genesis/formal_research/checker.py',
             'src/genesis/formal_research/search.py', 'toolchain/FORMAL_WORKSPACE.json'],
            ['tests_formal/test_formal_research.py']),
    'W09': ('TCSR and missing-concept recovery (own library and typed anti-unification; no Mathlib-history study)', B,
            ['src/genesis/invention/recovery.py', 'src/genesis/invention/recovery_experiment.py',
             'evidence/invention_b18/recovery/comparison.json'],
            ['tests_formal/test_invention.py']),
    'W10': ('Representation and ontology invention (vertex-class grammar; B20_R17/R19 generated relational decoders, '
            'B20_R26 quotients with a parametric transport theorem, B20_R27 decompositions with a composition theorem, '
            'B20_R31/R36 generated pattern inequalities with Lean-checked validity; all Lean-checked, all '
            'NO_UTILITY_AFTER_COST on DEV in construction)', B,
            ['src/genesis/invention/representations.py', 'evidence/invention_b18/representations/package.json',
             'src/genesis/invention/soundness.py', 'evidence/soundness_b20r/modes.json',
             'src/genesis/invention/codegree.py', 'evidence/codegree_b20r/package.json',
             'src/genesis/invention/relations.py', 'evidence/relation_invention_b20r17/package.json',
             'src/genesis/invention/quotients.py', 'evidence/quotient_invention_b20r26/package.json',
             'src/genesis/invention/decompositions.py', 'evidence/decomposition_invention_b20r27/package.json',
             'src/genesis/invention/cuts.py', 'evidence/relaxation_invention_b20r31/package.json'],
            ['tests_formal/test_invention.py', 'tests_formal/test_soundness_modes.py', 'tests_formal/test_codegree.py',
             G + 'test_relations.py', 'tests_formal/test_relation_invention.py', G + 'test_quotients.py',
             G + 'test_decompositions.py', 'tests_formal/test_quotient_invention.py',
             'tests_formal/test_decomposition_invention.py', G + 'test_cuts.py',
             'tests_formal/test_relaxation_invention.py', G + 'test_dense_construction.py']),
    'W11': ('Theory-centered discovery and theory packages (first package path only)', B,
            ['src/genesis/formal_research/theory_package.py', 'src/genesis/formal_research/triangle_theory.py',
             'evidence/formal_research_b17/package/package.json'],
            ['tests_formal/test_formal_research.py::CommittedPackage']),
    'W12': ('Worlds, counterfactual theories and transport', B,
            ['src/genesis/invention/worlds.py', 'evidence/invention_b18/worlds/package.json',
             'src/genesis/invention/soundness.py'],
            ['tests_formal/test_invention.py', 'tests_formal/test_soundness_modes.py::Wiring']),
    'W13': ('Construction, obstruction and certified reductions (LP relaxation with exact dual certificates; B20_R32: '
            'exact certificates over generated rows with a Lean-bound registry, DEV only, NO_CERTIFICATION_UTILITY '
            'on an unenriched sample; B20_R35: CERTIFICATION_UTILITY on enriched settings, 27/40 vs 7/40; B20_R37: '
            'generator v2 on seven vertices, Lean-checked, no further coverage gain; no symmetry reduction, kernelization '
            'or continuation yet)', B,
            ['src/genesis/discovery/obstruction.py', 'evidence/discovery_b19/obstruction/evaluation.json',
             'src/genesis/verification/lp_dual_rows.py', 'src/genesis/discovery/generated_certify.py',
             'evidence/generated_certification_b20r32/summary.json', 'evidence/dense_certification_b20r35/summary.json',
             'src/genesis/invention/cuts_v2.py', 'evidence/generator_v2_b20r37/package.json',
             'src/genesis/verification/certificates_rows.py', 'docs/GENERATED_ROWS_REFERENCE.md'],
            ['tests_formal/test_discovery.py', G + 'test_lp_dual_rows.py', G + 'test_generated_certification.py',
             G + 'test_dense_certification.py', G + 'test_cuts_v2.py', 'tests_formal/test_generator_v2.py',
             G + 'test_certificates_rows.py']),
    'W14': ('Active experiments and identifiability (B20_R117: a hidden-confounder causal-discovery benchmark with '
            'established baselines; B20_R118: their calibration; B20_R119: FCI and an active procedure proposing the '
            'interventions that resolve hidden causes; B20_R120: its test; B20_R121-R122: version 2 and its test); B20_R124: Gaussian noise; B20_R129: the adaptive experimental scientist (ADAPTIVE_SCIENTIST) and its reconciliation; B20_R130: choice, instrument and interpretation separated (CHOICE); B20_R131: the cascade (NO_VERIFIED_TRIGGER by protocol)', B,
            ['src/genesis/discovery/active.py', 'evidence/discovery_b19/active/evaluation.json',
             'src/genesis/causal/sem.py', 'src/genesis/causal/admg.py', 'src/genesis/causal/methods.py',
             'docs/checkpoints/B20_R117_RECORD.md', 'scripts/b20r118_causal_calibration.py',
             'evidence/causal_calibration_b20r118/summary.json', 'src/genesis/causal/fci.py',
             'src/genesis/causal/active.py', 'docs/checkpoints/B20_R119_RECORD.md',
             'scripts/b20r120_propose_interventions.py', 'evidence/propose_interventions_b20r120/summary.json',
             'src/genesis/causal/active2.py', 'docs/checkpoints/B20_R121_RECORD.md',
             'scripts/b20r122_hidden_causes_v2.py', 'evidence/hidden_causes_v2_b20r122/summary.json', 'scripts/b20r124_gaussian_hidden_causes.py', 'evidence/gaussian_hidden_causes_b20r124/summary.json', 'src/genesis/science/design.py', 'src/genesis/science/acquire.py', 'src/genesis/science/library.py', 'src/genesis/causal/active3.py', 'src/genesis/causal/instruments.py', 'src/genesis/causal/joint.py', 'src/genesis/causal/global_ml.py', 'scripts/b20r129_adaptive_scientist.py', 'evidence/adaptive_scientist_b20r129/summary.json', 'scripts/b20r130_choice_instrument_interpretation.py', 'evidence/choice_instrument_interpretation_b20r130/summary.json', 'scripts/b20r129_reconcile.py', 'evidence/r129_reconciliation/summary.json', 'scripts/b20r131_cascade.py', 'evidence/cascade_b20r131/summary.json'],
            ['tests_formal/test_discovery.py::ActiveSelection', 'tests_genesis/test_causal_domain.py',
             'tests_genesis/test_causal_calibration.py', 'tests_genesis/test_causal_active.py',
             'tests_genesis/test_propose_interventions.py', 'tests_genesis/test_causal_active2.py',
             'tests_genesis/test_hidden_causes_v2.py', 'tests_genesis/test_gaussian_hidden_causes.py', 'tests_genesis/test_science_design.py', 'tests_genesis/test_causal_active3.py', 'tests_genesis/test_adaptive_scientist.py::RecordB20R129', 'tests_genesis/test_global_ml.py', 'tests_genesis/test_causal_joint.py', 'tests_genesis/test_causal_instruments.py', 'tests_genesis/test_choice_instrument_interpretation.py', 'tests_genesis/test_cascade_study.py', 'tests_genesis/test_primitive_library.py']),
    'W15': ('Causal concept catalysis and idea combinations (DEV factorial and controls)', B,
            ['scripts/b19_discovery.py', 'evidence/discovery_b19/catalysis/solver.json'],
            ['tests_formal/test_discovery.py::Evidence']),
    'W16': ('Ghost Census beyond the small development family (DEV diagnostic; Lean replay of E proofs; B20_R25 '
            'ground-hint generator v2: Wolfram-axiom chains 0/19 -> 19/19 on identical proof objects)', B,
            ['src/genesis/discovery/ghost_census.py', 'src/genesis/formal_research/fof_lean.py',
             'evidence/ghost_census_b19/run2/summary.json', 'evidence/hint_ab_b20r25/ab.json'],
            ['tests_formal/test_ghost_census.py', 'tests_formal/test_hint_versions.py']),
    'W17': ('Literature, priority and faithful formalization', B,
            ['src/genesis/literature.py', 'evidence/literature_b19/records/summary.json'],
            [G + 'test_literature.py']),
    'W18': ('Replayable research macros and proof-carrying compression (equational domain: induced lemma programs '
            'with dependencies, faithful replay, revocation, transfer)', B,
            ['src/genesis/learning/macros.py', 'evidence/learning_b20/w18/same_system.json'],
            ['tests_formal/test_learning.py', G + 'test_research_resource_accounting.py']),
    'W19': ('Research-policy learning (fixed, random, heuristic, bandit and a frozen learned policy at equal research '
            'budgets)', B,
            ['src/genesis/learning/research.py', 'src/genesis/learning/budget.py', 'src/genesis/learning/custody.py',
             'evidence/learning_b20/w19/rows.json', 'evidence/e3_fresh_b20r/e3_summary.json',
             'evidence/e3_costaware_b20r3/e3_summary.json'],
            ['tests_formal/test_learning.py', G + 'test_research_resource_accounting.py',
             'tests_formal/test_successor_proof_custody.py', G + 'test_research_policy_v2.py']),
    'W20': ('Curriculum, experience synthesis and capability memory (screened memory, failure-driven curriculum, '
            'demotion; B20_R93: the adaptation cell, which senses weaknesses in studies, remembers what answered '
            'them and gates the next design)', B,
            ['src/genesis/learning/memory.py', 'src/genesis/learning/partitions.py',
             'evidence/learning_b20/w20/rows.json', 'src/genesis/adaptation/receptors.py',
             'src/genesis/adaptation/ledger.py', 'src/genesis/adaptation/design.py',
             'src/genesis/adaptation/checkpoint.py', 'scripts/b20r93_cell.py',
             'evidence/adaptation_cell_b20r93/ledger.json', 'docs/CAVEATS.md', 'src/genesis/autonomy/loop.py',
             'src/genesis/autonomy/studygen.py', 'src/genesis/autonomy/qet.py', 'src/genesis/autonomy/archive.py',
             'src/genesis/autonomy/adversary.py', 'docs/AUTONOMY.md', 'evidence/qet_large_b20r97/summary.json',
             'src/genesis/autonomy/portfolio.py', 'src/genesis/autonomy/portfolio_tasks.py',
             'scripts/b20r148_harness_portfolio.py', 'docs/OMEGA_META_ADAPTIVE.md',
             'evidence/harness_portfolio_b20r148/summary.json', 'docs/checkpoints/B20_R148_RECORD.md',
             'evidence/adaptation_cell_b20r97/ledger.json', 'src/genesis/autonomy/kmap.py',
             'scripts/b20r100_knowledge_map.py', 'evidence/knowledge_map_b20r100/summary.json',
             'src/genesis/autonomy/feedback.py', 'scripts/b20r103_zero_signal.py', 'docs/RESEARCH_ALERTS.md',
             'evidence/zero_signal_b20r103/summary.json', 'scripts/b20r107_contract_v2.py',
             'evidence/contract_v2_b20r107/summary.json',
             'docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md', 'src/genesis/vault.py', 'src/genesis/discovery_cli.py', 'src/genesis/replayers.py', 'src/genesis/interpret.py', 'docs/OMEGA_DISCOVERY_SCHEMA.md', 'docs/OMEGA_CAPABILITY_GRAPH.md'],
            ['tests_formal/test_learning.py', 'tests_formal/test_learning_partitions.py',
             G + 'test_adaptation_cell.py', G + 'test_autonomy.py', G + 'test_knowledge_map.py',
             G + 'test_portfolio.py', G + 'test_harness_portfolio.py',
             G + 'test_feedback_contract.py', G + 'test_contract_v2.py', G + 'test_vault.py', G + 'test_interpret.py']),
    'W21': ('Better-improver and multigeneration controller (B20_R2: pure lineage validator; B20_R4: the campaign '
            'loop writes native lineage records, crash/resume charges interrupted attempts, the custodian checks '
            'generation requests against the qualifying chain; B20_R16: active-version pointer, rollback, inherited '
            'version revocation, resume gate; sealed improver evaluation still refused; B20_R150: ARA-1, the '
            'Autonomous Research Architect on fixtures)',
            B, ['src/genesis/lineage.py', 'src/genesis/campaign.py', 'src/genesis/custodian.py', 'src/genesis/versions.py',
                'src/genesis/architecture/graph.py', 'src/genesis/architecture/ara.py', 'src/genesis/architecture/judge.py',
                'docs/OMEGA_ARCHITECTURE_INVENTION.md', 'docs/checkpoints/B20_R150_RECORD.md'],
            [G + 'test_generation_lineage.py', G + 'test_campaign_lineage.py', G + 'test_versions.py',
             G + 'test_architecture_graph.py', G + 'test_architecture_judge.py', G + 'test_architecture_rewrite.py',
             G + 'test_architecture_ara.py', G + 'test_architecture_boundary.py']),
    'W22': ('New primitives, research-language evolution and trust changes (derived primitives with reference '
            'expansions, conformance, versioned registries; DEV: none of four starting primitives is a gain; '
            'B20_R153: the engine language Λ1, mcx3 with the builder\'s construct algebra, mcx2 programs identical, '
            'named statements with versioned libraries, the inventor\'s operators over Λ0 and Λ1; B20_R154: library learning, '
            'the language judge, the consolidator, the generation pipeline, on a planted fixture)', B,
            ['src/genesis/primitives.py', 'scripts/b20r_primitives.py', 'src/genesis/candidate_kinds/mcx3.py',
             'src/genesis/candidate_kinds/native/mcx3.c', 'scripts/b20r153_build_mcx3.py',
             'src/genesis/expressive/lambda1.py', 'src/genesis/expressive/operators.py',
             'docs/OMEGA_EXPRESSIVE_LANGUAGE.md', 'docs/checkpoints/B20_R153_RECORD.md',
             'scripts/b20r151_expressiveness.py', 'src/genesis/expressive/library.py',
             'src/genesis/expressive/judge.py', 'src/genesis/expressive/consolidate.py',
             'src/genesis/expressive/workflow.py', 'src/genesis/expressive/pipeline.py',
             'docs/checkpoints/B20_R154_RECORD.md'],
            [G + 'test_primitives.py', G + 'test_mcx3_kind.py', G + 'test_expressive_lambda1.py',
             G + 'test_expressive_operators.py', G + 'test_expressiveness_study.py', G + 'test_expressive_library.py',
             G + 'test_expressive_judge.py', G + 'test_expressive_consolidate.py', G + 'test_expressive_pipeline.py',
             G + 'test_expressive_boundary.py']),
    'W23': ('Fault-tolerant reasoning and expert interaction (heterogeneous routes, quarantine, adjudication without '
            'majority vote; no expert-interaction channel)', B,
            ['src/genesis/verification/reliability.py', 'src/genesis/graphs.py'],
            [G + 'test_reliability.py', 'tests_certificates/test_reliability_routes.py']),
    'W24': ('Transfer and independent reproduction (B20_R46: the row-invention procedure transferred to C4-free '
            'subgraphs with a registered adaptation, 37/37 obligations Lean-CHECKED; B20_R47: no certification '
            'coverage gain from the rows alone (22 vs 22); B20_R48: with certified branch and bound, CERTIFICATION_UTILITY '
            'on fresh C4 hosts, 38 vs 26 of 40; B20_R49: a registered ablation attributes it to the transferred rows '
            '(36 vs 24 of 40, p 0.00024); B20_R50: the rows make E1b\'s C4 arm scorable (two calibrated C4 settings, '
            'READY_FOR_REVIEW, MIP-dominated); near-domain evidence only; B20_R53/R54: the equational target has no '
            'research headroom; B20_R55: the procedure transferred to sum-free sets of integers, a different theorem '
            'family, 20/20 obligations Lean-CHECKED; B20_R56: NO_CERTIFICATION_UTILITY there (28 vs 26 of 40, p 0.25); '
            'B20_R57: CERTIFICATION_UTILITY on hosts hard for the conventional route (22 vs 14 of 40, p 0.0039), '
            'NOT_REPLICATED on fresh hosts (B20_R59: 23 vs 21, p 0.25) while its bound advantage replicated; '
            'independent reproduction not started)', H,
            ['src/genesis/invention/cuts_c4.py', 'scripts/b20r46_c4_generator.py',
             'src/genesis/verification/lp_dual_rows_c4.py', 'src/genesis/discovery/generated_certify_c4.py',
             'scripts/b20r47_c4_certification.py', 'src/genesis/verification/lp_dual_tree_c4.py',
             'src/genesis/discovery/generated_bnb_c4.py', 'scripts/b20r48_c4_tree_certification.py',
             'scripts/b20r49_c4_rows_ablation.py', 'scripts/b20r50_e1b_c4_readiness.py',
             'src/genesis/verification/certificates_tree_c4.py', 'scripts/b20r52_e1b_c4_package.py',
             'src/genesis/invention/cuts_sf.py', 'scripts/b20r55_sf_generator.py',
             'src/genesis/verification/lp_dual_tree_sf.py', 'src/genesis/discovery/generated_bnb_sf.py',
             'scripts/b20r56_sf_tree_certification.py', 'scripts/b20r57_sf_hard_certification.py',
             'scripts/b20r59_sf_replication.py'],
            [G + 'test_cuts_c4.py', 'tests_formal/test_c4_generator.py', G + 'test_lp_dual_rows_c4.py',
             G + 'test_c4_certification.py', G + 'test_lp_dual_tree_c4.py', G + 'test_c4_tree_certification.py',
             G + 'test_c4_rows_ablation.py', G + 'test_e1b_c4_readiness.py', G + 'test_wiring_tree_c4.py',
             G + 'test_e1b_c4_package.py', G + 'test_cuts_sf.py', 'tests_formal/test_sf_generator.py',
             G + 'test_lp_dual_tree_sf.py', G + 'test_sf_tree_certification.py', G + 'test_sf_hard_certification.py',
             G + 'test_sf_replication.py']),
    'W25': ('Trainable model extension', N, [], []),
    'W26': ('Software research extension', N, [], []),
    'W27': ('Numerical, empirical and instrument extension', N, [], []),
    'W28': ('Economics, long-run operations and retirement', N, [], []),
}
EXPERIMENTS = {f'E{i}': t for i, t in enumerate((
    'Integrity and reproduction', 'Useful checked solver improvement', 'Concept/theory catalysis', 'Better improver',
    'Compounding generations', 'Structural transfer', 'Independent replication and priority',
    'Extended-domain studies'))}

# Catalogue: tests that exercise the mapped mechanism, with a keyword that must appear in the test file.
SHARED_TESTS = {
    'Epistemic Typing': (G + 'test_evidence_kernel.py', 'SPECULATIVE|speculative'),
    'Reflective Trust Tower': (G + 'test_evidence_kernel.py', 'CIRCULAR_JUSTIFICATION'),
    'Anytime-Correct Reasoning': ('tests_certificates/test_sat_certificates.py', 'certified_bounds'),
    'Approximation-to-Exact': ('tests_certificates/test_sat_certificates.py', 'certified_bounds'),
    'Semantic Randomization': (G + 'test_macros_market.py', 'label_sensitivity|barrier'),
    'Value-of-Computation Controller': (G + 'test_macros_market.py', 'should_stop|allocate'),
    'Reproducibility Compiler': (G + 'test_macros_market.py', 'replay'),
    'Structural Separators': (G + 'test_macros_market.py', 'local_to_global'),
    'Universal Search Fallback': (G + 'test_research_runtime.py', 'Campaign'),
    'Placebo Generator': (G + 'test_research_runtime.py', 'placebo|causal'),
    'Patch Replay': (G + 'test_research_runtime.py', 'replay'),
    'Diversity-Constrained Search': (G + 'test_macros_market.py', 'diversity|recent_classes'),
    'Option-Preserving Development': (G + 'test_research_runtime.py', 'Ecology|retire'),
    'Open-Ended Quality-Diversity': (G + 'test_research_runtime.py', 'frontier|Ecology'),
    'Shadow Successor': (G + 'test_research_runtime.py', 'Campaign'),
}
NOT_SHARED = {'Evaluator Attack': 'adversarial suites exist (escape suite, GI6, B14 red team) but are human/agent '
                                  'authored; the engine (synthesizing attacks) is not implemented'}
EXTENSION_ENGINES = {'Instrument Compiler', 'Metrology/Instrument Validity', 'Adaptive Model Growth',
                     'Training-Objective Synthesizer', 'Teacher Compiler', 'Data-Mechanism Provenance',
                     'Semantic Pruning', 'Multi-Fidelity Bridge', 'Certified Continuum', 'Dimensional Intelligence',
                     'Hybrid Discrete-Continuous', 'Selection/Missingness/Bias', 'Strategic-Agent Engine'}


def spec_toc():
    lines = (ROOT / 'spec' / 'GENESIS_FINAL_SPECIFICATION.txt').read_text().splitlines()
    out = []
    for ln in lines[:700]:
        m = re.match(r'^\s*(\d+(?:\.\d+)*)\.?\s+(.+?)\s*(?:\.\s*)+\s*(\d+)\s*$', ln) or \
            re.match(r'^\s*(\d+)\.\s+(.+?)\s{3,}(\d+)\s*$', ln)
        if m:
            out.append((m.group(1), m.group(2).strip(' .'), int(m.group(3))))
    return out


def check_refs(row, problems):
    for c in row['code']:
        if not (ROOT / c).exists():
            problems.append(f"{row['id']}: code path {c} does not exist")
    for t in row['tests']:
        f, _, cls = t.partition('::')
        if not (ROOT / f).is_file():
            problems.append(f"{row['id']}: test file {f} does not exist")
        elif cls and not re.search(rf'^class {re.escape(cls)}\b', (ROOT / f).read_text(), re.M):
            problems.append(f"{row['id']}: test class {cls} not in {f}")
    if row['disposition'] in (B, S, R_) and not row['tests'] and row['id'] not in ('SPEC-36.2', 'SPEC-40'):
        problems.append(f"{row['id']}: {row['disposition']} without an executed test reference")


def row(rid, title, source, disp, scope, code, tests, remaining, blockers, efficacy, ws, owner='research implementer'):
    tests_exist = bool(tests)
    return {'id': rid, 'title': title, 'source': source, 'disposition': disp, 'scope': scope, 'code': code,
            'tests': tests, 'evidence': [], 'remaining': remaining, 'external_blockers': blockers, 'owner': owner,
            'workstream': ws,
            'implementation': {I: 'N/A', N: 'NOT_IMPLEMENTED', D: 'NOT_IMPLEMENTED'}.get(disp, 'IMPLEMENTED_BOUNDED'),
            'local_execution': 'TESTS_EXECUTED_IN_MATRIX' if tests_exist else ('N/A' if disp == I else 'NOT_EXECUTED'),
            'independent_verification': 'N/A' if disp == I else 'PENDING',
            'scientific_efficacy': efficacy,
            'acceptance': {'decision': 'N/A' if disp == I else 'PENDING_INDEPENDENT_ACCEPTANCE', 'date': None}}


def build():
    from genesis.registry import registry
    rows, problems = [], []
    toc = spec_toc()
    for sid, title, page in toc:
        if sid not in SPEC:
            problems.append(f'spec §{sid} has no ledger row')
            continue
        disp, scope, code, tests, remaining, blockers, eff, ws = SPEC[sid]
        rows.append(row(f'SPEC-{sid}', title, f'spec §{sid} (p. {page})', disp, scope, code, tests, remaining, blockers,
                        eff, ws))
    extra = set(SPEC) - {s for s, _, _ in toc}
    if extra:
        problems.append(f'ledger rows for sections not in the spec: {sorted(extra)}')
    for rid, (disp, scope, code, tests, remaining, blockers, eff, ws) in ROADMAP.items():
        rows.append(row(rid, scope, 'roadmap §3', disp, scope, code, tests, remaining, blockers, eff, ws))
    for rid, (disp, scope, code, tests, remaining, blockers, eff, ws) in REVIEW.items():
        rows.append(row(rid, scope, 'B20 external review (B20_R1)', disp, scope, code, tests, remaining, blockers,
                        eff, ws))
    for rid, (disp, scope, code, tests, remaining, blockers, eff, ws) in GATES.items():
        rows.append(row(rid, scope, 'roadmap §5', disp, scope, code, tests, remaining, blockers, eff, ws,
                        owner='release authority'))
    for rid, (title, disp, code, tests) in WORKSTREAMS.items():
        rows.append(row(rid, title, 'roadmap §7-10', disp, 'workstream' + (' (B14 scope delivered; acceptance pending)'
                                                                            if disp == B else ''),
                        code, tests, [] if disp == B else ['not started in B14'], [], 'N/A', rid))
    for rid, title in EXPERIMENTS.items():
        rows.append(row(rid, title, 'roadmap §12', N, 'experiment not run', [], [], ['run under its gate'],
                        ['independent operator' if rid != 'E0' else 'second supported machine'], 'NOT_TESTED', 'W24'))
    for i, e in enumerate(registry(), 1):
        name = e['engine']
        rid = f'CAT-{i:03d}'
        comp = ' -> '.join(e['composition'])
        if e['status'] == 'IMPLEMENTED_BOUNDED':
            r = row(rid, name, 'spec Appendix A', B, f"{e['note']} ({comp}); graph wedge only", ['src/genesis/macros.py'],
                    [G + 'test_macros_market.py::Macros'], ['efficacy beyond DEV'], [], 'NOT_TESTED', 'W18')
        elif name in SHARED_TESTS:
            f, kw = SHARED_TESTS[name]
            if not re.search(kw, (ROOT / f).read_text()):
                problems.append(f'{rid} {name}: mapped test {f} does not mention {kw}')
            r = row(rid, name, 'spec Appendix A', S, f"shared: {e['note']}", [], [f], ['engine-level semantics beyond '
                                                                                        'the shared mechanism'], [],
                    'N/A', 'W18')
        else:
            note = NOT_SHARED.get(name, 'composition hypothesis only; listing a composition is not an implementation')
            r = row(rid, name, 'spec Appendix A', N, note + f' ({comp})', [], [], ['concrete engine with tests'], [],
                    'NOT_TESTED', 'W27' if name in EXTENSION_ENGINES else 'W22')
            if name in EXTENSION_ENGINES:
                r['proposed_disposition'] = D
                r['scope'] += ' — proposed DEFERRED_EXTENSION; requires explicit scope agreement'
        rows.append(r)
    if len([r for r in rows if r['id'].startswith('CAT-')]) != 137:
        problems.append('catalogue must have 137 rows')
    for r in rows:
        if r['disposition'] not in DISPOSITIONS:
            problems.append(f"{r['id']}: unknown disposition {r['disposition']}")
        if r['disposition'] == 'IMPLEMENTED_AND_ACCEPTED':
            problems.append(f"{r['id']}: no row may be accepted without an external acceptance record")
        check_refs(r, problems)
    return rows, problems


def render(rows):
    from collections import Counter
    out = ['# Requirements ledger (W01)', '',
           'Generated by `scripts/build_ledger.py` from the frozen specification table of contents, the reviewer '
           'roadmap and the engine registry. Machine-readable copy: `ledger/requirements_ledger.json`.', '',
           'Columns keep four things apart: implementation, local execution (tests ran in this repository\'s '
           'matrix), independent verification, and scientific efficacy. **No row is accepted**: every acceptance '
           'decision is pending an independent auditor. The builder\'s P0-P2 labels are assessments only, and were '
           'made before the R-01/R-02 defects were reproduced.', '', '## Summary', '']
    groups = {'Specification §1-48': 'SPEC-', 'Roadmap defects': 'R-', 'B20 review findings': 'B20', 'Gates': 'GV',
              'Workstreams': 'W',
              'Experiments': 'E', 'Engine catalogue (137)': 'CAT-'}
    out += ['| Group | Rows | ' + ' | '.join(d.replace('_', ' ').title() for d in sorted(DISPOSITIONS)) + ' |',
            '|---|---:|' + '---:|' * len(DISPOSITIONS)]
    for name, prefix in groups.items():
        sel = [r for r in rows if r['id'].startswith(prefix)]
        c = Counter(r['disposition'] for r in sel)
        out.append(f'| {name} | {len(sel)} | ' + ' | '.join(str(c.get(d, 0)) for d in sorted(DISPOSITIONS)) + ' |')
    out += ['', 'Proposed DEFERRED_EXTENSION rows remain NOT_IMPLEMENTED until Daniel agrees the release scope '
            '(roadmap §17: difficult requirements are not silently dropped).', '']
    for name, prefix in groups.items():
        out += [f'## {name}', '', '| ID | Title | Disposition | Scope | Tests | Remaining | External blockers | Efficacy |',
                '|---|---|---|---|---|---|---|---|']
        for r in rows:
            if r['id'].startswith(prefix):
                cell = lambda xs: '<br>'.join(x.replace('|', '/') for x in xs) or '—'
                out.append(f"| {r['id']} | {r['title']} | {r['disposition']} | {r['scope'].replace('|', '/')} | "
                           f"{cell(r['tests'])} | {cell(r['remaining'])} | {cell(r['external_blockers'])} | "
                           f"{r['scientific_efficacy']} |")
        out.append('')
    return '\n'.join(out) + '\n'


def main():
    rows, problems = build()
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 1
    (ROOT / 'ledger').mkdir(exist_ok=True)
    (ROOT / 'ledger' / 'requirements_ledger.json').write_text(json.dumps(
        {'schema': 'genesis-requirements-ledger-v1', 'rows': rows}, indent=1, sort_keys=True) + '\n')
    (ROOT / 'docs' / 'REQUIREMENTS_LEDGER.md').write_text(render(rows))
    print(f'{len(rows)} rows written')
    return 0


if __name__ == '__main__':
    sys.exit(main())
