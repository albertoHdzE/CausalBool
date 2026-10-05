# Bitacora — identification screen

Scientific record of the three-day headroom screen run under
`PROTOCOL_screen_identification.md` (frozen at `dcc1d59e`, 2026-09-29).
Landscape of competing methods: `RELATED_METHODS.md`.

Each entry records what was measured, where the number lives, and what it does
and does not mean. Every number is quoted from a results file under
`results/screen_identification/`, written by a script under `experiments/`;
the file is named beside the number.

| Entry | Date | Content |
|---|---|---|
| `01_day1_measurements.md` | 2026-09-29 | Corpus freeze, S2, S3a, S3b complete; S1 running; the author's first questions |
| `02_verdict.md` | 2026-09-29 | S1 complete, H3, verdict NARROW and its qualifications |

Scripts: `experiments/screen_common.py`, `screen_s0_corpus.py`,
`screen_s1_full_table.py`, `screen_s2_queries.py`, `screen_s3a_one_step.py`,
`screen_s3b_multi_step.py`, `screen_s6_report.py`, and the two BoolNet drivers
`screen_boolnet_reconstruct.R`, `screen_boolnet_attractors.R`.
Pinned competitor tools: `requirements-screen.txt`.
