# Multilevel abstraction contract

A finite, deterministic target contract. It is **not** a claim that every notion of causal
abstraction reduces to the equations below. External definitions were inspected in the PDFs
(see `evidence_manifest.json`): Rubenstein et al. 2017, Definition 1 (SEM with a poset of perfect
interventions I_X), Definition 3 (exact τ-transformation: a surjective order-preserving
ω: I_X → I_Y with P^i_{τ(X)} = P_Y^{do(ω(i))} for all i), Theorem 6 (causal consistency);
Beckers and Halpern 2019, Definitions 3.1 (exact transformation), 3.5 (uniform), 3.7
(compatibility τ(M_L(u, Y←y)) = M_H(τ_U(u), ω(Y←y))), 3.12 (ω_τ induced by τ), 3.13
(τ-abstraction: τ surjective, τ_U compatible, I_H = ω_τ(I_L)) and 3.15 (strong τ-abstraction).
Constructive abstraction was **not** inspected. Both papers treat static (recursive or
uniquely solvable) causal models with distributions over exogenous contexts; our object is a
one-step deterministic dynamical map. The correspondence used here is the two-layer unrolling
x(t) → x(t+1) with the context being the initial state; this transfer is our construction, not a
result of either paper.

## 1. The user's ideas and their evidential roles

| idea | role in this contract | what it may claim | what it may not claim | needed before any causal reading |
|---|---|---|---|---|
| several word widths and origins (dictionary views w4…w64, offsets) | **candidate measurements**: each (width, origin) is a declared map α_w,o from a string to a token sequence | that a view yields a shorter archive, in archive bits | that tokens are causal variables | a labelled state space and an α on it satisfying §3 |
| occurrence gaps and scale-dependent breaks | **descriptive statistics / hypothesis proposals**. A gap is the first difference of an occurrence set (GLOSSARY §5); its denominator is the number of occurrences minus one in the declared window; a break is a declared change-point rule with a declared scale grid | that the gap sequence has a stated structure relative to a declared null | that a break is a regime change in a mechanism | a shuffle or generator null fixed in advance, and multiple-comparison accounting across scales |
| grammar and nested patterns | **exact structural descriptions** (CONCAT, REPEAT, XFORM rules) | that the string equals the decoded DAG | that nesting is recovered reuse rather than **forced grouping** (a CONCAT imposed by segmentation is not evidence of reuse; SYNTHESIS §3) | a reuse count where a shared rule is referenced at least twice, and a comparison with a fixed-grid control |
| levels of abstraction | **explicit maps** α between state spaces with a testable target (§2, §3) | consistency on a declared domain | causal abstraction without §3 | supplied or learned α declared before checking |
| self-similarity / fractal dynamics | two **separate** claims: (a) scaling of a declared statistic across a declared scale grid; (b) a temporal law (dynamics) | (a) a fitted exponent with its null; (b) a predictive score | either from nesting alone | a scaling null and a separate temporal null; nesting is a representation, not a scaling law |

## 2. Autonomous dynamical consistency

Let F: X → X be deterministic, X finite, and α: X → Y a declared map with image α(X).

**Definition.** F̄: α(X) → α(X) is a macro map for (F, α) if α(F(x)) = F̄(α(x)) for all x ∈ X.

**Proposition.** A macro map exists iff for all x, x' ∈ X, α(x) = α(x') ⇒ α(F(x)) = α(F(x')).
*Necessity*: if F̄ exists and α(x) = α(x'), then α(F(x)) = F̄(α(x)) = F̄(α(x')) = α(F(x')).
*Sufficiency*: for y ∈ α(X) choose any x with α(x) = y and set F̄(y) = α(F(x)); the condition
makes the choice irrelevant, and the equation holds by construction. F̄ is then unique on α(X).

W3 instantiates both directions: identity satisfies the condition for α = x1, xor_first violates
it on both fibres. If α is injective the condition always holds; that is a change of name (a
reversible codec dictionary), not a coarse-graining, and is not counted as a macro-level finding.
This is **autonomous** consistency only.

## 3. Intervention consistency

Declare before checking:
1. a finite set Q of micro interventions, each with its **timing**: `reset` (set coordinates,
   then apply F once: F_q = F∘r_q), `replace` (f_i := c at the update: mechanism replacement), or
   `clamp` (both);
2. **feasibility**: every q ∈ Q is admissible from every x in the declared domain D (no
   state-dependent exclusions introduced after results);
3. a set Q̄ of macro interventions with maps F̄_q̄: α(D) → α(D), and a map β: Q → Q̄; micro
   interventions with equal β-image are declared to **share a macro meaning**;
4. the domain D ⊆ X, fixed before checking; restricting D after seeing a failure is a protocol
   violation, not a repair.

**Requirement (exact intervention consistency on D).** For all q ∈ Q and x ∈ D:
α(F_q(x)) = F̄_β(q)(α(x)), and the identity intervention maps to F̄.

A **necessary condition** for each q, independent of how Q̄ is chosen, is the fibre condition of §2
applied to F_q: equal-α states must have equal-α images under F_q. W4 fails it: under reset x1 := 0,
the fibre {00, 11} goes to α-values {0, 1}. Therefore no Q̄ and no β can make α = x1 ⊕ x2 an
intervention-consistent abstraction of the identity for that q, although F itself is autonomously
consistent. Following Beckers and Halpern, one may instead **exclude** q from the allowed set:
that is a legitimate abstraction only if Q is declared before checking and the exclusion is
reported as a restriction of the claim (the abstraction then answers fewer questions). Further
requirements adapted from their Definition 3.13, stated but not imposed by default: α surjective
onto the macro space, and Q̄ = the induced image of Q (no macro interventions without micro
counterparts).

## 4. Learned versus supplied α, costs and controls

- **Supplied α**: declared by the user with its source; zero selection cost but its description
  length is charged in any comparison.
- **Learned α**: chosen from a finite declared family A after looking at data. Every member tried
  is counted; the report states |A| and selects by a rule fixed in advance. A consistency found
  after trying |A| maps is an existence statement about A, not evidence that the world has that
  macro level. Confirmation needs fresh states or fresh interventions not used in the selection.
- **Nontriviality controls**: identity α and constant α always satisfy §2 (and constant α also
  satisfies §3 trivially). They are reported as controls, never as discoveries. A nontrivial α
  has 1 < |α(D)| < |D|.
- **Coverage**: report |α(D)|, the number of fibres actually populated by checked states, and the
  number of (q, fibre) pairs checked over the number declared. Unchecked pairs are reported as
  unavailable, never as passes.
- **Ambiguity**: when several α ∈ A pass, report all; the target is not the shortest one unless a
  declared cost decides, and then the selection is labelled as such.
- **Unseen interventions**: consistency on Q says nothing about q ∉ Q.
- **Cost accounting in future comparisons**: dictionaries, metadata, interventions and α are
  charged in the same algorithmic description length as the rest of the code
  (DESCRIPTION_LENGTHS); none is free. An invertible token dictionary (codec) and an
  information-losing α are different objects with different roles; the first is priced as code,
  the second is tested by §2–§3.

## 5. Relation to the stopped compression line

The dictionary/HID views act on R1 strings. They supply candidate α only after a state space is
declared: e.g. a labelled R3 table whose rows are encoded by a view. Until such a pairing is
specified, none of the dictionary results bears on §2 or §3, and none is causal evidence.
