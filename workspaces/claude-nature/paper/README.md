# Nature Paper Workspace

This directory is the active Nature-facing paper execution workspace.

## Role

- `code/`: executable paper pipelines and reproduction entry points
- `figures/`: manuscript-facing generated figures and summary tables
- top-level `.tex` and `.md` files: process reports, plans, and manuscript-support text

## Relationship to `doc/`

- `doc/newIntPaper/` preserves planning and process-history material.
- `doc/finalpaper/` preserves manuscript assembly and historical draft variants.
- This directory is the most operational paper branch in the repository and should be treated as the active reproducibility workspace.

## Cleaning note

- Prefer preserving code, plans, and provenance here.
- Remove only generated clutter when it is reproducible and clearly non-source.
