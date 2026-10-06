# Claude Code delegation: final audit closure

Read PROTOCOL.md, ACCEPTANCE.md and manifest.json in this directory, then execute the
bounded closure. Read the supervisor review at
`../../supervision/task-compaction-v1-finalization-r1/REVIEW.md`.

The integrated compaction code, tests, portable fixture, documentation and owner entry
are accepted and must stay byte-identical. Fix only R1 (fixture validation) and R2
(seal coverage/authority) in a separately identified run-local audit revision.

Output only to
`index-deconvolution/results/causal_task_compaction_v1/finalization_review_closure/task-compaction-v1-finalization-r1/`
and scratch directories under /tmp. No production rerun, new study, active-source edit,
dependency install, commit, staging, push, publication or recurring task.

Executor cap: 1,800 wall-clock seconds, including thinking, failed attempts and final
writes; preserve a separate 300 seconds for Codex. Do not start follow-up work. Finish
with HANDOFF.md marked **ready for Codex review; not yet accepted**.
