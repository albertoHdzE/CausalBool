# Related methods: who else answers exact questions about a system

Written 2026-09-29, after the arena-planner verdict (STOP at K0). It records the
established methods that also build exact models or answer exact questions from
compressed representations. The claim "our method answers questions because it
compresses" is not by itself a niche. These tools do that too, and any niche must
be measured against them (`PROTOCOL_screen_identification.md`).

Every reference below was checked against Crossref or arXiv on 2026-09-29.

---

## 1. Exact questions over compressed representations

| Method | What it does | Reference |
|---|---|---|
| Binary decision diagrams (BDDs) | A canonical, often very compact graph for a Boolean function. Operations and questions are answered on the graph without enumerating inputs | Bryant [1] |
| Symbolic model checking | Uses BDDs to ask temporal questions ("can state X ever be reached?") of systems with around 10^20 states and beyond. It is standard in hardware verification | Burch et al. [2] |
| SAT and SMT solvers | Decide whether any input makes a formula true; used industrially for verification and test generation | de Moura and Bjørner [3] |

These tools need the model to be **given**. They answer questions about a known
system; they do not recover the system from its behaviour.

---

## 2. Recovering an exact model of a black box from its behaviour

| Method | What it does | Reference |
|---|---|---|
| Angluin's L* | Learns the minimal deterministic automaton of an unknown regular language from *membership queries* (is this string accepted?) and *equivalence queries* (is this hypothesis right? if not, give a counterexample) | Angluin [4] |
| LearnLib | Open-source library of active automata learning (L*, TTT and others) for Mealy machines and DFAs | Isberner, Howar and Steffen [5] |
| Model learning, survey | Active learning of software and protocol models as black boxes, in practice | Vaandrager [6] |
| Passive identification | Finding the smallest automaton consistent with given data, without queries, is NP-hard | Gold [7] |

**Why this has the right flavour for us.** L* returns the **minimal** automaton
consistent with the behaviour: the shortest description within the class of
finite automata, which is guaranteed by the Myhill–Nerode theorem. That is a
Kolmogorov-style object restricted to one model class, and it is recovered from
the black box's behaviour alone. The spirit is close to our deconvolution.

**The difference that matters.** L* learns systems with **inputs and hidden
state**: a small automaton driven by an input stream. Our deconvolution learns
an autonomous synchronous network whose state is fully observable, where the
difficulty is the width of the state (n bits and 2^n states), not a hidden
memory. Treated as a transition system, an n-node network has up to 2^n states,
far beyond what L* handles directly. The two methods are therefore complementary
before they are competitors, and the screen measures where each wins.

---

## 3. Recovering Boolean networks specifically

These are the direct competitors of the deconvolution.

| Method | Access | Reference |
|---|---|---|
| Identification from few expression patterns | random state–successor samples; bounded in-degree k; sample count grows only logarithmically in n | Akutsu, Miyano and Kuhara [8] |
| Identification by strategic disruptions and over-expressions | chosen perturbations (queries) | Akutsu, Kuhara, Maruyama and Miyano [9] |
| Best-fit extension and consistency | samples with errors; learning theory of the Boolean network model | Lähdesmäki, Shmulevich and Yli-Harja [10] |
| BoolNet | R package: reconstruction from time series, attractor search | Müssel, Hopfensitz and Kestler [11] |
| PyBoolNet | Python package: attractors and model checking of Boolean networks through external solvers | Klarner, Streck and Siebert [12] |

---

## 4. Why none of this transfers directly to the time-series and finance side

Active automata learning is the closest in spirit to what the time-series
programme wants: an exact model of a black box, recovered from its behaviour.
It does not transfer directly, for three reasons. Each reason is a property of
markets, not a weakness of the method.

1. **No queries.** L* requires choosing an input and observing the answer. A
   market cannot be queried; it can only be watched. Without queries the
   problem becomes passive identification, which is NP-hard even for exact,
   noise-free data [7].
2. **No determinism.** L* assumes the same input always gives the same output.
   Market data are stochastic and noisy, so exact consistency with every
   observation is the wrong goal. It leads to overfitting, not to the
   mechanism.
3. **No stationarity.** An automaton is one fixed machine. A market's
   generating process drifts over time. That is why our own clock results are
   judged against nulls and eras rather than by exact reproduction.

**What does exist for passive, stochastic sequences:**
- **State-merging learners of stochastic automata** (ALERGIA, Carrasco and
  Oncina [13]). These are L*'s cousins for noisy data that cannot be queried.
- **Computational mechanics:** the ε-machine is the minimal causal-state model
  of a stochastic process (Crutchfield and Young [14]). CSSR reconstructs it
  from a discrete sequence without being told its structure (Shalizi and
  Shalizi [15]).

The ε-machine is the closest established object to what the clock work is
looking for: a minimal machine whose states are the distinct futures the past
predicts. One caution applies. Its usual complexity measure, *statistical
complexity*, is a Shannon entropy over causal states, which our programme does
not use as a complexity measure (`GOVERNANCE/DESCRIPTION_LENGTHS.md`, enforced by
`tests/analysis/test_description_length_is_algorithmic.py`). The construction can
serve us; the measure cannot.

**A concrete, falsifiable use.** Discretise the pivot-clock sequences exactly
as the clock experiments already do, run CSSR on them, and compare its
held-out predictions with our clock model under the same null. If CSSR matches
us, the clock finding is a known kind of structure. If it does not, that is
evidence the clock carries something a minimal stochastic automaton misses.
This belongs to the time-series programme, not to the screen below.

---

## References

1. Bryant, R. E. (1986). Graph-Based Algorithms for Boolean Function
   Manipulation. *IEEE Transactions on Computers* C-35, 677–691.
   doi:10.1109/TC.1986.1676819
2. Burch, J. R., Clarke, E. M., McMillan, K. L., Dill, D. L. and Hwang, L. J.
   (1992). Symbolic model checking: 10^20 states and beyond. *Information and
   Computation* 98, 142–170. doi:10.1016/0890-5401(92)90017-A
3. de Moura, L. and Bjørner, N. (2008). Z3: An Efficient SMT Solver. *TACAS
   2008*, LNCS 4963, 337–340. doi:10.1007/978-3-540-78800-3_24
4. Angluin, D. (1987). Learning regular sets from queries and counterexamples.
   *Information and Computation* 75, 87–106.
   doi:10.1016/0890-5401(87)90052-6
5. Isberner, M., Howar, F. and Steffen, B. (2015). The Open-Source LearnLib.
   *CAV 2015*, LNCS, 487–495. doi:10.1007/978-3-319-21690-4_32
6. Vaandrager, F. (2017). Model learning. *Communications of the ACM* 60(2),
   86–95. doi:10.1145/2967606
7. Gold, E. M. (1978). Complexity of automaton identification from given data.
   *Information and Control* 37, 302–320. doi:10.1016/S0019-9958(78)90562-4
8. Akutsu, T., Miyano, S. and Kuhara, S. (1999). Identification of genetic
   networks from a small number of gene expression patterns under the Boolean
   network model. *Pacific Symposium on Biocomputing* 1999, 17–28.
   doi:10.1142/9789814447300_0003
9. Akutsu, T., Kuhara, S., Maruyama, O. and Miyano, S. (2003). Identification
   of genetic networks by strategic gene disruptions and gene overexpressions
   under a Boolean model. *Theoretical Computer Science* 298, 235–251.
   doi:10.1016/S0304-3975(02)00425-5
10. Lähdesmäki, H., Shmulevich, I. and Yli-Harja, O. (2003). On Learning Gene
    Regulatory Networks Under the Boolean Network Model. *Machine Learning* 52,
    147–167. doi:10.1023/A:1023905711304
11. Müssel, C., Hopfensitz, M. and Kestler, H. A. (2010). BoolNet — an R
    package for generation, reconstruction and analysis of Boolean networks.
    *Bioinformatics* 26, 1378–1380. doi:10.1093/bioinformatics/btq124
12. Klarner, H., Streck, A. and Siebert, H. (2017). PyBoolNet: a python
    package for the generation, analysis and visualization of boolean
    networks. *Bioinformatics* 33, 770–772. doi:10.1093/bioinformatics/btw682
13. Carrasco, R. C. and Oncina, J. (1994). Learning stochastic regular grammars
    by means of a state merging method. *ICGI 1994*, LNCS 862, 139–152.
    doi:10.1007/3-540-58473-0_144
14. Crutchfield, J. P. and Young, K. (1989). Inferring statistical complexity.
    *Physical Review Letters* 63, 105–108. doi:10.1103/PhysRevLett.63.105
15. Shalizi, C. R. and Shalizi, K. L. (2004). Blind Construction of Optimal
    Nonlinear Recursive Predictors for Discrete Sequences. arXiv:cs/0406011.
