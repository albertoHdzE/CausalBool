# Resumption review — 9 September 2026 (historical findings and disposition)

> This review records the defects that motivated protocol version 2.0.0. Its
> findings are evidence; `00-protocol.md` and `01-record-schema.md` are the
> authoritative current contract.

**Verdict: the project can be continued, but the current pilot is an exploratory prototype, not a validated scientific result.** There is a worthwhile research question here: how do restrictions on a Boolean network's wiring constrain the distributions and payoffs an adversary can attain? Completing that study requires correcting the measurement contract and several implementation defects before expanding the experiments.

This review reconciles `03-continuation.txt`, the protocol, schema, plan, source, parent engine contracts, and saved pilot records. The handoff is evidence of prior decisions and claims; the executable code and artifacts determine what was actually measured. No implementation or historical pilot data was changed during this review. The new deliverables are this report and the audit script/evidence linked below.

**What the handoff establishes.** The intended work is a forward experiment: fix local gate families, perturb connectivity, compute behavior, and compare distributions, support, loss, and description length. The accepted working approach uses adapters inside `doppel-challenge`, reuses the parent CausalBool implementations, starts with additions, excludes empty regulatory inputs, expands across topologies, and records elapsed time and ETA. The final handoff stops after adding a base-validation screen to the family pilot. It does not establish that the large-N engine, final detector, scientific tests, or paper are complete.

**Evidence collected in this review.** The reproducible program is [review_checks.py](../audit/2026-09-09/review_checks.py); its output is [evidence.json](../audit/2026-09-09/evidence.json). It records source hashes, artifact hashes, counterexamples, and three bounded Wolfram comparisons. From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python doppel-challenge/audit/2026-09-09/review_checks.py --wolfram --output doppel-challenge/audit/2026-09-09/evidence.json
```

The output is an audit report, not a passing certification suite. Repeating the command overwrites that report; use a different output path to retain subsequent runs. Kernel exit outcomes can vary between executions.

| Check | Observed result | What it establishes |
|---|---|---|
| Existing add-edge catalogues audited | 10 catalogues, 865 rows including their bases | Concrete coverage of the saved pilots; these are not 865 independent network replicates |
| Attractor calculation against an independent, uncached trajectory oracle | 36/36 seeded cases at N=4,5,6 | Positive evidence for the Python attractor probabilities in those four tested gate families |
| Distribution codec round trips | 865/865 audited rows | The current single-distribution encoding preserves those rational distributions |
| Artifact digest checks using the implementation's rule | 865/865 rows | Internal integrity under that rule |
| Digest checks using the documented rule | 0/865 rows | A reproducible implementation/schema disagreement |
| New sparse-random base comparisons | Original fails; row-repaired and transposed versions pass, all with exit 0 | A concrete explanation and repair direction for the final handoff's skipped base |

**Critical finding 1 — The adjacency convention is inconsistent.**

The parent Python engine [causalbool.py](../../index-deconvolution/src/causalbool.py) defines `C[target][source] = 1`; `Network.connected_inputs` reads a row. The Wolfram exhaustive owner [Experiments.m](../../src/Packages/Integration/Experiments.m) does the same. In contrast, [perturbations.py](../src/doppel_challenge/perturbations.py), starting at `indegrees`, sums columns, and [pilot_runner.py](../src/doppel_challenge/pilot_runner.py) constructs `cm[source][target]` and patches empty columns. No adapter transposes these matrices before execution.

Consequences are substantive: the guard checks out-degree under the engine convention; directed topology interpretations are reversed; some claimed regulatory hubs are actually nodes with many inputs; gate-to-degree associations differ from the intended design.

For `sparse_random`, N=10, seed=0, every column is nonempty but row 0 is all zeros. The engine therefore evaluates node 0 as an empty-input AND. The guard admits it. In the original unscreened catalogue, **all 70 mismatches coincide with an empty engine input row; all 10 cases without an empty row match**. This is stronger evidence than the handoff's unsupported conclusion that sparse-random topology lies outside the validated domain.

New bounded experiments on the same base gave:

| Matrix | Exhaustive output patterns | Reconstructed patterns | Exact | Kernel exit |
|---|---:|---:|---|---:|
| Original generated matrix | 132 | 264 | false | 0 |
| Original plus `cm[0][9] = 1` | 180 | 180 | true | 0 |
| Transposed generated matrix | 100 | 100 | true | 0 |

Both changes alter the actual network and serve as diagnostic interventions, not replacements for the old observations. Neither proves universal correctness. They show that excluding a whole family was premature.

The same convention error explains why the previous `net10a` guard could admit removals at flattened indices 3 and 68: these delete the sole inputs in rows 0 and 6. The handoff mapped their directions and target gates using the opposite convention. Reassess its claimed second removal-failure regime before treating it as a distinct scientific discovery.

**Repair:** adopt one explicit convention across protocol, generators, guards, records, and edge labels, preferably the parent's row-input convention. Keep historical matrices unchanged and version regenerated experiments. Test an asymmetric directed example; symmetric graphs can conceal this bug. Retain the user-selected empty-input exclusion as an explicit domain restriction, while reporting all exclusions and engine failures separately.

**Critical finding 2 — The reported KL is a different statistic.**

[stats.py](../src/doppel_challenge/stats.py), `kl`, conditions both distributions on their support intersection. This conditional divergence can be useful if explicitly named, but it is not the original game's KL constraint. The protocol itself specifies a third quantity: an unnormalised intersection sum, which can be negative.

For `q=(1,0)` and `p=(0.01,0.99)`, the implementation returns `D_KL_nats=0`, although 99% of p's mass lies outside q's support. Standard forward KL is positive infinity whenever p assigns positive mass where q is zero; see the primary [SciPy relative-entropy definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.rel_entr.html). A common ambient alphabet already exists: all N-bit states. Differing supports do not require intersecting or discarding outcomes.

This affects existing results: **49 of the 88 rows in the original `net10a` add-edge catalogue have infinite standard forward KL**, despite finite reported values. Claims about low-KL attacks and rankings must be recomputed. Conversely, merely removing a state from p's support does not necessarily make forward KL infinite; the direction matters.

`L_ENTROPY` has the corresponding defect: it skips states with q=0. On the example above it returns zero rather than infinite cross-entropy. Also, this is cross-entropy relative to the baseline, not the perturbed distribution's entropy.

**Repair:** report standard forward KL, its finite/infinite status, mass outside the baseline support, and optionally conditional KL as a separate diagnostic. Encode infinity with an explicit status and nullable numeric value in strict JSON. Add total variation and Jensen–Shannon divergence as finite descriptive comparisons. If finite KL under unseen states is required, define an observation-noise or smoothing model in advance and report sensitivity to its strength; smoothing changes the experiment.

**Critical finding 3 — Numerical agreement is conflated with process success.**

[full_behaviour.py](../src/doppel_challenge/full_behaviour.py) parses useful JSON even after nonzero process exits. Preserving diagnostic output is reasonable. However, `all_exact_match` in [add_edge_catalogue.py](../src/doppel_challenge/add_edge_catalogue.py) ignores the exit code, and joint rows omit it.

The saved N=12 pilot has **117/126 kernel exits equal to -11**, while its summary says `all_exact_match=true`. The original `net10a` add-edge catalogue has 2/88 such exits, and the screened N=10 ring has 3/85. These records may contain numerically matching output emitted before a crash, but they do not establish successful execution. The review has not established the crash's cause.

**Repair:** distinguish mathematical comparison, process outcome, warning status, and overall acceptance. Require normal exit, valid payload, invariants, and numerical agreement for an accepted validation case. Preserve crashed outputs for diagnosis; do not quietly remove them from denominators. Add timeouts, bounded retries, and a failure taxonomy. Investigate the N=12 failure before another scale increase.

**Critical finding 4 — Two different observables are being called repertoire.**

The Python [repertoire.py](../src/doppel_challenge/repertoire.py) calculates the basin-weighted, phase-averaged long-run attractor distribution specified in protocol §3.2. The Wolfram [comparison script](../src/doppel_challenge/full_behaviour_compare.wl) compares the exhaustive **one-step map** with a reconstructed one-step pattern-to-input-position map. The parent function name `calculatingAttractors` does not turn that map into a dynamical attractor distribution.

These quantities differ even on two nodes. For `C=[[0,1],[1,1]]` and gates `[AND,AND]`, the one-step distribution is `{0:1/2, 1:1/4, 3:1/4}`; the long-run distribution is `{0:3/4, 3:1/4}`. A one-step histogram alone also loses the input/output pairing required to derive dynamics.

The owner comparison is useful, but the runner does not feed its reconstructed transition map into the Python attractor calculation or compare attractor basin probabilities across engines. It therefore does not validate the entire statistic-producing chain. The new 36-case independent oracle check is positive evidence for the Python path, not a substitute for that missing integration test.

**Repair:** use explicit names and record fields for the transition map, one-step output distribution, and long-run attractor distribution. Preserve the current long-run definition unless the scientific protocol is explicitly amended. If the thesis's one-step compressed-query object is the intended primary observable, state that choice and regenerate accordingly. Validate transition-map equality, cycles, basin sizes, phase weights, and encoded probabilities as separate contracts. For long-run observations, specify a random phase or Cesàro averaging: deterministic periodic trajectories do not generally converge to a single-time stationary limit.

**High-priority finding 5 — The present codec does not substantiate the CausalBool/NCD claims.**

[compression.py](../src/doppel_challenge/compression.py) encodes support states as fixed-width bits and probability numerators with Elias gamma codes. This is a reversible distribution codec, but it is not the parent's `Locations/Sumandos` mechanism representation. `schema_length` is normally null for the current attractor repertoires. The docstring's delta/support and parent-schema descriptions do not accurately describe the active implementation.

The pair-length calculation uses a separate asymmetric scheme based on the first distribution's counts and their differences from the second. The audit example gives `NCD(p,q)=1.6`, `NCD(q,p)=1.542857…`, and `NCD(p,p)=0.171428…`. The original catalogue reaches approximately 2.7733. Nonzero self-distance and slight values above one can arise from finite compressor overhead; they are not automatically invalid. Here, however, the promised symmetry fails directly and no overhead bound or normal-compressor argument is established. Small-object rankings may be dominated by encoding design.

The relevant NCD guarantees are conditional on compressor properties, not simply on inserting lengths into a formula. See Cilibrasi and Vitányi's primary paper, [Clustering by Compression](https://arxiv.org/abs/cs/0312044).

**Repair:** distinguish a custom rational-distribution code length from a CausalBool mechanism code length. Specify a canonical serialization, a decoder for each encoded object/pair, required metadata including N, and consistent compression rules for singles and concatenations. Establish or measure symmetry, self-distance, overhead, and sensitivity to state/node encoding. Compare against simple baselines and general compressors. Report these as computable description lengths; do not promise universal similarity or faithful Kolmogorov-complexity rankings without evidence. A fixed decoder gives an upper bound with decoder/metadata cost, not a tight estimate. A unit test cannot in general calculate uncomputable K to verify the plan's proposed bound numerically.

**Critical theoretical finding 6 — The catalogue-membership detector cannot have the claimed role.**

Protocol §8.3 raises an alarm when a distribution is **outside the attacker's reachable catalogue**. Every enumerated attack lies inside that catalogue by construction. The membership branch consequently adds no alarms against that defined class in the exact-information experiment. If a held-out attack is omitted from a training catalogue, this is a different open-set experiment and must be defined separately.

The baseline is also included in the alternative as currently written. Separate benign and malicious hypotheses, and distinguish identity perturbations from attacks. Changes of wiring are not intrinsically malicious; they need an exogenous loss or authorized-mechanism definition.

There is a further identifiability limit. The two-node matrices `[[0,1],[1,1]]` and `[[1,1],[1,1]]`, both with AND gates, have the same long-run distribution `{0:3/4,3:1/4}` despite different wiring and transition maps. The review reproduces this collision. A detector observing only samples from that distribution cannot distinguish the mechanisms, even with unlimited samples. A deterministic compression statistic of the same exact distribution cannot recover information that has been discarded.

Protocol §9.3 also equates deconvolution with a Bayesian posterior and catalogue membership with a Neyman–Pearson test. Neither follows without a likelihood, observation model, and prior where applicable. Inverse reconstruction is not automatically a posterior; composite alternatives do not automatically admit one uniformly optimal test.

**Repair:** make exact reachable-distribution geometry the first study. For a separate detection study, define what is observed, number of samples, restart/trajectory sampling, noise, benign variability, and attack distribution or worst-case set. Calibrate detectors at a shared false-positive rate using independent benign data and compare held-out power. If observations are i.i.d. states, multinomial likelihoods are available; a single deterministic trajectory requires different dependence assumptions. [Agrawal's finite-sample relative-entropy study](https://arxiv.org/abs/1904.02291) is relevant to the i.i.d. multinomial case, not a blanket justification for trajectory data.

**High-priority finding 7 — The optimization and some proposed theory are incorrect or unimplemented.**

The correct finite-catalogue objective is the maximum expected loss among admissible distributions satisfying the declared divergence budget. In [driver.py](../src/doppel_challenge/driver.py), the reported `optimal_attacker` only requires a non-null divergence; it never applies `D_KL <= C`. The newer add-edge runner reports maxima and rankings without implementing the constrained optimum or calibrated defender comparison.

Protocol §9.2's claimed equivalence between maximizing expected loss and minimizing KL to the unconstrained worst distribution is false in general. If the latter distribution is a point mass, the proposed KL objective is infinite for every candidate that puts mass elsewhere. It cannot rank those candidates by payoff. The exponential tilt is a solution of a convex distributional relaxation under appropriate support and active-constraint conditions; it is not generally an attained network solution or a projection onto a nonconvex finite catalogue.

**A stronger proposed contribution:** compare achievable network payoff with the unconstrained KL-ball benchmark. For bounded loss and finite forward KL, define

\[
V_k(C)=\max_{A\in\mathcal P_k^{\mathrm{adm}}(A_0),\;D_{KL}(\mu_A\|q)\le C} E_{\mu_A}[s].
\]

An upper bound is

\[
V_k(C)\le U(C)=\inf_{\lambda>0}
\frac{C+\log\sum_x q(x)e^{\lambda s(x)}}{\lambda}.
\]

This follows directly from `KL(p || q_lambda) >= 0`, with `q_lambda` the exponential tilt of q. Treat zero budget, constant loss, zero-support targets, and saturation as explicit boundary cases. The gap `U(C)-V_k(C)` quantifies the effect of restricting attacks to network perturbations. Exhaustive small-N catalogues give exact achievable values; sampled large catalogues give observed feasible lower bounds, not certified optima. An ordinary bootstrap over observed attacks cannot certify that no better unobserved attack exists.

Other repairs: the radius-k full Hamming ball contains `sum(comb(N*N,r), r=0..k)`, not `comb(N*N,k)`; N=8,k=3 gives 43,745 including the base. A directed graph cycle does not guarantee a dynamical limit cycle. A cumulative maximum over nested balls is monotone by construction, whereas a maximum or average at exact distance k need not be. Rare outcomes need not have high Kolmogorov complexity. These statements must be corrected before using them as acceptance criteria or scientific interpretations.

**High-priority finding 8 — There is no demonstrated large-N route for the chosen observable.**

`compute_repertoire` explicitly constructs all `2**N` transitions and distributes mass across each starting state's eventual cycle. Long cycles can make the repeated cycle-mass work worse than a single state-space traversal. `enumerate_attractors` builds the transition map again. Every catalogue validation also enumerates all inputs in Wolfram and reconstructs explicit position lists.

Thus the implementation is not linear in N. Even a compact formula for certain queries would not establish linear-time computation of the complete long-run distribution or its divergences. Parent compression helpers can also materialize large `Sumandos` lists and full reconstruction lists. Complexity claims need to identify the actual algorithm, query, arity, intermediate representation size, and output size.

The forecast in the handoff multiplies larger catalogue sizes by the measured N=12 cost per case. It omits the increasing cost per case and is additionally based on a crash-heavy pilot. It is not a defensible N=19 budget.

**Repair:** benchmark each stage and peak memory on a bounded ladder after correctness repair. Reuse transition maps, aggregate mass per basin/cycle once, stream perturbations, and separate validation runs from production computations. For larger N, either prove and implement a compressed algorithm for the exact observable on a stated class, or use explicitly approximate trajectory/restart estimators with convergence and uncertainty checks. Do not claim exact all-state inference at N=60 from the present code.

**High-priority finding 9 — Resumability, provenance, and schema validation are incomplete.**

The catalogue runner buffers its records until the entire loop finishes. Progress snapshots exist, but records are not durable checkpoints and no resume path skips already completed cases. `write_jsonl` opens in `w` mode despite describing append semantics. A crash can lose the useful work; reusing an output path can overwrite an earlier run. There is no timeout in the production Wolfram adapter.

The schema says hash with `sha256` set to an empty string; `canonical_bytes` removes that key instead. Random/time-derived IDs, timestamps, and runtime values enter records and their hashes, so timestamp normalization alone cannot yield the promised repeatable hashes. The legacy driver drops `probability_denominator` before recompressing records, while the codec defaults a missing denominator to 1. Its NCD values can therefore encode counts as unnormalised masses. The newer runner retains the denominator.

There are no implemented `doppel-challenge/tests/` or `schemas/` directories at review time, and no local pytest configuration. The 37 planned implementation/veracity tasks remain marked Ready. Source files and smoke executions are not evidence that their acceptance criteria passed.

**Repair:** persist configuration and provenance before execution; write validated per-case checkpoints atomically; use stable matrix/configuration/content identities alongside distinct run IDs; separate deterministic scientific digests from runtime envelopes. Record source revision or source-tree hashes, Python and Wolfram versions, platform, seeds, gate parameters, actual division size, and failure policy. Implement schema validation and regeneration checks. Consolidate or retire the divergent legacy and current driver paths.

**Additional implementation/design findings.**

| Issue | Evidence or consequence | Required treatment |
|---|---|---|
| Multi-edge IDs collide | `index` ranks within a distance shell without offsets; 11 N=2,k=2 networks produce only 7 distinct IDs including identity | Use stable edge-set/matrix IDs or a correctly offset combinatorial rank before k>1 |
| Graph/gate constraints are not enforced consistently | Guard only checks its mistaken degree condition; self-loop additions and arity increases are unrestricted | Declare loop policy, max/min arity, gate parameters, and admissibility after every move |
| Target selection is biased | Current runner always takes the first sorted base support state, rather than a seeded random target; current family pilots target state 0 | Use prespecified targets/functional losses and report baseline loss and excess loss |
| Topology and logic are confounded | Fixed gate cycle ties gate types to node labels; repaired ER sampling changes its intended ensemble; N=10 with `modules=3` actually creates four blocks via integer division | Define and verify graph ensembles, balance degree/density, vary gate assignments independently, record achieved structure |
| Disjoint/empty cases can crash summaries | Raw min/max and sorting compare numeric divergences with None; empty admissible catalogues also reach min/max | Explicit statuses and denominators for all summaries and rankings |
| Approximate membership undercounts variation | `in_catalogue` sums absolute probability differences only on the intersection | Compute total variation on the union; test approximate matching separately from exact membership |
| Graph samples and distribution samples differ | Multiple graphs can induce one repertoire; repeated catalogue rows are dependent neighbors of one base | Report multiplicity and distinguish graph-uniform summaries from summaries over unique distributions |
| Desired findings are treated as tests | Planned detection >=0.95 and empirical monotonicity conditions pre-impose research outcomes | Test computation/invariants; estimate scientific outcomes, including null and negative results |

**Proposed route to a defensible completion.**

| Milestone | Concrete output | Evidence required before proceeding |
|---|---|---|
| 1. Reconcile the scientific contract | Amended protocol, glossary, schema, and updated task status; explicit observable, adjacency convention, admissibility, loss, and KL semantics | Every implementation field maps to one definition; historical results marked exploratory |
| 2. Repair and validate the small laboratory | Consistent generators/guards, metric corrections, independent exact oracle, actual codec contract, strict kernel acceptance | Asymmetric orientation tests, small exhaustive catalogues, probability/basin checks, cross-engine integration, known counterexamples captured |
| 3. Make runs durable | One documented runner, stable provenance, timeouts, atomic checkpoints, resume, diagnostic logs | Interrupted/resumed execution agrees scientifically with uninterrupted execution; old outputs remain attributable |
| 4. Run a prespecified exact study | Multiple independent networks per topology, independently varied gates, admissible additions/removals, thresholds and losses fixed before evaluation | Report all attempted bases, failures, exclusions, graph counts and unique distributions; uncertainty clustered by base network |
| 5. Evaluate the scientific hypotheses | Achievable-payoff frontiers and relaxation gaps; support-change geometry; compression baselines and ablations | Exact optimum only for exhaustive sets; held-out utility beyond support size/simple metrics; effect sizes with uncertainty |
| 6. Add detection and scale studies where justified | Explicit finite-observation detector comparison and validated approximation/scaling results | Matched false-positive rates, independent calibration/test data, dependence assumptions, runtime/memory/error curves |
| 7. Produce the reproducible paper | Methods/results/discussion, figures with underlying data, software/environment manifest, reproduction command | Every headline traces to a validated artifact; limitations and negative results are included; manuscript compiles |

For the main study, start with ring, sparse-random, modular, and hub families after convention repair, with multiple seeds where randomization is meaningful. Independent base networks are the replication unit; perturbations within one base are clustered observations. Choose replicate counts from pilot variability and a target precision rather than inventing a universal count. Keep an exhaustive small-N reference subset and use stratified sampling with declared weights if larger perturbation balls are sampled. Do not discard bases because they are inconvenient for the compressor; distinguish scientific admissibility from computational failure.

For compression, test whether it improves held-out prediction or detection beyond total variation, support mismatch, support size, and simpler description lengths. Different metric leaders are expected for different objectives and do not by themselves demonstrate an additional scientific contribution. For the phishing motivation, describe this as a constrained generative laboratory unless real message/traffic evidence is added; these pilots do not establish deployment performance against phishing.

**Continuation assessment.** The existing adapter structure, exact small-state machinery, and retained diagnostic artifacts are sufficient to resume productively. The immediate next work should be milestones 1 and 2, beginning with adjacency orientation and the KL/observable contract. Publication readiness should mean a correct, reproducible study with a supported conclusion, including the possibility of a negative result. Neither successful scaling to 60 nodes nor a mechanistic detector advantage can responsibly be promised from the present evidence.
