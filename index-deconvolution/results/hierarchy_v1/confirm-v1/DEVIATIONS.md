# confirm-v1 — append-only deviation log

## 2026-10-02 (end of run)

**Frozen sources:** unchanged since the freeze (`verify` re-hashes all 17 frozen source
files and the four protocol files; `freeze_problems: []`). No run was invalidated; no
correctness fix was needed after freezing; no scientific change was made after seeing
held-out results.

**Presentation files created or edited after the freeze** (outside the frozen set; no
numerical semantics):

| file | sha256 (first 16) | change |
|---|---|---|
| `index-deconvolution/hierarchy/present.py` | e19775a277468112 | new: markdown tables and handoff artefacts from stored rows/archives |
| `index-deconvolution/notebooks/build_16.py` | db7fe5bac3ce0da6 | new: notebook 16 builder (reads saved artefacts) |
| `index-deconvolution/notebooks/build_15.py` | 1833e4ad19d32d76 | the author's own comment block (A64/A72 as 8-bit rows), added by hand to the executed notebook 15 at 09:43 local time, folded verbatim into the builder so builder and notebook agree; the author's edited notebook is preserved at `development/provenance/untracked_copies/15_shifted_zero_bdm_probe.author_edit_0943.ipynb` |

**Environment notes:** `tools/check_single_engine.sh` fails on nine checks, every one
naming a file under `.kilo/worktrees/held-saguaro/`, a separate worktree dated
2026-10-01 23:14 that predates this stage and was not touched. Logs under `logs/` are
matched by a repository ignore rule and are retained locally only. `cases.jsonl` (39 MB)
is kept out of history by a local `.gitignore`; see `ARTEFACT_MANIFEST.json`.
