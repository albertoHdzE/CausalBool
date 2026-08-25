# Generated Web Bundles Archive

This directory stores large generated JavaScript bundles moved out of the repository root during cleanup on the `clean` branch.

The archived files are build artifacts rather than handwritten project source.
They were preserved because they may still have historical or forensic value, but they are not treated as active repository entrypoints.

Archive policy for this directory:

- keep the bundles unchanged
- preserve original filenames for traceability
- do not treat archived bundles as authoritative source code

See `mapping/move_delete_candidates.md` and `mapping/cleaning_bitacora.md` for the supporting rationale.
