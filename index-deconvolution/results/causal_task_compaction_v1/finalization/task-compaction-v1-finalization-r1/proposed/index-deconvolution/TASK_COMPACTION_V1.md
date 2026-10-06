# Task-preserving state compaction, v1

This note is the user-facing contract of three functions in
`index-deconvolution/src/deconvolution.py`: `minimal_task_partition`,
`distinguishing_task_word` and `task_word_path`. It states what they compute, what they
accept, what they return, what they cost and what they do not claim. The examples below
are executable: `python -m doctest TASK_COMPACTION_V1.md` runs them against the active
owner (see *Reproducing* at the end).

## The contract

The inputs are a **supplied, total, deterministic model**:

- a finite state set `{0, …, N-1}`;
- an ordered, non-empty list of `Q` action tables `T_0, …, T_{Q-1}`, each a complete map
  of the whole state set into itself (a table is a list or tuple of length `N`);
- an observable `outputs`, a list or tuple of `N` non-negative integer labels.

Every state is an admissible starting state; nothing is pruned by reachability. An
action is identified by its position, so two equal tables remain two actions. A *word*
is a finite sequence of action indices applied in written order, first letter first;
the empty word is permitted.

`minimal_task_partition` returns the **coarsest** grouping `alpha*` of all `N` states
such that two states in the same group have the same observable **now and after every
permitted word**. Because the empty word is permitted, equal groups imply equal current
outputs. Equivalently, `alpha*` is the greatest partition that refines the output
partition and is closed under every action table, so it carries exact macro dynamics:
one macro table per action and a decoder from groups to outputs, both checked on every
state before the function returns. `K* = max(alpha*) + 1` is the number of groups.

Two consequences of this contract are often misread.

- **State-count reduction is not archive-bit reduction.** `K* < N` says that fewer
  *states* suffice for this observable under these actions. It says nothing about the
  number of bits needed to store the model, the grouping map, the decoder or the macro
  tables, all of which are additional objects.
- **`K* = N` is a result, not a failure.** It means that, for this contract, no smaller
  exact state grouping exists: every pair of distinct states is separated by some
  permitted word. The pair-separating word may differ from pair to pair. Nothing here
  asserts the existence of a single universal distinguishing experiment that separates
  all pairs at once.

Every claim is scoped to the supplied model, the supplied action list and the supplied
observable. Adding an action can only refine the grouping; changing the observable
changes the problem.

## The three functions

### `minimal_task_partition(outputs, transitions) -> dict`

Accepts `outputs` as a non-empty list or tuple of non-negative built-in integers, and
`transitions` as a non-empty list or tuple of tables, each a list or tuple of length
`len(outputs)` whose entries are built-in integers in `0 … N-1`. `bool` is rejected
everywhere and nothing is coerced. A malformed call raises `ValueError` before any
evaluation; every table is checked, including tables that would never be used.

It returns a dictionary (the *certificate*):

| key | meaning |
|---|---|
| `alpha` | the stable grouping `alpha*`, labelled in order of first appearance |
| `K` | the number of groups, `max(alpha) + 1` |
| `stages` | `P_0 = ` canonical output partition, then each refinement `P_{d+1}`, ending with the first repeated vector, so `stages[-1] == stages[-2]` |
| `strict_rounds` | `len(stages) - 2` |
| `representatives` | the smallest state of each group |
| `decoder` | `decoder[k]` is the output of group `k` |
| `macro` | `macro[q][k]` is the group reached from group `k` by action `q` |
| `coarsening` | `coarsening[d][k]` is the `P_d` group containing `P_{d+1}` group `k` |

`P_d(x) == P_d(y)` holds exactly when every word of at most `d` actions gives equal
outputs from `x` and `y`. `P_d` alone preserves outputs only up to horizon `d` and is in
general not closed under the actions.

### `distinguishing_task_word(outputs, transitions, stages, x, y) -> list[int] | None`

Returns a shortest word whose final outputs differ when it is applied from `x` and from
`y`, with ties broken by the lexicographically least action-index word. It returns
`None` exactly when `x` and `y` share a group of `stages[-1]`, and `[]` when their
current outputs already differ.

`stages` must be the `stages` of a certificate produced by `minimal_task_partition` for
the same `outputs` and `transitions`. The function checks the contract of its inputs,
the shape of `stages` (at least two vectors of length `N`, ending in a repeated vector)
and the consistency of the certificate along the path it follows. These checks are
**not** a verification of the certificate: a well-shaped but wrong `stages` can produce
a wrong answer. Full certificate verification is the separate, independent audit of the
v1 evidence package, not part of this function.

### `task_word_path(transitions, x, word) -> list[int]`

Returns the states visited from `x` when `word` is applied in written order, starting
with `x` itself, so the result has `len(word) + 1` entries. `transitions` obeys the same
contract as above, `x` is a built-in integer state and `word` is a list or tuple
(possibly empty) of built-in integer action indices. Everything is validated before the
first step; a generator, a set, a `bool` or an out-of-range index raises `ValueError`.

## Worked examples

The examples use fixtures declared before the first execution in
`tests/fixtures/task_compaction_v1.json`; nothing here is a new benchmark.

    >>> import sys; sys.path.insert(0, "src")
    >>> from deconvolution import minimal_task_partition, distinguishing_task_word, task_word_path

### A two-step separation (fixture `FX3_two_step`)

Four states, one action, and an observable that is `1` only in state 2.

    >>> outputs, T = [0, 0, 1, 0], [[1, 2, 2, 0]]
    >>> r = minimal_task_partition(outputs, T)
    >>> r["stages"]
    [[0, 0, 1, 0], [0, 1, 2, 0], [0, 1, 2, 3], [0, 1, 2, 3]]
    >>> r["K"], r["strict_rounds"]
    (4, 2)

States 0, 1 and 3 look alike now. One step separates state 1 (it moves to state 2,
output 1) from 0 and 3. Two steps are needed to separate 0 from 3:

    >>> distinguishing_task_word(outputs, T, r["stages"], 0, 3)
    [0, 0]
    >>> task_word_path(T, 0, [0, 0]), task_word_path(T, 3, [0, 0])
    ([0, 1, 2], [3, 0, 1])
    >>> [outputs[s] for s in task_word_path(T, 0, [0, 0])], [outputs[s] for s in task_word_path(T, 3, [0, 0])]
    ([0, 0, 1], [0, 0, 0])
    >>> distinguishing_task_word(outputs, T, r["stages"], 0, 2), task_word_path(T, 0, [])
    ([], [0])

Here `K* = N = 4`: every pair is separated by some word, so no smaller exact grouping
exists for this contract. That is the answer, not a shortcoming of the algorithm.

### Adding an intervention action (fixture `FX4_added_action`)

With only the identity action, the observable `[0, 0, 1, 1]` is preserved by grouping
`{0, 1}` and `{2, 3}`:

    >>> outputs = [0, 0, 1, 1]
    >>> auto = minimal_task_partition(outputs, [[0, 1, 2, 3]])
    >>> auto["alpha"], auto["K"], auto["decoder"], auto["macro"]
    ([0, 0, 1, 1], 2, [0, 1], [[0, 1]])
    >>> distinguishing_task_word(outputs, [[0, 1, 2, 3]], auto["stages"], 0, 1) is None
    True

Declaring a second, intervention action `b = [0, 2, 2, 3]` (it moves state 1 to state 2)
splits the first group, because `b` separates 0 from 1 in one step:

    >>> T = [[0, 1, 2, 3], [0, 2, 2, 3]]
    >>> intv = minimal_task_partition(outputs, T)
    >>> intv["alpha"], intv["K"], intv["macro"]
    ([0, 1, 2, 2], 3, [[0, 1, 2], [0, 2, 2]])
    >>> distinguishing_task_word(outputs, T, intv["stages"], 0, 1)
    [1]

The intervention grouping refines the autonomous one, as it must: more permitted words
can only separate more states.

## Cost

These are algorithmic bounds for this implementation, not measured resource guarantees.

- **Input.** The explicit tables hold `Q·N` entries; for `n` Boolean variables
  `N = 2^n`, so the contract is exponential in `n` before any computation starts.
- **Storage.** Every refinement stage is retained in the certificate. With `R` stages,
  `R = O(N)` (at most `N - K_0` strict rounds plus the initial and repeated vectors),
  the stages add `R·N` entries. The macro tables add `Q·K* ≤ Q·N`, and the coarsening
  maps add at most `R·N`. Worst-case storage is therefore `O(Q·N + N^2)` entries,
  before the constant overhead of Python objects.
- **Time.** Each round builds an `(Q+1)`-tuple signature per state and relabels, which
  is `O(Q·N)` expected time with hashing; with `O(N)` rounds the worst case is the
  classical `O(Q·N^2)`. This is the classical layer-wise refinement, **not** a Hopcroft
  implementation, and the faster refinement variants discussed by Knuutila (2001, §3.2
  onward) are not implemented.

## Position in the literature

This component is an implementation and application of established partition-refinement
theory, packaged with certificates, witnesses and an independent evidence audit. No
novelty is claimed for the theorem, the algorithm or the packaging. The contribution is
factual: a tested owner function under an explicit all-start, multi-action,
arbitrary-observable contract, a certificate that can be checked independently, and a
validated small-model evidence package.

The mappings below are scoped exactly as stated; the source versions read are recorded
in the v1 review-closure literature map.

- **Knuutila (2001)**, *Re-describing an algorithm by Hopcroft*, Theoretical Computer
  Science 250, 333–363, §2.3–2.4 and Proposition 4. `alpha*` is the greatest congruence
  of the unary algebra `({0..N-1}; T_0..T_{Q-1})` that saturates the kernel of
  `outputs`: Knuutila's construction with the binary final-state partition replaced by
  the output partition, computed by the layer-wise refinement of Proposition 4. Unlike
  Knuutila, the quotient is taken over the whole state set, not a connected automaton.
- **Zhang and Zhang**, arXiv:1405.6780v2, Definition 5. Encoding the model as a Boolean
  control network (one input value per action, outputs encoded injectively), `K* = N`
  holds exactly when that network is observable in the sense of Definition 5, which asks
  for one separating input sequence **per pair** of states. It is strictly weaker than
  their Definition 6 (one sequence for all pairs); nothing here concerns Definition 6.
- **Argyris et al.**, arXiv:2206.15169v3 (generalised forward bisimulation, GFB), and
  BMC Bioinformatics 24(Suppl 1):212, 2023 (Boolean backward equivalence, BBE). Both
  group *variables* rather than states. BBE preserves dynamics only on states constant on
  each block, so it is a different contract. When the observable factors through a GFB
  aggregate that is valid for every action table, that aggregate is a valid grouping
  with at least `K*` groups: it gives an upper bound on `K*`, never a smaller exact
  grouping.

## What v1 does not do

- **Faster refinement.** Hopcroft-style refinement would improve time under the same
  contract but is not implemented.
- **Symbolic methods.** BDD- or SAT-based bisimulation that avoids explicit tables is
  outside v1; it was not read and no claim is made about it.
- **Finite-horizon or approximate grouping.** Each would be a new contract, not a
  parameter of this one. A finite horizon `d` has the preserved-partition `P_d` already
  in the certificate, but `P_d` is in general not closed under the actions, so a contract
  would have to give up exact macro dynamics or index them by horizon. An approximate
  contract needs a stated tolerance, which could be a worst-case bound over all starts
  and words or a measure over starts and/or words. Neither is implemented here.

The one condition under which a successor would be justified is a concrete application
that cannot use the explicit-table contract (for example, a model whose `Q·N` tables
cannot be materialised). No such successor is planned.

## Reproducing

Scoped active tests, run from `index-deconvolution/` (the empty configuration keeps the
repository-wide collection rules out of this scoped run), then these examples:

    cd index-deconvolution
    PYTHONDONTWRITEBYTECODE=1 ../venv/bin/python -m pytest -q -p no:cacheprovider -c /dev/null --rootdir=. \
        tests/test_deconvolution.py tests/test_abstraction.py \
        results/causal_abstraction_validation/abstraction-validation-v1-r1-source-r2/test_study.py \
        tests/test_task_compaction.py
    PYTHONDONTWRITEBYTECODE=1 ../venv/bin/python -m doctest TASK_COMPACTION_V1.md

The owner tests need no result directory. The saved v1 evidence is verified, against the
historical identities frozen for it, by the finalization package's
`VERIFY_HISTORICAL.sh` under
`results/causal_task_compaction_v1/finalization/task-compaction-v1-finalization-r1/`.
