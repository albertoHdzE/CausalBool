# Causal state grouping — source revision r2

Accepted robustness correction to abstraction-validation-v1-r1. This is a separately identified source revision, not a new study or a replacement result. study.py and test_study.py are byte-identical to the reviewed Claude correction. The original frozen study and all V/D/X results remain unchanged. No production runner or execution authorization is supplied.

R1 corrects incomplete-evidence decisions; R2 is adopted in the existing core owner. Identity and preserved frozen core/test bytes are in ../supervision/abstraction-validation-v1-r1-closure/adoption.json. The original freeze still describes the historical sources; the active core now has a new identity. To reproduce the historical freeze, use an isolated repository copy and restore the two snapshots listed there to their original paths. Do not rewrite the old freeze or its source in place.

Run regression tests from the repository root with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=index-deconvolution/src using pytest -p no:cacheprovider, the active tests/test_deconvolution.py and tests/test_abstraction.py, and this revision's test_study.py. This runs fixture tests only.
