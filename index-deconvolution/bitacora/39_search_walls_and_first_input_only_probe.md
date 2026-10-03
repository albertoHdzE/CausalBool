# The negative result is not an impossibility result

Date: 2026-10-02. Status: **post-hoc exploratory diagnosis**, following acceptance
of the frozen study and review of its validator patch. No frozen implementation,
protocol, baseline archive, result row or scientific verdict was changed.

The accepted result concerns one automatic search, one representation, specified
budgets and a finite benchmark. It does not establish that hierarchical index
deconvolution cannot be built or improved. A lossless implementation already
exists. What failed was its prespecified overall code-length superiority test,
not exact reconstruction and not the possibility of a better discovery procedure.

## 1. Separate the questions

1. Can the language express an exact description? Retained archives establish
   this for all study inputs; literal fallback makes representation broadly
   possible but alone says nothing about useful compression.
2. Can it express a *short* useful description? Explicit legal witnesses answer
   this positively on particular structured cases, not universally.
3. Can an automatic method discover that description from the bits alone within
   budget? This is the main unresolved research target.
4. Does the full method beat strong comparators on a declared population? The
   frozen version failed that aggregate test. No impossibility theorem follows.

The previous F12 witness (22,480 bits vs 28,528 from automatic search) used known
construction boundaries. It demonstrated a representational opportunity, not
automatic discovery. The new probe below makes progress on question 3 for noisy
periodic strings without access to generator metadata.

## 2. Concrete obstacles in the current implementation

| Obstacle | Evidence | Investigation |
|---|---|---|
| Noisy template estimated from the first block | `candidates.noisy_periods` repeats the first p observed bits; an error there is repeated in the proposed clean model | Estimate each phase by consensus across repeated observations, then transmit every residual error |
| Sparse noisy-period grid | Current grid is 1..32, 64,128,256; 63 is absent from this proposal family | Search 1..256 uniformly, without supplying the true period |
| Correction cap restricts large inputs | Search cap is min(64, floor(L/16)); a 65,536-bit 1/32-noise input has about 2,048 errors | Compare local capped corrections with an explicitly relaxed whole-input correction cap; the existing wire format can represent the latter |
| Fixed segmentation misses mixed regimes and edits | F12 feasible description is shorter when boundaries are supplied | Learn boundaries from input-only description-cost changes; compare automatic and boundary-assisted costs separately |
| Description overhead and search are conflated | Full-archive costs depend on record/reference overhead as well as which graph is found | Measure both costs before deciding a new opcode or statistical leaf is needed |
| Finite search may spend effort poorly | Candidate/work caps stop some searches; ordering affects which candidates are reached | Profile candidate yield and allocate effort by complete-archive improvement, testing under the same total resource budget |

These are testable algorithmic and engineering questions. The original study does
not establish that any single obstacle accounts for the entire aggregate loss.

## 3. New input-only probe

Implementation: `experiments/probe_hierarchy_search_walls.py`.
Evidence and complete generated archives:
`results/hierarchy_wall_probes/noisy_consensus_v1/`.

The proposer has one input: the binary string. It receives no family label,
period, seed, construction boundary or noise mask. Evaluation deliberately selects
all F06 (noisy-period) and F07 (fair-IID) transfer cases from the already inspected
study: 16 strings per family, each formed from **eight base/ragged pairs**. These
are not 16 independent experimental units per family.

It tests four fixed variants:

1. First-block templates, original period grid, 1,024-bit local correction blocks.
2. Consensus templates, original grid, the same local correction blocks.
3. Consensus templates, every period 1..256, the same local correction blocks.
4. Consensus templates, every period 1..256, one global correction list.

For a period p, consensus chooses the majority bit among positions with the same
index modulo p; ties choose 0. Candidate models require at most floor(n/16)
differences. Local patches retain the original per-node min(64, floor(L/16)) cap,
falling back to a literal segment if needed. The global variant deliberately
removes the fixed 64-error limit while retaining the n/16 bound. It changes a
search restriction, **not the wire language**.

Every candidate includes transmitted templates, lengths, references, corrections,
headers and padding. Consensus does not discard noise: the decoder reconstructs
the exact original string. Winning proposal archives were independently decoded.

The reported augmented cost is the smaller of the saved frozen HID archive and
the new proposal archive. This tests the value of the proposal source; it is not
a rerun of the full search with a newly frozen end-to-end compute budget.

| Variant | F06 strings shorter than frozen HID | F06 strings beating portfolio |
|---|---:|---:|
| First block, original grid, local patches | 2 / 16 | 2 / 16 |
| Consensus, original grid, local patches | 8 / 16 | 8 / 16 |
| Consensus, dense grid, local patches | 16 / 16 | 12 / 16 |
| Consensus, dense grid, global patch | 16 / 16 | 16 / 16 |

All F07 controls retain the literal archive and tie the baseline portfolio. That
is consistent with the literal fallback; it is not an independent calibration of
false discoveries or evidence that random data can always be recognized.

For `transfer-F06-65536-2000-base`:

| Description | Complete archive bits |
|---|---:|
| Frozen automatic HID | 50,728 |
| Best baseline portfolio member | 25,936 |
| Dense consensus with local capped patches | 30,904 |
| Dense consensus with one global patch | **16,992** |

The global proposal selected period **63 from the full 1..256 grid**, encoded all
**2,048** corrections, used five rules at depth four, and decoded exactly. This
demonstrates a discoverable short description on that input without true-period
or true-noise-mask access. It does not certify a shortest description.

All four variants together took at most 0.122 seconds per tested input in this
exploratory execution. This excludes the original search's runtime and is not a
claim of end-to-end resource-policy compliance. The script passes repository lint.

## 4. Interpretation and limits

This is concrete evidence that a major failure on these noisy-period cases is
addressable without abandoning hierarchical descriptions or inventing another
wire format. The local variant already improves all F06 cases while retaining
the per-patch correction cap. The global variant removes substantial record
overhead by encoding one correction list.

It is **not a new positive confirmatory result**. The families, failures and
period-grid gap were inspected before designing this probe. The cases are reused,
only two families were evaluated, and no new confidence interval or whole-benchmark
superiority claim is justified. There are no results here about predicting unseen
suffixes, causal identification, or finding every class of useful structure.

The frozen study's negative result remains unchanged. The new result is an
exploratory reason to investigate specific solutions rather than conclude that
the research aim is impossible.

## 5. Next research stage

Prioritize search improvements within the current language before adding new
encoding operators:

1. Integrate the consensus, period-coverage and correction-placement proposals in
   an isolated development branch, alongside the approved validator patch. Compare
   changes individually, preserving a literal fallback and actual archive costs.
2. Evaluate all previously inspected families as development/regression data,
   recording exact decoding, byte savings, candidate counts, runtime and memory.
   Measure the complete integrated algorithm under the resource limit; adding a
   useful proposal can still displace other candidates in a bounded search.
3. Investigate F12 boundary discovery separately. Preserve the boundary-assisted
   witness only as a feasible-cost reference; automatic inference must not receive
   its boundaries. Record the gap between automatically found and feasible costs.
4. Account for record/reference overhead independently. Consider changing the
   format only where cost accounting supports that decision; any new opcode or
   entropy-coded component requires a new version and explicit baseline comparison.
5. Freeze the revised algorithm, budget and analysis before evaluating newly
   reserved seeds. Retain the predefined all-family/structured populations and
   controls; add prospectively specified families if claiming broader structural
   generalization. Newly reserved seeds test new instances, not unfamiliar families.

Success criteria remain exact reconstruction, reproducibility, resource compliance
and measured comparative performance. A positive result is a hypothesis to test,
not a condition to force. The study has identified actionable obstacles; it has
not exhausted the research direction.
