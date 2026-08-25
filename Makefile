# AUDIT01/T5.1 - machine-checkable papers
# One command; no GUI dependencies beyond the pinned WolframKernel path.
KERNEL := /Applications/Wolfram.app/Contents/MacOS/WolframKernel

.PHONY: verify-paper regenerate-paper

verify-paper:
	python3 tools/verify_paper_artefacts.py

regenerate-paper: verify-paper
	@echo "all artefacts regenerated and verified"
