# Corpus, resource policy and analysis

Normative companion to [the protocol](../../PROTOCOL_hierarchy_search_v2.md).
No reserved prospective key from §2 may be generated, scored, previewed or used
for tuning before the new source/configuration/analysis freeze. These namespaces are reserved
by this packet, subject to a preflight exposure check. If already accessed, record
the exposure and return for an amended reservation before prospective execution.
Their presence in this specification is not data exposure; actual generation,
inspection or scoring of the corresponding strings is. Section 1 explicitly
authorizes development scoring of the previously inspected historical keys.

## 1. Development: explicitly inspected data

Reuse inputs from the immutable `results/hierarchy_v1/confirm-v1-r1/` raw archives.
Decode and check hashes against their case records. Keep original case IDs and
source references in a new development manifest, with `evidence_role=development`.
They are no longer held-out examples, including F03/F10/F11/F12.

Fixed pilot: all 12 families, original confirmation size 1,024 with replicates
1000,1001, and original transfer size 65,536 with replicates 2000,2001, each base
and ragged: **96 strings**. Run all six new HID arms and nine baselines plus the
derived portfolio row, for **1,536 rows**.

Full development regression: all **1,632** original confirmation/transfer strings,
all 16 rows per string: **26,112 rows**. Encode each method afresh under the new
resource policy; old archives are input/provenance references, not free results.
The pilot may be reused only through verified same-config immutable resume records
with its original computation included in resource accounting. Preserve all
attempts and prefreeze defect corrections. No search-parameter selection is
authorized: this packet specifies one configuration. Development verifies it and
diagnoses failures; a scientific redesign needs an explicit amendment.

Fixture tests may use hand-authored strings and namespace `search_v2_fixture`,
with maximum length 65,539, including tiny stress-generator instances. Do not use
the reserved namespaces or generate length 131,072/131,075 performance probes
before freeze. Testing arithmetic/constants for those sizes without producing
their strings is allowed. The 131,072 size is a prospective size extension;
16,384 and 65,536 were already inspected and are not unseen sizes.

## 2. Prospective design

Each unit generates one N=base_length+3 string. Score its prefix of base_length
and the complete N string, labeled base and ragged. They are one paired unit,
not two independent replicates. All string lengths below are input bit lengths.

| Role | RNG namespace | Families | Base lengths | Replicates | Strings | Rows |
|---|---|---|---|---|---:|---:|
| confirmation | `search_v2_confirmation` | F01–F12 | 256,1024,4096 | 3000..3019 | 1,440 | 23,040 |
| transfer | `search_v2_transfer` | F01–F12 | 16384,65536,131072 | 5000..5003 | 288 | 4,608 |
| stress | `search_v2_stress` | S01,S02 | 4096,65536 | 4000..4007 | 64 | 1,024 |
| total | | | | | **1,792** | **28,672** |

There are six HID methods from SEARCH.md, the existing nine actual baseline
methods (`BASELINE_METHODS`), and one `baseline_best` derived row: 16 per case.
The baseline portfolio is the minimum **complete archive** of all nine baselines
on that same string. Recompute it independently during verification; a supplied
portfolio row does not establish its own correctness. Do not add or delete a
baseline. Keep deterministic tie ordering from the baseline owner.

For F01–F12 reuse existing `corpus.generate_unit` and its unchanged generator
functions. Pass the RNG namespace as its seed-selection string, while storing
the role (`confirmation`, `transfer`, `stress`) separately. The namespace must
not start with `development`; otherwise the existing generator changes parameter
ranges. Test this separation explicitly. Preserve independent structure/content/
noise streams from `corpus.stream_rng`, whose seed key is
`hid-v1|{namespace}|{family}|{base_length}|{replicate}|{stream}`.
No new RNG implementation or accidental reseeding by raggedness is allowed.

All twelve families are familiar. Confirmation therefore tests new instances of
declared generators, not unknown structural families. Transfer and stress below
are descriptive extensions, not substitutes for a failed primary endpoint.

## 3. Exact stress-generator definitions

Stress generators live in the evaluation layer, reusing `stream_rng`, `tile`,
`primitive_word`, `complement`, `rotate_right` and `rand_word`. In the following
draw order, rs,rc,rn denote structure, content and noise streams respectively;
uniform choice means `seq[rs.randrange(len(seq))]`. Existing primitive-word guard
failures invalidate generation; never silently retry a different unit.

**S01: unfamiliar periods and two correction densities.** Let N=base_length+3.
Draw p uniformly from (37,43,59,67,97,127,193,251); draw a primitive p-bit word
from rc; draw r=rs.randrange(p); tile rotate_right(word,r) to N. Set
k=floor(N/64) for even replicate numbers, floor(N/16) for odd. Draw
`sorted(rn.sample(range(N), k))` and flip exactly these positions. Metadata records
word, p, r, density, k and positions; workers never receive it. Base is the prefix
of the resulting noisy N-string, so its realized error count need not equal
floor(base_length/density). Do not repair this sampling fluctuation.

**S02: unfamiliar mixed boundaries with insertion/deletion.** Let N=base_length+3.
In this order draw a=rs.randrange(N//6,N//3+1),
b=rs.randrange(2*N//3,5*N//6+1), p1 from (19,23,29,37), and p2 from (41,43,47,53).
Draw U1=primitive_word(rc,p1), then a fair word R=rand_word(rc,b-a), then
U2=primitive_word(rc,p2). Form
`z=tile(U1,a) + R + tile(U2+complement(U2)+U2[::-1],N-b)`.
Draw i=rn.randrange(N+1), v=str(rn.getrandbits(1)); insert v just before z[i]
(i=N appends), producing length N+1. Draw d=rn.randrange(N+1) and delete index d
of that intermediate string, producing length N. Edits may cancel; do not resample.
Record original cuts, intermediate/final edit coordinates, words and draw order.
Base/ragged extraction is the same as other units. S02 uses different parameters
within an already familiar mixed-regime idea; it is not an independent new-family
discovery claim.

For boundary-reference mapping, define original cut coordinate k as the boundary
immediately before original element k. Insertion at i shifts it to
k'=k+1 if i<=k, otherwise k; deletion at intermediate index d maps it to
k''=k'-1 if d<k', otherwise k'. Add final insertion-adjacent cuts only if the
inserted element survives: j=i-1 if d<i, otherwise i, and cuts j,j+1.
The deletion join is min(d,N). Clip these boundary candidates to each scored
prefix and remove endpoints and duplicates. Use this same explicit edit mapping
where applicable to old F12 metadata; document any schema-specific translation.

## 4. Freeze, execution and failure semantics

The freeze includes this packet, contract, actual resolved configurations,
generator and analysis adapters, all new proposer modules, every executable
dependency in the scientific path, original shared owners, environment/package
versions and baseline settings. Archive sources and hash their contents. A git
commit alone is insufficient in this working tree. Snapshot helper/test/notebook
versions too; tests and presentation do not authorize changing scientific sources.

Before each launch/resume and before final report/verify, validate the freeze.
Never downgrade a source mismatch to a warning or edit the old freeze to match.
The case design comes from the frozen Cartesian product, not from observed rows.
No reserved strings or construction truth are passed into prefreeze diagnostics.

Use 30 seconds and 1 GiB per encoder worker, at most two workers; record actual
wall time, watchdog statuses and platform memory accounting. Whole-wrapper cost
includes legacy inference, new stages, serialization, candidate decoding and
telemetry. Baseline cost likewise includes its actual encoding. Both sidecar and
archive I/O attribution must be documented; follow the existing worker boundary.
Retain literal fallback for HID resource limits using explicit deployed statuses.
Baseline resource censoring prevents portfolio-superiority support on the affected
claim population. No missing/censored row is silently dropped. Programmer errors,
bad archives and contradictory metadata are invalidity, not censoring.

Missing declared rows mean incomplete (exit 3), while malformed/duplicate/
undeclared rows, missing/malformed required archives, mismatched identities and
source mismatches mean invalid (exit 2). Valid and complete can exit 0 with a
negative endpoint. If both invalid and incomplete, invalid takes precedence.
Preserve the approved validator's initial `not_verified` marker and whole-run
scope. Known malformed-JSON paths may fail closed with that marker; do not report
a completed successful verification after an exception.

## 5. Primary endpoint

Population: confirmation, families F01,F02,F03,F04,F05,F06,F12, all three sizes and
20 replicates, both lengths: **840 strings, 420 paired units, 21 cells**.
For each scored string x, let

```text
s(x) = (bits(baseline_best(x)) - bits(hid_full(x))) / input_length(x)
```

Average the two s values within each base/ragged unit; average units within each
(family,base_length) cell; average the 21 cell means equally. Do not pool bits,
treat 840 strings as independent, weight longer inputs more, or optimize this
population after seeing results.

Use the existing paired cell-stratified bootstrap helper with
`numpy.random.default_rng(44001)`, 10,000 draws, resampling 20 paired units with
replacement within each cell, carrying every method together. Iterate families,
sizes and replicates ascending. Use percentile [2.5,97.5], NumPy linear quantiles.
Record library versions and interval algorithm. Estimate and interval are in
saved bits per input bit; positive is better for HID.

Evidence gates in order: whole-run engineering validity; completeness of this
declared claim population; availability of all nine baselines per string; then
the interval. Invalid or incomplete yields `not_assessed`. Censored baselines
yield `inconclusive`, regardless of the available-row interval. With gates passed:
lower bound >0 is `supported`; upper bound <0 is `not_supported`; an interval
touching/crossing zero is `inconclusive`. No apparent mean alone overrides a gate.
Partial summaries must be explicitly `partial_diagnostic`, never the endpoint.

An incomplete transfer/stress split does not mathematically change a complete
valid confirmation endpoint, but the overall study remains incomplete. An invalid
artifact anywhere blocks confirmatory claims until resolved under the provenance
policy. Timeout fallback in HID is a measured deployed outcome and stays included.

## 6. Five targeted cumulative comparisons

| Contrast | Population | Per-string saving |
|---|---|---|
| P versus L | confirmation F06 | (L bits − P bits)/n |
| C versus P | confirmation F06 | (P bits − C bits)/n |
| D versus C | confirmation F06 | (C bits − D bits)/n |
| G versus D | confirmation F06 | (D bits − G bits)/n |
| B addition: full versus G | confirmation F12 | (G bits − full bits)/n |

Each population has 120 strings, 60 paired units and three equally weighted size
cells. Jointly draw within all 21 primary cells with seed 44002 and 10,000 draws,
carrying pairs and all methods together; extract each target's three-cell mean.
Draw replicate indices against the frozen 20-unit index design for all 21 cells,
in ascending family/size order regardless of row availability. Each contrast
dereferences only its required complete cells and methods. Missing unrelated
cells neither change RNG consumption nor block a complete targeted population;
never drop those cells from the random-draw sequence.
Use percentile [0.5,99.5] for five two-sided 99% intervals (Bonferroni family-wise
level 95%, subject to bootstrap approximation). Positive lower bound supports
that targeted addition under this resource policy. Keep all five prespecified
contrasts even when a stage never wins. Check required methods/population gates
separately per contrast, while whole-run invalidity blocks all inference.

These contrasts have different target families. Do not average their estimates,
call them an additive decomposition of the primary endpoint, or claim pure
mechanism effects with equal work. More proposals incur more work. Contrasts may
be positive while the primary test remains negative. Both facts must be reported.

## 7. Descriptive reports and audit

Report full versus legacy and full versus portfolio for every family-size cell,
all-family confirmation, structured transfer, each transfer size, and stress
family-size cells. Use the same pair/cell weighting. Show sample counts, all
resource/censoring rates and archive cost components. These are descriptive,
without superiority verdicts or additional significance stars. Confidence
intervals are optional only for these three prespecified summaries: all-family
confirmation (seed 44003), structured transfer across its 21 cells (44004), and
all stress across four cells (44005), each 10,000 draws and 95% percentile limits.
Use the same draws to report full-versus-legacy in a summary; do not search seeds.
All other descriptive breakdowns use estimates, counts and distributions only.

Use no BDM criterion for acceptance. Explain old BDM observations only as historical
motivation. Supplied-boundary references and overhead accounting follow SEARCH.md
and must be labeled diagnostic. Any unplanned exploration is explicitly post-hoc
and cannot change the frozen decision rules.

Independently recompute the primary point estimate from saved row/archive lengths
in a small audit script that does not call the production report's endpoint
function. Assert agreement within 1e-12 and independently check the baseline min,
unit counts, equal-cell weighting and sign. Production remains the sole bootstrap
owner; audit fixtures with hand-computable pair/cell examples test its weighting
and gate logic. Do not claim an independent statistical implementation merely
because the same function was called twice.
