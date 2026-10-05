# Inputs, prospective design, estimand and decisions

## 1. Development and compatibility: inspected inputs only

Decode saved raw archives, verify bytes/length/input hashes, and retain provenance.
Do not regenerate historical strings. All old confirmation, transfer, stress,
pilot and development inputs are exposed and cannot serve as new confirmation.

Fixed compatibility population: **all 1,792 strings** in accepted
`hierarchy_search_v2/search-confirm-v2-r1`. Run the updated compatibility arm
`hid_full` on every string and require byte-identical output to the saved full
archive. Compare old deterministic stage fields, B cuts/rounds/counts/stops and
selected-stage fields, excluding recorded timings and new separate trace fields.
Preserve the old configuration dictionary and hash. Any unexplained mismatch is
a prefreeze failure, not a tolerated performance regression of the control.

Fixed treatment development population: the diagnosis's **208 D2 strings**:
176 targets (all F12 confirmation/transfer plus S02 stress) and the 32 fixed D2
controls. Run `hid_refine4` on every one, with the same limits as the control.
Read exact membership from contract.json. The control's matching compatibility
jobs provide their already-paid control results, including direct traces on these
208 strings. This reuse is a verified immutable job reference, not an incumbent
inside another encoder. No new baseline encoding is needed in development.

Thus there are **2,000 distinct successful-design worker jobs** before repairs:
1,792 control plus 208 treatment; 416 HID arm records in the 208-string paired
development comparison. Keep any repaired attempts and their charges; never
pool different code versions into a successful final gate. Fixture tests may
use hand-authored strings or `search_v3a_fixture` at lengths <=131,075, including
tiny existing F12/S02 generator fixtures. This maximum size was already inspected.
Do not call a reserved RNG namespace in tests, timings, examples or notebooks.

Compatibility requires successful uncensored encodings on all 1,792 controls;
a resource failure cannot demonstrate byte reproduction. Fixed development jobs
must have valid terminal records; ordinary watchdog raw fallback is reported,
not hidden. Trace completeness is required for the 176 paired target traces;
an unavailable trace prevents the engineering prefreeze gate, not grounds to
drop its case. If a persistent worker limit prevents the gate, return incomplete.
No improvement threshold controls progression: report development even if k=4
is worse, identical, or has lower observed proposal coverage. No development CIs.

## 2. Fresh prospective population

This final design uses **20 paired units per target cell**, including large-size
and S02 cells, rather than the smaller counts in the exploratory draft. This
avoids giving equal cell weight to cells with only four units. It is a fixed
design, not a power guarantee and not a sample size that can grow after results.

| Role / case prefix | RNG namespace | Families | Base lengths | Replicates | Units | Strings | Primary? |
|---|---|---|---|---|---:|---:|---|
| boundary | search_v3a_confirmation | F12 | 4096 | 6000..6019 | 20 | 40 | yes |
| boundary_large | search_v3a_transfer | F12 | 16384,65536,131072 | 7000..7019 | 60 | 120 | yes |
| boundary_stress | search_v3a_stress | S02 | 4096,65536 | 8000..8019 | 40 | 80 | yes |
| controls | search_v3a_controls | F01,F06,F07,F11 | 4096 | 9000,9001 | 8 | 16 | no |
| Total | | | | | **128** | **256** | **120 units / 240 strings / 6 cells** |

Each unit is one existing generator call at N=base_length+3; base is its first
base_length bits, ragged is the whole string. Never generate them independently.
Use unchanged `study_corpus.generate_unit` (F01–F12 delegate to corpus, S02 to
the existing S02 owner), with RNG namespace as seed-selection string and role
as a separate label. Namespaces never start with `development`. Preserve the
`hid-v1|namespace|family|base_length|replicate|stream` seed formula and independent
structure/content/noise streams. Case IDs use the existing case_id formatter,
with the role as prefix. No string generation is authorized during packet setup.

Before freeze, search local source/result/manifests for prior actual use of these
namespaces and key ranges. Mentions in protocol drafts are not exposure; prior
generation, scoring or inspection is. Save the evidence and declaration. If
exposed, do not privately choose new names: stop for an amended reservation.

Generate and retain every intended raw input only after the complete freeze is
validated, with generator metadata inaccessible to encoder processes. Invalid
generation does not permit skipping/reseeding a unit. Hash duplicates must be
reported, never resampled; natural duplicate strings are not new independent
evidence beyond their declared generated units. The families and sizes are
familiar; this is fresh-instance confirmation of a targeted contrast.

## 3. Methods, order and row accounting

On all 256 strings independently run `hid_full`, `hid_refine4`, and the unchanged
nine baselines in their owner order:
`raw,rle,gaps,period,bernoulli,context,zlib,lzma,pair_grammar`.
Derive one `baseline_best` row afterward by the existing complete-archive minimum
and tie order. **2,816 encoder jobs, 256 derived portfolio rows, 3,072 total rows**.
Targets account for 2,640 encoder jobs / 2,880 rows; controls 176 jobs / 192 rows.
No row for an old cumulative ablation is required in this study.

Freeze a queue sorted by role order in the table, family, numeric base length,
replicate, base before ragged. For even replicate numbers dispatch HID control
then treatment; for odd replicate numbers treatment then control. Then dispatch
the nine baselines in the order above. At most two workers; assign the next
queued job to a free slot. Completion timing never selects a new case or method.
Flush status/archives atomically before a checkpoint. Compute rows once per exact
freeze/input/method identity; verify hashes/decodes before immutable reuse.

HID watchdog timeout/RSS fallback uses the existing independently validated raw
archive with explicit `timeout_raw`/`rss_limit_raw` status. It is a real deployed
cost and may enter the primary contrast; it is not an uncensored algorithm
archive or proof of a complete trace. Decode/source/worker errors are invalid,
not raw fallback. Baseline timeout/RSS rows remain censored, and the portfolio
incomplete; do not replace a missing baseline with raw and claim a full portfolio.

## 4. Primary estimand and one prospective decision

For string x of actual length n:

`saving(x) = (bits(hid_full(x)) - bits(hid_refine4(x))) / n`.

Positive means k=4 saves bits. Use full bytes times eight, including raw fallback
when its declared status is valid. Average base/ragged per paired unit, units
within each role-family-base_length cell, then the **six cell means equally**.
Do not pool bytes, weight by n, count strings as independent units, or include
controls. Store per-string, per-unit, per-cell and overall values.

Use the existing shared `report.cell_index_draws` / `stratified_bootstrap`,
`weighted_mean` and `percentile_interval`; a thin adapter assembles the six
role-qualified cell keys and eligibility gates. Do not implement another bootstrap.
**10,000 draws, numpy.random.default_rng seed 55001, two-sided 99% percentile
interval, NumPy linear quantiles**. Sort cells by `(role,family,base_length)`
lexicographically (so boundary, boundary_large, boundary_stress), units by
replicate ascending. Each draw resamples 20 paired units within each cell with
replacement, preserving both strings and all compared methods. Freeze this exact
ordering. One primary contrast; no claim of familywise power from this interval.

Decision precedence:

1. Engineering invalidity (source/config mismatch, contradictory/duplicate rows,
   wrong decode/hash/length, violated deterministic or observer semantics) ->
   `INVALID`, no inferential primary verdict.
2. Any intended study job absent/not_run, or unverified retained archive ->
   `INCOMPLETE`, no primary inferential verdict. Show counts from the declared
   design and only explicitly partial diagnostic estimates; no primary CI.
3. With valid, complete required HID target rows: calculate the primary interval.
   Baseline censoring is separately flagged and blocks a portfolio conclusion,
   not this HID-versus-HID contrast. Missing/not_run rows still trigger item 2.
4. Lower bound >0 -> `SUPPORTED`; upper bound <0 -> `HARMFUL`; otherwise
   `INCONCLUSIVE` (including equality at zero). Map these sign readings through
   the existing report owner, with this study-specific label adapter.

Distinguish algorithmic cap stops (valid normal outcomes), external HID raw
fallback (valid cost, failed resource run disclosed), baseline censoring,
unavailable traces, and missing jobs. A trace incomplete solely because of a
real watchdog kill does not conceal its status or become a fabricated trace.
Unexpected missing trace on an `ok` HID job is an engineering failure.

## 5. Descriptive findings and independent verification

No other intervals, p-values or superiority verdicts are authorized. Report:

- six primary cell means, signed better/tie/worse counts and archive-size
  distributions; equal-cell k=4-versus-portfolio and k=1-versus-portfolio means
  only where all nine constituents are available;
- four control-cell outcomes (each two paired units), every changed control,
  cap/resource statuses, selected stages, work counts and instrumented wall/RSS;
- proposed/evaluated/returned cut trace counts and full-arm trace summaries.
  No prospective supplied-cut oracle evaluation or mechanism ranking;
- comparison with development, clearly labelled inspected and descriptive.

Always state that a positive primary result is improvement over k=1 on this
fixed mixture of six cells, not proof of beating the portfolio or improvement
across all families. Controls may change and are not a zero-change promise.

Independent audit reads archive bytes, recomputes both HID lengths and raw-fallback
validity, decodes to saved inputs, reconstructs the nine-way portfolio and its
ties/status, and recomputes the primary point estimate and six cell means without
using saved aggregate values as inputs. Inspect bootstrap draw counts/order;
production keeps the single statistical owner. Audit all promised archives and
all intended membership, not a winning subset. No encoding in the audit.

## 6. Exposure and stopping

Once prospective strings are generated or inspected, they remain exposed even
if the run fails. No post-freeze k selection, sample-size extension, drop of a
bad cell, substitution of a new seed, or rerun until positive. Complete the fixed
queue within limits and preserve incomplete outcomes if limits bind. A negative
or null result is sufficient to finish this phase and return for review.
