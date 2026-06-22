## Root Wrapper Archive

This directory stores former repository-root wrapper scripts that are not part of the current preferred interface.

Policy:

- preserve small historical entrypoints instead of deleting them outright
- move wrappers here when they are redundant, stale, or operationally weaker than the module entrypoints they wrap
- keep active root-level entrypoints in place when they still provide a documented or clearly intentional interface

Current contents:

- `process_data.py`: archived because it was an unreferenced root wrapper, lacked the `src/` bootstrap used by the other surviving root wrappers, and duplicated processing entrypoints already exposed by `src/integration/grn_data_pipeline.py`
- `run_process.py`: archived because it was an unreferenced root wrapper around `BulkScraper.process_raw_files()`, and the same functionality is available via `src/integration/BulkScraper.py` and other module-level entrypoints
- `report_dataset.py`: archived because it was an unreferenced operator utility and did not need to occupy the repository root
