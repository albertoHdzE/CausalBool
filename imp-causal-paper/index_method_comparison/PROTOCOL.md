# PRE-REGISTRATION (DRAFT — AWAITING AUTHOR SIGN-OFF, DECISION D-7)

**Status: FROZEN DRAFT.** Per AUDIT_FIXING_PLAN_01 v1.2 decision D-7, this
pre-registration requires the author's explicit approval BEFORE the comparison
executes. Nothing in `results/` has been produced by this protocol; no run has
happened. On approval, the approval is recorded (commit trail + Appendix D)
dated strictly before the earliest results commit (AC-2.4e).

## 1. Purpose and scope

The imp-causal-paper replication compared the Zenil calculus against the paper's
claims but contains **no comparison against this programme's own index method**
(the stated gap that motivates T2.4). This protocol pre-registers an
index-method capability comparison over the SAME networks the Zenil-calculus
comparisons used, mirroring the capability-table format of
`imp-causalNet-paper/COMPARISON.md` (rows scored: **ours / both / theirs /
neither**) and the pre-registration house style of `imp-prices` (design fixed
and committed before the first number is seen).

## 2. Evidence policy — recommendation for D-5

Recommendation **(i)**: track JSON summaries (≤ a few MB each) under git in this
directory's `results/`; raw trajectories stay gitignored. A `MANIFEST.sha256`
hash manifest of every tracked artifact is committed with them and verified by
`scripts/verify_manifest.py`. (Option (ii), release artifacts + manifest, stays
available if summaries grow.)

## 3. Networks (fixed at registration; no post-hoc substitution)

| arm | source artifacts (committed) | notes |
|---|---|---|
| CA set | `results/ca/original.csv`, `data/processed/ca/*`; the 10 ECA rules of the replication | exact global-map regime |
| Th17 | `data/processed/th17/` as committed at registration time | Yosef et al. 2013 lineage networks per ledger §A |
| E. coli subset | `data/processed/ecoli/ecoli_confC_node_signature.csv`, `ecoli_tf_gene_confC.txt` | **subset rule below** |

**Subset rule (declared in advance):** any network with more than 2⁴ = 16 nodes
cannot be exhaustively deconvolved (V4 stamp: n ≤ 16 cap; grieco_mapk n=54,
remy n=35 precedent). The E. coli subset is therefore the top-K most-connected
nodes subnetwork induced by `ecoli_tf_gene_confC.txt` with K fixed so that the
induced network has n ≤ 16; K is recorded in the results manifest before any
deconvolution output is computed. If a listed dataset directory is empty or
unparseable at execution time, the arm is recorded **excluded-with-reason** in
the capability table — never silently dropped.

## 4. Method under test (ours)

The root project's exact deconvolution engine
(`index-deconvolution/src/{causalbool,deconvolution}.py`) via the two-copies
rule (any edit mirrors into `imp-prices/vendor/`). Inputs are repertoires
computed exhaustively from the same parsed Boolean rules used by the
replication (`imp-causal-paper/parsers` / `bnet` path). No node ordering,
sign-agreement scoring, or other researcher degree of freedom enters "ours":
the engine either reproduces the generating `(C, D)` elementwise or it does not.

## 5. Interpretation rules — fixed BEFORE the run

1. **Exact recovery (per network):** recovered connectivity C' equals C
   elementwise AND recovered gates D' equal D gate-for-gate on the induced
   node set. Partial matches are reported as partial, never rounded up.
2. **Capability row scoring:** a row scores *ours* only if criterion 1 holds
   for every network in the arm AND the Zenil-calculus side fails or cannot
   express the task; *theirs*/*both*/*neither* follow COMPARISON.md's semantics.
3. **Success criteria (pre-declared):**
   - CA arm: 10/10 rules exact global-map recovery expected from prior evidence;
     any miss is reported as a finding, not tuned away.
   - Th17/E. coli arms: report exact-recovery fraction over networks; no
     minimum was pre-registered — the table reports what is true.
4. **No outcome-dependent changes:** thresholds, subsets, orderings, or metrics
   may not be altered after the first run. Failures are findings.
5. **Seeds:** every stochastic step pins seeds (recorded in the manifest);
   determinism asserted by double-run byte-identity where feasible.
6. **Reporting:** symmetric-difference reporting for any equality claim (U8):
   which rows/gates differ, never counts alone.

## 6. Planned deliverables on approval

- `index_method_comparison/run_comparison.py` (committed before execution)
- `results/index_method_comparison/capability_table.md` + JSON twin
- `MANIFEST.sha256`
- One paragraph adjacent to every sign-agreement percentage in the replication
  docs recording the node-ordering researcher degree of freedom
  (REPRODUCTION_LEDGER :1045–1067) — T2.4 step 3, executed together.
