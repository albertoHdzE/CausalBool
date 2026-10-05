# Prospective ownership ticket — abstraction (fibre) checker

**Status: PROPOSED. No source, governance or core file was edited.** Acceptance by Codex/user is
required before any code.

- **Owner:** `index-deconvolution/src/deconvolution.py` (REVIEW R3 prospective choice). It already
  owns `Network` tables and `essential_variables` (line 95), which Track X uses.
- **Proposed API (names indicative):** `induced_map(alpha_codes, image_codes) -> dict | None`
  (None iff the fibre condition fails; witness pair returned separately); `compare_induced(rep,
  member) -> AGREE | DISAGREE(d) | NOT-EVALUABLE(reason)`. Inputs are integer arrays over X; no
  study semantics (β schemes, labels) enter the core.
- **Study orchestration:** thin, run-local, imports the core; holds β schemes, decision table,
  ledgers. No second checker anywhere (the earlier `check_witnesses.py` is a run-local witness
  script and is not promoted).
- **Guard (Q4):** a manifest/grep guard that fails when a second definition of the fibre condition
  appears outside the owner, verified by planting a copy, shipped with the code.
- **Dependencies outside this ticket:** U2 block-value occurrence extractor — owner
  `../series-deconvolution/src/seqdecon/operators.py` has `gaps` (line 133) but no extractor of
  frames where a block equals a value; an upstream ticket is needed there. U3 — no declared import
  route from CausalBool to the sibling package. Both block Track G only.
