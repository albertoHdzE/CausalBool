# AUDIT_FIXING_PLAN_01

**Version:** 1.3 — 2026-08-24 (v1.3: author-initiated at the gate session —
T5.5 post-fix cross-replication accuracy sweep added as MANDATORY; inventory at
`T5_5_SWEEP_INVENTORY.md`; first finding: imp-results.md E. coli row corrected).
**Version 1.2:** 2026-08-23 (v1.2: sibling-absence fallback defined for T1.4;
T2.4 pre-registration sign-off added as AUTHOR-DECISION D-7).
**Version 1.1:** 2026-08-23 (amended per second review pass: Wave-0 paper-number
snapshot added as T0.5; T0.1 split into parser/discovery phases; T1.1 decoupled from
D-2 and reordered behind T1.2; D-2 option (d) added; interim 0.51875 disclosure as T1.5;
AC-1.4d made mechanically checkable; AC-0.2a volatility exclusion defined; effort
estimates and restart-point scoping added — see Appendix D changelog).
**Version 1.0:** 2026-08-23.
**Status:** ACTIVE — cleaning/restarting point for the CausalBool programme.
**Origin:** adversarial audit of 2026-08-23 (four parallel deep audits covering: Mathematica
core + papers, `index-deconvolution` levels 0–18, the three `imp-*-paper` replications,
`imp-prices`, and the sibling settlement repo `series-deconvolution`). Every material claim
was independently re-verified by a second agent ("Claude feedback"); that feedback is
adjudicated in Part A and incorporated throughout.
**Governance:** on *definitions*, the GLOSSARY (materialised in-repo by T1.4; until then
`~/Documents/projects/series-deconvolution/GLOSSARY.md`) outranks every document including
this one. On *remediation execution*, this plan is the source of truth. Historical
documents, pre-registrations and results bitácoras are **never retro-edited**; corrections
enter as dated addenda. This plan obeys its own rule: amendments are appended, dated.

---

## HOW TO USE THIS DOCUMENT

Designed so execution-time uncertainty is minimal — target zero. Eight mechanisms bind
every task:

| # | Mechanism | Rule |
|---|---|---|
| U1 | Evidence re-statement | Before acting, re-read the cited file:line and confirm the quoted state. Files drift; citations age. If reality differs from citation, STOP, log a dated deviation in Appendix D, proceed only after adjudication. |
| U2 | Binary acceptance criteria | Every task ends in a PASS/FAIL check: a command plus an expected observable output. No "looks good". |
| U3 | Baseline-first ordering | Nothing is repaired until the measuring instrument itself works and a true baseline is recorded (Part C). Until T0.1/T0.2 land, `OK=87 FAIL=0` is **not a measurement** — treat repo health as unknown. |
| U4 | Decision registers | Judgement points are marked `AUTHOR-DECISION` with enumerated options, implications, and a recommendation. No executor invents policy silently. |
| U5 | Protected history | Bitácoras, pre-registrations, past results files are read-only. Fixes touch living docs (READMEs, FINDINGS headers, manuscripts) or append dated addenda. |
| U6 | Sibling permission gate | Edits outside CausalBool (`series-deconvolution`, vendored reference code) require author approval (standing rule). Flagged `NEEDS-SIBLING-EDIT`. |
| U7 | Suite delta proof | Mathematica/Python-engine changes are bracketed by suite runs with recorded deltas. After T0.1/T0.2, "delta is zero" is meaningful because failures propagate to exit codes. |
| U8 | Datasaurus reporting | Equality/exactness claims report the **symmetric difference and where it lives**, elementwise — never counts or percentages alone. Every number quoted anywhere traces to an executed run. |

Task cards carry **Context** (theoretical/empirical background being transferred),
**Evidence**, **Steps**, **Expected evaluation**, **Acceptance criteria**, **Risks**.
Task IDs are stable; future plans (`AUDIT_FIXING_PLAN_02…`) reference them.

---

# PART A — AUDIT PROVENANCE AND FEEDBACK ADJUDICATION

Epistemic foundation of the plan: what is trusted, what was corrected, what remains
unverified (and therefore gets verification tasks, Part F, before anything depends on it).

### A.1 Verified by direct re-read/re-execution (trusted as-is)

| Audit claim | Verdict | Anchor evidence |
|---|---|---|
| §2.1 call-before-definition in flagship script | CONFIRMED | `generate_paper_outputs.wl:84` calls `indexSetAnalytic`, defined at `:118`; absent from `CausalBoolCore.wl` |
| §2.1 unconditional success banner | CONFIRMED | `generate_paper_outputs.wl:423` prints `=== ALL VERIFICATIONS PASSED ===` unguarded; no `Exit` in file |
| §2.1 composed semantics of flagship example | CONFIRMED, **sharpened** | `corroboration_6node.wl:66`: `y6 = Mod[input[[1]]+input[[3]]+y5, 2]` ⇒ rule x₁⊕x₃⊕AND(x₂,x₄). See A.3 |
| §2.2 packaged API covers 5/12 gates | CONFIRMED | `Gates.m:39–50`; `True,{}` fall-through otherwise |
| §2.2 `indexSetAnalytic` unpackaged, triplicated | CONFIRMED | copies at `papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl:38`, `generate_paper_outputs.wl:118`, `tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m:71`; zero copies under `src/Packages/` |
| §2.3 packaged index path scores 0.51875; paper omits it | CONFIRMED | `results/tests/mixed001FormulaVsExhaustive/Summary.json` `accuracyIndex: 0.51875`; `method_paper.tex:1784–1799` lists only 0.66875 / 1.0 / 1.0 |
| §2.4 three-way MAJORITY tie divergence | CONFIRMED | `Gates.m:16` (`Count[1]>Count[0]` ⇒ ties→0); `CausalBoolCore.wl:27` (`>Floor[d/2]` ⇒ ties→0); `TSK-MIXED-001:21` (`>=Ceiling[d/2]` ⇒ ties→1). Even arity diverges |
| §2.5 FAIL recorded while rollup green | CONFIRMED, **citation corrected** | FAIL lives in `results/tests/mixed001FormulaVsExhaustive/Status.txt`; `Summary.json` holds metrics only, no verdict string. Rollup: `results/tests/runall/Status.txt` = `OK=87 FAIL=0` |
| §2.5 `--all` skips six existing sections | CONFIRMED | `run-tests.sh:25` hardcodes 7 dirs; `Arch`, `Compare`, `Exper`, `Sampling`, `Stoch`, `Tests` exist on disk and are skipped |
| §2.7 C18 prose vs hash-pinned JSON | CONFIRMED, **scoped** | Only the **hill-climb clause** is wrong (`FINDINGS.md:164` "5 winners, modal {WTI_CL} 55.0%" vs `b4_description_length.json` hill_climb: 6 winners, modal `WTI_Spot`, 0.375). Index-set (22 winners/26.7%) and CPT (4/51.7%) figures match. Both docs pin sha256 `160d8437a2eb20dc`, matching the archived file |
| §2.7 tautological assertion | CONFIRMED | `imp-prices/tests/test_clock.py:30`: `assert real not in (min(surr),) or True` |
| §2.8 dangling GLOSSARY authority | CONFIRMED | `src/causal/CausalBool.m:2183,2289` cite GLOSSARY.md; no such file anywhere in repo |
| §2.8 dead manuscript path in CLAUDE.md | CONFIRMED | points at `papers/method/manuscript/` — does not exist (actual: `manuscript_formal/`, `manuscript_computational/`) |
| Vendor byte-parity today, manual sync only | CONFIRMED **[executed]** | `imp-prices/vendor/causalbool.py`, `vendor/deconvolution.py` md5-identical to `index-deconvolution/src/`; no hash pin/CI anywhere |
| imp-prices suite health | CONFIRMED **[executed]** | 95 passed in its own venv (hmmlearn 0.3.3 pinned); 7 collection errors from parent venv caused by eager `hmmlearn` import in `src/imp_prices/__init__.py` |

### A.2 Corrections applied by this plan (audit overstated or miscited)

| # | Correction | Effect on plan |
|---|---|---|
| C-1 | "The test suite cannot fail" is imprecise: individual scripts **do** export honest FAIL verdicts; nothing **reads** them. A wiring failure, not an absence of checking — the fix is small, not a test rewrite. | T0.1 scoped to ~10-line runner surgery + dynamic discovery. Framing softened everywhere. |
| C-2 | §2.5 originally cited Summary.json for the FAIL verdict; it is `Status.txt`. | All citations herein: `Status.txt` = verdicts; `Summary.json` = metrics. |
| C-3 | §3.7 downgraded from "internal contradiction" to **notation collision**: text presents base {141,217} × 8 offsets; table presents anchor {141} × 16 offsets; **both unfold to the same 16 indices** (S2 likewise). Same object, two encodings sharing one label. Severity P1→P2. | Task T4.6 (rename one encoding), not a correctness repair. |
| C-4 | §2.4 paper prose is *ambiguous*, not wrong: `method_paper.tex:455` "at or above the strict majority threshold" is self-contradicting phrasing. The three-way **code** divergence is the real defect. | T1.3 keeps the paper fix minimal (disambiguate one sentence); concentrates on single-implementation repair. |
| C-5 | Reviewer sharpening adopted (A.3): the flagship defect is worse than a broken script — cardinality-based validation would pass while comparing different functions. | T1.1 acceptance upgraded to elementwise symmetric-difference under declared semantics. |

### A.3 The sharpened flagship finding (transfer forward verbatim)

The composed node-6 rule is **y₆ = x₁ ⊕ x₃ ⊕ AND(x₂, x₄)** (node 6 consumes node 5's
*output* within the synchronous pass; nodes 1–5 consume raw coordinates). The index-set
machinery computes the one-set for XOR over connected inputs I_c={1,3,5}, i.e.
**x₁ ⊕ x₃ ⊕ x₅**. Executed comparison [by the re-verifier]: both one-sets have cardinality
**32** (of 64 rows) and differ on exactly **32 of 64 rows — agreement at chance**.

Standing lesson for every future verification design in this programme: *identical
cardinality defeats any size-based or spot-check validation while the two functions share
nothing.* Equality claims require elementwise symmetric-difference checks (U8), never
cardinality, never spot rows.

### A.4 Not verified by the re-verifier — MUST be verified before dependent action

| Audit claim | Verify task | Gates |
|---|---|---|
| §2.6 replication-trio status-document contradictions | V1 | T2.4 |
| §2.9 sibling defect-log false entry + b21/b22 compression of history | V2 | T2.7 |
| RegulonDB 14.5 vs paper ~9.x substitution | V3 | T2.4 |
| §3.1 bio-arm round-trip-circularity framing | V4 | T4.2 |
| §3.6 description-length definitions nonidentity | V5 | T4.5 |

---

# PART B — GUIDING CONVENTIONS FOR ALL TASKS

1. **Branch discipline.** All work on branch `clean` (live; `main` stale by policy).
   One commit per task, message prefix `[AUDIT01/<task-id>]`. `main` reconciliation is
   T0.4, deliberately late.
2. **Suite bracketing.** Mathematica-touching tasks: full-suite run before first edit of
   the day and after the last; both counts recorded in the commit message (U7). Before
   T0.2 lands, record kernel-exit rollup **and** new Status-parsed counts side by side.
3. **Environments.** Root venv for root-level Python; `imp-prices` has its own venv —
   never mix. WolframKernel path fixed: `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`.
4. **No drive-by fixes.** Defects discovered mid-task get logged in Appendix D as
   candidates; fixed only via their own task. Exception: a defect blocking the current
   task's acceptance criterion halts the task and triggers a plan amendment.
5. **Author gates.** `AUTHOR-DECISION` items pause their thread until decided; everything
   else proceeds autonomously.
6. **Definition of done.** Steps executed ∧ acceptance criteria PASS ∧ listed doc updates
   committed ∧ Appendix D status line updated.

### B.9 THE RESTART POINT (scope honesty — added v1.1)

The actual cleaning/restarting unit is **Wave 0 + T1.2 → T1.1 → T1.3 + T1.4 + T1.5**
(roughly one week of work). That path retires every P0 in the exactness engine and ends
with: an instrument that can fail, two honest baselines (tests and paper numbers), a
packaged theorem engine, a self-falsifying flagship script, one tie convention, live
governance files, and a paper that cannot silently lie while repairs proceed.
**Everything from Wave 2 onward is a real backlog with owners and estimates — not a
continuation of the restart**, and this plan now says so explicitly instead of implying
it (effort table: Appendix B2; scheduling reality: Wave 2 alone spans seven tasks across
four repositories behind two author gates).

---

# PART C — WAVE 0: RE-ESTABLISH THE MEASURING INSTRUMENT

> Adopted from reviewer feedback: fix `run-tests.sh` **before touching anything else**,
> because until then no subsequent repair can be shown to have worked.

## T0.1a — Make the MUnit runner able to fail: parser wiring ONLY

**Priority:** P0 · Wave: 0 · Depends on: none · Blocks: everything.
**Effort:** S (≤2 h). **Scope guard (v1.1):** this task does ONE thing — verdict parsing
and exit-code propagation over the **seven known sections**. Section discovery is
T0.1b, deliberately separate: if a newly discovered section fails, attribution requires
that the parser landed clean on known ground first (the plan's own U3 applied to itself).

**Context.** MUnit-style tests export a human-readable verdict in
`results/tests/<name>/Status.txt` and metrics in `Summary.json`. The runner judges
success only by kernel exit code (`run-tests.sh:55–62`), so a script may record FAIL,
exit 0, and be counted OK. Today's consequence: rollup `OK=87 FAIL=0` while a genuine
FAIL sits in `mixed001FormulaVsExhaustive/Status.txt`. This is a *wiring* defect — the
checking exists; nothing consumes it.

**Steps.**
1. Inventory verdict vocabulary across existing `results/tests/*/Status.txt`; catalogue
   exact tokens (expect `OK`, `PASS`, `FAIL`; check for others). Parser grammar comes
   from this inventory — never guessed.
2. Edit `run-tests.sh`: after each invocation read `Status.txt` — `{OK,PASS}` → pass;
   `FAIL` → fail; anything else → fail as `UNPARSEABLE STATUS`; missing file → fail as
   `NO STATUS EXPORTED`. Exit non-zero iff any failure. Keep per-section rollups; append
   final line `TRUE TOTAL: ok=<n> fail=<m> unparsed=<k>`.
3. Prove wiring both ways on scratch copies: positive control (planted FAIL → non-zero
   exit naming it), negative control (untouched seven sections behave per current state).

**Acceptance criteria.**
- AC-0.1a Planted-FAIL control: runner exits non-zero and names the failing test (then reverted).
- AC-0.1b Over the seven known sections only: exits non-zero iff ≥1 parsed verdict ≠ OK/PASS; TRUE TOTAL matches a manual recount of their Status.txt files.
- AC-0.1c Seven-section wall-clock ≤ 60 min.

---

## T0.1b — Enable section discovery + second baseline

**Priority:** P0 · Wave: 0 · Depends on: T0.1a, T0.2 (first baseline exists).
**Effort:** M (half-day).

**Steps.**
1. Replace the hardcoded list (`run-tests.sh:25`) with dynamic discovery (subdirectories
   containing `.m` files); keep `--section <name>` semantics; per-section timeout
   default 900 s (raises logged); optional per-section `SKIP_REASON.txt` — reported,
   never silent.
2. Run every newly discovered section once manually before enabling in `--all`.
3. Extend BASELINE.md with a dated second block covering all sections; attribute any new
   red entries to their section explicitly.

**Acceptance criteria.**
- AC-0.1d Executed-section count = discovered-section count; six previously skipped sections now run or carry explicit SKIP_REASON entries.
- AC-0.1e Every newly-run failing test has a BASELINE entry naming its section and one-line cause (attribution guaranteed by two-phase baselining).
- AC-0.1f Full `--all` wall-clock ≤ 90 min at defaults.

## T0.2 — True baseline ledger

**Priority:** P0 · Wave: 0 · Depends on: T0.1a. **Effort:** M.
**Two-phase (v1.1):** baseline v1 covers the seven known sections immediately after
T0.1a; baseline v2 (all sections) lands with T0.1b. Both blocks live in BASELINE.md,
dated, so red-attribution stays clean.

**Context.** With the instrument repaired, freeze an honest health snapshot as the
reference for every later delta claim (U7). Known red member:
`mixed001FormulaVsExhaustive` (Summary.json metrics: accuracy 0.66875, accuracyIndex
0.51875, accuracyAnalytic 1.0; Status.txt: FAIL — the 0.51875 path is a suspected
ordering-bridge mismatch, root-caused properly in T4.1).

**Steps.**
1. Run every in-scope section with the repaired runner.
2. Commit `tests/MUnit/BASELINE.md`: per section — found/passed/failed (names + one-line
   cause where obvious)/unparsed/skipped; date; runner commit hash; raw rollup embedded
   verbatim.
3. Document delta policy in the same file: future runs diff vs BASELINE; **new** failures
   block merges; pre-existing failures retire only via explicit task IDs of this plan.

**Expected evaluation.** First honest snapshot in repository history. Red set beyond
mixed001 unknown until run — precisely the uncertainty Wave 0 eliminates.

**Acceptance criteria.**
- AC-0.2a Second run reproduces the embedded rollup **after excluding volatile lines**: comparison ignores timestamp/date lines (e.g. `mixed001FormulaVsExhaustive/Status.txt` embeds a date line after the verdict) and any duration fields. The exclusion list is stated in BASELINE.md itself. Stochastic sections pin seeds or are flagged NONDETERMINISTIC with stated tolerance policy.
- AC-0.2b Every baseline-red test carries an owning task ID or an Appendix D entry marked UNOWNED.
- AC-0.2c The string `OK=87 FAIL=0` appears only as labelled historical context ("kernel-exit rollup, superseded").

## T0.3 — Working-tree checkpoint (AUTHOR-DECISION D-1)

**Priority:** P0 · Wave: 0 · Depends on: none.

**Context.** Significant uncommitted modifications sit adjacent to canonical engines
(`index-deconvolution/src/ca_deconvolution.py`, `src/finance.py`, notebooks, scalability
outputs, `papers/method/manuscript_formal/method_paper.pdf`,
`tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m`) plus untracked imp-pathinfo docs.
Repairs must start from an authored checkpoint so plan diffs are separable from WIP.
Standing rule: the tree is the author's work; nothing is staged unilaterally.

**Steps.** Author reviews `git status`; commits a WIP checkpoint
(`[checkpoint] pre-AUDIT01 working state`) or directs selective staging; Appendix D
records choice + HEAD hash. Defer `main` merge to T0.4.

**Acceptance criteria.**
- AC-0.3a `git status --short` (excluding `.DS_Store` noise) empty at the recorded HEAD.

## T0.4 — Branch reconciliation and tag

**Priority:** P2 · Wave: gate at start of Wave 3 · Depends on: T0.2, T0.3.

**Steps.** Once Waves 1–2 land: fast-forward/merge `clean` → `main`, tag
`audit01-baseline`, record hashes in Appendix D. Until then `main` stays stale by policy;
CLAUDE.md (T1.4 edit) must say so explicitly so agents stop trusting it.

**Acceptance criteria.**
- AC-0.4a `git rev-parse main clean` identical or annotated merge exists; tag `audit01-baseline` created; hashes recorded.

---

## T0.5 — Paper-number baseline snapshot (added v1.1)

**Priority:** P0 · Wave: 0 · Depends on: T0.3. **Effort:** M (half-day).

**Context.** U3 says nothing is repaired until the instrument measures — but v1.0 applied
that only to the test runner, while T1.2 (packaging), T1.3 (MAJORITY) and T4.1 (ordering)
can each move numbers printed in `method_paper.tex`, and the instrument that would catch
it (T5.1 regenerate-and-diff) sat in Wave 4 — *the plan's strongest idea applied one wave
too late*. This task snapshots every currently-published number so Waves 1–3 diff against
it; otherwise we finish the repairs unable to say whether the paper still states true
things.

**Steps.**
1. Enumerate numeric claims in both manuscripts (`manuscript_formal/method_paper.tex`,
   `manuscript_computational/comp_paper.tex`): every table row, every inline statistic
   (accuracies 0.66875/0.51875/1.0, D_formula=135.66 bits, J₆ set constants,
   attractor counts |Im F|=206 / basins 488/320/204/12, corroboration booleans,
   benchmark tables :1070–1234, four-paths table :1784–1799).
2. Write `papers/method/artifact_baseline/paper_numbers.json`: entries
   `{id, tex_file, tex_line, value_raw, context_snippet, producing_script_or_null}`.
   Entries with a known producer get its path; producers unknown are marked
   `producer: null` — that null itself is inventory for T5.1.
3. Add `tools/diff_paper_numbers.py`: re-extracts from current .tex and diffs against
   the committed snapshot; exits non-zero listing changed IDs.
4. Commit BEFORE any Wave-1 edit lands.

**Acceptance criteria.**
- AC-0.5a Snapshot committed; covers every table environment in both manuscripts (count stated in the file header; spot-check three IDs by hand).
- AC-5-style control: planting a digit change in a scratch .tex copy makes `diff_paper_numbers.py` exit non-zero naming the ID (then reverted).
- AC-0.5b Snapshot regenerates deterministically from the extraction script (second run → identical JSON).
- AC-0.5c Every Wave-1 task card below lists this diff among its bracket checks where numbers could move (T1.2, T1.3, T1.5 explicitly do).

---

# PART D — WAVE 1: CORE REPAIRS (P0 defects in the exactness engine)

> **Execution order within this wave (v1.1):** `T1.2 → T1.1 → T1.3 → T1.4 → T1.5`.
> v1.0 had T1.1 first on the critical path but blocked on open research decision D-2 —
> a repair gated on new theory. Inverted: T1.2 needs no decision and unblocks everything;
> T1.1 then consumes the packaged API. The composed-semantics *research* track (former
> option b) moves to Part I item 7.

## T1.1 — Flagship verification script: fix mechanics, gate the banner, disambiguate semantics

**Priority:** P0 · Wave: 1 · Depends on: **T1.2** (packaged engine), T0.2. **Effort:** M once T1.2 lands.

**Context (three layers — transfer all three).**
1. *Mechanical.* `generate_paper_outputs.wl:84` calls `indexSetAnalytic` before its
   definition at `:118`; loaded library `CausalBoolCore.wl` never defines it. Wolfram
   keeps the call symbolic; `Select` at `:94` propagates symbolism; `verifiedXOR` at
   `:108` compares symbol vs 32-element list ⇒ permanently False, silently; `:423`
   prints the success banner unconditionally.
2. *Semantic.* See A.3: composed rule y₆=x₁⊕x₃⊕AND(x₂,x₄) vs computed x₁⊕x₃⊕x₅ — equal
   cardinality 32, symmetric difference 32 rows (chance). Any cardinality/spot-check
   "verification" passes while comparing different functions.
3. *Institutional.* Companion scripts already gate correctly
   (`corroboration_6node.wl:83–86`, `ordering_invariance_6node.wl:47–50`,
   `mixed_interaction_10node.wl:253–256`); this script alone prints a banner.

**AUTHOR-DECISION (D-2): flagship network semantics.** *(v1.1: option list completed
and recommendation changed; former option (b) — layered-update evaluator as new theory —
moved to Part I item 7, off the repair critical path. Note that y₆ = x₁⊕x₃⊕AND(x₂,x₄)
is a legitimate synchronous map — a function of the raw row; it is simply not a 3-input
XOR over I_c={1,3,5}.)*
- (a) Recompute the worked example under local semantics (J₆ for XOR on I_c={1,3,5});
  regenerate paper Table 3 via T0.5/T1.5 pipeline. Cheapest; loses the pedagogical
  composed example.
- (b) *MOVED TO BACKLOG* (Part I item 7): keep the composed example and make composition
  first-class via a layered-update evaluator in the package + theorem-scope statement.
  Real research contribution; does not belong in front of every P0 repair.
- (c) Drop node 6 from the flagship network (5-node example). Cheapest of all; weakens
  the showcase.
- (d) **(Recommended, v1.1)** Keep the network unchanged; declare node 6 an
  **in-degree-4 composite gate outside the twelve-family catalogue**, and obtain its
  one-set by **composing index sets** (node-level sets for AND(x₂,x₄) then XOR over
  {x₁, x₃, node-5-output}) rather than by the XOR closed form over raw coordinates.
  Keeps the pedagogical example, requires no layered evaluator, verifies against an
  exhaustive baseline of the declared composed map elementwise, and — decisively —
  makes the theory's scope boundary visible in the showcase itself, which is arguably
  the more honest demonstration of what the twelve-family proposition does and does not
  cover.

**Steps.**
1. Execute D-2 decision record (options considered, choice, implications).
2. Repair call ordering: definition before use — now satisfied by consuming the T1.2
   packaged engine instead of the local script copy.
3. Convert banner to a real gate mirroring companion style:
   `If[And @@ {allVerifications}, Print["=== ALL VERIFICATIONS PASSED ==="], Print["=== VERIFICATION FAILED: ", names, " ==="]; Exit[1]]`.
4. Upgrade every verification in the script to elementwise form: compare sorted index
   lists with `SameQ` after canonicalisation, report `Complement[a,b] ∪ Complement[b,a]`
   size and location on mismatch (U8). No cardinality-only checks anywhere.
5. Under chosen semantics, assert the script's J₆ against an exhaustively computed
   baseline of the **same declared function** — under (d): compose node-level one-sets,
   verify the composition equals the exhaustive set of y₆ = x₁⊕x₃⊕AND(x₂,x₄), report
   any symmetric difference — and print a one-line statement of which function was
   verified (composed map with its formula, or local XOR over I_c).
6. Re-run suite; record delta (expected: none outside this script's own artefacts); run
   `tools/diff_paper_numbers.py` if Table 3 constants moved under the chosen option.

**Expected evaluation.** Script becomes self-falsifying: any future regression in the
flagship path fails loudly with exit≠0 and prints the symmetric difference.

**Acceptance criteria.**
- AC-1.1a Deliberately breaking one verification in a scratch copy makes the script exit non-zero and print the differing element count + location; restored copy exits 0.
- AC-1.1b Output states the verified function's formula explicitly (no ambiguity possible about which semantics ran).
- AC-1.1c `grep -n "ALL VERIFICATIONS PASSED" generate_paper_outputs.wl` shows exactly one occurrence, inside an `If[...]` guard whose condition includes all verification booleans.
- AC-1.1d Suite delta recorded; unrelated sections unchanged vs BASELINE.

**Risks.** Under D-2(d), index-set composition for the composite node is itself a small
lemma — it must be verified empirically here (exhaustive, elementwise) even though the
general theory lands later in Part I item 7. If composition fails to reproduce the
exhaustive set, STOP: that falsifies the composition assumption at n=6 and becomes a
finding logged in Appendix D before any paper text moves.

## T1.2 — Package the closed-form engine; make Proposition "Gate-Family One-Sets" executable

**Priority:** P0 · Wave: 1 · **Executes FIRST in Wave 1** · Depends on: T0.2, T0.5 (snapshot exists to catch paper-number movement). **Effort:** L (1–2 days incl. tests).

**Context.** The paper's central proposition (:269–471) states closed-form one-sets for
twelve gate families; conclusion (:1925) claims truth-table equality across all twelve.
The packaged API implements five (`Gates.m:39–50`); the real engine (`indexSetAnalytic`)
exists only as three script copies. The theorem's implementation is folklore. This also
blocks honest per-gate testing: NIMPLIES and MAJORITY currently have **no dedicated MUnit
tests at all**, and Analysis/-section network tests exist only for NOT, IMPLIES, KOFN,
CANALISING.

**Steps.**
1. Port `indexSetAnalytic` into `src/Packages/Integration/Gates.m` as the implementation
   behind `IndexSet[gate, arity, params]` (replacing the `{}` fall-through), keeping the
   public signature stable. Preserve LSB weights w(i)=2^(i−1) as the internal convention;
   expose MSB transport exclusively via `Phi` (ordering unification lands later, T4.1 —
   do not attempt both in one task).
2. Delete the three script copies; replace with package loads. Grep confirms zero
   remaining private definitions (`grep -rn "indexSetAnalytic\\[" --include="*.wl" --include="*.m"` shows only the packaged definition and call sites).
3. New MUnit test `Gates/TSK-GATES-013-OneSetAllFamilies.m`: for each of the 12 families,
   at arities 2..6 where defined: build closed-form set via `IndexSet`, build exhaustive
   set from `TruthTable`, assert elementwise equality (sorted lists `SameQ`; on failure
   print symmetric difference). MAJORITY included **after** T1.3 fixes its convention.
4. Add missing per-gate Analysis tests: minimum one truth-table test each for NIMPLIES,
   MAJORITY (parity with existing gates' coverage pattern).
5. Update `README.md` Gate Catalogue section: IndexSet now covers all families.

**Expected evaluation.** Paper proposition ↔ packaged API correspondence becomes
machine-checked; the triple-duplication drift class is extinct.

**Acceptance criteria.**
- AC-1.2a For all 12 families × supported arities ≤6: closed-form vs exhaustive symmetric difference = ∅ [elementwise, executed].
- AC-1.2b `IndexSet["AND",3]` (and OR/XOR/NAND/NOR/XNOR/MAJORITY) returns non-empty correct sets — `{}` fall-through unreachable for supported gates.
- AC-1.2c Exactly one definition of `indexSetAnalytic` (or its renamed successor) exists under `src/Packages/`.
- AC-1.2d Suite: all previously-green tests remain green (delta zero beyond intended additions).
- AC-1.2e `tools/diff_paper_numbers.py` run before commit and after commit; any moved paper number is listed and explained in the commit message (bracket required by AC-0.5c).

**Risks.** CANALISING/KOFN parameter grids can explode combinatorially at arity 6 — bound
the parameter sweep in tests to the documented grid; keep runtime ≤ suite budget.

## T1.3 — MAJORITY tie convention: one implementation, one sentence

**Priority:** P0 · Wave: 1 · Depends on: T0.2 (and feeds T1.2 step 3). **Effort:** M (probe + alignment).

**Context.** Even-arity ties resolve differently in three places: package `Gates.m:16`
(strict `>` ⇒ ties→0), core library `CausalBoolCore.wl:27` (ties→0), MUnit harness
`TSK-MIXED-001:21` (`>=Ceiling[d/2]` ⇒ ties→1) — the last disagrees inside the very test
that exercises the benchmark's 4-input majority node 10. Paper `:455` is ambiguous prose
("at or above the strict majority threshold"). Note relationship: KOFN k=⌈d/2⌉ with ≥ is
ties→1; strict majority reading is ties→0. Both are legitimate conventions; ambiguity
itself is the defect.

**AUTHOR-DECISION (D-3): tie convention.** Options: (i) ties→0 everywhere ("majority"
strictly); (ii) ties→1 everywhere (threshold ⌈d/2⌉, matches KOFN special-case reading);
(iii) explicit `tiePolicy -> "strict"|"atOrAbove"` parameter defaulting to one of them.
Recommendation: **(iii)** with default **ties→0** (conservative, matches package today),
because it changes no historical behaviour while making the alternative expressible.

**Pre-decision empirical fact to establish (reduces D-3 to zero-risk):** does the mixed10
benchmark's majority node ever encounter a tied input row across its 1024 rows? Compute
once; if never, published numbers are invariant to the choice either way — record result
in the decision entry regardless.

**Steps.**
1. Run the tie-row probe; attach result to D-3.
2. Implement chosen convention single-source: `Gates.m` `myMajority` (+ optional
   `tiePolicy`), `CausalBoolCore.wl`, `indexSetAnalytic` threshold, `TSK-MIXED-001`
   `vectorPredict` — all delegating conceptually to one documented rule.
3. Disambiguate `method_paper.tex:455` to one sentence naming the convention.
4. Dedicated MUnit test `Analysis/MAJORITYTests.m` incl. even-arity tie cases asserting
   the convention.
5. Regenerate affected artefacts if (probe shows ties occur AND convention differs from
   what produced them); otherwise record invariance note. In either case run
   `tools/diff_paper_numbers.py` before/after (AC-0.5c bracket) so any benchmark-table
   movement in the manuscripts is caught at commit time.

**Acceptance criteria.**
- AC-1.3a All four sites return identical outputs on a fixed even-arity tie vector probe (e.g. d=4 inputs {1,1,0,0}) under the declared default.
- AC-1.3b New MUnit majority test green; suite delta as expected (zero, or exactly the regenerated artefacts listed).
- AC-1.3c Paper sentence names the convention unambiguously; grep for "at or above the strict majority threshold" returns the corrected sentence only.

## T1.4 — Materialise governance: GLOSSARY in-repo, CLAUDE.md repair, canonical manuscripts

**Priority:** P0 · Wave: 1 · Depends on: T0.3. **Effort:** M.

**Context.** The terminology settlement (2026-08-22, commits `cba2eec`,`4d9a959`) renamed
code identifiers but left: (i) citations pointing to a GLOSSARY.md that exists only in the
sibling repo (`CausalBool.m:2183,2289`); (ii) CLAUDE.md pointing at non-existent
`papers/method/manuscript/`; (iii) two live manuscripts (`manuscript_formal/method_paper.tex`,
2117 lines, theory; `manuscript_computational/comp_paper.tex`, distinct title/co-author,
own `indexSetAnalytic` copy :700–748) sharing the mixed-10 benchmark with no designated
roles — live divergence risk. Also stale technical-sense "pivot" survives in
`doc/newIntPaper/docProcess.tex` (:485,491,514,518,763,772,1103) and derivations
(`exam.tex:185,230–258`; `02_cb_and.tex:59,73,96`; `01_causalBool_inputs.tex:83,177`) —
files the settlement claimed jurisdiction over.

**AUTHOR-DECISION (D-4): manuscript roles.** Recommendation: declare both canonical with
distinct scopes — `manuscript_formal` = theory/method paper; `manuscript_computational` =
computational/validation paper; shared benchmark owned by code under
`papers/method/code/`, both papers regenerate tables from it (enforced later by T5.1).
Alternative: single merged manuscript. Decide now; CLAUDE.md records the outcome.

**Steps.**
1. Copy sibling `GLOSSARY.md` → `GOVERNANCE/GLOSSARY.md` with provenance header
   (source path, source commit hash, copy date, "synchronized copy; canonical at
   source"). Add a parity check script `tools/check_glossary_sync.sh` (hash comparison)
   runnable in CI/cron. Copying FROM the sibling needs no permission (U6 covers edits).
   **Sibling-absence fallback (v1.2):** if `../series-deconvolution/GLOSSARY.md` is
   absent AND `GOVERNANCE/GLOSSARY.md` does not already exist from a prior run — STOP,
   do not synthesise a glossary from memory or partial sources; log a dated BLOCKED entry
   in Appendix D naming the missing path and request the file from the author. If the
   in-repo copy already exists but the sibling is absent, `check_glossary_sync.sh`
   reports `SYNC-UNKNOWN: sibling absent` and exits 2 (distinct from drift=1 and
   clean=0) — never a silent pass; all three states are documented in the script header.
2. Repoint citations: `CausalBool.m:2183,2289` → `GOVERNANCE/GLOSSARY.md §…`;
   `index-deconvolution/src/deconvolution.py:44`, `level5/pivots.py:7`,
   `level10/oracle.py:14` likewise (they cite the sibling path — update to name both:
   in-repo synchronized copy authoritative locally, source-of-truth at sibling).
3. Rewrite CLAUDE.md: active-manuscript pointers per D-4; branch status note (`clean`
   live, `main` stale until T0.4); true-suite command unchanged but reference BASELINE.
4. Terminology completion pass (settlement §2 sources #1–#5 applied to files the
   settlement outranks): docProcess.tex + derivation files — replace technical-sense
   "pivot" with "decimal anchor"/"pivot coordinates" per GLOSSARY §3 naming rules.
   English-sense uses stay. Historical bitácoras stay untouched (U5).
5. Re-run full suite; delta must be zero (text-only changes except CausalBool.m comments).

**Acceptance criteria.**
- AC-1.4a `GOVERNANCE/GLOSSARY.md` exists with provenance header; `tools/check_glossary_sync.sh` exits 0 today and detects a planted mutation in scratch (both controls demonstrated); with the sibling path temporarily renamed, it exits 2 printing `SYNC-UNKNOWN: sibling absent` (third control, v1.2). If the sibling is permanently absent and no in-repo copy exists, the task is BLOCKED per step 1 — BLOCKED is a valid terminal state, recorded in Appendix D; silent synthesis is not.
- AC-1.4b Zero dangling references: `grep -rn "GLOSSARY.md" src/ papers/ doc/newIntPaper/ index-deconvolution/src index-deconvolution/level5 index-deconvolution/level10` — every hit resolves to `GOVERNANCE/GLOSSARY.md` or the documented dual-path form.
- AC-1.4c CLAUDE.md contains no reference to `papers/method/manuscript/`; contains branch-status and manuscript-role statements matching D-4.
- AC-1.4d Sense-aware check made mechanical (v1.1 — grep cannot see sense, so the curated-inventory pattern is used instead): (i) produce once `GOVERNANCE/pivot_sense_inventory.txt` listing every remaining "pivot" occurrence in living theory docs (docProcess.tex, derivations/, papers/method/*/{*.tex,*.wl}) with a per-line classification {technical→fix-now | guard-comment | english-sense}; regex pre-filter (`\bpivot` case-insensitive) generates candidates, classification is frozen at commit; (ii) acceptance = fresh candidate scan's line-set equals the inventory's line-set exactly (diff empty). Any unlisted hit fails; listed technical hits must be zero after this task's step 4.
- AC-1.4e Suite delta zero.

## T1.5 — Interim honesty patch: publish the 0.51875 row now (added v1.1)

**Priority:** P0 · Wave: 1 · Depends on: T0.5, D-2 not required. **Effort:** S (≤1 h).

**Context.** The 0.51875 row was routed to Waves 3–4 in v1.0, but it is a
publication-facing honesty issue *today*: F06 maps to T4.1/T5.1, yet if the formal paper
goes anywhere before Wave 4, tab:four-paths still omits the project's own framework's
failing path while claiming four computational paths. One sentence now de-risks the whole
publication path.

**Steps.**
1. In `method_paper.tex`, four-computational-paths table (:1784–1799): add the
   accuracyIndex row (0.51875) annotated "under investigation (ordering-bridge mismatch;
   remediation T4.1)" — or, if layout forbids a row, a footnote carrying the number and
   the same annotation.
2. Run `tools/diff_paper_numbers.py`: snapshot gains the new ID; diff passes.
3. Log in Appendix D that disclosure preceded root-cause (correct order: honesty first,
   repair second).

**Acceptance criteria.**
- AC-1.5a The number 0.51875 appears in method_paper.tex with the investigation annotation; grep-verified.
- AC-1.5b Snapshot diff tool exits 0 with the updated baseline committed.
- AC-1.5c No paper sentence claims exhaustive agreement of all four paths without qualification until T4.1 closes (grep for the :1925-area claim sentence to confirm it reads accurately or carries the pointer).

---

# PART E — WAVE 2: EVIDENTIARY-CHAIN RESTORATION (replications + finance)

> Verification-first (Part F, tasks V1–V5) gates actions depending on unverified audit
> claims. V-tasks are cheap; run them first within this wave.

## T2.0 — imp-prices hygiene bundle

**Priority:** P1 · Wave: 2 · Depends on: T0.3. **Effort:** M.

**Context.** Five small confirmed defects plus one environment coupling:
(a) `tests/test_clock.py:30` tautological assertion (`... or True`) in a package whose
brand is guards-with-teeth; (b) `src/imp_prices/__init__.py` eagerly imports
`.discretise` → `hmmlearn`, so even pivot/clock tests fail collection outside the HMM
venv — this manufactured a false "tests cannot run" defect report in the sibling log;
(c) vendor copies byte-identical today **[executed]** but synced by manual discipline
only — no hash pin, no CI (commit `4d9a959` shows the human re-copy process);
(d) README status block three versions stale ("Phase 1 in progress, 45 tests" vs actual
95 passing); (e) `results/b4_description_length.json` prequential block contains
duplicate rows (index-set WTI_CL ×2 at 134.9; cpt WTI_CL ×2 at 116.5).

**Steps.**
1. Replace the tautology with the bound assertion that test's docstring intends; state
   what it asserts and why.
2. Make `__init__.py` lazy: move `.discretise` import into the functions needing it;
   verify pivot/clock/index-set modules import cleanly under the ROOT venv.
3. Add `tests/test_vendor_parity.py`: hash-compare `vendor/causalbool.py`,
   `vendor/deconvolution.py` against `../index-deconvolution/src/` counterparts; skip
   with loud notice if sibling absent. Never silently pass on absence.
4. Rewrite README status block to executed reality.
5. Handle duplicate JSON rows by regeneration from the producing script if available;
   else append a dated `_curation_note` key documenting duplicates (never falsify history).

**Acceptance criteria.**
- AC-2.0a Root venv: pytest collects without hmmlearn; HMM-dependent tests skip with explicit reason.
- AC-2.0b Own-venv suite: 95 passed / 0 failed baseline preserved, +1 new parity test.
- AC-2.0c Parity test demonstrably fails on planted scratch mutation (then reverted).
- AC-2.0d README test count quoted from the AC-2.0b run.

## T2.1 — C18 reconciliation (prose vs pinned JSON)

**Priority:** P0 · Wave: 2 · Depends on: T0.3. **Effort:** M. Scope confirmed (A.1): only the
hill-climb clause is wrong.

**Context.** `FINDINGS.md:164` and bitácora 04 state hill-climb yields "5 distinct
winners over 120 resamples (modal {WTI_CL}, 55.0%)"; the archived JSON they sha256-pin
(`160d8437a2eb20dc`) records 6 winners, modal `WTI_Spot`, frequency 0.375 (WTI_CL
second, 0.3333). Index-set and CPT clauses match the JSON. A ledger whose entry rule is
"produced by code, re-runnable" misreporting its own pinned file is the gravest slip
class this programme defines.

**Steps.**
1. Re-execute hill-climb resampling from committed code (seed 42 + hash-seed sweep as
   declared). If reproduction gives 6/WTI_Spot/0.375 ⇒ prose was always wrong. If it
   gives 5/{WTI_CL}/0.55 ⇒ two JSON generations exist; provenance broke — escalate to
   Appendix D before touching text.
2. Correct `FINDINGS.md:164` in place with dated correction note quoting verified
   numbers; append dated addendum to imp-prices bitácora 04 (U5).
3. Ledger lint script: assert prose-quoted statistics of §C18 appear verbatim in the
   cited JSON.

**Acceptance criteria.**
- AC-2.1a Executed re-run recorded under `results/recheck_c18/` (command + output committed).
- AC-2.1b FINDINGS and bitácora-04 addendum carry identical corrected triple tracing to that run.
- AC-2.1c Lint exits 0 on corrected text; detects a planted scratch mismatch.

## T2.2 — Corrections-without-code: commit C29/C36 machinery; caveat pre-guard daily cells

**Priority:** P0 · Wave: 2 · Depends on: T0.3. **Effort:** M.

**Context.** The density-artefact correction numbers (C29: random 14×14 BDM
189.39±22.75 @17 edges vs 214.83±17.40 @23 edges; z=−3.35/−2.90; "+21.82 of +33.08 =
66%") and window distribution (C36: 6,478 windows; 1.26±1.12 pivots; "7 occurs in 2")
exist only in prose — no committed code computes them, violating the entry rule at the
exact moment the package corrected itself. Separately, Phase-2 daily cells ran hours
BEFORE the negative-price guard existed, on data containing −37.63 (2020-04-20):
surrogate counts 170/151/130 of requested 200 evidence nan-propagation; FINDINGS C26
quotes these numbers uncaveated.

**Steps.**
1. Implement + execute `experiments/c29_density_matched_null.py` (density-matched random
   binary matrices at edge counts 17/23; pybdm; z-scores) and
   `experiments/c36_window_distribution.py`; commit code + outputs to `results/`.
2. Verify regenerated numbers reproduce the prose (expected: match; arithmetic internally
   consistent at 65.96%≈66%). Divergence ⇒ Appendix D investigation first.
3. Append dated caveats to FINDINGS C26 and Phase-2 daily rows: computed pre-guard;
   surrogate shortfalls; superseded-by-guard status.

**Acceptance criteria.**
- AC-2.2a Both scripts execute deterministically (pinned seeds); outputs committed.
- AC-2.2b Regenerated values equal prose values (else deviation logged first).
- AC-2.2c Caveats present with dates; no unqualified pre-guard number remains in FINDINGS.

## T2.3 — imp-causalNet-paper: persist artifacts; correct three README claims

**Priority:** P1 · Wave: 2 · Depends on: T0.3.

**Context.** The strongest index-method comparison of the trio, but: (i) zero
machine-readable result artifacts — all evidence lives in one executed notebook (141
cells, 67 code, 0 errors) plus prose; CTM cross-check silently depends on ephemeral
`/tmp/cdn` clone; (ii) three README-vs-output mismatches confirmed by audit: tally "ours
6" at `README.md:265` vs `COMPARISON.md:41` "ours 7" (printed table counts 7); Cliff's
delta "−0.78" (`:67`) vs executed notebook output −0.770; "Exact — 99.8% attribution" on
"the Fig. 2 image" (`:74,:118–121`) conflates the synthetic-data number with the figure
number (notebook itself says 96.7% on-figure). Also `README.md:144` says 25 fidelity
tests; actual 47.

**Steps.**
1. Export notebook results to `results/*.json` (one file per experiment block); commit.
2. Vendor or pin the CTM dependency path; make the cross-check skip reason explicit and
   loud when absent.
3. Fix the four README numbers to match committed artifacts; add one line per fix noting
   source artifact filename.
4. Rename the same-named decoy module `src/imp_causalnet_paper/deconvolution.py` →
   `zenil_algorithms.py` (it transcribes Algorithms 1–2 of arXiv:1802.09904 — BDM edge
   information — unrelated to the root engine). Update imports; grep for plain
   `import deconvolution` after `load_root_modules()` to confirm collision eliminated.

**Acceptance criteria.**
- AC-2.3a `results/` contains ≥4 JSON artifacts regenerable by a committed command; README references them by name.
- AC-2.3b Zero numeric mismatches between README and artifacts (spot-check script or manual diff recorded).
- AC-2.3c No file named `deconvolution.py` inside imp-causalNet-paper; suite/notebook still execute green after rename.

## T2.4 — imp-causal-paper: supersede contradictory handoffs; evidence policy; index-method comparison

**Priority:** P1 · Wave: 2 · Depends on: **V1 + V3** stamps; T0.3.
AUTHOR-DECISION (D-5) on evidence policy; AUTHOR-DECISION (D-7) on pre-registration
sign-off (v1.2). **Effort:** L.

**Context (gated on V1/V3 verification before acting).** Four status documents
chronologically contradict each other: AI_AGENT_HANDOFF ("not yet full") →
REPRODUCTION_LEDGER (detailed partials; E. coli via RegulonDB 14.5 proxy for paper ~9.x;
CellNet 14/16) → SESSION_HANDOFF ("Full Reproduction Complete", all ✓) → imp-results.md
(latest: "partial, reduced, qualitative shadow… not a full reproduction"). Persisted CLI
artifact contradicts the EXACT-ρ claim (`results/ca/summary.json`: inferred_rule 222 vs
true rule 254). Sign-agreement percentages embed post-hoc per-network node orderings.
All evidence gitignored (`.gitignore:33–43`). And per the programme's stated goal, this
replication contains no comparison against the index method at all.

**Steps.**
1. (After V1/V3 stamp) Add dated supersession header to SESSION_HANDOFF.md and
   AI_AGENT_HANDOFF.md pointing to imp-results.md as current truth (U5-style: never
   delete history, mark it stale in place).
2. D-5 options for evidence: (i) track `results/`+`data/processed` summaries (not raw)
   in git under this directory; (ii) move to release artifacts / external storage with
   hash manifest committed. Recommend (i) for JSON summaries ≤ few MB, raw stays ignored.
3. Record the node-ordering researcher-degree-of-freedom explicitly next to the 97–99%
   sign-agreement claims (one honesty paragraph), citing ledger :1045–1067.
4. New module `index_method_comparison/`: run the project's exact deconvolution engine
   over the same networks used for the Zenil-calculus comparisons (Th17, E. coli subset,
   CA set); produce capability table mirroring imp-causalNet-paper's COMPARISON.md format
   (ours / both / theirs / neither). Pre-register interpretation rules before running
   (which outcomes count as wins) — house style from imp-prices Phase protocol.
   **AUTHOR-DECISION (D-7, v1.2): pre-registration sign-off.** Because this is a *new*
   experiment, not a repair, its interpretation rules and network selection constitute
   analysis freedom that must be closed before the run: the pre-registration commit
   (rules + network list + success criteria) requires the author's explicit approval
   BEFORE the comparison executes. An agent may draft the protocol; only the author may
   unfreeze it. This closes the same loophole imp-prices' Phase discipline closes: no
   self-certified goalpost placement on new experimental ground.

**Acceptance criteria.**
- AC-2.4a Both stale handoffs carry dated supersession headers naming the authoritative document.
- AC-2.4b Chosen evidence policy implemented; hash manifest verifiable.
- AC-2.4c Orderings DoF paragraph present adjacent to every sign-agreement percentage.
- AC-2.4d Comparison table exists with pre-registered reading rules committed BEFORE the run output (commit order checkable in history).
- AC-2.4e (v1.2) The pre-registration commit carries the author's recorded approval (commit trail or Appendix D entry) dated strictly before the earliest results commit; git-history checkable.

## T2.5 — imp-pathinfo-paper: reconcile campaign numbers to ledgers

**Priority:** P2 · Wave: 2 · Depends on: T0.3. **Effort:** S.

**Context.** Gold-standard replication methodology, but its own status numbers drifted:
README :197–202 ("490 of 648 runs…"), FINDINGS §6/NEXT_PHASES §8 ("607 runs, 202 of 216")
vs actual ledgers (`results/runs*.jsonl`, distinct keys = line counts): 623 runs,
208/216 noise cells; Mix-Hop complete; Graphormer missing only Lipophilicity (plus one
2-replicate cell). Test counts: README :160 "39" vs :172 "18" vs pytest-collected 41.
"100% of ~25,000 atoms" (:71–72) is actually 24,880 atoms from a 200-molecules/dataset
subsample cap documented nowhere.

**Steps.**
1. Write `scripts/campaign_status.py` deriving counts directly from ledgers; run it.
2. Replace all three documents' campaign blocks with generated output (dated, script
   name embedded). Single source: the ledgers.
3. Correct test-count mentions to the collected number; add collection command.
4. Add subsample-cap disclosure beside every atom-total claim.

**Acceptance criteria.**
- AC-2.5a Status generator exists; all three docs quote its output verbatim (grep-verified).
- AC-2.5b One test-count number everywhere, matching pytest collection.
- AC-2.5c Subsample cap stated wherever atom totals appear.

## T2.6 — index-deconvolution documentation settlement completion

**Priority:** P1 · Wave: 2 · Depends on: T0.3.

**Context.** The terminology settlement renamed code docstrings but left the repo's front
door teaching the ruled-out category error: `index-deconvolution/README.md:20–25,46`
still presents pivots/sumandos as one dichotomy (GLOSSARY §1c confusion source #5);
TRANSFERENCE.md ends on the Level-10 handback calling the oracle/pivot relation "a
geometric identity… only interpretive" (the over-correction logged as confusion source
#3) with no amendment; stale inventories persist (README :64 "bitacora 00–04" vs 32
existing; :104–124 "16/16 unit tests" undated vs 146 now).

**Steps.**
1. Rewrite README method section per GLOSSARY §1c (two decompositions; decimal anchor;
   free coordinates; lossless Dec(L,S)).
2. Append dated addendum section to TRANSFERENCE.md recording the #3 amendment chain
   (b21 oversell → b22 re-rate → GLOSSARY #3 correction) without editing historical text.
3. Refresh inventories: bitácora count (00–31), test count referencing the new BASELINE
   mechanism, level map 11–18 noted as README-pending (backlog item T5.4).

**Acceptance criteria.**
- AC-2.6a README contains the two-decomposition table language consistent with GOVERNANCE/GLOSSARY.md §1c; grep for old single-dichotomy phrasing returns nothing.
- AC-2.6b TRANSFERENCE.md carries dated addendum; original lines untouched (git diff shows append-only).
- AC-2.6c Counts match executed reality (bitácora ls | wc; baseline rollup reference).

## T2.7 — Sibling defect-log correction (NEEDS-SIBLING-EDIT)

**Priority:** P2 · Wave: 2 · Depends on: **V2** stamp; author approval. **Effort:** S.

**Context (gated on V2).** If V2 confirms: series-deconvolution TRANSFERENCE §9.6
records "imp-causalNet-paper's copy of `deconvolution.py` diverges from the other two" —
false: that file transcribes arXiv:1802.09904 Algorithms 1–2, a same-named unrelated
module (real hazard is the name collision itself, resolved by T2.3 step 4). Also the
one-line b21/b22 history ("21 stated an identity; 22 retracted") compresses three steps
(b21 containment-with-residual + θ=c "identity"; b22 re-rated epistemics rather than
retracting mathematics; GLOSSARY #3 then amended the demotion). A court must be more
accurate than its defendants.

**Steps.** With approval: append dated correction entries to sibling TRANSFERENCE §9.6
and a precision note to GLOSSARY §8 propagation table. No retro-edits.

**Acceptance criteria.**
- AC-2.7a Sibling docs carry dated corrections referencing this plan's task ID.
- AC-2.7b Original text unmodified (git diff shows append-only in sibling repo).

---

# PART F — VERIFICATION-FIRST TASKS (cheap; run before dependents)

Each V-task produces a stamp appended to Appendix D: **VERIFIED / REFUTED /
CORRECTED-WITH-DETAILS**, plus evidence file:line. Downstream tasks unlock on stamps.

## V1 — Replication-trio status contradictions
Read chronologically: imp-causal-paper `AI_AGENT_HANDOFF.md`, `REPRODUCTION_LEDGER.md`,
`SESSION_HANDOFF.md`, `imp-results.md`. Confirm/refute: (i) SESSION_HANDOFF claims full
reproduction with all ✓ while latest says shadow; (ii) SESSION_HANDOFF :12 EXACT ρ=+1.0
for 10 ECA rules vs persisted `results/ca/summary.json` inferred_rule 222 vs rule 254;
(iii) imp-results.md :69,:71 deny E. coli/CellNet work contradicted by ledger :823–844,
:905–957 and on-disk JSONs. Output: stamped verdict per sub-claim.

## V2 — Sibling defect-log entry and b21/b22 wording
Read `index-deconvolution/bitacora/21` and `/22` in full. Determine: does 21 state an
identity or containment-with-residual? Does 22 retract the mathematics or re-rate the
framing? Then diff `imp-causalNet-paper/src/imp_causalnet_paper/deconvolution.py` against
`index-deconvolution/src/deconvolution.py` to confirm unrelated-algorithm status. Stamp.

## V3 — RegulonDB versioning
Locate the paper's stated RegulonDB version (iScience 2019 / arXiv:1709.05429 methods);
read ledger :823–844. Confirm 14.5-vs-~9.x substitution and its exact-comparison
consequence. Stamp.

## V4 — Bio-arm circularity framing
Trace ground truth: `index-deconvolution/experiments/exp04_biological.py` +
`src/bnet.py` — confirm repertoires are produced by exhaustive evaluation of parsed .bnet
expressions and deconvolution inverted against that same matrix; confirm n≤16 cap
(grieco_mapk n=54 excluded); confirm REGULATORY gate defined from fission yeast networks
then counted on them. Verdict determines T4.2's wording strength. Stamp.

## V5 — Description-length nonidentity
Extract the four formulas (`imp-causalNet-paper index_set_description_length`;
pathinfo `graph_description_length`/`node_description_cost`; causalNet
`measure.model_description_length`; Mathematica `BioMetrics.m` D/D_v2). Evaluate all on
one shared toy input (e.g., 4-node network, fixed wiring+gate) ; tabulate values.
Nonidentical values ⇒ nonidentity confirmed; identical on toy ⇒ test a second input
before concluding. Stamp feeds T4.5 design.

---

# PART G — WAVE 3: THEORY HARDENING

## T4.1 — Ordering unification and the 0.51875 root cause

**Priority:** P1 · Wave: 3 · Depends on: T0.2, T1.2. **Effort:** L.

**Context.** The codebase runs two ordering conventions bridged ad hoc: MSB-first
(`TruthTable`, `IndexSet`, `IndexSetNetwork`, band indices in `IndexAlgebra.m`) vs
LSB-first (`CreateRepertoiresDispatch`, legacy `Alpha.m` `createRepertoires/runDynamic`
via `allPosibleInputsReverse :108–109`, `indexSetAnalytic` weights 2^(i−1), summandos
construction at Alpha.m :2517), plus a third lexicographic enumeration in BioExperiments
(`Tuples[{0,1},n]`). Every consumer must remember Φ; the recorded
`accuracyIndex=0.51875` shows at least one shipped bridge is semantically mismatched.
Paper declares LSB primary (:181) with MSB transported by Φ (Thm :1451) — the code never
obeyed. Also note legacy hazard discovered en route: `createRepertoires`/`runDynamic`
silently leave `resOp` stale for any gate outside {AND,OR,XOR,NAND} (Alpha.m :375–390)
— no error raised.

**Steps.**
1. Root-cause first, separately committed: instrument TSK-MIXED-001's IndexSetNetwork+Φ
   path; locate the exact mismatched bridge (suspects: Φ applied/not-applied at matrix
   write-in :62; network-vs-local semantics; MAJORITY tie interaction). Fix or quarantine
   with explanation. Re-run test; expected accuracyIndex → 1.0 or documented reason why
   the packaged path cannot reach it.
2. Design doc `GOVERNANCE/ORDERING.md`: LSB-first canonical internal representation;
   Φ applied exactly once at interop boundaries (paper tables MSB, legacy imports);
   every public function documents its input/output convention; BioExperiments migration
   path to canonical enumeration.
3. Migrate call sites per design doc; delete per-call-site Φ bookkeeping where the design
   makes it redundant; add the stale-`resOp` guard (explicit `Failure["UnsupportedGate"]`)
   to legacy dispatch while touching it.
4. Full suite bracketing; BASELINE diff must show only intended changes.

**Acceptance criteria.**
- AC-4.1a Root cause of 0.51875 documented in commit + ORDERING.md appendix; fixed path re-measures 1.0 on the mixed10 benchmark OR carries a written impossibility argument reviewed by author.
- AC-4.1b ORDERING.md exists; grep audit shows no consumer applies Φ ad hoc where design forbids (spot-check list embedded).
- AC-4.1c Unsupported-gate input to legacy dispatch now raises instead of silently mis-executing (negative-control probe demonstrates).
- AC-4.1d Suite delta = intended changes only.

## T4.2 — Bio-arm claim reframing (gated on V4)

**Priority:** P1 · Wave: 3 · Depends on: V4 stamp. **Effort:** S.

**Context (if V4 confirms).** Exact repertoire reproduction 8/8 is a round-trip
certificate: ground truth is exhaustively evaluated parsed .bnet; deconvolution inverted
against that same repertoire; given a column's exhaustive table determines its function
uniquely, round-trip exactness follows modulo bugs. It validates parser + forward model +
inverter — valuable — but "recovers real gene-regulatory networks exactly" (bitácora 05)
asserts discovery where consistency is proven. Historical bitácora stays untouched (U5);
living claims change.

**Steps.**
1. Reword living docs (index-deconvolution README results section; papers citing the
   8/8) to: "round-trip exactness certificate on exhaustive repertoires" + explicit
   scope statement.
2. Backlog promotion: trajectory-route validation experiment on n>16 models (new plan).

**Acceptance criteria.**
- AC-4.2a No living document claims biological discovery from round-trip results; each such claim carries the certificate framing + V4 evidence pointer.
- AC-4.2b Historical bitácoras byte-identical (git diff empty).

## T4.3 — CA coverage-sweep experiment (pre-registered)

**Priority:** P2 · Wave: 3 · Depends on: T0.2. **Effort:** M/L.

**Context.** CA exactness (12/12 rules, global-map equality) holds under generating
assumptions (radius-1, ≤3 inputs, homogeneous gate, periodic boundary) with pooled ICs
ensuring neighbourhood coverage. Failure behaviour under partial coverage is unstudied;
exactness currently reads as unconditional. This experiment characterises the operating
envelope — turning "recovers ECA exactly" into a defensible, quantified claim.

**Steps.**
1. Pre-register (`experiments/ca_coverage/PROTOCOL.md`, committed before run): sweep
   coverage fraction p ∈ {0.5,…,1.0} of neighbourhoods seen before inversion; all 12
   rules × width 12 × 20 seeds; success = global-map exact; report recovery curve per
   rule class (saturating vs non-saturating).
2. Execute; commit code+outputs; one figure (G1-style render: recovery vs coverage).

**Acceptance criteria.**
- AC-4.3a Protocol committed with timestamp preceding results commit (history-checkable).
- AC-4.3b Recovery curves reproducible from committed seeds; summary JSON traces to executed run.
- AC-4.3c Paper-facing sentence drafted stating identifiability envelope honestly.

## T4.4 — Null-nuisance declaration rule

**Priority:** P1 · Wave: 3 · Depends on: none (documentation). **Effort:** S.

**Context.** Two reversals on one table (imp-prices C22 density confound; sibling B1
codeword-syntax null) share a mechanism: randomization destroyed structure imposed by the
code/pipeline rather than by the data, because nuisance dimensions of the statistic were
never enumerated. Rule: *before running any null, declare what the statistic responds to
(shape, density/marginal, alphabet, length, codeword syntax); hold all but the claimed
dimension fixed; state which dimension the null destroys.*

**Steps.** Write `GOVERNANCE/NULLS.md` with the rule, the two case studies as worked
examples, and a checklist template appended to future pre-registrations.

**Acceptance criteria.**
- AC-4.4a NULLS.md exists with both case studies traceable to their bitácora entries.
- AC-4.4b Template referenced from series-deconvolution Phase-2 pre-registration TODO (pointer only; sibling edit gated separately).

## T4.5 — Description-length consolidation interface (gated on V5)

**Priority:** P2 · Wave: 3 · Depends on: V5 stamp. **Effort:** M.

**Steps.** Design doc `GOVERNANCE/DESCRIPTION_LENGTHS.md`: name each variant, its cost
model, domain, and mapping table; single shared BDM wrapper module with pinned pybdm
version + edge-semantics documentation (pathinfo None-below-4-atoms behaviour preserved
per-consumer via flags); cross-repo parity tests on shared fixtures.

**Acceptance criteria.**
- AC-4.5a Doc exists with V5 tabulated nonidentity as motivation; fixtures reproduce all four values on the toy example.
- AC-4.5b One wrapper module; consumers import it or carry documented exceptions.

## T4.6 — Offset notation disambiguation (P2, per C-3)

**Steps.** In `method_paper.tex` (:1258–1267 region and tables :1122–1125,:1142–1143),
rename the script's delta-encoding ("anchor ± offsets") distinctly from free-coordinate
offsets Ω(F_q) — e.g., "residual deltas" — one sentence noting both unfold to identical
index sets here. Regenerate affected tables via T5.1 pipeline.

**Acceptance criteria.**
- AC-4.6a The two encodings never share a label; text states their equivalence explicitly for this benchmark.

## T4.7 — Validation-map honesty repair

**Priority:** P1 · Wave: 3 · Depends on: T1.2. **Effort:** M/L (branch-dependent).

**Context.** Paper :1836–1839,:2065–2067 claim the stratified sampled audit "confirms"
the Canonical Exact Reconstruction beyond exhaustive range, but its cited artifact
(`TSK-ALGO-002-ImportanceSampling.m`) compares `ApplyGate` against `TruthTable` of the
same local rule — dispatch consistency only — restricted to {AND,OR,XOR,NAND,NOR,XNOR,
MAJORITY}; no analytic/index-set path involved.

**Steps.** Either (i) build the missing artifact: sampled large-n audit comparing
packaged closed-form sets (post-T1.2) against baseline row construction, stratified,
seeded, with elementwise agreement counts; then the paper claim stands with the right
citation. Or (ii) rewrite the two sentences to claim only dispatch-vs-truthtable
consistency. Recommend (i): it converts an overclaim into a real scalability result.

**Acceptance criteria.**
- AC-4.7a Chosen branch executed; if (i): new artifact committed with seeds + symmetric-difference reporting; paper cites it; if (ii): sentences rewritten, citation corrected.
- AC-4.7b No remaining paper sentence cites TSK-ALGO-002 for theorem-level reconstruction (grep-verified).

---

# PART H — WAVE 4: MACHINE-CHECKABLE PAPERS

## T5.1 — Regenerate-and-diff for the flagship manuscripts

**Priority:** P1 · Wave: 4 · Depends on: T1.2, D-4. **Effort:** L.

**Context.** Reviewer's second-highest endorsement: §2.1, §2.3, §3.7 are all code–prose
divergences — exactly the class a regenerate-and-diff target eliminates. imp-prices
already runs this discipline (hash-pinned ledgers, machine-generated notebooks); the
flagship manuscript is where it is absent — the same authority inversion Part A names.

**Steps.**
1. Every numeric table in `method_paper.tex` (and `comp_paper.tex`) gets an artifact ID
   (`%% ARTEFACT: <id>` comment) and a producing script under `papers/method/code/`
   writing JSON + the exact .tex rows.
2. Makefile target `make verify-paper`: regenerates all artifacts; diffs against the
   .tex-embedded rows; exits non-zero listing mismatched IDs.
3. Start with known-divergent objects: four-computational-paths table (:1784–1799 — must
   gain the 0.51875 row or its documented exclusion rationale per T4.1 outcome),
   mixed10 summary tables (:1070–1234), corroboration constants, D_formula=135.66 bits
   (:1860), attractor statistics from generate_paper_outputs.wl §6.
4. CI-able: one command, no GUI dependencies beyond kernel path already fixed.

**Acceptance criteria.**
- AC-5.1a `make verify-paper` exists; currently-green on repaired tables; demonstrably fails when a scratch value is perturbed (then reverted).
- AC-5.1b The 0.51875 question resolved visibly: either present with explanation or excluded with written reason in the paper text.
- AC-5.1c Every artefact ID maps to a committed script + JSON (inventory file).

## T5.2 — Derivations completion or proposition scoping (AUTHOR-DECISION D-6)

**Priority:** P2 · Wave: 4 · Depends on: T1.2. **Effort:** L/M (option-dependent).

**Context.** `papers/method/derivations/` covers only band framework, AND, OR, exam —
10 of 12 families lack derivation documents while :1925 asserts gate-level corroboration.
Post-T1.2, exhaustive verification to arity 6 constitutes mechanical proof witnesses.

**Steps.** Choose: (i) generate per-family derivation docs (template + closed forms +
arity-≤6 verification output embedded); or (ii) scope the paper sentence to families with
derivations + cite AC-1.2a as machine verification for all twelve. Either closes the gap;
(i) preferred for referee optics.

**Acceptance criteria.**
- AC-5.2a Chosen option executed; :1925-area sentence matches reality exactly.

## T5.3 — Levels 11–18 READMEs (backlog)

One page each: purpose, key result, pointer to owning bitácoras. Restores the repo's own
documentation rule (TRANSFERENCE.md:295–297). Acceptance: README exists per level dir.

## T5.4 — Full ledger lint for imp-prices FINDINGS (optional extension of T2.1 step 3)

Sweep every C-section's quoted statistics against cited artifacts; report first, fix by
same addendum protocol after author review.

> **PROGRAMME CLOSE-OUT.** When all Wave 3–4 rows above reach DONE in Appendix E,
> the terminal step of this programme line is **boarding**
> `ROADMAP_R4_SEGMENTED_GRAMMAR.md`: run the final closure audit (both gates +
> suite vs BASELINE), set every Appendix E row final, then draft the Route 4
> pre-registration and HALT for author sign-off. R4 *execution* opens the
> successor effort and never runs under this plan's authority.

## T5.5 — Post-fix cross-replication accuracy sweep (added v1.3; MANDATORY)

**Priority:** P0 · Wave: 5 · Depends on: Waves 1–2 landed. **Effort:** L.
**Origin:** author directive 2026-08-24 at the gate session ("review carefully all
replication notebooks and all related subprojects to update carefully with accuracy —
this should be mandatory").

**Context.** Waves 0–2 changed code (packaged engine, MAJORITY policy, renames,
runners), corrected ledger prose (C18, C26, C29/C36 provenance), renamed a decoy
module, and re-based campaign counts on ledgers. Any notebook or document that quotes
numbers downstream of those objects is now unverified until reconciled. First sweep
finding: `imp-causal-paper/imp-results.md`'s E. coli row denied work that demonstrably
exists (fixed `4d9701f`). Second registered inconsistency: index-deconvolution exp04
pins 10 `.bnet` models in code while the persisted artifact records 8 considered/8 exact.

**Steps.**
1. Work item by item through `T5_5_SWEEP_INVENTORY.md` (N1–N6 notebooks, D1–D4 docs);
   the inventory itself is living — extend it as items close.
2. Re-execute each notebook in its own environment; require 0 errors / 0 unexecuted;
   reconcile quoted numbers elementwise against current artifacts; corrections enter
   as dated addenda (U5), never retro-edits of executed outputs without re-execution.
3. Adjudicate D2 (exp04 10-vs-8): either re-run exp04 with the current model list or
   annotate the artifact with a dated note naming the discrepancy cause.
4. Every equality/agreement claim touched passes datasaurus gates before it is written.

**Acceptance criteria.**
- AC-5.5a Inventory file shows every row DONE or explicitly deferred with reason.
- AC-5.5b No notebook in any subproject carries error/unexecuted cells post-sweep.
- AC-5.5c Every number quoted in living docs traces to a post-fix executed run or
  carries a dated pointer to the historical artifact it cites.

---

# PART I — POST-CLEANUP RESEARCH BACKLOG (pointers only; new plans will own these)

Ordered by expected scientific value:

1. **Clock-network bridge experiment.** Binarise each instrument's market clock to a
   per-day event indicator → synchronous multivariate binary trajectory across N
   instruments — exactly the input shape `src/deconvolution.py` consumes → test recovered
   wiring against per-instrument-shuffle null. First genuinely novel result produced by
   *combining* the Boolean arm with the finance arm; tests whether markets possess
   gate-shaped clock structure in the method's home regime (synchronous networks).
   Motivating asymmetry: exact method succeeded precisely on synchronous networks (ECA,
   bio); failed on univariate paths; shared-clock R²≈0.45 synchronous-not-lead-lag is a
   negative against Granger-style hypotheses, not against this model class.
2. **In-degree penalty theorem (from C18).** Prove/simulate the condition under which
   deterministic-map two-part codes under-penalise in-degree vs CPTs on stochastic
   targets (log₂a vs (a−1)·½log₂N per realised pattern). Durable positive theory from an
   honest negative; feeds back into when index-set descriptions can be trusted to select
   structure.
3. **ε-machine / computational-mechanics unification.** Reconstruct ε-machines of ECA
   clocks, bio attractor sequences, market clocks; compare statistical complexity C_μ
   ordering against programme hierarchies (Wolfram classes; α≈½ universality).
4. **Oracle-minus-pivot residual object.** ~1.37%-of-actions set "requiring the future":
   gap distribution, volatility-cluster relation, Hawkes predictability of residual vs
   pivot. Cheap, well-posed, existing pipelines.
5. **High-entropy positive control for series-deconvolution trio.** Non-periodic,
   large-alphabet generators: Recamán-style, Thue–Morse transforms, dimensionless digit
   channel of constants (G3-compliant; ISC/Plouffe precedent). Pre-register: median match
   length >20, G1-positive, generator-family retrieval.
6. **Publication strategy per track** (post-Waves): method paper scoped per D-2/D-6;
   replication set completed per Wave 2; finance negative-results paper built around
   B4/B5 double refutation + item 2 theorem + dependency-aware inference methods; Phase 2
   of series-deconvolution proceeds under its revised bar (median match length >6,
   declared effect size, ≥2000 surrogates).
7. **Composed-semantics as first-class theory (former D-2(b), moved here v1.1).** Add a
   layered-update evaluator to the package (nodes read upstream outputs within one
   synchronous pass, topologically ordered); state the index-set identity for composed
   nodes; prove/verify at small n; scope the main theorem to local maps with the composed
   case as a validated corollary. This is new theory, not repair — it earns its own plan,
   pre-registration, and possibly its own section of the method paper. Interim coverage
   during Waves 1–3: D-2(d)'s composition lemma (verified empirically in T1.1) plus
   T1.5's disclosure.

---

# APPENDIX A — CONSOLIDATED DECISION REGISTER

| ID | Decision | Options | Recommendation | Status |
|---|---|---|---|---|
| D-1 | Working-tree checkpoint | commit-all WIP vs selective staging | commit checkpoint | OPEN |
| D-2 | Flagship network semantics | (a) local recompute / ~~(b) layered evaluator~~ → Part I item 7 / (c) drop node 6 / **(d) composite-gate declaration: node 6 = in-degree-4 gate outside the twelve-family catalogue, one-set obtained by composing index sets** | **(d)** v1.1 — keeps the example, no new theory on the critical path, makes the scope boundary visible; composition lemma verified empirically in T1.1 | OPEN (options expanded v1.1) |
| D-3 | MAJORITY tie convention | ties→0 / ties→1 / tiePolicy param | (iii) param, default ties→0; gated on tie-row probe | OPEN |
| D-4 | Manuscript roles | two-canonical-scoped / merge | two canonical, distinct scopes | OPEN |
| D-5 | imp-causal-paper evidence policy | track summaries / external+manifest | summaries ≤ few MB tracked | **CLOSED 2026-08-24: option (i)** |
| D-6 | Derivations completion vs scoping | generate 10 derivations / rescope claim | **CLOSED 2026-08-25: generate — extended by author to ALL TWELVE families** (not only the 10 missing); executed as T5.2 |
| D-7 | T2.4 comparison pre-registration sign-off | agent self-certifies / author approves before run | **author approves** (v1.2) — new experiment, analysis freedom must be closed pre-run; agent drafts only | **CLOSED 2026-08-24: APPROVED as drafted** |

# APPENDIX B — EXECUTION ORDER (DAG)

```
T0.3 ─┬→ T0.1a → T0.2(v1: 7 sections) ─┐
      │           │                    │
      │           └→ T0.1b (discovery + baseline v2)
      ├→ T0.5 (paper-number snapshot)     ← gates all Wave-1 numeric edits
      │
      ├── RESTART POINT = T0.* + T1.2 → T1.1(D-2) → T1.3(D-3) → T1.4(D-4) → T1.5
      │
T0.5,T1.2 ─→ Wave-2 V-tasks (V1..V5) ─┬─→ T2.4 (V1,V3,D-5,D-7)
                                      ├─→ T2.7 (V2, approval)
                                      └─→ T4.2 (V4), T4.5 (V5)
T0.3 ─→ T2.0, T2.1, T2.2, T2.3, T2.5, T2.6
T0.2,T1.2 ─→ T4.1 ─→ T4.7 ; T4.3, T4.4 standalone
T0.5 ─→ T5.1 ─→ T4.6 ; T1.2 ─→ T5.2 (D-6)
T0.4 [gate: Waves 1–2 landed] ; Backlog items 1–7: separate plans after tag audit01-baseline.
```

# APPENDIX B2 — EFFORT ESTIMATES AND SCHEDULE REALITY (added v1.1)

Scale: **S** ≤ 2 h · **M** half-day · **L** 1–2 days. Owner column: A = agent-executable,
Au = author-gated or author-required.

| Task | Effort | Owner | Task | Effort | Owner |
|---|---|---|---|---|---|
| T0.1a parser | S | A | V1 trio docs | S | A |
| T0.1b discovery | M | A | V2 sibling b21/22 | S | A |
| T0.2 baselines | M | A | V3 RegulonDB | S | A |
| T0.3 checkpoint | S | Au | V4 bio-arm trace | M | A |
| T0.4 branch/tag | S | Au | V5 desc-lengths | M | A |
| T0.5 paper snapshot | M | A | T4.1 ordering+0.52 root | L | A |
| T1.1 flagship script | M | A(+Au: D-2) | T4.2 bio reframing | S | A |
| T1.2 package engine | L | A | T4.3 CA sweep | M/L | A |
| T1.3 MAJORITY | M | A(+Au: D-3) | T4.4 NULLS.md | S | A |
| T1.4 governance | M | A(+Au: D-4) | T4.5 desc-length iface | M | A |
| T1.5 interim 0.52 row | S | A | T4.6 offset rename | S | A |
| T2.0 hygiene bundle | M | A | T4.7 validation-map | M/L | A |
| T2.1 C18 reconcile | M | A | T5.1 regenerate-diff | L | A |
| T2.2 C29/C36 code | M | A | T5.2 derivations | L/M | Au(D-6) |
| T5.4 full ledger lint | ✅ DONE (report-first) | `201677f`: scripts/lint_ledger_full.py sweeps 41 C-rows / 170 quoted decimals (row+window citations, JSON+CSV harvest, rounding-tolerant); **75 verified directly; 95 UNVERIFIED across 27 rows listed for author review** (unverified ≠ wrong — defined in report header); FINDINGS untouched pending review per fix protocol |
| T2.3 causalNet fixes | M | A | T5.3 level READMEs | S | A |
| T2.4 causal-paper arc | L | A(+Au: D-5, D-7) | T5.4 full lint | M | A |
| T2.5 pathinfo counts | S | A | T2.6 idx-deconv docs | S | A |
| T2.7 sibling addendum | S | Au | | | |

**Wave totals:** Wave 0 ≈ 3–4 days (incl. one author gate). **Restart point**
(Wave 0 + T1.2/T1.1/T1.3/T1.4/T1.5) ≈ **one working week**, retiring every P0 in the
exactness engine and ending with both instruments measuring (tests *and* paper numbers).
Wave 2 ≈ 1.5–2 weeks across four repositories behind two author gates — schedule it as a
backlog with owners, not a continuation. Waves 3–4 ≈ 2–3 weeks, partly parallelisable;
T4.1 should start early in background once T1.2 lands because its outcome feeds the
T1.5 annotation's resolution.

# APPENDIX C — FULL FINDINGS INVENTORY (audit → task mapping)

| # | Finding (file:line) | Severity | Task |
|---|---|---|---|
| F01 | Call-before-definition + symbolic propagation, generate_paper_outputs.wl:84/:94/:108/:118 | P0 | T1.1 |
| F02 | Unconditional banner :423 | P0 | T1.1 |
| F03 | Composed-vs-local semantics schism; 32/64-row chance agreement | P0 | T1.1/D-2 |
| F04 | IndexSet {} fall-through, Gates.m:39–50 | P0 | T1.2 |
| F05 | indexSetAnalytic triplicated (mw:38/gpw:118/tm:71) | P0 | T1.2 |
| F06 | accuracyIndex 0.51875 recorded; omitted from paper :1784–1799 | P0 | **T1.5 (interim disclosure)** → T4.1 root cause / T5.1 permanent |
| F07 | MAJORITY three-way divergence (g16/core27/test21); paper :455 ambiguity | P0 | T1.3/D-3 |
| F08 | Runner exit-code-only (:55–62); FAIL unread (Status.txt) | P0 | T0.1 |
| F09 | --all omits six sections (:25) | P0 | T0.1 |
| F10 | OK=87 FAIL=0 not a measurement | P0 | T0.2 |
| F11 | C18 hill-climb clause wrong (FINDINGS:164 vs b4 JSON) | P0 | T2.1 |
| F12 | C29/C36 corrections without code; pre-guard daily cells uncaveated (C26) | P0 | T2.2 |
| F13 | Tautological assert test_clock.py:30 | P1 | T2.0 |
| F14 | __init__ hmmlearn coupling | P1 | T2.0 |
| F15 | Vendor parity manual-only | P1 | T2.0 |
| F16 | imp-prices README stale; prequential duplicate rows | P1/P2 | T2.0 |
| F17 | causalNet README mismatches (tally/delta/attribution/tests); no persisted artifacts; /tmp/cdn dependency | P1 | T2.3 |
| F18 | deconvolution.py name-collision decoy | P1 | T2.3 |
| F19 | causal-paper contradictory handoffs; gitignored evidence; orderings DoF; no index comparison | P1 | T2.4/V1/V3/D-5 |
| F20 | pathinfo campaign/test-count/subsample drift | P2 | T2.5 |
| F21 | index-deconvolution README category error; TRANSFERENCE stale handback; inventories stale | P1 | T2.6 |
| F22 | Dangling GLOSSARY citations; dead CLAUDE.md path; dual-manuscript divergence risk | P0 | T1.4/D-4 |
| F23 | Stale technical-sense "pivot" in docProcess.tex + derivations | P1 | T1.4 |
| F24 | Ordering split-brain; legacy stale-resOp silent corruption | P1 | T4.1 |
| F25 | Bio-arm round-trip framing (gated V4) | P1 | T4.2/V4 |
| F26 | CA identifiability envelope unstudied | P2 | T4.3 |
| F27 | Null nuisance-dimension rule missing | P1 | T4.4 |
| F28 | Description-length nonidentity (gated V5) | P2 | T4.5/V5 |
| F29 | Offset notation collision (downgraded per C-3) | P2 | T4.6 |
| F30 | Validation-map overclaim citing wrong-support artifact | P1 | T4.7 |
| F31 | Missing derivations 10/12 vs :1925 claim | P2 | T5.2/D-6 |
| F32 | Sibling defect-log false entry + history compression (gated V2) | P2 | T2.7/V2 |
| F33 | Levels 11–18 lack READMEs | P3 | T5.3 |

# APPENDIX D — LIVING LOG (append-only; dated entries)

Template per entry:
`[date] [task-id/DEV-Vn] what was found/decided/stamped; evidence; consequence.`

- 2026-08-23 PLAN-CREATED v1.0. Baseline state: branch `clean`; rollup OK=87 FAIL=0
  (kernel-exit-only, superseded once T0.2 lands); imp-prices 95 passed own-venv
  **[executed]**; vendor md5 parity confirmed **[executed]**. Claude-feedback
  adjudication recorded in Part A (C-1..C-5); unverified claims routed to V1–V5.
- 2026-08-23 PLAN-AMENDED v1.1 (second review pass, all six findings adopted):
  (1) T0.5 paper-number snapshot added to Wave 0 — U3 extended from test runner to
  manuscripts; T0.5 gates Wave-1 numeric edits; AC-0.5c brackets added to T1.2/T1.3;
  F06 rerouted. (2) T1.1 decoupled from D-2 and reordered behind T1.2; D-2 option (d)
  composite-gate declaration added and recommended; former option (b) moved to Part I
  item 7 as research backlog; composition-failure stop-rule added to T1.1 Risks.
  (3) T0.1 split into T0.1a parser-only + T0.1b discovery-with-second-baseline for
  red-attribution cleanliness. (4) T1.5 interim 0.51875 disclosure added to Wave 1
  (honesty before root-cause). (5) AC-1.4d replaced with curated-inventory pattern
  (grep cannot see sense); (6) AC-0.2a now excludes volatile lines (timestamps,
  durations) with the exclusion list stated in BASELINE.md. Effort estimates and
  restart-point scoping added (B.9, Appendix B2); Wave 2+ explicitly reframed as an
  owned backlog rather than a continuation.
- 2026-08-23 PLAN-AMENDED v1.2 (handoff-hardening pass, two gaps closed):
  (1) T1.4 sibling-absence fallback defined — missing sibling + no in-repo copy ⇒
  BLOCKED state logged in Appendix D, never silent synthesis; `check_glossary_sync.sh`
  gains three-state exit semantics (0 clean / 1 drift / 2 SYNC-UNKNOWN), with the
  renamed-sibling control added to AC-1.4a. (2) T2.4's new-experiment pre-registration
  now requires author sign-off before execution — registered as AUTHOR-DECISION D-7,
  AC-2.4e makes the approval trail git-history checkable, DAG and B2 updated. Rationale:
  an agent drafting its own success criteria for a new comparison is analysis freedom
  unclosed; same loophole imp-prices Phase discipline closes.
<!-- PLAN COMPLETE v1.2 -->









- `[T1.2]` **F36:** canalisingIndex coordinate schism — MUnit copy used ABSOLUTE network
  coordinate; package ApplyGate/core use Ic-relative position. Latent only (benchmark
  sets no CANALISING params); owner T4.1 ordering-unification.
- `[T1.1]` **F37:** the archived `accuracyIndex=0.51875` is a STALE artefact from a
  superseded script revision; current code executes the index path at 1.0. The audit's
  §2.3 defect was real but had already been half-healed silently — F35 orphaning kept
  the healed script out of the suite so nobody could know. Root-cause archaeology stays
  open under T4.1.
- `[T1.1]` Composition lemma (D-2d) verified empirically at n=6 — first positive theory
  result produced by this plan; feeds Part I item 7.
- `[T0.5/T1.5]` Process slip recorded: snapshot was rebaselined before its delta was
  read; repaired post-hoc from git (`HEAD~1` diff): exactly ONE semantic block changed.

- `[T2.1]` **DEV-2.1 (2026-08-24) — re-execution matched NEITHER step-1 branch; logged
  before any text edit per task-card escalation clause.** Committed hill-climb code is
  byte-identical to the pinned commit and the pin's content hash is intact — but across
  a 45-seed `PYTHONHASHSEED` sweep (rng seed 42 fixed; determinism control passed) the
  statistic itself is hash-seed-unstable: winners 5–7, modal {WTI_CL|WTI_Spot}, modal
  frequency 35–55%. Pinned map (6/{WTI_Spot}/37.5%) reproduced **elementwise** by
  exactly seed 19/45 (provenance did NOT break — the JSON is a genuine draw); the prose
  triple (5/{WTI_CL}/55%) by seeds 17/33/39 (writer likely quoted an ad-hoc re-run).
  Original run recorded no PYTHONHASHSEED ⇒ pin is one unrepeatable-as-stood draw of a
  seed lottery. Resolution executed: quote-the-pin correction in FINDINGS C18 + dated
  note; bitácora/04 append-only addendum; instability disclosed in both; C18 verdict
  robust under every observed draw (22 ≫ max 7). New standing implication recorded:
  pgmpy structural claims must fix+record PYTHONHASHSEED (extends C12/C13). Evidence:
  `imp-prices/results/recheck_c18/`, `8c6f6e2`.

- `[T2.2]` **DEV-2.2 (2026-08-24) — C29's exact null moments are not recoverable;
  conclusion robust.** The prose-only null (189.39±22.75 @17 / 214.83±17.40 @23)
  matches no principled committed sampler (off-diagonal 182-cell, 196-cell,
  upper-triangular, Bernoulli matched-density; N=20000, seeds pinned): recomputed
  moments land CLOSE but derived share/z diverge (71.6% vs 66%; z_gate −3.14 vs
  −3.35). Under every principled sampler the CONCLUSION holds (density share
  66–72%; both networks ≈3σ below own-density nulls). Resolution: committed script
  is single source going forward; quoted moments annotated as one unrecoverable
  scratch draw (`6bbc9fb`). C36 by contrast reproduces exactly incl. two disclosed
  presentation artefacts (6,479-vs-6,478 window enumeration; March-2020 sequence =
  raw-series episode, elementwise 8/8).

- `[T2.4/T2.7]` **AUTHOR DECISIONS RECORDED 2026-08-24** (interactive session; this
  entry is the pre-run approval record required by AC-2.4e):
  - **D-7 APPROVED** — index-method-comparison pre-registration
    (`imp-causal-paper/index_method_comparison/PROTOCOL.md`, committed `6bfedca`)
    approved AS DRAFTED. Execution may proceed under its rules; no outcome-dependent
    changes permitted.
  - **D-5 CLOSED — option (i)**: JSON summaries tracked in git + committed
    `MANIFEST.sha256`, raw gitignored.
  - **Supersession headers APPROVED AS DRAFTED** for SESSION_HANDOFF.md and
    AI_AGENT_HANDOFF.md.
  - **U6 PERMISSION GRANTED (both)** — sibling series-deconvolution may receive the
    drafted §9.6 correction and GLOSSARY §8 precision note (append-only).
  - **DEV-2.1 / DEV-2.2 RATIFIED**, with the added condition: verification through
    the `datasaurus` skill's four gates (render / elementwise compare / knobs /
    mechanism), acting on any failure. Gate artifacts to follow in the results tree.
- `[T2.4/T2.7]` **GATES EXECUTED 2026-08-24** — T2.4 DONE (`70068fd`,`3eb87ac`,
  `bc3935e`; ACs 2.4a–e all satisfied, incl. approval commit `2b6c5a8` pre-dating
  the earliest results commit); T2.7 DONE (sibling local commits `62fb3b3`,
  `b868cd0`, append-only, remote untouched; CausalBool resync `3e23d0c`, sync exit 0).
- `[DEV]` **DATASAURUS VERIFICATION COMPLETE 2026-08-24 — ALL GATES PASS.**
  `imp-prices/scripts/datasaurus_gates_c18_c29.py` renders the seed-sweep and
  null-distribution objects (`figures/dev21_c18_seed_sweep.png`,
  `figures/dev22_c29_nulls.png`) and writes the gate checklist to
  `imp-prices/results/datasaurus_gates_2026-08-24.md`: G1 render ✓; G2 elementwise
  (pinned map = seed 19 exactly; CLOSE moments reported as divergent, never rounded
  into agreement) ✓; G3 knobs (45-seed bracket, duplicate-seed determinism, SE≈0.16)
  ✓; G4 mechanism + exact scoping (triangular/DAG null z_gate=−0.75 explicitly
  excluded from the matched-convention robustness claim) ✓.
- `[T5.5]` **PLAN AMENDED v1.3 (2026-08-24, author-initiated at the gate session):
  post-fix accuracy sweep is MANDATORY.** Every executed notebook and every document
  quoting numbers must be reconciled against post-fix code/artifacts. First finding
  already landed: `imp-causal-paper/imp-results.md`'s E. coli row ("nothing exists /
  Not reproduced") was factually false — parse/perturb/enrichment scripts and
  RegulonDB 14.5 artifacts (949 nodes; classification 122/38/789) exist and ran;
  corrected by dated addendum `4d9701f`. Triage inventory:
  `T5_5_SWEEP_INVENTORY.md`.
- `[T5.5]` **SWEEP EXECUTED 2026-08-24 — ALL ROWS CLOSED.** N2: imp-causal-paper
  walkthrough re-executed green, all number-bearing outputs identical to committed;
  only delta = historical run had used ROOT venv instead of README-prescribed `.venv`
  (provenance drift recorded); refreshed notebook committed. N3/N4/N5 closed (N4:
  campaign-status regeneration byte-identical). N6: 15/15 non-empty idx-deconvolution
  notebooks executed 0 errors under root venv; **0-byte corrupt stray**
  `031_financial_honest_negative.ipynb` removed. D2 RETRACTED as false alarm —
  `n_models_considered` = graded-within-cap semantics; exp04 re-ran today, 8/8 exact
  reproduced; two over-cap models correctly recorded `skipped: too_large` in-artifact.
  D1 fixed pre-sweep (`4d9701f`). D4 paper gate PASS re-confirmed.

- `[T0.4]` **T0.4 EXECUTED 2026-08-24 — main reconciled, tag audit01-baseline published.**  Pre-merge audit all green (paper gate 112/112; GLOSSARY sync 0; MUnit fresh
  OK=46 FAIL=4 == BASELINE v2; subproject suites green). Two merge-construction
  events recorded for audit: (1) first local merge a081ff6 inherited ~28 GiB of
  gitignored legacy data blobs from unpushed April lineage (3f9bd13/ceab8db:
  data/DepMap/** incl. 4.17 GB blob, data/cancer/patients_mapk_large/**,
  data/gnomAD/**) via ours-side conflict stages — superseded pre-publication;
  (2) published merge **366d771** = fixing's audited tree + adjudicated
  resolutions (170 files, 3.9 MiB: archive preservation + level-8 paper outputs
  + CellCollective exports), parents fff5750+0cb3646; excluded legacy dumps
  remain on local disk/local history, documented in merge message. Tag
  audit01-baseline @ 366d771 pushed. Author's untracked workspaces build
  artifacts backed up to /tmp/premerge_workspaces_backup/.

- `[T4.1]` **T4.1 EXECUTED 2026-08-25 — root cause + ordering unification closed.**
  (1) ROOT CAUSE of archived accuracyIndex=0.51875 CORRECTS the plan's own
  context: it is not an ordering-bridge mismatch. The archived
  OutputsPredictiveIndex.csv (@406a010, Status Sat 22 Nov 2025) is an all-zero
  matrix; agreement = baseline zero-cell fraction 1−4928/10240 = 0.51875 EXACTLY.
  Fresh-executed bridge falsification: Φ-omitted and Φ-doubled paths both give
  accuracy 0.6/4096 mismatches — no scramble reproduces the figure. Mechanism:
  superseded script revision with a silently dead Index path, preserved by F35
  orphaning + exit-code-only runner. Evidence: tools/T41_RootCauseProbe.wl,
  tools/t41_archived_artifact_diff.py, rootcause/*.json (`12e481b`). Lesson
  appended to ORDERING.md §6: accuracies must ship confusion counts/per-node
  symmetric differences so degenerate all-zero agreement is visible.
  (2) GOVERNANCE/ORDERING.md established: LSB-canonical representation,
  Φ-exactly-once at interop boundaries, public-function contract table,
  BioExperiments migration path documented (§7, execution deferred), spot-check
  grep audit list embedded (all expectations verified).
  (3) F36 CLOSED: canalisingIndex is Ic-relative everywhere;
  Gates.m IndexSetNetwork CANALISING branch fixed (was reorder-and-pass-through,
  correct only for ci=Ic[[1]]); pinned elementwise by new
  TSK-GATES-014-CanalisingCoordTests.m (40 cases incl. ci∉first, all three paths
  equal). Non-globbed helpers Comparison.m/OnPossibleBehaviour.m keep absolute
  reading as DOCUMENTED EXCEPTIONS pending their own coverage.
  (4) F24 CLOSED: stale-resOp guards ×6 legacy dispatch loops
  (Failure["UnsupportedGate"] + message); negative-control probe green;
  positive controls cross-checked against packaged dispatch with programmatically
  derived references after TWO hand-built references were themselves wrong
  (U8 lesson reconfirmed: never hand-compute reference constants).
  (5) COLLATERAL DISCOVERY: TSK-MIXED-002 was a pre-guard FALSE GREEN — it
  validated legacy createRepertoires-vs-runDynamic consistency on networks with
  NOR/XNOR nodes where BOTH sides were identically stale; guard made Failure
  metadata differ → symbolic inequality also broke its Status.txt export
  (unevaluated If exported as verdict, ARCH-004 defect class). Fixed in
  experiments/mixed/Mixed.m: cell-level MapThread(…,{2}), Failure-pairs counted
  consistent-by-construction, UnsupportedGateCells=8 disclosed in Metrics.json.
  Published mixed001 figures invariant. Suite delta exactly +1 intended test.

- `[T4.2]` **T4.2 EXECUTED 2026-08-25 — bio-arm reframing per V4 stamp.** Living
  claims reframed to "round-trip exactness certificate" with explicit scope
  (parser + forward model + inverter consistency, guaranteed modulo bugs; n≤16)
  and V4 evidence pointer: index-deconvolution/README.md experiments table row +
  snapshot bullet. REGULATORY 8/8 now carries the V4-confirmed training-on-test
  caveat (gate defined from the fission-yeast clause, counted on those same
  networks). Papers carry no bio-recovery claim (grepped). Bitácora 05 line 117
  ("recovers real gene-regulatory networks exactly") left byte-identical per U5.
  **BACKLOG PROMOTED:** trajectory-route validation experiment on n>16 models
  (observe state trajectories, deconvolve from data instead of self-repertoire)
  — routed to the successor plan's intake list, not executed under this plan.
- `[T4.3]` **T4.3 EXECUTED 2026-08-25 — identifiability envelope measured.**
  Protocol frozen pre-run (`4c848da`); three deviations logged before adoption
  (D1 string-form rng seed; D2 target-level binning; D3 coverage redefined as
  min-over-ALL-cells after the discarded first run DIAGNOSED the interior-cell
  blind spot: cells at 0.75–0.88 coverage default unobserved LUT entries to 0 →
  globally wrong yet trajectory-exact). Final run: all 12 exp03 rules saturating
  at 20/20 seeds when every cell has seen all 8 neighbourhoods; class-dependent
  degradation below. Determinism control: second execution byte-equivalent.
  Paper sentence drafted in experiments/ca_coverage/PAPER_SENTENCE.md. The
  first-run artifacts were superseded and never cited (U5/U8 respected).

- `[T4.4]` **T4.4 EXECUTED 2026-08-25 — NULLS.md live.** Rule + both case
  studies (anchors: imp-prices FINDINGS:210/:220 + bitacora/07 §1; sibling
  bitacora 03:316, 05:62, 06:77) + checklist template. AC-4.4b's sibling
  Phase-2-TODO pointer is a PENDING SIBLING EDIT requiring its own U6 approval —
  recorded here so it is not silently dropped in close-out.

- `[T4.5]` **T4.5 EXECUTED 2026-08-25 — one wrapper, four named quantities.**
  Nonidentity re-established by FRESH EXECUTION on a shared toy network (four
  distinct values) rather than by quoting V5's scratch numbers; V5's stamped
  single-node values reproduced ELEMENTWISE by the committed parity test.
  Header asymmetry pinned at exactly log₂(4)=2 bits on the toy. WL side pinned
  via t45_biometrics_toy.m. Subproject mirrors remain frozen exceptions pending
  their own venvs' migration tasks.

- `[T4.7]` **T4.7 EXECUTED 2026-08-25 — overclaim converted into a real result;
  one new engine defect found and fixed en route.**
  **DEV-T4.7-1:** ApplyGate's KOFN branch dropped `params["strict"]`
  (myKOfN had no params argument) while IndexSet/IndexSetAnalytic honored it —
  the exact three-site drift class T1.3 fixed for MAJORITY ties. Found because
  ALGO-004 draws strict=True at random; node-level COMPLETE comparison
  localized it to popcount-1..k patterns elementwise. Fix: myKOfN[.,k,params]
  with default strict=False (zero historical behaviour change); GATES-013's
  KOFN grid repaired (Scan level-spec had fed sublists as #1, never truly
  exercising strict=True — the hole that hid this for months).
  Harness lessons recorded in-code: Module init-list entries evaluate before
  earlier locals bind (ConstantArray[0,2^d] stayed symbolic); Flatten dissolves
  row vectors; lsbBits is integer-only. The audit's final run: 0 mismatches,
  node-complete + 4080 rows.
  Paper: both manuscripts' validation claims rescoped to what the artifacts
  show; snapshot rebaseline verified token-exact before commit.

- `[T5.1]` **T5.1 EXECUTED 2026-08-25 — regenerate-and-diff live.** Generic
  marker-based verifier + inventory; producers genuinely re-executed by the
  gate (mixed001 kernel run, complexity_analysis, ALGO-004). Session lesson
  recorded: an uncommitted-file `git checkout` during control setup wiped
  marker edits once — controls must run against COMMITTED state only (done).
- `[T5.2]` **T5.2 EXECUTED 2026-08-25 — D-6 CLOSED interactively.** Author chose
  full coverage: "consider the whole set of gates... all of them, not only 10."
  Witnesses are EXECUTED artifacts (not prose): 250 elementwise cases across 12
  families × arities ≤6, zero failures. En-route finding: implication-family
  `pair`/NOT `i` params are absolute-coordinate while canalisingIndex is
  Ic-relative — both now pinned with named authority in ORDERING.md §4b;
  witness ground truth follows the established vectorPredict semantics.
- `[T5.3/T5.4]` **EXECUTED 2026-08-25.** T5.3: eight level READMEs (11–18)
  added — purpose + qualitative verdict + bitácora/experiment pointers; no
  numbers quoted (single source stays the pinned artifacts). T5.4: full-sweep
  ledger lint executed report-first; 95 decimals across 27 rows queued for
  author adjudication via the T2.1 addendum protocol; known harvest limits
  documented (prose-only stats per DEV-2.2, notebook-executed numbers).
# APPENDIX E — EXECUTION STATUS LOG (living; one line per task, newest wave first) (living; one line per task, newest wave first)

Legend: ✅ DONE (commit ref) · 🔶 PARTIAL · ⏳ PENDING · 🚫 BLOCKED (reason) · ➖ NOT STARTED

| Task | Status | Evidence / commit |
|---|---|---|
| T0.3 checkpoint | ✅ DONE | `406a010` commit-all WIP; tree clean after |
| T0.1a parser wiring | ✅ DONE | `2b414aa` + resolver fix `ad97eb8`; planted-FAIL control exit=1 naming test; NOT/AND slices green end-to-end |
| T0.2 baseline v1 | ✅ DONE | `2fc2b7b`; **OK=77 FAIL=10** (6 unique root-caused); F35 discovered: FormulaVsExhaustive orphaned from `*Tests.m` glob — never executed by `--all` |
| T0.5 paper-number snapshot | ✅ DONE | `6cb0f58`; 112 entries / 14 table blocks; deterministic `--check` gate PASS |
| T0.1b discovery + baseline v2 | ⏳ PENDING | after Wave-1 core, per DAG |
| T0.4 branch/tag | ➖ NOT STARTED | gated on Waves 1–2 |
| T1.2 package engine | ✅ DONE | `d8d3809`; IndexSetAnalytic packaged (12 families incl. closed CANALISING); {} fallthrough dead via Phi transport; 3 copies deduped; OneSetAllFamilies+NIMPLIES+MAJORITY tests OK; suite +6 OK / FAIL set identical |
| T1.1 flagship script | ✅ DONE (D-2(d)) | `d42f371`; COMPOSITION LEMMA VERIFIED n=6: symDiff ∅ between composed-set (XOR{x1}⊕XOR{x3}⊕AND{x2,4}) and exhaustive LUT; banner→real exit-gate (10 checks listed); F35 fixed by rename→glob, theorem-paths criterion OK |
| T1.3 MAJORITY | ✅ DONE (D-3 adopted) | `e87927e`; tiePolicy param both policies tested; PROBE: node10 d=4 has ties but output-neutral verified (0.66875/3392 unchanged) |
| T1.4 governance | ✅ DONE | `316ce22`; GLOSSARY in-repo w/ provenance + 3-state sync (controls 0/1/2 all shown); 6 citations repointed → 0 dangling; CLAUDE.md D-4 + branch + BASELINE; 21 technical-sense pivots fixed across backbone+derivations; inventory frozen @0 |
| T1.5 interim disclosure | ✅ DONE | `bd6a365`; tab:four-paths row+caption disclose archived 0.51875 vs current 1.0, T4.1 open; snapshot delta audited post-hoc: 1 semantic block + pure line-shifts |
| V1–V5 stamps | ✅ DONE | `dae59a3`; all five VERIFIED with evidence |
| T0.1b discovery + baseline v2 | ✅ DONE | `2d89313` (see INCIDENT entry) — genuine ledger OK=46 FAIL=4 @167s |
| T2.0 imp-prices hygiene | ✅ DONE | `470682a`; parity gate caught real drift first-run; 97 passed own-venv / 35+4skipped root-venv |
| T2.1 C18 reconciliation | ✅ DONE (DEV-2.1) | `8c6f6e2`; prose-vs-pin confirmed (6/{WTI_Spot}/37.5 vs printed 5/{WTI_CL}/55); 45-seed recheck: hash-unstable statistic, pin = genuine draw (seed 19 elementwise); quote-the-pin correction + dated notes both docs; lint PASS + 3 planted-mismatch controls exit 1 |
| T2.2 C29/C36 machinery | ✅ DONE (DEV-2.2) | `6bbc9fb`; C36 reproduces exactly (1.26±1.12, two 7-windows/0.031%, one negative-print pivot; off-by-one + raw-series-sequence disclosed); C29 conclusion robust (share 66–72%, z≈3σ) but exact moments unrecoverable → committed pinned nulls as single source; C26 pre-guard caveat appended |
| T2.3 causalNet fixes | ✅ DONE | `e348d68`; 5 result JSONs exported by committed command; README tally 6→7 (machine-counted), −0.78→−0.770, 99.8%→executed on-figure numbers (98.8%/96.7%; 99.8% = orphaned synthetic figure), 37→43 columns, tests 25→47; CTM table vendored @pinned commit (parity test now runs: 65,536/65,536); decoy renamed zenil_algorithms.py + collision probe clean; suite 47/47 green; notebook re-executed 0 errors, numbers reproduce elementwise |
| T2.5 pathinfo counts | ✅ DONE | `49333bb`; audit confirmed elementwise (ledger truth: 623/648 runs, 207+1 of 216 cells, all gaps = graphormer/Lipophilicity only — README's per-model gaps were wrong); scripts/campaign_status.py = single source, block quoted verbatim ×3 docs (grep-verified); test count unified to collected 41; 200-molecule cap disclosed beside every atom claim (24,880 atoms) |
| T2.6 idx-deconv docs | ✅ DONE | `005dcc1`; README method section rewritten per GLOSSARY §1c (two decompositions, decimal anchor/sumandos encodings, lossless Dec(L,S); old dichotomy phrasing greps clean); bitacora inventory 00–31 (32 files); status refreshed (pytest 146/146; BASELINE v2 reference; levels 11–18 → T5.3) with historical snapshot labelled; TRANSFERENCE dated append-only addendum (+33/−0) recording #3 chain b21→b22→GLOSSARY amendment |
| T2.4 causal-paper arc | ✅ DONE (D-5(i) + D-7 approved) | headers `70068fd`+`3eb87ac`; DoF paragraph adjacent to canonical sign-agreement table (`3eb87ac`); comparison `bc3935e`: **10/10 ECA rules exact** elementwise (0/225,280 cells mismatched per-rule set; seeds pinned, no outcome-dependent tuning), Th17+E.coli EXCLUDED-WITH-REASON (no ground truth without inventing gates — recorded as finding); D-5(i) live: results un-ignored selectively, MANIFEST.sha256 + verify_manifest.py PASS, reruns byte-identical |
| T2.7 sibling addendum | ✅ DONE (U6 granted) | sibling series-deconvolution @main, LOCAL commits `62fb3b3` (§9.6 corrections: divergence entry false → unrelated arXiv module; banner+hmmlearn fixed upstream) & `b868cd0` (GLOSSARY precision note: three-step chain) — append-only, NOT pushed to remote; CausalBool GOVERNANCE/GLOSSARY.md resynced @b868cd0 (`3e23d0c`), check_glossary_sync.sh exit 0 |
| T5.5 post-fix sweep | ✅ DONE (v1.3) | `9b8c655`+`4d9701f`; all inventory rows closed: imp-causal-paper walkthrough re-executed (numbers identical; root-venv provenance drift recorded), 15/15 idx-deconv notebooks green, 0-byte stray removed, pathinfo regeneration identical, N5 no-action verified, D2 retracted as my misread (exp04 re-run: 8/8 exact reproduced); paper gate PASS |
| T4.1 ordering unification | ✅ DONE | root cause `12e481b`: archived 0.51875 = ALL-ZERO dead-path artifact (= baseline zero-fraction 5312/10240 exactly; Φ-omitted/doubled bridges give 0.6, i.e. NO scramble reproduces it — plan-context suspicion corrected); ORDERING.md live (LSB canonical, Φ-exactly-once, public-contract table, BioExperiments migration path §7); F36 CLOSED Ic-relative (IndexSetNetwork branch fixed, 40-case elementwise pinning test GATES-014 OK); F24 guards ×6 legacy sites (negative-control probe exit-gated; positive controls vs packaged dispatch programmatically derived); MIXED-002 pre-guard FALSE-GREEN exposed & fixed (identical stale corruption had counted as agreement; now Failure-pairs consistent-by-construction + UnsupportedGateCells disclosed = 8); mixed001 published figures invariant (0.66875/3392/1.0×3); suite bracket-after **OK=47 FAIL=4 TOTAL=51** (+1 intended GATES-014; owned reds unchanged) |
| T4.2 bio-arm reframing | ✅ DONE | README living claims → round-trip-certificate framing + n≤16 scope + V4 pointer + REGULATORY training-on-test caveat; papers grepped clean; bitácora 05 untouched (U5); n>16 trajectory-validation backlog promoted (Appendix D) |
| T4.3 CA coverage sweep | ✅ DONE | protocol frozen `4c848da` (D1 `296e48e`, D2/D3 pre-adoption `65b0287`); EXECUTED: 12 rules × 20 seeds × levels k∈{4..8}/8, min-over-CELLS coverage; **all 12 saturating: 20/20 global-map exact at k=8**; below-full-coverage degradation is rule-class-dependent (170/204 from k=4; 90/250 ~k=6–7; 30/45/57 near 8; 110/232/150/73 only at 8; 254 needs full); deterministic rerun byte-equivalent; figure committed; PAPER_SENTENCE.md drafted (AC-4.3a–c) |
| T4.4 NULLS rule | ✅ DONE | GOVERNANCE/NULLS.md `6e84464`: response-profile/held-fixed/destroyed-dimension rule + both case studies bitácora-traceable (C22→C29 density; B1 codeword syntax) + pre-registration checklist template; sibling Phase-2 TODO pointer PENDING its own U6 gate |
| T4.5 description-length consolidation | ✅ DONE | GOVERNANCE/DESCRIPTION_LENGTHS.md `5f48c24`: variants A–D named/scoped/mapped; shared wrapper src/description_lengths.py (pybdm==0.1.0 pinned, bdm_2d below_floor knob preserves pathinfo None-semantics per-consumer); toy fixture EXECUTED (A=20.8974/B=27.9248/C=6.3399/D=25.9248 — four distinct values = nonidentity by execution; header delta exactly 2=log₂4); parity test PASS incl. V5 stamps reproduced elementwise (7.1699…/6.3399…); subproject mirrors documented exceptions (AC-4.5a/b) |
| T5.1 regenerate-and-diff | ✅ DONE | harness `baed4ad` + control `baed4ad`-successor: Makefile verify-paper → tools/verify_paper_artefacts.py; inventory 3 COVERED (four_paths_table incl. mandatory 0.51875 disclosure; mechanism_vs_dataset D=135.66/C=23; comp_validation_summary ALGO-004 all-zero+1020rows) + 5 PENDING-with-reasons (T5.1.v2); markers embedded both manuscripts; AC-5.1a control: planted digit change → FAIL naming ID, revert → green; AC-5.1b closed visibly via T4.1 wording; snapshot gate PASS |
| T5.2 derivations | ✅ DONE (D-6 CLOSED) | author directive: ALL TWELVE; `t52_family_witnesses.wl` executed → verification/*.json (250 cases, 0 failures, arities 2–6); ten derivation docs generated w/ embedded witnesses + README index; :1936 sentence matches reality; pair/i-vs-canalisingIndex coordinate conventions pinned in ORDERING.md §4b; gates PASS |
| T4.7 validation-map repair | ✅ DONE (option i) | `cf31b20`: NEW closed-form-set audit ALGO-004 — node-COMPLETE pattern comparison + 4080 stratified rows, n∈{16,20}, all 12 families, **0 mismatches**; **DEV-T4.7-1**: ApplyGate KOFN silently dropped `strict` (diverged from analytic exactly when strict=True) → myKOfN now honors params (default False = historical), GATES-013's Scan level-spec hole repaired (Tuples); both manuscripts rescoped: theorem evidence = closed-form-set audit n∈{16,20}, n∈{20,50} explicitly dispatch-only/no-theorem-weight (AC-4.7b grep clean); snapshot rebaselined after token-delta verification (109 entries, gate PASS); suite OK=47 FAIL=4 TOTAL=51 |

## Execution findings ledger (new defects/discoveries during implementation)

- `[T0.1a]` arch4 + MIXED-002-Dispatch export **unevaluated WL expressions** as verdicts
  (`If[…]` strings) — a defect class the old runner could never see. Recorded in
  BASELINE.md; owners UNOWNED.
- `[T0.2]` **F35:** flagship `TSK-MIXED-001-FormulaVsExhaustive.m` does not match the
  runner's `*Tests.m` glob ⇒ the suite's most important failing test never runs under
  `--all`. To be fixed in T1.1 alongside the script repair.
- `[T0.2]` Three genuine reds silent since Feb 2026 (KOFN-network, IMPLIES-network,
  TEST-002-property) — the exit-code runner hid them for ~7 months.

## Execution findings ledger (new defects/discoveries during implementation) — cont.

- `[branching]` 2026-08-23: all restart-point work pushed to **`fixing`** (`c5c08ca`,
  tracks origin/fixing). Local `clean` intentionally left ahead-but-unpushed so its
  remote remains the pristine pre-fix reference for review diffs. Progressive merge
  to `main` deferred until the full fix programme passes its own acceptance gates
  (T0.4 policy unchanged).

## VERIFICATION STAMPS (Part F) — 2026-08-24

- **V1 — VERIFIED (with sharpening).** (i) `SESSION_HANDOFF.md` ("Full Reproduction
  Complete", all ✓, ρ=+1.0 EXACT all 10 rules) vs latest `imp-results.md` ("partial,
  reduced, qualitative shadow… not a full reproduction") — direct contradiction; latest
  wins. (ii) Persisted `results/ca/summary.json`: `inferred_rule=222` vs `rule=254` — at
  least one artifact contradicts the blanket EXACT claim. (iii) SHARPENED: imp-results.md
  :69/:71 contain **false existence claims** — `scripts/run_ecoli_perturbation.py`,
  `scripts/run_cellnet_complexity.py`, `data/processed/ecoli/*` (RegulonDB 14.5 metadata)
  and `data/processed/cellnet_16ct/*.csv` all exist on disk. The newest audit document is
  itself factually wrong about the tree it audits.
- **V2 — VERIFIED.** bitacora/21 titles Result A "the cost-threshold theorem (the
  headline, and it is exact)" and ":144 closes the flagship"; bare "identity" only for
  θ=c (:163). bitacora/22 re-RATES (containment ~1.0 on stocks/GBM/noise ⇒ "true but
  geometry"), does not retract the mathematics; GLOSSARY #3 later amends 22's demotion.
  Three-step history confirmed; sibling one-line summaries compress it. Decoy module:
  `imp-causalNet-paper/.../deconvolution.py` header = "Algorithms 1 and 2 of
  arXiv:1802.09904v8" + networkx/numpy ⇒ unrelated algorithm, same filename; sibling §9.6
  entry false as stated (collision is the real hazard; resolved for that repo by T2.3).
- **V3 — VERIFIED.** Ledger :793 states paper used ~9.x (2018), RegulonDB 14.5 adopted as
  best-available proxy, network grown ⇒ exact comparison impossible by construction;
  artifact JSON carries version=14.5, downloaded 2026-07-03.
- **V4 — VERIFIED.** Ground truth chain: `bnet.py` parses .bnet → columns evaluated
  exhaustively to LSB-first LUTs; `causalbool.repertoire()` builds the 2^n×n matrix;
  `deconvolve()` validates len==2^n and inverts THAT matrix ⇒ round-trip certificate,
  exactness guaranteed modulo bugs. n≤16 cap explicit (grieco 54, remy 35 excluded).
  REGULATORY was defined from the fission yeast clause and counted on fission yeast ⇒
  mild training-on-test flavor CONFIRMED. Audit §3.1 framing stands.
- **V5 — VERIFIED.** Four cost models are structurally distinct; on a shared toy node
  (n=4, d=2, AND): row-run model **6.9658** bits, pathinfo/BioMetrics-family
  **7.1699** bits, measure.model_description_length **6.3399** bits. Additionally
  BioMetrics.encodeNodeCost ≡ pathinfo.node_description_cost in structure, but
  graph_description_length adds a log2(n) header BioMetrics' D lacks ⇒ cross-repo "D"
  is not one quantity. Gate for T4.5 open.

- `[T0.1b/T0.2]` **INCIDENT (datasaurus class, caught by U1/U7):** the T0.1a watchdog line
  `perl -e 'alarm $ARGV[0]; exec @ARGV'` silently no-ops the exec on this platform
  (rc=0, kernel never starts). Every runner-based "suite run" from T0.1a until the fix
  classified stale Status.txt artifacts, not fresh executions; BASELINE v1's rollup is
  therefore superseded by method error. Caught via a wall-clock impossibility (1 s for
  50 kernels) during T0.1b. Fixed idiom: `alarm shift @ARGV; exec @ARGV or die`.
  **BASELINE v2 (fresh, verified-executing, wall=167 s) is the first genuine ledger:
  OK=46 FAIL=4 TOTAL=50** — two v1 "failures" were stale-artifact ghosts that pass when
  actually run (MIXED-002-Dispatch, TEST-002-Property); four genuine reds remain
  (Topologies dead-export, KOFN-network, IMPLIES-network, ARCH-004 unevaluated export).
  All direct-kernel evidence elsewhere in this log (new tests, flagship runs,
  composition lemma) was produced by real executions and stands unaffected.

---

# APPENDIX F — SESSION HANDOFF FOR THE NEXT INSTANCE (2026-08-24)

> **SUPERSEDED 2026-08-24 by APPENDIX G** (post-T0.4 state). Kept for
> provenance; environment facts in F.3 remain valid and are restated in G.

You are a fresh agent continuing AUDIT_FIXING_PLAN_01. Read this appendix FIRST, then
Part B (conventions U1–U8), then Appendix E (status). You need no prior conversation
history: everything below is sufficient.

## F.1 Where things stand

- **Branch:** `fixing` (tracks `origin/fixing`). Work ONLY here; commit per task with
  `[AUDIT01/<task-id>]`; PUSH after every completed task. Local `clean` is deliberately
  unpushed (pristine pre-fix reference). `main` untouched until T0.4.
- **Restart point COMPLETE:** T0.1a, T0.1b(+incident), T0.2(v2), T0.3, T0.5, T1.1–T1.5,
  V1–V5, T2.0 — all DONE with commit refs in Appendix E.
- **Genuine suite ledger:** `tests/MUnit/BASELINE.md` v2 = OK=46 FAIL=4 TOTAL=50
  (@167 s wall-clock). The 4 owned reds: TopologiesTests (dead export),
  KOFNNetworkTests, IMPLIESNetworkTests (silent-since-Feb reds), TSK-ARCH-004
  (exports unevaluated code as verdict).

## F.2 Remaining queue (in this order)

1. **T2.1** C18 reconciliation — re-run `imp-prices/scripts/phase1_b4_description_length.py`
   hill-climb block; reconcile prose (`FINDINGS.md:164`, bitácora 04) against
   `results/b4_description_length.json`; dated addendum; ledger lint script.
   ACs: AC-2.1a–c.
2. **T2.2** C29/C36 — write+run `experiments/c29_density_matched_null.py` and
   `experiments/c36_window_distribution.py` (density-matched random matrices @17/23
   edges; pybdm; pinned seeds); verify prose numbers reproduce; date-caveat pre-guard
   daily cells in FINDINGS C26. ACs: AC-2.2a–c.
3. **T2.3** causalNet — export notebook results to committed JSONs; fix README tally
   6→7, −0.78→−0.770, 99.8%→96.7%-on-figure; rename decoy module
   `src/imp_causalnet_paper/deconvolution.py` → `zenil_algorithms.py` (+ imports).
   ACs: AC-2.3a–c.
4. **T2.5** pathinfo — `scripts/campaign_status.py` deriving from ledgers; replace
   status blocks in README/FINDINGS/NEXT_PHASES verbatim; single test-count;
   subsample-cap disclosure. ACs: AC-2.5a–c.
5. **T2.6** index-deconvolution README pivots/sumandos category-error rewrite +
   TRANSFERENCE dated addendum + inventory refresh. ACs: AC-2.6a–c.
6. **STOP — AUTHOR GATES.** T2.4: draft supersession headers + index-method-comparison
   pre-registration, then HALT for D-5/D-7 approval. T2.7: sibling edit needs explicit
   author permission (U6). Do not improvise past these.

## F.3 Environment facts (all verified by execution)

- WolframKernel fixed path `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`.
- Suite: `zsh tests/MUnit/run-tests.sh` (~3 min genuine; ~50 tests). Judge health ONLY
  vs `tests/MUnit/BASELINE.md` v2. New failures block; pre-existing 4 reds stay.
- Paper gate: `python3 tools/snapshot_paper_numbers.py --check` must PASS before ANY
  commit touching `.tex`. If numbers legitimately moved, run snapshot (rebaseline) AND
  list changed IDs explicitly in the commit message. Post-hoc delta reconstruction from
  git is the recovery protocol if you forget (see T1.5 slip in Appendix E).
- GLOSSARY sync: `tools/check_glossary_sync.sh` → exit 0 clean / 1 drift / 2 sibling-absent.
- imp-prices uses ITS OWN venv: `cd imp-prices && .venv/bin/python -m pytest`
  (97 passed). Root venv has NO hmmlearn BY DESIGN: `pytest imp-prices/tests`
  there yields 35 passed / 4 loud skips. pytest summary line can hide under `-q`;
  trust exit code + `grep -E "passed,"`.
- **Vendor two-copies rule:** editing `index-deconvolution/src/causalbool.py` or
  `deconvolution.py` REQUIRES mirroring into `imp-prices/vendor/` in the same commit,
  else `tests/test_vendor_parity.py` fails (it already caught one real drift).
- Python gotcha recorded: `perl -e 'alarm $ARGV[0]; exec @ARGV'` silently no-ops exec;
  correct idiom is `alarm shift @ARGV; exec @ARGV or die ...` (Incident, Appendix E).
- WL test-writing gotchas: pure-function pairing `Function[{a,b}] & /@ pairs` breaks
  silently — use `Function[pair, …] & /@ pairs` and unpack; scripts need
  `AppendTo[$Path, "src/Packages"]` BEFORE Needs; test filenames MUST end `Tests.m` to
  enter the runner glob; exports follow `base = FileNameJoin[{"results","tests",…}]`.
- Conventions inside WL core: LSB-canonical internally; MSB only via Phi transport;
  MAJORITY tiePolicy ("strict" default); CANALISING coordinate schism (F36) is OPEN —
  do not "fix" silently; belongs to T4.1.
- Definitions authority: `GOVERNANCE/GLOSSARY.md` outranks every document including
  papers. Historical bitácoras/pre-registrations: never retro-edit; dated addenda only.

## F.4 Standing rules recap (full text Part B)

Evidence re-statement before acting (U1); binary acceptance criteria (U2); baselines
first (U3); decisions marked AUTHOR-DECISION pause their thread (U4/U6); protected
history (U5); suite/paper-gate bracketing with recorded deltas (U7); elementwise
symmetric-difference reporting, never counts alone (U8).

---

# APPENDIX G — SESSION HANDOFF FOR THE NEXT INSTANCE (2026-08-24, post-T0.4)

Read this appendix FIRST, then Part B (U1–U8), then the task cards you will
execute (Part G for Wave 3, Part H for Wave 4), then Appendix E (statuses).
You need no prior conversation history.

## G.1 Where things stand

- **Branches:** work on `fixing` (push per task). `main` = published remediation
  baseline, synced via merge; **tag `audit01-baseline` @ 366d771**. Local branch
  `clean` = pristine pre-fix reference — NEVER touch. T0.4 DONE: main
  reconciled at 366d771 over clean parents (fff5750 + 0cb3646); superseded
  local lineage a081ff6/ceab8db/3f9bd13 carried ~28 GiB gitignored legacy data
  and was never published (see Appendix D T0.4 entry). Those data dirs
  (`data/DepMap/**`, `data/cancer/patients_mapk_large/**`, `data/gnomAD/**`)
  stay OUT of any published tree.
- **COMPLETE:** Wave 0 (instrument + BASELINE v2), Wave 1 (T1.1–T1.5), V1–V5,
  Wave 2 (T2.0–T2.3, T2.5, T2.6, T2.4 with approved D-5/D-7, T2.7 sibling
  local commits 62fb3b3/b868cd0 unpushed-by-design), sweep T5.5, T0.4.
- **REMAINING QUEUE (exact order):**
  1. **T4.1** ordering root-cause formal closure (F37: archived 0.51875 was a
     stale artifact; current index path measures 1.0 — archaeology + ORDERING.md)
  2. **T4.2** bio-arm reframing per V4 stamp
  3. **T4.3** CA coverage-sweep experiment (pre-registered)
  4. **T4.4** GOVERNANCE/NULLS.md
  5. **T4.5** description-length consolidation (V5 tabulation on record)
  6. **T4.6** offset-notation disambiguation
  7. **T4.7** validation-map honesty repair (recommend option (i))
  8. **T5.1** regenerate-and-diff harness (`make verify-paper`)
  9. **T5.2** derivations/scoping — **HALT: D-6 is an open AUTHOR decision**
  10. **T5.3** levels 11–18 READMEs · **T5.4** full ledger lint
  11. Close-out → board ROADMAP_R4_SEGMENTED_GRAMMAR.md (see its "Boarding
      sequence"; draft pre-registration, HALT for sign-off; R4 execution opens
      the successor plan).

## G.2 Environment facts (verified)

- WolframKernel: `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`.
- WL suite: `zsh tests/MUnit/run-tests.sh` (~3 min); judge ONLY vs
  `tests/MUnit/BASELINE.md` v2 (**OK=46 FAIL=4 TOTAL=50**, owned reds:
  TopologiesTests, KOFNNetworkTests, IMPLIESNetworkTests, TSK-ARCH-004).
- Paper gate before ANY `.tex` commit: `python3 tools/snapshot_paper_numbers.py --check`.
- GLOSSARY sync: `bash tools/check_glossary_sync.sh` → 0 clean / 1 drift / 2 absent.
- imp-prices own venv `.venv/bin/python -m pytest` = 97 passed; root venv has NO
  hmmlearn by design (35 passed / 4 loud skips).
- pathinfo venv 41 passed · causalNet venv 47 passed incl. vendored CTM parity ·
  idx-deconvolution pytest 146/146 · exp04 re-run 8/8 exact.
- Vendor two-copies rule: editing `index-deconvolution/src/{causalbool,
  deconvolution}.py` ⇒ mirror into `imp-prices/vendor/` same commit.
- pgmpy structural claims must fix AND record `PYTHONHASHSEED`
  (DEV-2.1 lesson; see imp-prices/results/recheck_c18/).
- Pushes can be slow (repo carries GiB-scale packs); use nohup+log if needed.
- Never publish: `data/DepMap/**`, `data/cancer/patients_mapk_large/**`,
  `data/gnomAD/**` (merge message 366d771 documents the policy).

## G.3 Conventions recap

Commit prefix `[AUDIT01/<task-id>]`, push after each task, Appendix E row per
task, dated deviations to Appendix D, U1–U8 in force, protected history
(addenda only), AUTHOR-DECISION items halt their thread (D-6 at T5.2).

## G.4 Kickoff prompt (paste verbatim in the new session)

Continue AUDIT_FIXING_PLAN_01 from APPENDIX G (post-T0.4 handoff) in this file.
Read Appendix G first, then Part B conventions, then the Part G task cards for
Wave 3. Work on branch `fixing`, one commit per task prefixed [AUDIT01/<task-id>],
pushing after each task and updating Appendix E as you go. Execute the remaining
queue exactly in G.1 order: T4.1 → T4.7, then T5.1 → T5.4. Halt only at T5.2's
D-6 author decision and at anything that trips U1/U4. Judge suite health only
against tests/MUnit/BASELINE.md v2 and run both gates (paper numbers, glossary
sync) before touching .tex or governance files. Do NOT execute or draft anything
under ROADMAP_R4_SEGMENTED_GRAMMAR.md until Waves 3–4 are closed and logged.
