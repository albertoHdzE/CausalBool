# Protocol bdm_anatomy_v1 — how BDM works, when it works, and how it relates to index-set codes

**Version 1.0, written 2026-10-04, frozen by `freeze.json` before the first confirmatory
run.** Any later change is an amendment appended at the end, with its date and reason;
nothing above it is edited. The producer refuses to run if the sha256 of this file, of the
owner sources or of the producer itself differs from `freeze.json`.

Background: `index-deconvolution/bitacora/43_bdm_anatomy_initial_study.md` (exploratory),
and the plan `plans/wait-we-can-do-floating-starlight.md`. Bitacora 43's numbers came from
unregistered probes; none of them is evidence for this protocol, and all are regenerated
here under fixed rules.

## 1. Objects and measures

**BDM.** `description_lengths.bdm_1d` (1-D, pybdm 0.1.0, D(5) CTM table, block 1–12) and
`bdm_2d` (2-D, 4×4 blocks). 1-D BDM in this protocol is always **aligned with the
recursive remainder** (`remainder="recursive"`), so every bit is scored exactly once,
unless a hypothesis states otherwise.

**Block code parts.** `description_lengths.block_code_parts`: dictionary (Σ CTM over
distinct blocks), counts (Σ log2 multiplicity), arrangement (log2 m!/∏n!), and
`decodable_bits`, the length of an actual prefix code (round-trip tested).

**Our two measures, kept separate and never merged.**
- **Certified code** (`description_lengths.certified_eca_code`): ⌈D_schema(rule)⌉ + γ(w) +
  literal seed + γ(steps). Defined where the generator is an ECA. Round-trip tested.
- **HID-v1 archive bits** (`hierarchy.infer(bits).archive_bits`, configuration `FULL`,
  sha recorded in the results): a complete decodable archive; defined on every string,
  with the literal archive as fallback.

**Emulators of BDM** (H5): E0 block-entropy foil Σ_w n_w log2(m/n_w) on the same
partition; E1 dictionary count at a flat price, Σ_distinct len(w) + Σ log2 n_w; E2 the same
with each word priced at the mean CTM of all words of its length; E3a zlib and E3b lzma
archive bits (`hierarchy.baselines.encode_baseline`); E4 HID-v1 archive bits.

**ECA.** `ca_deconvolution.evolve_eca` (periodic boundary); two-rule rings by
`ca_deconvolution.heterogeneous_eca_network` and `causalbool.evolve_network`; our
reconstruction by `ca_deconvolution.deconvolve_ca` (strict, `max_radius=1`).

**Seeds.** Master seed 20261004. Every random draw uses `random.Random(s)` with
`s = int(sha256(f"20261004|{name}|{i1}|{i2}|...").hexdigest()[:16], 16)`, where `name`
identifies the hypothesis and family. numpy draws use `numpy.random.default_rng(s)`.

## 2. String families (H5; also D-demonstrations)

Each family is a function of the length n and a seeded generator.

| id | family | definition |
|---|---|---|
| F1 | eca_row | rule uniform 0–255; random seed of width n; the row after 32 steps |
| F2 | eca_spacetime | h = largest divisor of n with h² ≤ n; w = n/h; rule uniform; random seed of width w; the h-row diagram flattened row by row |
| F3 | periodic | period p uniform in 1..min(24, n); random unit; tiled and cut to n |
| F4 | biased_coin | q uniform in [0.02, 0.5]; i.i.d. bits with P(1) = q |
| F5 | counter_or_shuffle | word width k uniform in 2..8; start uniform; consecutive k-bit numbers mod 2^k; with probability ½ the words are shuffled; cut to n |
| F6 | bn_repertoire | random Boolean networks, N uniform in 3..6 nodes, in-degree uniform in 1..min(3, N), inputs sampled without replacement, gate uniform over {AND, OR, XOR, NAND, NOR, XNOR, MAJORITY}; repertoire rows flattened; further independent networks appended until length n; cut to n |
| F7 | two_word | word length b′ uniform in 2..12; words 0^b′ and 1^b′; with probability ½ alternating, otherwise each word chosen by a fair coin; cut to n |

## 3. Hypotheses and decision rules

Every statistic is printed with its denominator. A check that runs over zero cases fails.

### T1 — permutation invariance (theorem, with a guard)
Aligned BDM depends only on the multiset of blocks. **Test:** 1,000 random block
permutations for each of 7 families × lengths {96, 384} × blocks {4, 8, 12} (lengths and
blocks chosen so that n is a multiple of b). **Supported iff** every permuted score
equals the original within 1e-9 (floating-point summation order), 0 failures.

### T2 — logarithmic bound (theorem)
BDM_b(x) ≤ C_b + 2^b·log2 m for m complete blocks, C_b = Σ CTM over all b-bit words.
**Test:** fair coins, b ∈ {4, 8, 12}, m ∈ {1, 10, 100, 1,000, 10,000}, 5 seeds.
**Supported iff** 0 violations.

### H1 — what BDM omits, measured
On fair coins, block 12, N ∈ {1,200; 12,000; 120,000; 1,200,000}, 20 seeds each.
**Supported iff all three hold:** (a) the ratio of the largest to the smallest mean BDM/N
across the four lengths exceeds 5; (b) mean BDM/N at N = 1,200,000 is below 0.2;
(c) `decodable_bits`/N is at least 0.95 at every length and seed (a decodable code cannot
compress fair coins), and its mean at N = 1,200,000 lies in [1.0, 1.2].

### H2 — the fill ratio decides when a disruption is visible
Strings of length n ∈ {64, 128, 256, 512, 1,024, 2,048, 4,096}; blocks b ∈ {2, 3, 4, 6, 8,
10, 12}: 49 cells. **Seam string:** left half periodic with period p uniform in {2, 3, 5}
and a random unit, right half a fair coin. 5 seam strings per cell. **Null:** 50 fair-coin
strings of the same length per cell. **Signature:** 128 positions per half (all if the half
is shorter), seeded; I(i) = BDM(x) − BDM(x with bit i flipped). **AUC** = P(|I| at a
right-half position > |I| at a left-half position), Mann–Whitney. A cell is **visible**
iff the median seam AUC over its 5 strings lies outside the 5–95 % range of its 50 null
AUCs. **Fill ratio** f = (n/2)/b / 2^b. **Supported iff** a logistic regression of
visible on log2 f (scikit-learn, `C=1000`, lbfgs), evaluated leave-one-cell-out, gives
predicted probabilities whose ROC AUC against the observed outcomes is ≥ 0.9. If every
cell has the same outcome, H2 is reported **not testable**, which is not support.
Secondary, descriptive: the same with log2 b alone and log2 n alone as predictors.

### H3 — single-cell perturbation depends on the grid
All 256 ECA rules × 5 seeds; width 64, 64 rows (`evolve_eca(rule, seed, 64)`). Grid
phases: the space axis rolled by 0, 1, 2, 3 columns — an exact symmetry of a periodic
ECA. (Rolling the time axis is not a symmetry and is not used.) 100 cells sampled per
diagram; Δ = BDM_2d(S) − BDM_2d(S with the cell flipped), in each phase. **Sign
instability** of a diagram = share of its 100 cells whose sign of Δ (|Δ| < 1e-9 counts as
0) is not the same in all four phases; per rule, the mean over 5 seeds. **Supported iff**
the 95 % bootstrap CI (1,000 resamples over rules) of the mean sign instability lies
entirely above 0.10. Secondary: Spearman between per-rule instability and a randomness
proxy (lzma archive bits of the flattened diagram / its length), with a bootstrap CI.

### H4 — group-level readings survive the grid; single-cell readings do not
Same data as H3. The 100 cells are split, in sampling order, into 4 groups of 25. **Group
agreement** = share of groups whose sign of mean Δ is identical in all four phases.
**Single-cell rank agreement** = median over phases 1–3 of Spearman(Δ in phase 0, Δ in
phase k) (diagrams with a constant Δ vector are excluded and counted). **Supported iff**
the median over rules of group agreement ≥ 0.95 **and** the median over rules of
single-cell rank agreement < 0.5.

### H5 — can simpler algorithms emulate BDM? (the challenged claim)
Regimes: n ∈ {8, 12, 24, 48, 96, 384, 1,536, 6,144} × b ∈ {4, 8, 12}, with n ≥ b (23
regimes). 300 strings per family and length (2,100 per length, the same strings for every
b). Target: BDM_b, aligned, recursive remainder. Emulators as in §1.
- **ρ:** Spearman between emulator and BDM over the 2,100 strings, with a 1,000-resample
  bootstrap 95 % CI. An emulator constant over a regime gets ρ = 0 ("constant").
- **D1 pairwise order:** 2,000 seeded pairs of distinct strings; agreement = share of pairs
  where the emulator orders the pair as BDM does; pairs tied under BDM (|Δ| < 1e-9) are
  excluded and counted; a tie under the emulator alone is a disagreement.
- **D2 perturbation sign:** 300 seeded strings per length, one seeded bit flip each
  (the same flips for every b); agreement = share where sign(ΔE) = sign(ΔBDM), zero
  counted as a sign.
- **Decision agreement** = min(D1, D2).
**Rule:** an emulator **emulates BDM in a regime** iff the lower CI bound of ρ ≥ 0.95
**and** decision agreement ≥ 0.95. The result is a regime map per emulator; there is no
single global verdict. Written prediction, made before the run: E1 and E2 fail wherever
n ≤ b (one block, so they cannot vary with content while BDM can); where they start to
hold, if anywhere, is the finding. Secondary: the same statistics per family.

### H6 — our certified code against BDM on known generators (descriptive)
256 rules × steps {16, 32, 64, 128} × 5 seeds, width 64. Reported for every diagram:
BDM_2d, certified bits, HID-v1 archive bits of the flattened diagram, literal bits
(64 × steps). Reported per steps: the share of rules with BDM > certified, the median
ratio, and per rule the sign of the slope of (BDM − certified) against steps. No pass/fail.

### H7 — when do the two methods agree? (descriptive, one baseline check)
Two-rule rings of width 64, 64 rows; cells left of the boundary run rule A, the rest rule
B; random seed. **Ours:** `deconvolve_ca` on the diagram; each column is labelled by its
recovered support offsets and reduced table; the boundary estimate k̂ is the split
maximising the number of columns that match the modal label on their side. **BDM:** for
each column, mean |Δ BDM_2d| over 16 seeded flipped cells in that column; k̂ is the CUSUM
change point argmax_k √(k(64−k)/64)·|mean left − mean right|. Splits k run over 1..63
for both methods; ties are broken by the median of the tied splits (rounded down).
**Success** = |k̂ − true| ≤ 2.
Rule sets fixed now: SIMPLE = {0, 4, 8, 32, 40, 128, 136, 160, 200, 204, 232, 255};
COMPLEX = {30, 45, 54, 60, 90, 105, 106, 110, 150}.

| arm | what changes from A0 | 30 diagrams each |
|---|---|---|
| A0 | A from SIMPLE, B from COMPLEX (sides randomised), noiseless, boundary at 32, 16 flips per column | baseline |
| A1 | 1 % of cells flipped after evolution | noise |
| A2 | boundary at column 30 (not a multiple of the 4×4 grid) | misalignment |
| A3 | A and B both from COMPLEX, distinct | similar complexity |
| A4 | 1 flip per column instead of 16 | single-cell reading |

**Baseline check:** both methods succeed on ≥ 90 % of A0 diagrams; otherwise H7 is
reported as having no valid baseline. Every other arm is reported as success rates with
Wilson 95 % intervals. Condition "the regularity is local" is not varied: every ECA is
local, so this protocol cannot test it, and says so.

## 4. Demonstrations (deterministic; not hypotheses)

- **DM1** two-word order: m ∈ {100, 1,000, 10,000}, b′ = 12; alternating versus a seeded
  random order with equal counts; BDM_12, arrangement bits, decodable bits.
- **DM2** all 4,096 twelve-bit words in counting order versus a seeded shuffle;
  BDM_12, decodable bits, literal length, log2 4096!.
- **DM3** period × block: periods 2..16 × blocks 2..12, length 2,520 (divisible by
  2..10 and 12); BDM of the periodic string divided by the mean BDM of 10 seeded fair-coin
  strings of the same length.
- **DM4** the window walk of `1111100000` at word 5 with steps 5, 2 and 1.

## 5. Outputs

`index-deconvolution/results/bdm_anatomy_v1/<run-id>/`: one JSON per hypothesis and
demonstration, `run.json` (versions, freeze hashes, timings, HID config sha), `run.log`,
`MANIFEST.sha256`. The notebook reads these files and re-computes a pinned sample of each
table live; any disagreement stops it.

## 6. What the outcomes would mean

- T1/T2 failing would mean a defect in the owner or in pybdm, not a finding.
- H1 supported: BDM is not a code length, and its per-bit value is a function of length
  on data with no structure at all. Not supported: the omitted term is not the explanation.
- H2 supported: the fill ratio, a property of the input length and block, not of the
  object, predicts when BDM can locate a disruption.
- H3/H4 supported: single-element causal attributions by BDM require averaging over grid
  positions; group-level results of the published applications are not threatened by this.
- H5: wherever an emulator emulates BDM, a published BDM ranking in that regime does not
  require CTM; wherever none does, CTM is doing work no simpler method reproduces. Both
  outcomes are reported with equal weight.
- H6/H7 are descriptive and support no general claim beyond the objects tested.

## Amendments

(none)

### Amendment 1 — 2026-10-04 (before any hypothesis result was produced)

Run `a1` stopped inside H1, raised by the owner's internal consistency check in
`bdm_1d_trace`: the running sum of the trace and pybdm's own total differed by 3.1e-7 bits
on a total of 151,891 bits (relative 2e-12) for a 1,200,000-bit string, against an
ABSOLUTE tolerance of 1e-9. This is floating-point summation order over 100,000 terms,
not a defect. The checks in `bdm_1d_trace` and `block_code_parts` now use a RELATIVE
tolerance, 1e-9 × max(1, |score|). No returned value changes; the full Python suite passes
unchanged. The one number the error message displayed is the BDM of one H1 string; no
other hypothesis output had been produced. `a1` wrote DM, T1 and T2 only; those files are
kept as they are and are not used. The protocol is re-frozen
(`freeze.json`; the superseded freeze is kept as `freeze_v1.0_a1.json`), and the
confirmatory run is `a2`. The T1 criterion "within 1e-9" is unchanged (it compares scores
of strings of at most 384 bits).

### Amendment 2 — 2026-10-04 (after run a2; affects demonstration DM3 only)

While checking notebook 19 against run `a2`, every DM3 ratio was exactly 1.000. Cause: the
producer drew the DM3 periodic unit and each DM3 control string with a NEW seeded generator
for every character (`"".join(rng(...).choice("01") for _ in ...)`), so each was a constant
string. The two lines now create one generator per string. No hypothesis (T1, T2, H1–H7)
and no other demonstration uses that construction (checked by search). The protocol is
re-frozen (the superseded freeze is kept as `freeze_v1.1_a2.json`), the complete run is
repeated as `a3`, and notebook 19 reads `a3` and asserts that every hypothesis output of
`a3` equals `a2`'s byte for byte, so the only change is DM3.
