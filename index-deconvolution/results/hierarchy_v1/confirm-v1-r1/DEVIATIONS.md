# confirm-v1-r1 — append-only deviation log

## 2026-10-02 (end of run)

**Run relationship.** Correctness replay of `confirm-v1` under a new freeze (protocol
§7); see `../AMENDMENT_confirm-v1-r1.md`. Same predefined corpus, seeds, SearchConfig,
baselines, resource policy and analysis estimands; not an independent replication and
not a pristine holdout.

**Frozen sources:** unchanged since the freeze (`verify` re-hashes all 18 frozen source
files and the four protocol files; `freeze_problems: []`). No correctness fix was
needed after this freeze; no scientific change was made.

**Incident, no effect.** The first launch of the benchmark chain (17:19:52 UTC) failed in
argument parsing (`zsh` did not word-split the command string; `logs/console_chain.log`
shows the argparse error and `exit 2`). The CLI exited before touching the run: no
corpus manifest, row, archive or budget entry existed afterwards. The chain was
relaunched unchanged at once; the rows come entirely from that second launch.

**Presentation and documentation files created or edited after the freeze** (outside
the frozen set; no numerical semantics):

| file | sha256 (first 16) | change |
|---|---|---|
| `index-deconvolution/hierarchy/present.py` | dd1e856fbfca09ba | tables show the evidence gates, the all-12 aggregate, controls against the statistical codes and the ledger's gate column |
| `index-deconvolution/notebooks/build_16.py` (+ executed notebook `831c7666c00b38fd`) | eff7635368c4aceb | reads `confirm-v1-r1`; corrected C4/C5 and scope prose; §9b post-hoc witness, labelled |
| `index-deconvolution/hierarchy/README.md`, `TESTS.md`, `HANDOFF.md` | 4ec8f8a4a0a593ec, 02ce24bfe2bf733e, f79b64d692ce6ccb | run id, test inventory, supersession banner |

**Environment notes:** the frozen scientific environment equals the current one for
every purpose (`verification.json#environment_differences` is empty).
`tools/check_single_engine.sh` fails on nine checks, every one naming a file under
`.kilo/worktrees/held-saguaro/` (the pre-existing worktree recorded in `confirm-v1`);
no failing check names a file of this stage. Logs under `logs/` are matched by a
repository ignore rule and are retained locally only. `cases.jsonl` (39 MB) is kept out
of history by a local `.gitignore`; see `ARTEFACT_MANIFEST.json`.
