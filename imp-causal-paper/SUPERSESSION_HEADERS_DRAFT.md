# DRAFT — Supersession headers for the two stale handoff documents

**Status: AWAITING AUTHOR APPROVAL (AUDIT01/T2.4, gates D-5/D-7). Nothing in this
file has been applied to any target document. On approval, each header below is
inserted verbatim at the very top of its target file, and this draft is deleted
or archived per author preference.**

Evidence basis: VERIFICATION STAMPS V1 (2026-08-24, AUDIT_FIXING_PLAN_01
Appendix E) — (i) `imp-results.md` is the latest audit document and states the
work is "partial, reduced, qualitative shadow… not a full reproduction";
(ii) `results/ca/summary.json` records `inferred_rule=222` against `rule=254`
while carrying `exact_match: true`, contradicting any blanket EXACT claim;
(iii) the ledger documents RegulonDB 14.5 substituted for the paper's ~9.x,
making exact comparison impossible by construction (stamp V3).

---

## Header 1 → insert at top of `SESSION_HANDOFF.md`

> **SUPERSEDED 2026-08-24 (AUDIT_FIXING_PLAN_01 / T2.4).** This document claimed
> "Full Reproduction Complete" with all checks ✓ and ρ=+1.0 EXACT for all 10 ECA
> rules. That claim is contradicted by the project's own later records and
> artifacts and **must not be relied on**: the current statement of record is
> [`imp-results.md`](imp-results.md) ("partial, reduced, qualitative shadow… not
> a full reproduction"), corroborated by `results/ca/summary.json`
> (`inferred_rule=222` vs true `rule=254`) and by REPRODUCTION_LEDGER.md's
> partials (RegulonDB 14.5 proxy for the paper's ~9.x; CellNet 14/16). This file
> is preserved unedited as history. See also AI_AGENT_HANDOFF.md, which carries
> the same supersession notice. — AUDIT01/T2.4

## Header 2 → insert at top of `AI_AGENT_HANDOFF.md`

> **SUPERSEDED 2026-08-24 (AUDIT_FIXING_PLAN_01 / T2.4).** The status picture in
> this handoff predates the completed implementation-vs-paper audit and is
> stale where it conflicts with it. The current statement of record is
> [`imp-results.md`](imp-results.md); chronologically later evidence includes
> SESSION_HANDOFF.md (itself superseded), REPRODUCTION_LEDGER.md, and the
> persisted artifacts (e.g. `results/ca/summary.json`: inferred_rule 222 vs
> rule 254). This file is preserved unedited as history. — AUDIT01/T2.4
