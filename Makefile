# AUDIT01/T5.1 - machine-checkable papers
# One command; no GUI dependencies beyond the pinned WolframKernel path.
KERNEL := /Applications/Wolfram.app/Contents/MacOS/WolframKernel

.PHONY: verify-paper regenerate-paper closure

verify-paper:
	python3 tools/verify_paper_artefacts.py

regenerate-paper: verify-paper
	@echo "all artefacts regenerated and verified"

# AUDIT02/P5.1 — the closure set, run as one command.
#
# It is a QUARTET, not a triad. verify-paper is the only member that reconciles a
# manuscript number against a producer, and it was previously left out of the
# close-out sequence; check-single-engine is new in AUDIT02/P4e. What each member
# does and does NOT prove is documented in tests/MUnit/BASELINE.md.
#
# Non-zero exit is expected while an owned red remains in the MUnit ledger, so
# each member reports its own verdict rather than short-circuiting the run.
closure:
	@echo "── 1/5 paper-number gate (manuscript CHANGE detector, not a correctness check)"
	-@python3 tools/snapshot_paper_numbers.py --check
	@echo "── 2/5 GLOSSARY sync (document mirroring vs the sibling; does NOT check code)"
	-@zsh tools/check_glossary_sync.sh
	@echo "── 3/5 GLOSSARY conformance (the code side the sync check cannot see)"
	-@zsh tools/check_glossary_conformance.sh
	@echo "── 4/5 single-engine guard"
	-@zsh tools/check_single_engine.sh
	@echo "── 5/5 paper artefacts (the only member that ties a number to its producer)"
	-@python3 tools/verify_paper_artefacts.py
	@echo "── MUnit suite: run separately, it is slow"
	@echo "     zsh tests/MUnit/run-tests.sh --all"
