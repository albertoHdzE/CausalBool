# AUDIT01/T5.1 - machine-checkable papers
# One command; no GUI dependencies beyond the pinned WolframKernel path.
KERNEL := /Applications/Wolfram.app/Contents/MacOS/WolframKernel

.PHONY: help verify-paper regenerate-paper closure closure-pure closure-wolfram \
        ci-local suite suite-section sections test-python test-deconv test-subprojects \
        hooks lint

# `make` with no target must tell you what you can run. The selection below
# already existed inside run-tests.sh and pytest, but you had to read the shell
# script to discover that --section was a flag at all.
help:
	@echo "CausalBool — targets"
	@echo ""
	@echo "  RUN EVERYTHING CI CANNOT"
	@echo "    make ci-local             closure-wolfram + the 69-test MUnit suite"
	@echo ""
	@echo "  SELECTIVE — Wolfram"
	@echo "    make sections             list the MUnit sections"
	@echo "    make suite                all 69 MUnit tests (~40 min, run SERIALLY)"
	@echo "    make suite-section S=Gates        one section"
	@echo "    make suite-section S=Analysis G=NOT   one gate within a section"
	@echo ""
	@echo "  SELECTIVE — Python"
	@echo "    make test-python          tests/analysis (134) with the coverage gate"
	@echo "    make test-python K=kraft  only tests matching a -k expression"
	@echo "    make test-deconv          index-deconvolution (146)"
	@echo "    make test-subprojects     the four replication packages (28/97/47/41)"
	@echo ""
	@echo "  GATES"
	@echo "    make closure-pure         7 gates, no kernel needed — what CI runs"
	@echo "    make closure-wolfram      4 gates needing a local licensed kernel"
	@echo "    make closure              both"
	@echo "    make lint                 ruff, enforced rule set"
	@echo "    make hooks                install the pre-push hook (once per clone)"
	@echo ""
	@echo "  NOTE: which tests cover which owner is MEASURED, not guessed —"
	@echo "        see audit/AUDIT03_R2_collapse/MUTATION.md."

verify-paper:
	python3 tools/verify_paper_artefacts.py

regenerate-paper: verify-paper
	@echo "all artefacts regenerated and verified"

# AUDIT03-C — the closure set now DELEGATES to tools/run_closure.sh.
#
# It used to be a list of `-@` recipe lines. The `-` prefix tells make to ignore
# the error, so `make closure` exited 0 EVEN IF ALL NINE MEMBERS FAILED, and one
# member piped into `head` so its status was head's. A green `make closure` meant
# nothing, and putting it in CI would have produced a permanently green badge.
#
# The `-` prefix did buy one real property -- a single red must not hide the
# other eight -- and run_closure.sh keeps it by running every member, recording
# each verdict, and failing at the end.
#
# The tiers exist because the Wolfram members need a licensed local kernel that
# GitHub-hosted runners do not have. CI runs `closure-pure` and says plainly
# that it is not the whole story; the pre-push hook (make hooks) is what stops
# the Wolfram tier being silently skipped.

closure-pure:
	@zsh tools/run_closure.sh pure

closure-wolfram:
	@zsh tools/run_closure.sh wolfram

closure:
	@zsh tools/run_closure.sh all

suite:
	@zsh tests/MUnit/run-tests.sh --all

# Sections are DIRECTORIES under tests/MUnit, and membership is declared in
# MANIFEST.tsv rather than discovered by a glob.
sections:
	@echo "MUnit sections (use: make suite-section S=<name> [G=<gate>]):"
	@ls -d tests/MUnit/*/ | sed 's|tests/MUnit/||; s|/$$||' | grep -v '^results$$' | sed 's|^|  |'

# S is required; G is optional. Refusing on an empty S matters -- without it
# run-tests.sh would receive `--section ""` and quietly select nothing, which is
# the "green over zero cases" failure this programme keeps finding.
suite-section:
	@if [ -z "$(S)" ]; then \
	  echo "REFUSED: give a section, e.g. make suite-section S=Gates"; \
	  echo "         (make sections lists them)"; exit 2; fi
	@if [ -n "$(G)" ]; then \
	  zsh tests/MUnit/run-tests.sh --section $(S) --gate $(G); \
	else \
	  zsh tests/MUnit/run-tests.sh --section $(S); fi

# AUDIT04-E: no longer `tests/analysis` only. That path was the entire Python
# suite as far as this Makefile, CI and the coverage gate were concerned, while
# 24 declared-by-nothing files under tests/Bio, tests/Lev4-7 and tests/Nature ran
# in no command at all. pytest.ini now names every directory holding a declared
# test and conftest.py takes membership from tests/MUnit/MANIFEST.tsv, so the
# bare invocation IS the declared suite.
test-python:
	@if [ -n "$(K)" ]; then \
	  venv/bin/python -m pytest -q -k "$(K)" --tb=short; \
	else \
	  venv/bin/python -m pytest -q --cov --cov-config=.coveragerc --cov-report=json --tb=short; \
	  venv/bin/python tools/check_coverage_ratchet.py; fi

test-deconv:
	@cd index-deconvolution && ../venv/bin/python -m pytest -q --tb=short

test-subprojects:
	@for d in imp-causal-paper imp-prices imp-causalNet-paper imp-pathinfo-paper; do \
	  echo "── $$d"; \
	  ( cd $$d && .venv/bin/python -m pytest -q -p no:warnings --tb=short ) || exit 1; \
	done

# What a developer must run before pushing: everything CI cannot.
ci-local: closure-wolfram suite

hooks:
	@zsh tools/install_hooks.sh

lint:
	@venv/bin/ruff check --output-format=concise .
