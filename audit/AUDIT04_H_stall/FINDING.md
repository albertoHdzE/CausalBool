# AUDIT04-H · H3 — the intermittent stall: bounded guarantee, cause still unknown

**Branch:** `fixing`
**Anchor commit:** `fc003f8`
**Date written:** 2026-09-09
**Owners:** `tools/run_closure.sh`, `tools/test_h3_watchdog.sh`,
`tools/run_h3_4_licence_contention.sh`, `GOVERNANCE/VERIFICATION.md`

This note is the single record for task H3 of
`plans/AUDIT04-H_comparator_measures_and_lifecycle.md` (lines 515-560).
The task's goal was either to identify the cause of the intermittent pre-push
stall with evidence, or to install a mitigation that cannot mask a real failure
and state plainly that the cause remains unknown. The second outcome was
achieved. The owner is still `tools/run_closure.sh`; no second runner was
introduced.

---

## 1. Outcome in one paragraph

The cause of the intermittent stall remains unknown. What is now guaranteed is
that the closure runner cannot hang silently: every member emits a start/end
timestamp, every member runs under a named per-member watchdog, a timeout is a
distinct red (`exit 3`, verdict `TIMEOUT`) rather than a skip, and the runner
attempts a `sample`/`lsof` capture when the timed-out PID is still alive. The
licence-contention hypothesis was not reproduced by 30 consecutive
`wolfram-syntax` runs under a concurrently held second kernel: **30/30 passed**,
all in **5-6 s**, which bounds the per-invocation stall probability below
**9.5 % at 95 % confidence** if that hypothesis were the only cause.

---

## 2. H3.1-H3.3: timeline, watchdog, and plant

### 2.1 The watchdog idiom is measured, not asserted

The plan names the working perl form and warns against a near-identical broken
one. On this machine the difference is measurable:

| command | measured result |
|---|---|
| `time perl -e 'alarm shift @ARGV; exec @ARGV or die $! || 142' -- 2 perl -e 'sleep 5'` | exits **142** after **2.008 s** |
| `time perl -e 'alarm $ARGV[0]; exec @ARGV' -- 2 perl -e 'sleep 5'` | exits **0** after **0.007 s** |

The second form does not bound the child; it returns almost immediately and is
therefore unusable as a watchdog in this repository.

### 2.2 The production timeout fires at the production value

**Producer:** `zsh tools/test_h3_watchdog.sh`
**Denominator:** 1 planted timeout of `perl -e 'sleep 70'`, under the same
runner code used by `tools/run_closure.sh`.

Observed output:

```text
elapsed=60s rc=142
capture (plant): dead-pid line emitted (expected for a SIGALRM-reaped plant)

-- H3 watchdog self-test: PASS
  verdict=TIMEOUT rc=142 elapsed=60s (production timeout 60s)
  capture: STALL-CAPTURE stage=test-plant pid=28928 ts=20260909T134950Z
```

This is the acceptance condition the plan actually needs from the plant:
the timeout fired at the **production** pure-tier value of **60 s**, the member
went **red and named**, and the capture path recorded the stage and PID.

### 2.3 What the plant does and does not prove

The plant does **not** produce a live `sample` backtrace or a non-empty
`lsof` capture on this platform. The reason is architectural and measured in the
runner: the perl watchdog writes its PID to a PIDFILE and then `exec`s the
member, so the timed member inherits the same PID; when `SIGALRM` fires, the
exec'd child dies with the perl process, and by the time `capture_stall` runs
the PID is usually already gone. In that case the runner emits the named line

```text
process is NOT live: capture is timing + PID only
```

rather than a false artefact path. That is an honest bounded guarantee, not a
diagnosis. A future **live** timeout is still capable of producing
`/tmp/cb_stall_<stage>_pid<pid>_<ts>.txt` and `.lsof`; the code path exists in
the owner, but this plant does not keep the process alive long enough to reach
it.

---

## 3. H3.4: licence-contention hypothesis

**Producer:** `zsh tools/run_h3_4_licence_contention.sh`
**Artefact:** `/tmp/cb_h34_licence_contention.tsv`
**Denominator:** 30 consecutive `wolfram-syntax` invocations, each run under the
production watchdog value of **600 s**, with a second `WolframKernel` held open
for the full measurement by `While[True, Pause[3600]]`.

The experiment reuses the **same** watchdog and capture functions extracted from
`tools/run_closure.sh`, not a second timeout implementation. Each run therefore
has the same timeout semantics the closure runner would apply in the pre-push
path.

### 3.1 Summary

| quantity | measured value |
|---|---|
| completed runs | **30 / 30** |
| PASS / FAIL / UNKNOWN / TIMEOUT | **30 / 0 / 0 / 0** |
| elapsed range | **5-6 s** |
| mean elapsed | **5.40 s** |
| sample standard deviation | **0.49 s** |
| runs over 60 s | **0 / 30** |
| runs over 600 s | **0 / 30** |

No timeout occurred, so no `/tmp/cb_stall_wolfram-syntax_*` artefact was
produced. That is the correct result for this denominator: a capture file should
exist only if a live timeout occurred.

### 3.2 The 30-run table

| run | start UTC | verdict | exit | elapsed s |
|---|---|---|---:|---:|
| 1 | `2026-09-09T13:45:36Z` | PASS | 0 | 5 |
| 2 | `2026-09-09T13:45:41Z` | PASS | 0 | 6 |
| 3 | `2026-09-09T13:45:47Z` | PASS | 0 | 5 |
| 4 | `2026-09-09T13:45:52Z` | PASS | 0 | 5 |
| 5 | `2026-09-09T13:45:57Z` | PASS | 0 | 6 |
| 6 | `2026-09-09T13:46:03Z` | PASS | 0 | 5 |
| 7 | `2026-09-09T13:46:08Z` | PASS | 0 | 5 |
| 8 | `2026-09-09T13:46:13Z` | PASS | 0 | 6 |
| 9 | `2026-09-09T13:46:19Z` | PASS | 0 | 5 |
| 10 | `2026-09-09T13:46:24Z` | PASS | 0 | 5 |
| 11 | `2026-09-09T13:46:29Z` | PASS | 0 | 5 |
| 12 | `2026-09-09T13:46:34Z` | PASS | 0 | 6 |
| 13 | `2026-09-09T13:46:40Z` | PASS | 0 | 5 |
| 14 | `2026-09-09T13:46:45Z` | PASS | 0 | 5 |
| 15 | `2026-09-09T13:46:50Z` | PASS | 0 | 6 |
| 16 | `2026-09-09T13:46:56Z` | PASS | 0 | 5 |
| 17 | `2026-09-09T13:47:01Z` | PASS | 0 | 5 |
| 18 | `2026-09-09T13:47:06Z` | PASS | 0 | 6 |
| 19 | `2026-09-09T13:47:12Z` | PASS | 0 | 5 |
| 20 | `2026-09-09T13:47:17Z` | PASS | 0 | 6 |
| 21 | `2026-09-09T13:47:23Z` | PASS | 0 | 5 |
| 22 | `2026-09-09T13:47:28Z` | PASS | 0 | 6 |
| 23 | `2026-09-09T13:47:34Z` | PASS | 0 | 5 |
| 24 | `2026-09-09T13:47:39Z` | PASS | 0 | 6 |
| 25 | `2026-09-09T13:47:45Z` | PASS | 0 | 6 |
| 26 | `2026-09-09T13:47:51Z` | PASS | 0 | 5 |
| 27 | `2026-09-09T13:47:56Z` | PASS | 0 | 6 |
| 28 | `2026-09-09T13:48:02Z` | PASS | 0 | 5 |
| 29 | `2026-09-09T13:48:07Z` | PASS | 0 | 6 |
| 30 | `2026-09-09T13:48:13Z` | PASS | 0 | 5 |

### 3.3 Interpretation

The licence-contention hypothesis is **not reproduced** by this denominator.
That does **not** prove the hypothesis false in general. With **0 stalls in
30 runs**, the correct statement is:

> If the concurrent-kernel syntax run were the true generating mechanism,
> the per-invocation stall probability is bounded above by
> `1 - 0.05^(1/30) = 9.5 %` at 95 % confidence.

That bound does **not** exclude a rare intermittent defect. A bare sentence of
the form "0/30, hypothesis unsupported" would therefore overstate what this
measurement shows.

---

## 4. Conclusion for H3

H3 ends as a **bounded guarantee**, not a root-cause diagnosis.

What is now true:

1. `tools/run_closure.sh` names the stage it is in, with start/end timestamps
   and elapsed seconds.
2. Every closure member runs under a per-member watchdog and a timeout is a
   **named TIMEOUT red** with exit code **3**, not a pass and not a skip.
3. A future live timeout can emit `sample` and `lsof` into `/tmp/cb_stall_*`;
   the current plant proves the named timeout and PID capture path, but not a
   live backtrace.
4. The specific licence-contention hypothesis tested here is not reproduced by
   **30/30** syntax runs under a concurrently held second kernel.

What remains unknown:

1. The actual cause of the historical three-hour pre-push stall.
2. Whether the unreproduced stall sits in the syntax member, a later Wolfram
   member, or a full `make ci-local` interaction the reduced experiment does not
   cover.

What would close this finding:

1. A future timeout that yields a **live** `sample` backtrace and thereby names
   the blocked frame; or
2. **30 clean `make ci-local` / pre-push hook invocations** under the new runner
   with no timeout, at which point the old anecdote would be outweighed by a
   measured clean denominator under the actual hook path.
