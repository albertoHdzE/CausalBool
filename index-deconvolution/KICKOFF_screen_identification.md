# Kick-off prompt: identification screen

Paste the text below into a new Claude Code session started in
`~/Documents/projects/CausalBool`.

---

You are running a three-day headroom screen. Read, in full and in this order:
`index-deconvolution/RELATED_METHODS.md`, then
`index-deconvolution/PROTOCOL_screen_identification.md`. The protocol is frozen
and its gates are binding.

**Step 0.** Run `git log -- index-deconvolution/PROTOCOL_screen_identification.md`.
If the protocol is not committed, stop and ask me to commit it: no measurement
may precede the freeze.

Rules:
- Work in `index-deconvolution/`. Scripts go in `index-deconvolution/experiments/`
  and results in `index-deconvolution/results/screen_identification/`. Use the
  repository venv (`venv/bin/python`) and pin every new dependency.
- Before writing any code, find the existing owner (the monolithic-code skill).
  Our arms are existing code: `exact_query_representation`, `deconvolve`,
  `verify_forward`, `num_attractors` and `random_network`. Import them; never
  copy them. If a test file is added, declare it in `tests/MUnit/MANIFEST.tsv`.
- Competitors are run as their own software: BoolNet (R is at
  `/usr/local/bin/R`), PyBoolNet, a BDD package and Z3. A tool that cannot be
  installed and run within 2 hours is recorded with its error and replaced, as
  PROTOCOL §2 says.
- Every model is checked by `verify_forward` before it is scored. Every number
  in any document comes from a script and a results file.
- Do not build new arms. In particular, do not write a query-mode deconvolution
  or an index-based attractor search. If none exists, say so, and the protocol
  already says how that is treated.

Order of work:
1. Freeze the corpus. Generate the synthetic networks with pinned seeds, select
   up to 20 biological models from `data/bio/processed/` that load in every
   tool, and write a manifest with hashes.
2. **S1 and H3**, full table at n ≤ 20: `deconvolve` against BoolNet
   reconstruction and best-fit extension.
3. **S3a**, one-step causal questions: `exact_query_representation` against
   the same questions posed to a BDD package and to Z3, at n from 10 to 200.
   Report time and the size of each answer.
4. **S3b**, multi-step questions: PyBoolNet and BoolNet at every n, and our
   arm where it exists, labelled exhaustive where it is exhaustive.
5. **S2 and H1**, queries: the Akutsu-style competitors against the lower
   bound Q_LB of PROTOCOL §3.
6. Write `results/screen_identification/table.md` and `VERDICT.md`. The
   verdict is STOP, NARROW or GO, applied exactly as PROTOCOL §4 defines it.

After each numbered step, report in three lines at most. Stop after step 6 and
wait for me. Do not commit unless I ask.
