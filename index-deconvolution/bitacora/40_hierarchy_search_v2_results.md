# HID-search-v2: the prospective run is valid, complete and inconclusive

Date: 2026-10-02. Status: **developer evidence, ready for supervisor review; not
accepted.** Follows bitacoras 38 (validator closure accepted) and 39 (post-hoc wall
probe). Contract: `PROTOCOL_hierarchy_search_v2.md` and its annexes. Handoff:
`hierarchy/HANDOFF_SEARCH_V2.md`.

## What was tested

Bitacora 39 found short, legal, input-only descriptions on noisy-period strings that
the frozen HID-v1 search missed. This stage asked whether better proposals, under one
declared resource policy and inside the unchanged wire language, beat the nine-codec
portfolio on fresh instances of the structured population. Six cumulative arms were
built: the legacy search alone; plus first-block templates with local patches; plus
consensus templates; plus the dense period grid; plus one global correction list; plus
bounded input-only boundary discovery. Every arm reruns the legacy search and pays for
all its own work.

## Provenance first

Before any source edit, the r1 source and protocol set was archived as a tar whose 25
members all hash to freeze `f970efff…` (the historical description-length owner taken
from the verified retained copy, the active file untouched); a read-only wrapper reruns
the supervisor's r1 audit from that tar and reproduces the stored audit exactly. The
approved validator patch was applied once and matched its reviewed hashes. Both old run
trees are byte-identical before and after this work.

## Development (previously inspected inputs)

The 96-string pilot and the 1,632-string regression (26,112 rows) were valid and
complete, with no timeouts and no nesting violations. The legacy arm reproduced r1's
archive on 1,632 of 1,632 strings, and every baseline archive was identical. No defect
correction, parameter change or amendment was needed. The one disruption was external:
the agent tool's background time limit killed the first regression invocation, which
was resumed under the same fingerprint.

## Prospective result (`search-confirm-v2-r1`, freeze `0f0a72ef…`)

1,792 strings and 28,672 rows, all present and decoded exactly; no resource fallback,
censoring or error. On the primary population (420 paired units, 21 equally weighted
cells) the mean saving is **+0.0056 bits per input bit, 95% interval [−0.0021, +0.0130]**.
The interval crosses zero, so the prespecified verdict is **inconclusive**: superiority
over the portfolio is not demonstrated, and neither is inferiority. An independent
recomputation from archive bytes agrees exactly.

All five targeted contrasts are positive at 99%: on F06, first-block local patches
(+0.014 [+0.001, +0.034]), consensus (+0.122 [+0.071, +0.175]), dense periods
(+0.100 [+0.037, +0.170]) and the global patch (+0.046 [+0.039, +0.052]); on F12,
boundary search (+0.120 [+0.113, +0.128]). They measure costed, cumulative algorithm
changes on their target families; they do not add up to, or rescue, the primary test.

Descriptively, structured transfer sits at zero against the portfolio
(+0.0004 [−0.0035, +0.0043]) while improving on the legacy search by +0.055; the stress
families favour the new search (+0.174 [+0.151, +0.194]); across all twelve
confirmation families the portfolio still wins (−0.073), as the statistical controls
dominate that average.

## Reading

The specific obstacles named in bitacora 39 were real and addressable: consensus and
dense coverage repair the noisy-period failures, and the global patch removes much of
their record overhead. What did not move is the rest of the structured population. The
periodic and macro-order families (F01–F03) lose in every cell, exactly as before,
because the portfolio's period and grammar codecs carry less overhead than a HID graph;
F05 loses slightly; F12 at 4,096 bits and above loses, and the evaluation-only
supplied-boundary references are shorter there than the automatic archives, which points
(without proving it) at the boundary search's reach under its caps. Exact cost buckets
show transfer archives spending a third of their bits on child references. None of this
licenses changing the wire format; it locates where further work would have to look.

The earlier negative estimate (−0.0446) was measured on different reserved instances,
so the movement to an interval around zero is a descriptive observation, not a paired
effect. The study remains a statement about one language, one resource policy and
fresh draws of familiar generators: not Kolmogorov complexity, not generator
identification, not unfamiliar-family generalisation.
