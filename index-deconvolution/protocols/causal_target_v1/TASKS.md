# Required decisions and reviewable outputs

## A. Evidence reconciliation — EXISTING_EVIDENCE.md

Read the accepted synthesis closure/review and existing identification-screen
protocol/verdict/qualifications. Read the original order-discovery objective so
the user's interest in unknown information and multilevel descriptions is not
silently replaced by a fully observed network assumption.

Provide a table of claims, input access, demonstrated result, limitations and
provenance. Include full-table deconvolution, S2 query recovery, S3 questions
about an already supplied model, HID compression and unknown-sequence discovery.
Do not generalize absence of a query arm in an old document to current source
without inspection. Identify existing owners and any overlapping active work;
do not modify them. Cite exact functions/files for capabilities and artifacts
for empirical claims. Do not treat the screen's NARROW verdict as supervisor
acceptance of every scientific statement it contains.

Audit PROTOCOL_screen_identification section3's counting argument before using
its numerical headroom threshold. State whether its counted objects are distinct
functions, padded support sets or syntactic networks, whether degree is exact or
at most k, and what each allowed query reveals. An upper bound on a hypothesis
count does not by itself give a lower bound on required queries. Derive a valid
bound for a clearly specified finite class or mark the old threshold unvalidated.
Include a small hand count, without running screen jobs or changing their verdict.
Historical arithmetic is not new evidence of a competitive advantage. Account
for the recorded absence of a chosen-query competitor, biological-model selection,
and hardware/access differences before discussing any niche.

Follow current GLOSSARY rulings: connected inputs/essential variables, free
coordinates and schema-specific sumandos are distinct. Do not import the
finance pivot/residual terminology into exact Boolean deconvolution. Complexity
means an algorithmic description under the repository's contract, not a renamed
Shannon entropy or unexplained BDM sum.

## B. Target contract — TARGET_CONTRACT.md and target_contract.json

Distinguish four access regimes explicitly:

1. An unlabelled finite bit string: no supplied state coordinates, time axis,
   interventions or generating class. Output may be structural hypotheses;
   unique causal identification is not the default claim.
2. A passive labelled state trajectory: known state coordinates and transition
   boundaries, potentially incomplete state coverage. State all assumptions
   required even to treat it as one fixed deterministic transition map.
3. A complete labelled transition table: fully observed autonomous synchronous
   Boolean dynamics F:{0,1}^n->{0,1}^n, known labels/bit order, stationary and
   noiseless. Target functional dependencies and reduced Boolean functions,
   not unrecoverable original syntax or redundant declared edges.
4. Chosen state-successor access: define precisely how a state is set/reset,
   what output is returned, query costs and whether all initial states are
   admissible. Separate this from clamping during updates and from free access
   to a known model. Do not call a simulator oracle passive real-world evidence.

Choose one plausible primary FUTURE target, or explain why none is justified.
Default candidate for assessment is bounded-degree functional recovery under
chosen state-successor queries, because full-table recovery already exists;
this preference is not a GO decision. Specify n, model class, self-loops,
constants, degree definition, determinism, full observation, node labels,
noise/hidden-state exclusions, intervention semantics and identifiability scope.

Define the recovered object, allowed equivalence/relabeling, and an explicit
AMBIGUOUS or ABSTAIN result. Agreement on observed states, held-out predictive
accuracy, exact truth-table equivalence and causal/interventional equivalence
are separate endpoints. MDL may select a hypothesis; selection alone is not
identification. Canonical gate naming is a representation choice among
functionally equal implementations, not proof of the original gate's identity.

## C. Four tiny witnesses — IDENTIFIABILITY.md, witnesses.json, check_witnesses.py

Declare exactly these four example constructions and expected conclusions in
witnesses.json BEFORE running any checker. Use at most three Boolean state bits
(at most eight states per map). No random examples or additional fixture search.
Provide full hand-written maps/tables and hand reasoning, not generated network
instances. The small standard-library checker may enumerate these maps only.
Its results are mathematical sanity checks, not performance data or learned
recovery results. A declaration correction must be versioned before rechecking.

W1: two distinct two-bit transition maps, identity and coordinate swap, agree
on the entire observed all-zero trajectory. A chosen off-diagonal initial
state distinguishes them. Demonstrate ambiguity and specify that extra query.

W2: two syntactically different implementations of the same Boolean function,
one with a declared but functionally redundant input, agree on the complete
table. Show what minimal functional support recovers and why syntax/redundant
connectivity cannot be uniquely recovered from this table alone.

W3: alpha(x1,x2)=x1. Supply a two-bit map admitting a deterministic macro map
and another whose equal-alpha states have different next alpha values. Identity
and F(x1,x2)=(x1 XOR x2,x2) are the fixed constructions. Show both conditions
directly; a lossy coarse-graining is distinct from a reversible codec dictionary.

W4: identity two-bit dynamics with alpha(x1,x2)=x1 XOR x2 commutes autonomously.
An intervention setting x1=0 before the step makes two initially equal-alpha
microstates produce different next alpha values. Check whether any deterministic
macro operation depending only on alpha can represent this intervention for
all states. Distinguish autonomous consistency from intervention consistency.

Also hand-check the finite-class count from A on at most two Boolean inputs;
this is arithmetic attached to W2, not an extra model search. For example,
enumerate the distinct functions with at most one essential input and compare
them with the padded support/function count. Do not assume the lower bound is
tight or proves an existing learner near-optimal.

## D. Multilevel contract — ABSTRACTION_CONTRACT.md

Retain all user ideas with explicit evidentiary roles:

| idea | role to specify |
|---|---|
| several word widths/origins | candidate measurements or descriptions, not known causal variables |
| occurrence gaps and scale-dependent breaks | descriptive statistics/hypothesis proposals; define each gap and denominator |
| grammar and nested patterns | exact structural descriptions; distinguish forced grouping from recovered reuse |
| levels of abstraction | explicit maps between state/feature spaces and a testable consistency target |
| self-similarity/fractal dynamics | separate scaling and temporal claims with suitable controls, not an inference from nesting |

For a deterministic micro map F and declared state map alpha, define when a macro
map exists on alpha's image: equal-alpha microstates must have equal-alpha
successors. Give the short necessity/sufficiency argument and relate it to W3.
This alone is autonomous dynamical consistency, not full causal abstraction.

For allowed micro interventions q, define F_q, allowed macro interventions and
their map beta(q), and require alpha(F_q(x)) = Fbar_beta(q)(alpha(x)) over the
declared domain. Specify update/clamp timing, intervention feasibility, and which
micro interventions share a macro meaning; do not hide failures by restricting
the domain after seeing results. Relate the failure in W4 to these requirements.
This finite deterministic formulation is a target contract, not a claim that all
forms of causal abstraction reduce to this equation.

Address learned versus supplied alpha, multiple comparison/selection costs,
nontriviality (identity and constant maps are controls, not discoveries), macro
state coverage, ambiguity and unseen interventions. No free dictionaries,
metadata, interventions or abstraction mappings in a future cost comparison.
An invertible token dictionary and an information-losing macro-state map must
not be treated as the same object.

## E. Evaluation and decision — EVALUATION_SPEC.md and DECISION.md

Give separately scored endpoints for (i) functional recovery, (ii) support
recovery, (iii) predicted intervention answers and (iv) abstraction consistency.
Include exact ground-truth equivalence on a finite assessable class, and state
when success is only predictive. Incorrect confident identification on an
ambiguous case is an error, not successful compression. Failed runs, unavailable
answers, invalid evidence and justified abstention are distinct. Report
intended/available denominators; never replace missing values with zeros.

Specify fair competitors under the same access: exhaustive-table methods cannot
quietly receive data withheld from query learners; an equivalence oracle is not
a free state query. Include query counts, returned information, wall/RSS, and
all baseline/feature/abstraction costs. Do not promise an information bound
that counts the wrong objects. Consult primary sources before transferring a
competitor's guarantees or intervention assumptions; no installations/runs now.

Choose DRAFT_QUERY_RECOVERY, DRAFT_ABSTRACTION_VALIDATION, or
NO_JUSTIFIED_IMPLEMENTATION. If drafting, produce exactly one
DRAFT_EXECUTION_PROTOCOL.md with finite algorithm/access class, candidate
ordering/ties, baseline, predeclared witnesses, budgets, fresh-data separation,
endpoints and stopping rules. Mark it NOT AUTHORIZED FOR EXECUTION. It must say
what is new relative to existing deconvolution and what would falsify its value.
If no draft is justified, name the specific missing information or proof in
DECISION.md rather than inventing a productive-looking benchmark.

## F. Audit and handoff

Deliver every named document, an evidence/source manifest (including URLs and
retrieval dates for external sources), witness checker and retained outputs,
pre/post preservation, attempt/time ledger, and HANDOFF.md. Machine-check
document presence, JSON validity, hash integrity and witness conclusions.
Do not count a paper's abstract as verification of a theorem in its body; cite
the exact definition/assumptions inspected or mark the check unavailable.
Unmet assumptions and unresolved evidence are first-class findings. A design
specification is not an implemented or validated method.
