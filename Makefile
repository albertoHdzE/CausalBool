# AUDIT01/T5.1 - machine-checkable papers
# One command; no GUI dependencies beyond the pinned WolframKernel path.
KERNEL := /Applications/Wolfram.app/Contents/MacOS/WolframKernel

.PHONY: verify-paper regenerate-paper closure closure-pure closure-wolfram ci-local suite hooks lint

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

# What a developer must run before pushing: everything CI cannot.
ci-local: closure-wolfram suite

hooks:
	@zsh tools/install_hooks.sh

lint:
	@venv/bin/ruff check --output-format=concise .
