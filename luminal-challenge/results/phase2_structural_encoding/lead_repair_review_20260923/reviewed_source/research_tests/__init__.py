"""Package marker for the phase 2 research tests.

These modules test ``research/`` only. They live outside ``tests_direct/``
because the frozen historical evidence checker discovers every top-level Python
file there by glob and requires it to appear in a provenance record written
before this work existed. The lead's repair decision of 2026-09-23 relocates
them here; the original delegation package remains as historical input.
"""
