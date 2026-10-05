# Codex review — representation-review-v1-r1

**Decision: CHANGES REQUESTED; synthesis not yet accepted.**
The measurements are verified. Two bounded findings concern the recommendation's
logic and the delivered audit/provenance coverage. No encoder rerun, new method,
cap sweep or change to any previously accepted experiment is needed.

## Verified evidence

The supervisor read SYNTHESIS, HANDOFF, analysis.py, audit.py, manifest.py and
the owner ledger. A separate `audit_review.py` imports neither synthesis script.
All 15 numeric/preservation checks pass (`audit_review.json`):

- All 96 unique cases and 192 selected R/O candidates are reselected from saved
  traces by full bits and request ordinal; bytes, hashes, input identities and
  independent decoding match. A0 matches its pinned k=1 reference.
- Every A0/R/O component assignment is independently reconstructed from ledger
  fields, including indexed CONCAT child IDs. All per-case components, deltas,
  aggregate component sums, counts, identity counts and both bit/normalized
  margin distributions (including q25 and q75) match the delivered tables.
- The 30 literal-selected A0 cases and minimum candidate excess of 408 bits
  are verified. The four F10 tie lengths are 440,440,696,688 bits; the erratum
  is correct. Preserve the frozen dictionary handoff.
- All 11,722 recorded pre/post hashes agree and still match current files.
  The entire synthesis output tree is unchanged by supervisor checks.

The supervisor's added verification does not make the delivered audit's stated
coverage accurate. Closure should leave a reusable audit that checks its claims.

## R1 — unsupported impossibility and exclusivity claims (blocking)

SYNTHESIS section5, reasons(iii)/(iv), infers that improvement on literal-selected
cases requires a representation change, and calls a per-word optimum the only
discriminating next experiment with little prospect of fresh confirmation.
Neither conclusion follows. A0 is a finite heuristic; choosing a raw literal
does not certify that no shorter program/archive exists in the same language.
Likewise, development on exposed examples can be followed by a separately frozen
fresh evaluation. The evidence does not rule out other controlled experiments.

Keep STOP if desired, but ground it in observed zero retained gain, additional
work and a research-priority judgment. Use "A0 selected a raw literal" rather
than "incompressible". Explicitly state that stronger search under the same
format remains untested, not impossible. Do not prescribe fresh confirmation
for an unchanged extension that produced no gain.

Calibrate the adjacent claims too: H1's descriptive component comparison is not
a causal falsifier merely because reference bytes correlate with total length.
The saved ledgers can test a specified descriptive inequality without constructing
a new archive; absence of a controlled intervention is a different limitation.
For H2, independent per-word minima need not minimize a shared DAG's total cost;
an oracle would need joint full-archive optimization over an explicitly finite
set. Its conclusion would apply only to the tested set, not all same-format
methods. No oracle implementation is requested.

Distinguish capability availability in source from output witnesses: a CONCAT
rule alone does not certify shared grammar reuse or the search path that produced
it. The existing table marks segmentation with no archive witness; the handoff
must not imply every listed search operation has been demonstrated in a saved
archive. A code-only capability label is sufficient; do not run inference.

## R2 — independent audit and manifest scope (blocking, evidence already correct)

The delivered audit checks component sums but never independently reconstructs
the labels/amounts assigned to each component. Moving bytes from CONCAT.refs to
LITERAL.payload while preserving the total can therefore evade it—the same class
of error that occurred in the first analysis attempt. It also calls its quantile
checks complete while checking only min/median/max, and does not enforce the
exact96-case set before computing results.

Add independent component reconstruction, per-case/delta/aggregate comparisons,
full declared quantile checks (including q25/q75 and normalized margins), exact
case coverage, and checks of the R-minus-O distributions/counts claimed by the
report. Use the existing quantile definition, not a new estimator. Demonstrate
that controlled in-memory corruptions of component labels with unchanged totals,
a quartile and a duplicate/missing case are rejected. No producer imports in
the independent audit; intentionally shared decoder/ledger owners are fine.

The manifest omits all96 raw input archive paths read by both scripts. Its
11,722 hashes are preserved, but "all input files" overstates that inventory.
Add a supplementary/current closure input manifest including those raw paths,
their pinned CASES reference hashes and all actual analysis/audit dependencies.
Check input hash and n after decoding. Preserve the original manifests; do not
fabricate pre-execution hashes for files omitted then. Explain original coverage
versus current supplemental verification accurately.

## Accounting and preservation

Charge 300 seconds conservatively for supervisor review, audit and correction
instructions, including the executor's disclosed uncharged final handoff edit.
243 executor + 300 supervisor = 543 / 1,800 seconds. The original time ledger
remains unchanged. The closure instructions cap new executor work at600 seconds
and reserve300 for another supervisor review: maximum1,443/1,800, with no reset
or borrowing. Record actual closure time separately, retaining all prior charges.

Only this supervision directory was added. No implementation, study, notebook
or synthesis output was modified. No encoding, commits, pushes or schedules.
