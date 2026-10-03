# HID-v1 benchmark, freeze, and analysis — normative annex

Version 1, 2026-10-01. These are prospective requirements, not measured results.
Positive performance is not an acceptance test for the software.

## B1. Splits and exact case counts

An independent base unit is `(split, family, base_length, replicate)`. Generate
`base_length+3` bits and score both its first base_length bits and the full string.
These two lengths form a dependent pair and must remain paired in resampling.

| Split | Families | Base lengths | Replicates | Scored strings |
|---|---|---|---|---:|
| Development | F01,F02,F04,F05,F06,F07,F08,F09 | 256,1024 | 0..3 | 128 |
| Confirmation | F01..F12 | 256,1024,4096 | 1000..1019 | 1440 |
| Transfer | F01..F12 | 16384,65536 | 2000..2003 | 192 |

Confirmation and transfer are generated only after the source/configuration
freeze. F03, F10, F11, and F12 are held-out **generator families**: do not run
inference on their generated strings during development. Hand-written opcode
unit tests and generator correctness tests are allowed; tuning on their encoded
performance is not. Do not run a preliminary confirmation subset to select caps.

This is a bounded first study. Twenty independent base units per family/size can
leave broad intervals; that is an inconclusive result, not justification for
adaptive sampling until significance. Transfer has only four units per family/size
and is descriptive. No universal generalisation claim follows from these counts.

For deterministic generation, derive each stream seed as:

```python
key = f"hid-v1|{split}|{family}|{base_length}|{replicate}|{stream}"
seed = int.from_bytes(hashlib.sha256(key.encode("ascii")).digest(), "big")
rng = random.Random(seed)
```

Stream names are fixed strings in corpus.py (`structure`, `content`, `noise`).
Use standard-library integer draws (`getrandbits`, `randrange`, `sample`) rather
than platform-sensitive numerical-library sampling. Record the Python version and
input hashes. Family definitions below fix distributions; record all realised
parameters in an evaluation-only manifest that inference never imports or receives.

## B2. Family definitions

Let N=base_length+3. `tile(w,N)` repeats nonempty w and truncates to N. Random words
are independent fair bits unless stated otherwise. A primitive word has no smaller
exact cyclic repetition period dividing its length. Sample until primitive, with
a 1000-draw guard; hitting the guard is a generator error, never a chosen example.
Distinct-word requirements have the same guard. Use independent named streams.

| ID | Definition |
|---|---|
| F01 periodic | Choose p uniformly from {3,5,7,9} in development, {13,17,31,63} otherwise. Draw a primitive p-bit word, rotate it by an independently drawn r in 0..p-1, tile to N. |
| F02 macro order | Draw four distinct primitive words of common width w, chosen uniformly from {8,12} in development and {13,17,31} otherwise. Even replicates use repeated token sequence [0,1,0,2,0,1,0,3]; odd replicates draw each token independently uniformly from 0..3. Concatenate enough words, truncate to N. Record the submode and evaluate both. |
| F03 nested relations | Held-out. Draw primitive U of length 11, V=complement(U), W=reverse(U). Set A=U*3+V and B=(W+U)*2; macro=(A+B)*2+A*3. Tile macro to N. This tests repetition, nesting, and potentially reusable transformations. |
| F04 arithmetic support | Choose two distinct steps uniformly without replacement from {3,5,7,9} in development, {13,17,31,63} otherwise. For each step choose start uniformly in 0..step-1; extend its AP through the largest position<N. Choose foreground uniformly from 0/1; emit it on the union, opposite background elsewhere. |
| F05 schema support | Let d0=log2(base_length), an integer for these base lengths. Choose three distinct address coordinates from 0..d0-1 and a random ordering of them. On those coordinates use the schema union 01*, 10*, *10; all other coordinates are free. Choose foreground uniformly from 0/1. Evaluate addresses i=0..N-1 with the chosen coordinate order and foreground. This preserves don't-cares on participating coordinates; the high coordinate introduced by the ragged tail is free. |
| F06 noisy period | Generate the clean construction of F01 using this family's own streams. Choose exactly floor(N/64) flip positions in development and floor(N/32) otherwise, uniformly without replacement, and flip them. The decoder must preserve all noise bits. The true mask is not an inference input. |
| F07 fair IID | N independent fair bits. |
| F08 biased IID | Draw each bit using randrange(8)==0; complement all bits for odd replicates. The two marginal probabilities are 1/8 and 7/8. Compression relative to raw is expected and is not evidence beyond the statistical baseline. |
| F09 Markov | Start with a fair bit. At each step flip the previous bit with probability 1/16 for even replicates or 1/4 for odd replicates, using integer draws. No higher-order dependence is introduced. |
| F10 Thue–Morse | Held-out. Choose offset uniformly in 0..2^20-1 and complement flag uniformly in 0/1. Emit parity(popcount(i+offset)) XOR flag, i=0..N-1. No Thue–Morse operator may be added after its results are seen. |
| F11 rule-110 trace | Held-out. Width 64, periodic spatial boundary, independent fair initial row. Rule index is 4*left+2*centre+right; next bit is (110>>index)&1. Flatten rows including time zero in time-major, left-to-right order. Choose starting offset 0..63, generate enough rows, and take N bits. Inference receives only that flattened string. |
| F12 mixed regimes and edits | Held-out. Make three consecutive regions of lengths floor(N/3), floor(2*N/3)-floor(N/3), and N-floor(2*N/3). First is a tiled primitive 17-bit word; second is fair IID; third tiles U+complement(U)+reverse(U) for a fresh primitive 13-bit U. Insert one fair bit at index floor(N/5), then delete the bit at index floor(4*N/5) in the already-inserted string, leaving N bits. Boundaries and edit locations are evaluation-only. |

Generators must have independent correctness checks (e.g. AP membership, rule-110
truth table, popcount parity), not assertions comparing a function to itself.
Duplicate output hashes are retained and reported, with resampling sensitivity
analysis if duplicates materially reduce effective independent observations.

No parameter is selected because a particular method compresses it. The input
corpus contains both helpful and hostile structures by design.

## B3. Methods and fairness

For every scored string run:

- HID full and the five ablations from the main protocol;
- nine individual baseline codecs from the wire annex;
- the decodable best-baseline portfolio, derived from those nine archives.

This is 15 actual encodings and one derived portfolio selection per string.
Expected confirmation method rows: 1440*16=23,040. Transfer: 192*16=3072. Rows for
failed/timed-out methods count toward completeness but have explicit status.
Derived portfolio timing is the cost of running its constituents plus selection,
not the minimum of their individual times. Report both individual and portfolio
resources. Archive length is the primary metric; model-search time is separate.

Every returned archive is independently decoded and compared bit-for-bit with x.
The inference API is tested with opaque file/case names. A runner that invokes a
special period routine only for F01 violates the protocol even if its bytes decode.
All methods see identical x, including ragged ends and noisy bits.

Use the same interpreter and machine for comparisons. Record CPU/platform/RAM,
Python, source hashes, dependencies, and library compressor versions. One encoding
per method/case is sufficient for the primary size endpoint. Record encoder wall
time excluding interpreter startup, total worker time including startup, and peak
resident memory with units/platform provenance. Do not label tracemalloc alone as
total process memory. Timings are descriptive; no noisy speed ranking is a claim.

Default limits: 30 seconds wall time per encoding, 1 GiB worker RSS, at most two
workers concurrently, and a six-hour total benchmark/diagnostic wall-clock budget.
Use deterministic search counters inside inference; watchdogs are an outer safety
limit. Choose and freeze an OS-appropriate RSS measurement/termination mechanism.
Do not rely on a nonfunctional macOS virtual-memory limit as an RSS cap.

On a HID watchdog timeout, retain a raw fallback archive, record `timeout_raw`,
and count it in overall deployed-code size; do not exclude hard cases. An encoding
exception or wrong decode is an engineering failure, not a timeout. Determinism is
required for completed deterministic searches; timing-dependent fallbacks are
explicitly distinguished and may differ on replaying another machine.

On a baseline timeout, retain a literal fallback for operational reporting and
mark that baseline `censored_timeout`; do not pretend it was the baseline's normal
code. If any constituent baseline times out on the primary endpoint population,
the strong-baseline primary scientific verdict is **inconclusive** until those
cases are completed under a newly documented comparable resource policy. Show the
observed comparison, but do not turn an incomplete baseline into evidence of gain.

If the total budget expires, write all remaining case/method IDs as `not_run`, save
resume state, and label the study incomplete. No automatic cloud escalation or
shrinking of the test set. Optimise during development to avoid this situation.

## B4. Primary endpoint and uncertainty

The prespecified structured population is F01,F02,F03,F04,F05,F06,F12 in the
confirmation split. For each scored string define:

`saving_bits = baseline_best_archive_bits - HID_full_archive_bits`

`saving_per_input_bit = saving_bits / n`.

Report both. **The primary aggregate** is the equal-family, equal-base-size mean
of saving_per_input_bit, averaging the base/ragged pair within its independent
unit first, then units in each family/size cell, then the cells. Normalisation
prevents larger strings from deciding the result simply because they contain more
bits. This operational refinement of bitacora 33 is fixed before data are seen.

Use 10,000 stratified bootstrap replicates, seed 33001. Within each family/base-size
cell resample independent units with replacement, keeping their two lengths and
all method results together. Calculate the full weighted aggregate each time.
Report percentile 95% confidence interval, mean/median savings, and complete
family/size tables. CI and bootstrap details must be machine-readable.

- If the primary interval lies entirely above zero, all required baseline results
  are available, and engineering gates pass: support **average code-length gain
  on this prespecified structured benchmark**.
- If it lies entirely below zero: reject the advantage on that population.
- If it includes zero: inconclusive. Do not replace the endpoint with a winning
  subgroup or a best seed. Numerical significance does not imply practical value;
  report the effect magnitude and resource costs.

Show the same descriptive endpoint for all twelve families, the three statistical
controls, and transfer separately. Do not pool transfer with confirmation to make
the primary interval positive. Individual family intervals are descriptive, with
no uncorrected claims of significance for selected families.

For each of five ablations define incremental gain as
`(ablation_bits-full_bits)/n` on the same structured population, with the same
weighting. Report five **99% bootstrap intervals** (Bonferroni family-wise 5%
coverage target across five two-sided intervals). Use seed 33002 and resample
methods together. A component-specific advantage requires its corrected interval
above zero. If hierarchy has no detectable incremental benefit, do not credit
the overall result to hierarchy. Flat outperforming full is an informative negative.

No global minimum or true generator-recovery rate is a primary metric. Where a
synthetic representation is recognisable, compare semantic equivalence, not exact
syntax. Do not invent a rule-recovery accuracy metric after observing results.

## B5. BDM diagnostics, separate from compression

Use only the shared description-length owner with pybdm 0.1.0. BDM remains a
diagnostic score. The study must include the notebook's historical values and
these full-coverage configurations:

- b in {4,8,9,12};
- aligned recursive boundary policy, or sliding step=1 with raise;
- input circular rotation r in the distinct set {0,1,b-1}.

All diagnostic strings here have n>=24, so each sliding block fits. Report coverage,
configuration, score, and selected setting. A rotated input is the diagnostic
object; do not treat rotation as free in the compression arm.

For each of F01,F02,F03,F04,F05,F06,F12,F07,F08,F09, choose confirmation replicate
1000, base length 1024, the **non-ragged** variant, without inspecting outcomes.
Generate 199 uniform bit permutations using seeds derived with stream
`bdm_null_<draw>`. They preserve n and number of ones. Include observed input as
row 0 and compute the full configuration matrix for all 200 strings.

Calibrate adaptivity symmetrically:

Round all BDM scores to ten decimal places before ranking, consistently for every
row, to avoid assigning scientific meaning to summation-order roundoff in ties.

1. Within each configuration c, for every row i define its lower-tail rank fraction
   `u_ic = count_j(score_jc <= score_ic) / 200`, with ties counted inclusively.
2. For every row define `T_i = min_c(u_ic)`.
3. Adaptive p-value is `count_i(T_i <= T_0) / 200`, equivalently `(1+r)/(199+1)`
   with r null rows no larger than T_0. It can never be zero.

This includes setting selection on every null row, avoiding the invalid practice
of optimising only the observed input. Report fixed-setting results alongside the
adaptive result. If making individual detection claims across ten objects, use
Holm correction at family-wise alpha=.05; otherwise label the p-values descriptive.
Use no BDM score to rank HID models or to choose benchmark cases.

This particular null tests ordering beyond bit marginals. It does not preserve
Markov dependence, so a low p on F09 is not evidence of structure beyond its
Markov generator. The context-code baseline and F09 performance answer that
stronger question. Do not generalise a marginal-shuffle rejection into causal or
universal algorithmic discovery.

## B6. Provenance, result schema, and reviewability

Every actual encoding row includes at least:

```text
run_id, freeze_sha256, split, family, base_length, replicate, ragged
case_id, input_sha256, n_bits, method, config_sha256, status
archive_path, archive_sha256, archive_bits, raw_bits, raw_archive_bits
decode_ok, selected_codec_id, rule_count, dag_depth
candidate_count, deterministic_work, stop_reason
encode_wall_ns, worker_wall_ns, peak_rss_bytes, rss_method
exception_type, exception_message, stderr_log
```

Use null for inapplicable fields, never zero as a fake timing or fabricated score.
Derived portfolio rows name the selected constituent and have a decode check.
JSONL rows are stable-sortable by case_id/method. Writes are atomic and resumable;
a duplicate case/method with conflicting hashes is an error.

Archive all encoded outputs locally or retain them in a content-addressed store
with a manifest. The supervisor must be able to decode sampled successes, losses,
and fallbacks without rerunning inference. Do not store only inferred graph JSON.
Provide per-node field-cost ledgers for the notebook examples and at least one
case per family/size. Sum every ledger back to its actual archive size.

`summary.json` states expected/present/not_run/error/timeout counts by split/method,
round-trip counts, primary and ablation intervals, and engineering/scientific status
separately. `verification.json` includes every command, exit code, test count,
run manifest/hash verification, notebook execution, and unresolved problems.

Source fixes after freezing are described in an append-only deviation log, with
old run IDs and why they became invalid. Experiment and numerical-analysis sources
are immutable under a run ID. Pure presentation files outside that immutable set
(for example notebook prose and plot colours) may change without rerunning the
experiment; record their separate hashes and preserve all numerical semantics.
Do not modify a frozen report/analysis module and then claim it was only cosmetic;
either separate presentation beforehand or make a new documented run/version.

## B7. References and novelty boundaries

The original BDM paper explicitly discusses the partition/permutation issue and
alternative boundaries. Treat the probe as an illustration of those limitations,
not their first discovery:
[Zenil et al., Entropy 20(8):605](https://pmc.ncbi.nlm.nih.gov/articles/PMC7513128/).

Use MDL as the conceptual foundation for paying for the model and encoded data:
[Grunwald's tutorial](https://arxiv.org/abs/math/0406077).

Hierarchical grammar induction predates this project. Distinguish the implemented
pair-substitution baseline from SEQUITUR, and do not claim hierarchy itself as new:
[Nevill-Manning and Witten](https://arxiv.org/abs/cs/9709102).

Any future novelty claim needs a dedicated literature assessment of arithmetic,
schema, grammar, and transform-based codes. This implementation study establishes
evidence and limitations; it does not by itself establish priority.
