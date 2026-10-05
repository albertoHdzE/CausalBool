# Literature mapping — closure R1

All sources below were retrieved on 2026-10-05 into `/tmp` (not into the repository); identities in
`evidence_manifest.json`. Page numbers are the printed page numbers of the retrieved PDF.

## 1. Bshouty and Costa — read

| field | record |
|---|---|
| source | N. H. Bshouty, A. Costa, *Exact Learning of Juntas from Membership Queries*, arXiv:1706.06934, **v1** (submitted 2017-06-21; arXiv lists only v1), https://arxiv.org/pdf/1706.06934, 28 pp., sha256 `1b6bfa61…77e4` |
| inspected | abstract; §1 Tables 1–2 (pp. 3–5, read for context only); §2 definitions (pp. 5–6): relevant variable, equivalent set, d-Junta, (n,d)-universal set and bound (1); d-wise bipartite connected family and Lemma 4 (Damaschke: equivalent set for d-Junta iff d-wise bipartite connected family) (p. 7); §3.1 lower bound sketch and Theorem 1 with its proof (pp. 7–9); §3.2 opening, the reconstruction procedure, Lemma 6 and its proof, Remark, conditional-probability construction, **Theorem 2** (pp. 10–11) |
| not inspected | proof details of Lemmas 1, 3, 5 (cited constructions); Theorems 3 onward (§3.2 second and third algorithms beyond their statements, §4 randomised, §5 adaptive); appendices. No claim rests on them |
| class | d-Junta: all f: {0,1}^n → {0,1} with at most d relevant variables, x_i relevant iff ∃a: f(a\|x_i←0) ≠ f(a\|x_i←1) (§2, p. 6). Any Boolean function on the relevant set; constants included (0 relevant variables) |
| access | membership queries: the learner submits a ∈ {0,1}^n and receives f(a); **non-adaptive**: all queries fixed before any answer |
| output | the target function (its truth table on a d-subset of variables) and, if required, its relevant variables, "from its truth table" (§3.2, p. 10) |
| guarantee | **deterministic, exact**: the query set A is a d-wise bipartite connected family, hence by Lemma 4 an equivalent set, so the consistent function in d-Junta is unique and equals the target (§3.2, p. 10). No failure probability |
| query cost | O(d·2^d·log n) (Theorem 2, p. 11); lower bound Ω(2^d log n) for any deterministic adaptive learner (§3.1, p. 7) |
| runtime | n^{O(d)} for constructing A (Lemma 6) and for reconstruction, which tries every d-subset of variables (§3.2) |
| limits | asymptotic: constants in O(·) are not stated in the inspected text, so **no numerical query count for n ≤ 16, k = 3 is inferred**; correctness is for targets in d-Junta (an out-of-class target is not certified, consistent with TARGET_CONTRACT §3); single Boolean output |

## 2. Mapping onto the R4 network oracle (proof)

Let F = (f_1, …, f_n) ∈ C(n,k), i.e. every f_i has at most k essential variables, and let the
oracle be R4: submit x, receive F(x) ∈ {0,1}^n.

1. *Class.* "Essential" in TARGET_CONTRACT §1 (∃x: f_i(x) ≠ f_i(x ⊕ e_j)) and "relevant" in §2 of the
   paper (∃a: f(a\|x_j←0) ≠ f(a\|x_j←1)) are the same condition, since {a\|x_j←0, a\|x_j←1} =
   {x, x ⊕ e_j}. Hence f_i ∈ C(n,k) iff f_i ∈ d-Junta with d = k. A self-loop is x_i essential for
   f_i, just a variable among n; a constant has 0 relevant variables; redundant declared syntax is
   invisible to both definitions. No exception arises.
2. *Access.* An R4 query on x returns (f_1(x), …, f_n(x)): coordinate i is exactly a membership-query
   answer for f_i at x. R4 is adaptive-capable, so a non-adaptive set is admissible.
3. *Shared query set.* Theorem 2's set A depends only on (n, d) (Lemma 6 constructs it before any
   answer). Submit each a ∈ A once to R4; the returned vectors give, for every i, the full answer
   list {(a, f_i(a)) : a ∈ A}. By Lemma 4, A is an equivalent set for d-Junta, so for each i the
   consistent function in d-Junta is unique and equals f_i.
4. *Product class.* If F ≠ G in C(n,k), some coordinate has f_i ≠ g_i, both in d-Junta, so some
   a ∈ A separates them. A is therefore an equivalent set for the product class with **|A| state
   queries in total, not n·|A|**. Reconstruction work is n times the per-coordinate work,
   n · n^{O(k)}.

Conclusion: the draft's object (certified exact recovery of C(n,k) under R4) has a published
deterministic exact algorithm with a guarantee for the same class and access. No error in the
supervisor's mapping was found. This meets P1/F4.

What this does **not** say: that the known algorithm is practical at n ≤ 16, that its constants are
small, that no algorithm with fewer queries or less runtime exists, or that a separately justified
engineering implementation could not be worthwhile.

## 3. Akutsu, Miyano and Kuhara 1999 [8] — read, partly

| field | record |
|---|---|
| source | *Identification of genetic networks from a small number of gene expression patterns under the Boolean network model*, PSB 4:17–28 (1999), https://psb.stanford.edu/psb-online/proceedings/psb99/Akutsu.pdf, 10 pp., sha256 `86e9605f…71e4` |
| inspected | abstract; §2 problem definitions (CONSISTENCY, COUNTING, ENUMERATION, IDENTIFICATION over INPUT/OUTPUT state-transition pairs); §3 Theorem 1, Proposition 1, Theorem 2 statement and opening of its proof, Theorem 3 statement (§3.3) |
| not inspected | §3 algorithm details, §4 experiments, §5 discussion; Theorem 2's full proof |
| model | synchronous Boolean network, max in-degree K; data are (INPUT, OUTPUT) state pairs, OUTPUT = F(INPUT): the R4 answer form. Theorem 2 draws INPUTs **uniformly at random** (passive-random, not chosen) |
| statements | Thm 1: consistency, counting and identification are polynomial-time for constant K. Prop 1: if every assignment to every 2K-subset of nodes appears among the INPUTs, each node's function with its inputs is determined uniquely, if it exists — a deterministic sufficient condition, i.e. chosen INPUTs forming an (n, 2K)-universal set suffice under R4. Thm 2: O(log n) random INPUTs (constant exponential in K) identify with high probability. Thm 3: a worst-case lower bound of order 2^K + K log n pairs |
| limits | glyphs for exponents and probabilities are damaged in text extraction, so the exact constants of Thm 2 are **not** recorded; how "input nodes" are defined when a declared input is inessential was not checked |
| mapping | Prop 1 is a second, earlier deterministic route to exact identification of in-degree-≤K networks under chosen R4 queries (with a larger, 2K-wise query set). It strengthens, but is not needed for, the §2 conclusion |

## 4. Akutsu, Kuhara, Maruyama and Miyano 2003 [9] — not accessed

doi:10.1016/S0304-3975(02)00425-5 resolved to ScienceDirect, which returned HTTP 403 to the
retrieval on 2026-10-05; no other copy was sought within the cap. **Unverified.** Its perturbation
semantics (gene disruption and over-expression) are not transferred from the title; it is not
mapped onto R4, mechanism replacement or clamp.
