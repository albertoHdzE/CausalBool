"""Package marker for src/stats.

AUDIT04 Phase 1. This file exists for a measurement reason, not a stylistic one.

coverage.py can only enumerate the files it has NOT executed when they sit
inside an importable package. Without this marker, `--cov=src` reported only
the modules some test happened to import, so src/ showed 25 of its 54 files and
a coverage FLOOR over src/ could never have failed -- it would have been
measured against whatever the tests already touched.

Measured before adding these seven markers:

    src/data          __init__.py present   4 of 4 files reported
    src/integration   __init__.py present  18 of 18 files reported
    the other seven   no marker            only what a test imported

That is the same class of defect as the `-@` Makefile prefixes this programme
removed: an instrument that cannot report a failure.

tools/check_verification_numbers.py now refuses when the number of files in the
coverage report differs from the number of .py files on disk, so deleting this
marker goes red rather than going quiet.
"""
