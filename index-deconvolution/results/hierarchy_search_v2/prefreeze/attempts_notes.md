# Development attempts (HID-search-v2), 2026-10-02

1. `dev-search-v2-pilot` — complete in one invocation (961 s), valid, 1,536 rows; deliberate
   interruption after 8 cases then resume; fresh replay of 12 cases identical.
   Log: `prefreeze/pilot_attempt1.log`.
2. `dev-search-v2-regression`, invocation 1 — killed externally by the agent tool's
   background time limit (1,800 s) at 1,406/1,440 confirmation cases. No code defect;
   no orphaned workers; 1,406 atomic case files preserved; two in-flight worker stderr
   temporaries left in `tmp/`. A conservative 60 s ledger entry covers the unrecorded
   in-flight interval. Log: `prefreeze/regression_attempt1.log`.
3. `dev-search-v2-regression`, invocation 2 — resume of the same run id under the same
   development fingerprint (no source change between invocations).
