# Reference-timeout recovery amendment

Authorized by the user's request to investigate, fix and resume the final
replication. The original protocol, manifests, study sources and execution
profile remain intact. This is an explicit amendment to their no-automatic-
retry rule, not a retrospective claim that the interrupted run succeeded.

Observed failure: batch 747 (zero-based) ran for 300.057 seconds. All 48
records have `reference_owner_failure` with Wolfram status `timeout`; their
Python results passed. The existing batch implementation assigns one process
timeout to every member. It cannot identify a slow case, license contention,
or another cause inside the kernel from these records. The immediate cause is
the batch wall-time limit; its underlying cause is not established.

Recovery uses the existing individual Wolfram owner, one fresh process per
network, with the original 300-second per-process limit. Every result must
exit normally and reproduce the exact stored output digest. Independently
replay the Python dynamics and recompile the shared program before accepting
each replacement. Keep program bytes, BDM and dynamics unchanged.

Preserve exact copies of the failed records, audit, progress, controller
status and log. Stage all replacements before installing any of them. Failed
or interrupted individual attempts remain recorded and are not automatically
retried. A success record links the old record hash to the new reference and
the recovery amendment. Preserve prior accepted checkpoints.

Only pure Wolfram timeout batches qualify. Output mismatch, malformed data,
other owner failures, changed sources and budget exhaustion stop the run.
Allow at most three timeout-batch recoveries in this amended run (including
the current batch), with at most one individual attempt per affected network.
The regular 48-case execution profile remains unchanged; individual recovery
is a fallback after a failed stage. No new seeds, sample reduction, timeout
increase, or change to scientific definitions is permitted.

Charge recovery wall time to main/progress.json. Reserve 360 seconds before
each individual attempt (300 for Wolfram, 60 for validation/IO); retain the
reservation after interruption or failure. Settle to measured recovery time
after normal completion. Main resume reuses the cumulative charged budget.
Do not rerun the completed pilot or replace its forecast with resume overhead.

The recovery supervisor holds the original controller lock; recovery also
holds the main stage lock. The original run_stage owns the stage lock during
normal execution. Source checks and historical preflight/calibration evidence
must remain valid. Completion still means computation_complete_awaiting_analysis;
this amendment does not certify the final scientific analysis.

Commands from the repository root:

```
PYTHONPATH=doppel-challenge/src python tools/joint_reference_recovery/recover.py --action recover
PYTHONPATH=doppel-challenge/src python tools/joint_reference_recovery/recover.py --action launch
```
