# Manuscript readiness — Phase 2 release candidate

2026-09-24 · Claude Code · plan §7. This is an assessment only. The paper was
not edited. The evidence comes from `recovery_campaign_20260923_r3`, all of it
subject to Codex review. "Supported" means supported by retained raw rows that
two independent recomputations agree on; it does not mean accepted.

## Claim-to-evidence table

| # | Candidate claim | Evidence | Status |
|---|---|---|---|
| 1 | The four codecs are exact bijections on the implemented finite domains | P1: 24 exhausted codec/oracle comparisons with exact set equality, 0 round-trip failures, 0 defects | Supported, within the implemented F_d |
| 2 | Physically valid one-field neighbours of the direct incumbent round-trip exactly through all four codecs | 7,727 validated objects, 0 discrepancies, 3,835 physically invalid proposals and 2 deadline interruptions (not credited) | Supported as **local** codec coverage only |
| 3 | Random sampling of the codes covers the public feasible sets | Original streams: 0–234 distinct objects per program against the required 100 | **Not supported**; the original P1 coverage verdict fails |
| 4 | The fixed `structural_bound` gives lower J than accepted direct v4 at the primary budget on held-out programs | H2 primary: +0.0439 [0.0251, 0.0660]; 26 W / 74 T / 0 L over 100 programs in 5 families; reproduced exactly in `_r2`; independent auditor agrees | **Supported (confirmatory)**. The effect is small: a 4.3 % geometric-mean J reduction, carried by 26 % of programs |
| 5 | The same holds against accepted default and bootstrap, and at every budget | Descriptive: +0.040 to +0.057, no losses | Supported descriptively (unadjusted) |
| 6 | The gain comes from the admissible bound | `structural_dfs` equals `structural_bound` at 0.1 s and 1.0 s | **Not supported**. The gain comes from the matched-window structural search |
| 7 | The gain is mainly in scratch allocation | Of the 26 wins: 21 are scratch-only, 3 trade +1 cycle for a scratch reduction, 2 are cycle-only | Supported (descriptive, mechanism render) |
| 8 | Phase 2 improves the public score | Public: +0.0240 [0, 0.0721], 1 W / 7 T / 0 L; the interval touches zero | **Not supported**. Inconclusive, and not equivalence |
| 9 | The candidate has lower J than classical on held-out programs | +0.0882 [0.0592, 0.1194], 53 W / 35 T / 12 L | Supported descriptively (unadjusted, secondary) |
| 10 | The candidate is cheaper than classical | Compile time 7.3× [6.0, 8.7], process time 1.50×, RSS 1.18× | **Contradicted**. It is slower; this is a trade-off |
| 11 | The candidate compiles faster than accepted direct | 0.073× `accepted_budgeted` at 0.1 s; 0.042× default | True as measured, but it reflects an early stop at the query cap, not faster equal work. It must be stated with that mechanism |
| 12 | Structural models discover unseen good compilations (H4) | Only 1 of 12 fixtures is informative, so ≥3 families are impossible; ties on that one fixture | **Unmeasured / untestable** with the frozen fixtures |
| 13 | H3 structure triage | 7/11 informative fixtures across 3 families | Supported as triage only, not as a statistical test |
| 14 | The production compiler is unchanged and still accepted | `verify_direct` all stages PASS; `compare_direct` 8/8 gates PASS; classical frozen at 1.901379, direct 2.008466; protected hashes verified before and after | Supported. This validates the controls, **not** Phase 2 |

## Supported claims (bounded)

A deterministic structural search over a matched window around the accepted
direct bootstrap gives a small, reproducible, one-sided reduction in J = C × S on
100 held-out programs. The confirmatory estimate is +0.0439 [0.0251, 0.0660], with
no program worse. The reduction is mainly in scratch, and it costs a few
milliseconds. Against classical it gives lower J (descriptive) at a higher
compile cost.

## Unsupported or contradicted claims

The following claims are not supported by this evidence:
- superiority on the public programs or on the official public score;
- any benefit from the admissible bound or the expanded domain;
- faster compilation than classical;
- any H4/model advantage;
- diverse or uniform schedule sampling;
- global optimality;
- novelty.

## Limitations to state in any manuscript

1. The effect is small and concentrated in 26 of 100 programs. Technical
   repetitions measure time only, because J is deterministic in 1,498 of 1,500
   held-out cells across the two runs.
2. The held-out corpus is generated (5 families × 20 programs). Only the primary
   is confirmatory; the 23 other contrasts are unadjusted.
3. P1 passes only under the post-hoc recovery amendment, which is a recovery
   protocol and not a prospective registration. The original coverage fails.
4. The search is truncated by a 32-query cap in 64 % of held-out programs, so the
   measured effect is that of the configuration as frozen, not of the method's
   ceiling.
5. H4 cannot be tested with the frozen fixtures.
6. The pipeline needed seven post-checkpoint repairs (R1–R7). Two of them
   concerned the evidence checker and appeared only under a real campaign.
   `_r2` (checker v1) is retained, and the run of record is `_r3`.
7. The results come from a single machine (macOS 26.6.2 arm64, Python 3.13.12), and
   timing ratios are machine-specific.

## Open blockers before a new manuscript

- **Codex review and acceptance of this release**, the hard prerequisite.
- A decision on whether the paper reports this bounded result as it stands, or
  waits for the optimisation phase (`OPTIMIZATION_DECISION.md`). A paper that
  waits needs a fresh held-out cohort, because tuning on this one converts it
  into development data.
- Adding H4 to any paper requires new fixtures and a fresh run.

Assessment: the evidence is **sufficient for an honest, bounded manuscript
section** reporting a small confirmed held-out quality gain over accepted direct,
a quality/cost trade-off against classical, and explicit nulls and untestables.
It is **not sufficient** for a superiority, public-score or model-based claim.
The final decision rests with Codex.
