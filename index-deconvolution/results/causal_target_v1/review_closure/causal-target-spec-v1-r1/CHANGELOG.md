# Changelog — closure of `causal-target-spec-v1-r1`

Originals are untouched; every change lives in this directory. Marks [C-R1], [C-R2], [C-R3] in the
corrected copies point here.

## R1 — literature and decision

| original claim (file) | correction | where |
|---|---|---|
| "exact k-junta membership-query literature … not accessed" (DECISION, HANDOFF) | Bshouty–Costa v1 read: §2, Lemma 4, §3.1 Thm 1, §3.2 Thm 2; mapping proved, including the shared non-adaptive query set | `LITERATURE_MAPPING.md` §1–§2 |
| Akutsu 1999 and 2003 "not accessed" (DECISION, HANDOFF, EVALUATION_SPEC §4) | 1999 read in part (Thm 1–3, Prop 1); 2003 still not accessed (HTTP 403), unverified | `LITERATURE_MAPPING.md` §3–§4; `corrected/EVALUATION_SPEC.md` §4 |
| "Decision: DRAFT_QUERY_RECOVERY" (DECISION, HANDOFF) | NO_JUSTIFIED_IMPLEMENTATION for this proposed study | `DECISION.md` |
| draft §1 "new relative to existing deconvolution" | known problem with a known exact algorithm | erratum E1 |
| competitor table lacked the applicable exact learner (EVALUATION_SPEC §4, draft §4) | Bshouty–Costa and Akutsu 1999 rows added | `corrected/EVALUATION_SPEC.md` §4; erratum E2 |
| draft is a gated, possibly authorisable study | withdrawn; preconditions P2–P4 lapse | `corrected/DRAFT_WITHDRAWAL_ERRATUM.md` |
| — | `target_contract.json` gains `primary_future_target.prior_art` | `corrected/target_contract.json` |

## R2 — distribution

| original claim | correction | where |
|---|---|---|
| "Confirmation set B, class-uniform" (draft §5); "class-uniform sampler" (DECISION P3, HANDOFF) | the specified procedure is degree-stratified, equal weight per degree: P(f) = 1/[4·C(n,j)·E_j]; uniform over distinct functions needs P(j) = C(n,j)·E_j/N(n,3); n = 2, k = 1 hand check 1/4, 1/8 versus 1/6; n = 16 weights 2, 32, 1,200, 122,080 over 123,314 | erratum E3. No sampler written or run |

The corrected TARGET_CONTRACT, EVALUATION_SPEC and ABSTRACTION_CONTRACT never used the label, so
they needed no R2 change.

## R3 — abstraction scoring and outcome semantics

| original claim | correction | where |
|---|---|---|
| endpoint (iv): success = "fibre condition holds on every declared, checked pair" | split: (iv-a) preliminary per-q existence; (iv-b) full declared equation with supplied α, β, Ȳ, F̄, identity intervention included; CONSISTENT / INCONSISTENT / INCOMPLETE over \|Q\|·\|D\| | `corrected/EVALUATION_SPEC.md` §1 |
| macro maps F̄_q̄: α(D) → α(D) asserted for arbitrary D | declared codomain Ȳ ⊇ α(D); closure F_q(D) ⊆ D required before taking Ȳ = α(D); counterexample D = {00} | `corrected/ABSTRACTION_CONTRACT.md` §2, §3 item 3 |
| identity intervention "maps to F̄" stated only in the requirement | q_id is a declared member of Q, scored like any q (item 3a) | same, §3 |
| existence of induced maps and consistency with one declared system not separated | statements (1) and (2) distinguished; q0/q1 counterexample with hand proof, labelled as a supervisor-requested proof illustration, not a witness or test; wrongly supplied F̄ example for one q | same, §3 |
| coverage counted (q, fibre) pairs only | adds (q, x) pairs over \|Q\|·\|D\|; unchecked pairs never passes | same, §4 |
| "an INVALID on a deterministic oracle is a harness defect" (EVALUATION_SPEC §2) | defect only for an oracle verified in-class; correct falsification of membership otherwise | `corrected/EVALUATION_SPEC.md` §2; `corrected/TARGET_CONTRACT.md` §4; `corrected/target_contract.json` `recovered_object.invalid_semantics` |
| R2 regime: "never claimed: values of F on unvisited states" | OBSERVED / CLASS-ENTAILED / UNDETERMINED kept apart; class-entailed values allowed, conditional and labelled; nothing else on unvisited states | `corrected/TARGET_CONTRACT.md` §2; `corrected/target_contract.json` `value_labels` |

## Unchanged conclusions

Q_LB audit (EXISTING_EVIDENCE §2) and "S2 headroom not established"; the class-membership
impossibility for n > 2k (TARGET_CONTRACT §3); endpoint implication 3 ⇒ 4 (§5); witnesses W1–W4,
their declarations, checker and the accepted 53/53 result (not re-executed); the autonomous fibre
theorem (ABSTRACTION_CONTRACT §2) and the W4 argument; the singleton certifier as a mathematical
statement, with "cheap" meaning only its finite operation count. IDENTIFIABILITY.md and
EXISTING_EVIDENCE.md are not copied because no statement in them changes.
