# HANDOFF — gap-ranking-v1-r1

**Status: ready for Codex review; not yet accepted.**

Packet: `../delegation/gap-ranking-v1-r1/` (PROTOCOL.md, OWNERSHIP_AND_IMPORTS.md,
manifest.json; snapshot in `protocol/`). Input manifest verified before execution: 33 of 33
hashes (30 inputs + 3 packet files) matched.

## Results
See `REPORT.md` and `DECISION.md`. vs random expectation: 5 EARLIER / 0 TIE / 9 LATER;
vs canonical: 12 / 0 / 2; 6 cells NO_FULL_REFERENCE (M1 all τ, M3 τ=1). Two of the five
random-beating first hits (M3 τ=8, 16) have constant induced dynamics. Evidence status
VALID_COMPLETE.

## Dependency (U2/U3) — closed for this run, upstream patch unapplied
- Owner extended in an isolated copy only: `dependency/isolated/src/seqdecon/operators.py`
  adds `token_occurrence_frames`; `gaps` unchanged; version and registry
  `phase1.0` → `causal-grouping-gap-v1`.
- operator_group_hash 5d11bdde… → fb3f2aa4…; operators.py sha256 8eab0f32… → 3edf2d90…
  (`dependency/ticket_closure.json`, full trees of both packages).
- `dependency/upstream.patch` (operators.py + new `tests/test_token_occurrence_frames.py`);
  applies cleanly to a scratch copy of the sibling and reproduces the isolated bytes.
- Sibling repository untouched: HEAD d26343a, its pre-existing notebook modification only;
  operators.py still 8eab0f32…; nothing installed; no .pth edits.
- **Integration consequence for review:** applied upstream, the patch makes the sibling's
  pinned-hash test `test_operator_group_hash_is_stable_and_pinned` fail by design (the group
  grew). Its other three failures in this venv (duckdb, `experiments` absent) are identical on
  the original package (`logs/sibling_test_phase1_on_*.log`).
- U3 route: PYTHONPATH = index-deconvolution/src, …/abstraction-validation-v1-r1-source-r2,
  dependency/isolated/src; `src/routes.py` asserts resolved files and hashes and refuses any
  other module loaded from a sibling project path (the venv `.pth` injects sibling repos).
  Resolved identities: `production/imports.json`.

## Freeze, tests, audit
- `freeze.json`: 50 files (protocol, src, tests, dependency, fixtures, declarations, run.sh),
  imported identities, 30 expected inputs; verified unchanged before and after production.
- 73 regression (adopted revision) + 32 focused + 15 dependency tests pass; 6/6 mutants killed.
- Independent audit VALID_COMPLETE; corruptions 3/3 caught.
- `zsh run.sh <fresh dir>` reproduced all outputs byte-identically (`logs/reproduction.log`).
- Preservation: 109,754 protected files (index-deconvolution src/tests/notebooks/bitacora/
  protocols/results except this run, GOVERNANCE, sibling src/tests/docs) unchanged
  (`logs/preservation_diff.json`).

## Wall clock (executor cap 3,300 s; Codex reserve 300 s not used)
Measured from the first packet command (`logs/wallclock.jsonl`): input verification 22 s;
dependency closure 151 s (cap 600); development, fixtures and tests to freeze 530 s (cap
1,200); production, seal and join 9 s (cap 300); audit 12 s (cap 600); reporting,
reproduction, preservation and handoff 140 s (cap 600). Total 842 s. The preceding
repository commit requested by the user is outside this budget.

## Attempts (`attempts/attempts.jsonl`)
A1 sibling tests on the isolated copy; A2 route check rejected a venv module (narrowed,
pre-freeze); A4 a negative state was silently tokenised (now refused, pre-freeze); A5 guard
probe imported from the mutant directory (harness fix, pre-freeze); A6 join and audit
exercised on synthetic seeded labels in /tmp before the freeze — real FULL labels were not
read before sealing, but `nonf3_full_maps.json` was read for constant-dynamics flags (no flag
fired on synthetic data). No post-freeze change of any kind.

## Unresolved / for review
1. Upstream adoption and the pinned finance hash (above).
2. The outcome guard intercepts `open`, `os.listdir`, `os.scandir` and process creation
   audit events; it does not intercept `os.stat`-style metadata calls.
3. `preservation_before.json` was taken just before the freeze, after dependency and
   development work that wrote only inside this run directory and /tmp.
4. F3 first hits have no dynamics evidence (NOT_CHARACTERISED); no endpoint was invented.
5. Score saturation at large τ (REPORT §4) is an observed property of the declared score,
   not repaired here.
6. Scratch directories left in /tmp (ggap_dev1, ggap_repro, ggap_patch, ggap_apply*,
   ggap_phase1); none is needed for reproduction.

No commit, push, publication, schedule or follow-up study was made.
