# METHOD_ACCOUNT — the method in my own words, for the author to falsify

**AUDIT03/R0.2. Written 2026-09-03 after reading the primary sources, not the code.**

## How to read this, and how to reject it

This is the **R0.3 gate**. Its purpose is to be checked quickly and rejected
cheaply, so it is written as **numbered claims, one per line, each with a source
citation** rather than as a narrative. A narrative is pleasant to read and hard to
falsify, which is the wrong trade here.

**To reject a claim, name its number.** Anything you do not strike, I will treat
as confirmed, and `R2b`, `R3` and `R4` will be built on it.

**Why this document exists.** Three defects were found in this audit, and all
three were found by an author question, never by my own triage: the bio
description length was not a description length; I reached for Shannon entropy
inside an algorithmic accounting; and I asserted that Ω is the disconnected
coordinates. All three share one signature — **I read an implementation and
inferred a definition.** Every claim below therefore cites a *document*, and where
it cites code it says so explicitly.

Sources read: `derivations/01`, `02_cb_and`, `02_cb_or`, `03`–`12`;
`method_paper.tex`; `comp_paper.tex`; `doc/Tesis-UNAM/Capitulo4/resultados_y_analisis.tex`;
`GOVERNANCE/GLOSSARY.md`.

---

## §1 What the object is

**1.1** A Boolean network is a connectivity matrix `cm ∈ {0,1}^{n×n}` with
`cm[i][j] = 1` meaning **node j feeds node i**, plus a list of local gate labels.
`method_paper.tex:158`

**1.2** Node `i` has connected-input set `N_i = {j : cm[i][j] = 1}` and a local map
`g_i : {0,1}^{|N_i|} → {0,1}`. `method_paper.tex:164`

**1.3** The update is **synchronous and one-step**:
`F(x) = (g_1(x_{N_1}), …, g_n(x_{N_n}))`. `method_paper.tex:172`

**1.4** The **ordered exhaustive repertoire** is `{0,1}^n` *together with a declared
enumeration* of all `2^n` vectors; `U = {1,…,2^n}` is the index universe. The
enumeration is part of the object, not a presentation detail. `method_paper.tex:175`

**1.5** The method assumes the mechanism is **given**. It is a causal-*expression*
calculus, not a causal-*discovery* one. `method_paper.tex:141`

**1.6** "Causal" is used in the **mechanistic/generative** sense, not Pearl's
interventionist sense. No do-calculus, no confounders, no discovery from
observational data. `method_paper.tex:112`

---

## §2 Ordering — every index-set statement is ordering-relative

**2.1** Two orderings are in use. **LSB-first** (the code default):
`v(j) = Reverse(IntegerDigits(j−1, 2, n))`, weights `w(i) = 2^{i−1}`. **MSB-first**
(manuscript style): `v(j) = IntegerDigits(j−1, 2, n)`, weights `w(i) = 2^{n−i}`.
`method_paper.tex:181`

**2.2** `φ(j) = 1 + FromDigits(Reverse(IntegerDigits(j−1, 2, n)), 2)` is an
**involution** on `U`. `method_paper.tex:185`

**2.3** `φ` is load-bearing, not cosmetic: without it one confuses genuine
mathematical differences with encoding differences. `method_paper.tex:193`

**2.4 (theorem)** For *any* gate predicate `g` on any `N`,
`J_g^MSB = φ(J_g^LSB)`. Proof: `e_MSB(φ(j)) = e_LSB(j)`. `method_paper.tex:1460`

**2.5** Therefore exactness is invariant under ordering, and the *numeric* index
sets are not. A quoted index set without its ordering is meaningless.

**2.6** `CANALISING` is the one family where blind φ-transport was **rejected**,
because φ permutes coordinate positions and the canalising coordinate must be
re-expressed after transport. `derivations/12_cb_canalising.tex`

---

## §3 Bands — the algebraic structure the method exploits

**3.1** The structural observation the whole method rests on: **each coordinate of
an ordered exhaustive repertoire forms periodic bands**, and Boolean gates are
exact set operations on those bands. `method_paper.tex:196`

**3.2** `B_i^a = {j ∈ U : v_i(j) = a}` — the band where coordinate `i` takes value
`a`. `method_paper.tex:198`

**3.3** Parity classes `P_{Ic}^{0/1}` and Hamming-weight strata `W_{Ic}^r` are the
other two primitives. Bands capture fixed-bit conditions, parity captures
XOR-like structure, weight strata capture threshold logic. `method_paper.tex:205`

**3.4** Coordinate `k`'s bit alternates with period `2^{k−1}`, which is why the
bands are periodic — the "clocks ticking at different speeds" intuition.
`derivations/01_causalBool_inputs.tex:32`, `:60`

---

## §4 The twelve families — arity-parametric closed forms

**4.1** A **family** is an arity-parametric closed form, not a table entry. The
same expression is instantiated at every in-degree `d`.

**4.2** The one-set of each family, as set operations on bands
(`derivations/03`–`12`, one document each):

| family | one-set |
|---|---|
| AND | `⋂_{i∈Ic} B_i` |
| OR | `⋃_{i∈Ic} B_i` (band union) |
| NAND | `U \ ⋂ B_i` |
| NOR | `⋂_{i∈Ic} B̄_i` |
| XOR | `{r : Σ_{i∈Ic} x_i(r) ≡ 1 mod 2}` |
| XNOR | same with `≡ 0` |
| NOT | `B̄_a`, `a` an **absolute** coordinate |
| IMPLIES | `U \ (B_a ∩ B̄_b)` — fails exactly on `(1,0)` |
| NIMPLIES | `B_a ∩ B̄_b` |
| MAJORITY | `⋃_{|S|≥t} (⋂_{i∈S} B_i ∩ ⋂_{i∈Ic\S} B̄_i)`, `t = ⌊d/2⌋+1` under `strict` |
| KOFN | same with `|S| ≥ k` (`strict`: `> k`) |
| CANALISING | `B_c^v ∪ (B̄_c^v ∩ R)` for `o=1`; `B̄_c^v ∩ R` for `o=0`; `R` = OR over `Ic \ {c}` |

**4.3** `NOT` and `IMPLIES`/`NIMPLIES` take **absolute** coordinates; `CANALISING`
takes an **Ic-relative** index. These conventions differ and both are deliberate.
`derivations/07`, `08`, `12`; `GOVERNANCE/ORDERING.md §4b`

**4.4 (theorem, Canonical Exact Reconstruction)** The analytic predictor
`Y_{j,i} = 1 ⟺ j ∈ J_i` coincides **exactly** with the exhaustive synchronous
baseline. `method_paper.tex:934`

**4.5** The theorem does **not** claim the `2^n` states disappear. It claims the
behaviour is reconstructible from short local formulae without recomputing every
row gate by gate. `method_paper.tex:945`

**4.6** Notice the shape of the threshold and parity forms in **4.2**: each term
`⋂_{i∈S} B_i ∩ ⋂_{i∈Ic\S} B̄_i` **is a schema** over `Ic`. The one-set of every
family is therefore a **union of schemata**, and this is stated as such in
`comp_paper.tex:341`.

---

## §5 Base set, offset family, deconvolution — the part I got wrong

**5.1** `Δ_S(η) = Σ_{t∈S} η_t · w(t)` is the offset **for an arbitrary coordinate
subset `S`**. The formalism is defined with `S` as a free parameter.
`method_paper.tex:219`

**5.2** `P(Ic) = Σ_{i∈Ic} w(i)` is the **decimal anchor** — the *decimal encoding
of the pivot set*, not "the pivots". `method_paper.tex:219`,
`GOVERNANCE/GLOSSARY.md §1a`

**5.3** `Dec(L, S) = {ℓ + s : ℓ∈L, s∈S}` — the **deconvolution operator**. It
unfolds a compressed pair into the full index set. `method_paper.tex:242`

**5.4** The word *deconvolution* is used advisedly: the composite index is the
"convolved" signal and `Dec` recovers the constituent structure. It is
distinguished from a generic Minkowski sum by the causal interpretation of the
two factors. `method_paper.tex:250`

**5.5 (the correction)** **Ω is NOT "the disconnected coordinates."** The sumandos
are the fillings of **a schema's own don't-care positions, wherever they fall,
including on connected inputs.** `GOVERNANCE/GLOSSARY.md §1d`; established
2026-07-09 at `index-deconvolution/bitacora/11_gate_confusion_arity_schemata.md:83`

**5.6** **Rule 110 is the standing witness.** Three inputs, *all connected*. Under
the narrow reading its free set is empty, `Ω = {0}`, no compression, and `L` must
list all five minterms. Correctly, it is three schemata — `01*`, `10*`, `*10` —
every one of whose don't-cares sits on a **connected** input.

**5.7** **Disconnected ⇒ free. Free ⇏ disconnected.** The disconnected coordinates
are free in *every* schema and so are always present in `Ω`; they do not exhaust it.

**5.8 (in the manuscripts' defence, and against my own earlier overclaim)** The
*formalism* is already general — the manuscripts write `Ω(F_q)` and `Δ_S` **with
an explicit argument** (`comp_paper.tex:1067`, `method_paper.tex:1009`). What was
wrong was the **prose**, which collapsed the general object into the one instance
ever used. The correction needed was smaller than I implied on 2026-09-03.

**5.9** The offset family factorises into one independent binary choice per free
coordinate: `Ω = {0,w_1} ⊕ {0,w_2} ⊕ …`. That recursion **is** the self-similarity;
a flat run-length listing destroys it.
`papers/method/code/worked_example_7node/worked_example_7node.py:109`

**5.10** "Fractal" names exactly this: one short rule, self-replicated at every
scale, with the compression ratio growing without bound as the ambient space
grows. Measured — an `OR(d=3)` node covers 14 indices at `n=4` and 3,670,016 at
`n=22`, remaining **three schemata** throughout.
`audit/AUDIT03_R3_description_length/probe_sumandos_two_readings.py`

**5.11** The thesis calls the same thing *"the fractal distribution of the
information"* and ties it to integration: in a strongly integrated system most of
the system's definition is involved in generating answers about itself.
`Capitulo4/resultados_y_analisis.tex:795`

---

## §6 Queries, overlap, and where integration is measured

**6.1** A query is `q = (Q, σ)`: queried nodes and a target output pattern.
`method_paper.tex:984`

**6.2** `C_q = ⋃_{i∈Q} N_i` is the **query support union** — the coordinates that
can affect the query. `F_q = [n] \ C_q` are free *for that query*.
`method_paper.tex:987`

**6.3 (proposition, Overlap-Supported Query Factorisation)** For any exact mixed
query, `J_q = Dec(L_q^{(0)}, Ω(F_q))`, where `L_q^{(0)}` is the satisfying set with
every free coordinate held at zero. `method_paper.tex:994`

**6.4** This proposition is **true and exact**, and it is the *coarse* factorisation:
it factors out only coordinates appearing in **no** queried node's input set. It
is not the definition of Ω. Both **6.3** and **5.5** hold; they are two levels of
one decomposition.

**6.5** `d_q = Σ_{i∈Q}|N_i|` (sum of arities), `c_q = |C_q|` (distinct coordinates),
`μ_q = d_q − c_q` (**overlap multiplicity**), `R_q = 2^{μ_q}` (exact reduction
factor). `comp_paper.tex:1034`

**6.6** For the 10-node benchmark: `d_q=21, c_q=10, μ_q=11, R_q=2048`.
`comp_paper.tex:1048`

**6.7** **Overlap is not a nuisance but the source of the compression.** Repeated
coordinates are not recomputed as new information; they are shared constraints
propagated through several local laws. `method_paper.tex:947`

**6.8** Membership of the free set is **per query, not intrinsic**: it contracts as
more nodes are jointly interrogated, and *that contraction `μ_q` is the measure of
integration*. `comp_paper.tex:390`

**6.9** Schema **order** (number of fixed positions) is exactly `|C_q|`, and the
don't-care count is `n − |C_q|`, whence `|Ω| = 2^{n−|C_q|}`. Scalability governed
by `|C_q|` rather than `n` is therefore a statement about **schema order**.
`comp_paper.tex:352`

**6.10 (the origin)** The thesis states the answers are *"in a format equivalent
to Holland's schemas"*, giving `{{1,*,1,*,1,0,1,*,*}, {1,*,1,*,1,1,1,*,*}}`.
`Capitulo4/resultados_y_analisis.tex:782`

**6.11 (observation, mine — please confirm or reject)** Those two schemata differ
in **exactly one fixed position** (coordinate 6, `0` vs `1`), and coordinate 6 is
*inside* the input set `{1,3,5,6,7}`. By the standard adjacency rule they merge to
`{1,*,1,*,1,*,1,*,*}` — a single schema. **The method's own founding example
already contains an available merge that the implementation does not take.** This
is the gap between §6.3 and §5.5, visible in the origin document.

---

## §7 Description length — the declared language

**7.1** A description length is meaningless until the descriptive language is
fixed, so the language is **declared**. `comp_paper.tex:1214`

**7.2** `D_formula` charges per node: `log2 K` (which gate, `K=12`) + `log2(n+1)`
(in-degree) + `log2 C(n,d)` (which inputs) + a gate-specific parameter field.
`comp_paper.tex:1216`

**7.3** The **in-degree field is not decorative**: without `d` a decoder can
neither know how many bits to read for the input set nor interpret them as an
index into the `d`-subsets. A code lacking it is not uniquely decodable and is
**not a description length at all**. `comp_paper.tex:1235`

**7.4** Confirmed by execution: Kraft sum is exactly **1** with the field and
exactly **n+1** without it, `n=1..8`; 168 and 404 colliding descriptions at `n=3,4`
once it is stripped. `audit/AUDIT03_R3_description_length/FINDING.md`

**7.5** `D_formula` is an **upper bound on the shortest description in one declared
language — never an estimate of K**. The invariance theorem guarantees only an
additive constant, which in applications can be arbitrarily large.
`comp_paper.tex:1250`

**7.6** `C_formula = 23` is a **count of symbolic pieces**, not bits.
`complexity_analysis.py:126`

**7.7 (the stated limitation, and it is decisive for R3)** `D_formula` is a
function of `n`, the in-degrees and the gate types **alone; it never reads an
output bit**. Rewiring node 10 of the benchmark changes 440 of 1024 output rows
and drops distinct output states from 206 to 172 with `D` **bit-identical**.
`method_paper.tex:1904`

**7.8** The paper therefore states plainly that `D` **is not a complexity measure
of behaviour** and cannot rank networks by what they do. `method_paper.tex:1910`

**7.9 (mine, for R3)** `D_schema` — the schema-normal-form length — does read the
output, since it is built from the truth table. It separates an OR from an XOR of
equal in-degree, which `D_formula` cannot, both being one catalogue entry. It is a
legal code: Kraft exactly 1 over the `3^n` template alphabet.
`audit/AUDIT03_R3_description_length/probe_sumandos_two_readings.py`

---

## §8 BDM and Shannon — where each is legitimate

**8.1** The programme is **algorithmic (Kolmogorov / AID), not Shannon**.
`method_paper.tex:89`

**8.2** Shannon `H_total` and ZIP **are** used, and legitimately: they quantify
redundancy and distributional regularity **in the realised output dataset**, on
the *behaviour* side of a mechanism-versus-behaviour comparison. They are never
used to compute a mechanism description length. `method_paper.tex:1897`

**8.3** On the benchmark, Shannon (10,229.61 bits) and ZIP (10,016) are both close
to the raw table size, because the output bits are near-balanced and
statistically featureless. `method_paper.tex:1913`

**8.4** BDM returns **580.01 bits** on the same object, separating it from a
row-permuted control by 25.4× and from a density-matched random matrix by 26.8×.
**The algorithmic measure detects generative structure the statistical ones
cannot see.** `method_paper.tex:1916`

**8.5** So: BDM applies to the **materialised binary object** (output table,
adjacency matrix). Program length applies to the **mechanism**. Shannon applies
only as a **declared comparison baseline** on the dataset side, and must never
appear inside a description length. `recall decision #86`

**8.6** BDM's known caveat, carried from the sibling: it **is** a valid description
length and may enter an MDL budget; the real objection is that it is
**permutation-invariant**. `recall decision #52`

---

## §9 What the method does not do

**9.1** It does not remove the `2^n` state space; it replaces brute-force gate
evaluation with closed-form causal expressions. `method_paper.tex:153`

**9.2** It does not perform causal discovery, reason about interventions, or handle
confounders. `method_paper.tex:118`

**9.3** It is exact only over **exhaustive** inputs. Over the *reachable* states of
a running network, inputs can be correlated and both gate and arity can be
recovered wrongly — an OR can look like an AND. The method reports insufficiency
there rather than guessing.
`index-deconvolution/bitacora/11_gate_confusion_arity_schemata.md:41`

**9.4** Multi-valued threshold logic (`GEQ`, `LT` over `θ`) is **a different
object** and must not be forced into a Boolean family. 512 multi-valued plus 407
threshold formulas are unevaluable by construction. `AUDIT02/H`

---

## §10 Contradictions found while reading — R1 inputs, not claims

**10.1** `derivations/02_cb_and.tex` is internally inconsistent. Its §3 table
headed "Node 1 Output (AND)" shows output 1 **only at index 8**, which is AND over
`Ic = {1,2,3}`; but the surrounding text sets `Ic = {2,3}`. Under LSB-first with
`Ic = {2,3}`, index 7 has `v = (0,1,1)` and **does** satisfy AND.

**10.1a (verified by execution, not asserted)** Evaluating AND over `Ic={2,3}`
against the document's own transcribed table: **row 7 is the sole disagreement**,
and the table reproduces exactly the one-set of `Ic={1,2,3}`, namely `{8}`. The
table is for a different `Ic` than the text.

**10.2** Consequently the document's Discussion (`:119`) invents a defect — *"`Δ_nc`
may overgenerate (e.g. index 7)"* — that is an artefact of **10.1**, not a property
of the formula. Its §5 network-aware constraint already resolves it.

**10.3** `derivations/01_causalBool_inputs.tex:171` reports its own worked example
as producing indices `{1,5,17,21}` of which only `{1,5}` are correct, and blames
*"a potential issue in the original implementation"*. Unresolved in the document.

**10.4** These two are the **June 2025 hand-written** derivations; `03`–`12` are
**generated 2026-08-25** with executed elementwise witnesses and zero failures.
The two vintages should not be cited with equal confidence.

**10.5** `comp_paper.tex` and `method_paper.tex` prose defined Ω narrowly (§5.5);
corrected 2026-09-03 in `cbfe02a`, with a guard.

---

## §11 The five things I most need corrected

Ranked by how much downstream work rests on them.

1. **§6.11** — does the founding example's two-schema answer really admit the merge
   to `{1,*,1,*,1,*,1,*,*}`, and was *not merging* deliberate?
2. **§6.4** — is it right that §6.3 (coarse, `Ω(F_q)`) and §5.5 (fine, per-schema)
   are two levels of one decomposition, rather than a contradiction?
3. **§7.9** — is `D_schema` the measure you want, given §7.7 says `D_formula`
   never reads an output bit?
4. **§8.5** — is that the correct division of labour between BDM, program length
   and Shannon?
5. **§4.6** — is "the one-set of every family is a union of schemata" a statement
   you accept as central, or an incidental reformulation?
