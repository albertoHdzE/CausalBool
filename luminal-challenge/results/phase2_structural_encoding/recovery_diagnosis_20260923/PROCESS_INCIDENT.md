# Process-control incident record

Date: 2026-09-23 UTC. Recorded immediately after lead notification.

I mistakenly treated PID 60416 as the Phase2 runner based on a stale process
sample taken while the runner was active. I did not verify its command line or
ownership before signaling it. The lead's elevated process inspection later
identified PID 60416 as an unrelated Jupyter ipykernel, approximately 17 hours
old, and confirmed that no `research.run_structural_experiments` or
`research.classical_measurement_worker` processes remained. The signal below
terminated that unrelated kernel. This action was outside the experimental
process tree and is recorded rather than attributed to the recovery run.

Exact signal command: `kill -TERM 60416`.

Tool invocation time: 2026-09-23 20:11 UTC (approximate; the command response
was returned before the 20:13:50 UTC incident record). The command returned
exit code 0 and no output. Mistaken rationale: an earlier process listing
associated PID 60416 with the active Python runner; I inferred continuity from
the reused PID without checking executable arguments. The lead subsequently
corrected that identification. No further process signals were sent.

The recovery runner itself was interrupted through its own exec session
(`session_id=72879`) with Ctrl-C and returned exit code 130. The last P5 worker
log count is 3,594 lines and remained unchanged after the runner session ended.
The run's raw P5 result rows were not durably journaled. See
`../recovery_campaign_20260923/ABORTED_FOR_REPAIR.json` for the campaign's
incomplete accounting.
