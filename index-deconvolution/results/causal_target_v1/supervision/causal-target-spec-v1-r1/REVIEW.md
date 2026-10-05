# Codex review — causal-target-spec-v1-r1

Date: 2026-10-05. **CHANGES REQUESTED.** The artifact and core proof checks pass;
the specification as a whole is not yet accepted. No implementation is authorized.
This review leaves the original twenty run files unchanged.

## What passes

`audit_review.json` records fourteen passing review checks: all 25 preservation
hashes still match, all 15 manifested outputs and six additional read inputs
match, the packet's thirteen checks pass, and the witness rerun reproduces the
saved 53/53 result exactly. The rerun writes only into this supervision directory.
Independent small arithmetic checks reproduce W1–W4's conclusions and the
distinct-function counts and rounded bounds. Coverage is these named files,
not a claim that the whole dirty repository is unchanged.

The counting-bound correction is sound for the declared product class. The
class-membership impossibility argument is sound for an in-class-consistent
transcript and n > 2k: changing one unqueried output value produces an
out-of-class alternative. This prevents certification of membership; it does
not prevent falsifying membership on an inconsistent transcript. The exact
singleton certifier is mathematically sound. Its runtime has not been measured,
so “cheap” should mean only the stated finite operation count, not demonstrated
practicality. The autonomous fibre theorem and W4 counterexample are sound.
The disclosed checker/declaration corrections do not invalidate those proofs.

## R1 — the literature stop condition is met

Bshouty and Costa, *Exact Learning of Juntas from Membership Queries*,
[primary manuscript](https://arxiv.org/pdf/1706.06934), §2 defines the class using
at most d relevant inputs. §3.2, Theorem 2, gives deterministic non-adaptive
exact learning with O(d·2^d·log n) membership queries and n^{O(d)} time.
The section describes reconstructing the unique consistent function and its
relevant variables. Inspected: definitions and §3 through Theorem 2, including
the construction and reconstruction argument; not a review of every theorem.

**Application here (supervisor inference):** each output coordinate is exactly
such a function, with d=k. The non-adaptive query set depends on n,k, not on the
target output. Submit each state once to R4 and reuse all n returned bits to
reconstruct each node. Thus the same set identifies the whole product class;
one need not multiply the number of state queries by n. Reconstruction work
still grows with the number of outputs. Constants, self-loops and redundant
syntax introduce no exception to this mapping.

This meets the executor's explicit P1/F4 rule: an existing exact algorithm has
a guarantee for the same class and access. The submitted decision must therefore
be revised to **NO_JUSTIFIED_IMPLEMENTATION for this proposed study**, and its
draft marked withdrawn/superseded in a new closure artifact. Preserve the old
draft. The conclusion is not that no new query algorithm could improve runtime
or query count; that would require a different, justified comparison against
existing exact learners. Neither a full-table baseline nor RAND alone establishes
such a contribution. No practical advantage or tight numerical bound is inferred
from the asymptotic result.

Closure: read and map this primary source explicitly. Record what was and was
not accessed in the Akutsu sources; do not transfer their perturbation semantics
from titles. A complete Akutsu survey is not needed to establish the already
decisive counterexample to P1. Do not turn a known exact-learning task into a
novelty claim merely by changing package names or returning all nodes together.

## R2 — “class-uniform” sampling is not the distribution specified

Draft §5 chooses support size j uniformly from 0..3, then chooses an essential
support and a function uniformly within that stratum. A function of degree j
therefore has probability 1/[4·C(n,j)·E_j]. This varies with j. It is a
degree-stratified distribution with whole-class coverage, not a uniform draw
over distinct functions or networks.

To be class-uniform, choose j with probability C(n,j)·E_j/N(n,3), then support
and essential function uniformly; independently sample the node functions for
the product network class. A small exact comparison suffices: for n=2,k=1,
equal degree probabilities give each constant probability 1/4 and each literal
1/8, whereas a uniform draw gives each of the six functions 1/6.

Closure: issue a textual erratum consistently across the draft, decision and
handoff claims. Retain the original specified distribution under an accurate
name, and describe the alternative formula without implementing either sampler.
The draft's withdrawal does not make its distribution claim correct.

## R3 — evaluation must check the entire declared abstraction contract

EVALUATION_SPEC endpoint (iv) currently says success means the fibre condition
holds on every checked pair. That only establishes existence of an induced map
for each q separately. ABSTRACTION_CONTRACT §3 additionally supplies macro maps
and beta, and requires agreement with those maps. Both tests are necessary.

Concrete counterexample: X={00,01,10,11}, F=identity, alpha(x)=x1. Let q0 reset
x1=0 and q1 reset x1=1 before the step. Each intervention separately satisfies
the fibre condition: its induced macro map is constant 0 or constant 1. If
beta(q0)=beta(q1), no single macro map represents both. The current endpoint
would pass both fibre tests despite a failed declared intervention contract.
Even one q can pass its fibre test but disagree with a wrongly supplied macro map.

Closure: score alpha(F_q(x))=Fbar_beta(q)(alpha(x)) for every declared (q,x),
including consistency of interventions sharing beta, the identity intervention,
and membership of alpha(F_q(D)) in the declared macro codomain. Either require
appropriate domain closure or explicitly enlarge the macro codomain; do not
silently assert a self-map on alpha(D) for an arbitrary restricted D. Keep the
fibre-only existence test as a separately labelled preliminary property.
Give hand reasoning for the counterexample; no experiment is necessary.

While correcting outcome semantics, qualify EVALUATION_SPEC's assertion that
INVALID on any deterministic oracle is a harness defect. It is a defect for a
verified **in-class** oracle, but a deterministic out-of-class oracle can correctly
produce INVALID. Likewise R2's table must allow class-entailed values on unvisited
states while distinguishing them from observed values. No unrestricted inference
on unvisited states is licensed.

## Next action and accounting

Execute only `CLOSURE_CLAUDE.md`. It owns a new closure directory and leaves all
original evidence and source untouched. The useful target distinctions and
multilevel ideas are retained. This review stops this specific query draft;
it does not conclude that the overall method is complete or that multilevel
causal abstraction is impossible.

Executor charge: 760 s. Supervisor charge: conservatively 600 s (the complete
review reserve). Total charged: 1,360/3,600 s. The closure receives a maximum
1,200 s executor allowance and reserves 300 s for final supervisor review from
the same remaining budget: maximum cumulative charge 2,860/3,600 s. No reset,
transfer, generator, learner, benchmark or new study is authorized.
