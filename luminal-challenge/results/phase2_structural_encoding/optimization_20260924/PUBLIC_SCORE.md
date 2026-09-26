# Exact public-suite score (optimization protocol 1.0)

Scope: exact fixed public suite of eight programs; descriptive; not a significance test and not a private-grader claim.

Formula: `S_arm = sqrt(GM_i(C_serial_i/C_arm_i) * GM_i(S_serial_i/S_arm_i))`.

Serial re-measured on 8 programs x 15 repetitions: matches frozen records = True (120 rows).

| arm | min | max | geometric mean over repetitions | complete |
|---|---|---|---|---|
| accepted_bootstrap@None | 2.008466202284657 | 2.008466202284657 | 2.008466202284657 | True |
| accepted_budgeted@0.01 | 2.008466202284657 | 2.008466202284657 | 2.008466202284657 | True |
| accepted_budgeted@0.1 | 2.008466202284657 | 2.008466202284657 | 2.008466202284657 | True |
| accepted_budgeted@1.0 | 2.008466202284657 | 2.008466202284657 | 2.008466202284657 | True |
| accepted_default@None | 2.008466202284657 | 2.008466202284657 | 2.008466202284657 | True |
| classical@None | 1.9013791212645499 | 1.9013791212645499 | 1.90137912126455 | True |
| frozen_phase2@0.01 | 2.0327602339438613 | 2.0327602339438613 | 2.0327602339438613 | True |
| frozen_phase2@0.1 | 2.0327602339438613 | 2.0327602339438613 | 2.0327602339438613 | True |
| frozen_phase2@1.0 | 2.0327602339438613 | 2.0327602339438613 | 2.0327602339438613 | True |
| selected_nonmodel@0.01 | 2.0736243061428388 | 2.0736243061428388 | 2.0736243061428388 | True |
| selected_nonmodel@0.1 | 2.1027466543513094 | 2.1027466543513094 | 2.1027466543513094 | True |
| selected_nonmodel@1.0 | 2.1027466543513094 | 2.1027466543513094 | 2.1027466543513094 | True |

## Paired score ratios

| candidate vs control | strict gain every rep | improving/tied/worsening reps | ratio (rep 0) |
|---|---|---|---|
| selected_nonmodel@0.1_vs_accepted_default@None | True | 15/0/0 | 1.0469415178405328 |
| selected_nonmodel@0.1_vs_classical@None | True | 15/0/0 | 1.1059060399026766 |
| selected_nonmodel@0.1_vs_frozen_phase2@0.1 | True | 15/0/0 | 1.0344292549798968 |
| selected_nonmodel@0.1_vs_accepted_budgeted@0.1 | True | 15/0/0 | 1.0469415178405328 |
| frozen_phase2@0.1_vs_accepted_default@None | True | 15/0/0 | 1.012095813029649 |
| frozen_phase2@0.1_vs_classical@None | True | 15/0/0 | 1.0690977991763861 |
| frozen_phase2@0.1_vs_accepted_budgeted@0.1 | True | 15/0/0 | 1.012095813029649 |

Score-ratio reconciliation with exp(mean log J ratio / 2), all 15 repetitions agree within 1e-12: True.

## Per program C/S/J (distinct values over repetitions)

| program | serial C,S | selected_nonmodel@0.1 | frozen_phase2@0.1 | accepted_default | classical |
|---|---|---|---|---|---|
| vector_reduction | [19, 137] | [(12, 32, 384)] | [(12, 33, 396)] | [(12, 40, 480)] | [(12, 40, 480)] |
| parallel_memory | [21, 128] | [(13, 40, 520)] | [(13, 40, 520)] | [(13, 40, 520)] | [(14, 56, 784)] |
| vector_axpy | [14, 73] | [(10, 24, 240)] | [(10, 24, 240)] | [(10, 24, 240)] | [(10, 32, 320)] |
| scalar_selects | [20, 16] | [(9, 6, 54)] | [(9, 6, 54)] | [(9, 6, 54)] | [(9, 6, 54)] |
| scalar_dual_chain | [12, 9] | [(8, 3, 24)] | [(8, 3, 24)] | [(8, 3, 24)] | [(9, 5, 45)] |
| scalar_pipeline | [18, 15] | [(14, 6, 84)] | [(14, 6, 84)] | [(14, 6, 84)] | [(14, 6, 84)] |
| vector_bitmix | [16, 89] | [(10, 40, 400)] | [(10, 40, 400)] | [(10, 40, 400)] | [(10, 40, 400)] |
| mixed_broadcast | [11, 42] | [(9, 16, 144)] | [(10, 24, 240)] | [(10, 24, 240)] | [(9, 17, 153)] |

## One-program-at-a-time sensitivity (repetition 0)

| program removed | vs accepted_default | vs classical | vs frozen_phase2 |
|---|---|---|---|
| vector_reduction | 1.037161 | 1.104184 | 1.037161 |
| parallel_memory | 1.053825 | 1.089500 | 1.039444 |
| vector_axpy | 1.053825 | 1.099106 | 1.039444 |
| scalar_selects | 1.053825 | 1.121925 | 1.039444 |
| scalar_dual_chain | 1.053825 | 1.072664 | 1.039444 |
| scalar_pipeline | 1.053825 | 1.121925 | 1.039444 |
| vector_bitmix | 1.053825 | 1.121925 | 1.039444 |
| mixed_broadcast | 1.016067 | 1.117077 | 1.002200 |
