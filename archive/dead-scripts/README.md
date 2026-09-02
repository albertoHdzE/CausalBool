# Dead scripts carrying hardcoded numbers — retired 2026-09-02 (AUDIT02/P7)

Archived per the project's archive policy: preserved for provenance, never
deleted.

All three were referenced by nothing — no import, no `Get`, no runner, no
documentation outside this file. Each also carries numbers copied into the source
rather than computed, which is why they were a provenance trap rather than merely
unused: rerunning one would emit values that look computed but are transcribed,
with no producer to check them against.

| file | the hardcoding, verbatim |
|---|---|
| `compute_bdm_from_d5.py:162` | `# Original Gzip ratios from table (hardcoded for now as we are not recomputing gzip)` |
| `verify_bdm_from_mathematica_table.py:129` | `# Let's use the actual truth tables from json or hardcode them if we know them.` |
| `simulate_factorisation.py:46` | `# Gates (dummy)` |

None of them feeds any manuscript number. The reconciliation of manuscript values
to producers is `papers/method/artifact_baseline/artefacts.json`, enforced by
`make verify-paper`; none of these files appears there.

If any of this is wanted again, recompute the values from a real producer and
register the result in `artefacts.json` — do not restore the transcribed
constants.
