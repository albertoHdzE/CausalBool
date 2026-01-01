# Changelog

## v0.1.0 (2025-12-05)
- Augmented gate truth table tests to support arities up to 6 (backward compatible default was 4)
- Added per-case timing metrics and generated performance report structure (`PerfTT001.json`, `Report.txt`)
- Enhanced documentation: inlined TEST-001 summary table and added professional interpretation in `doc/newIntPaper/expProcess.tex`
- Added visual placeholders: index mapping figure (LSB→MSB via φ) and compact formula box (parameters, mapping)
- Noted limitations: exponential growth for high arities; special cases (NOT arity 1; IMPLIES/NIMPLIES arity 2; KOFN parameterisation)
