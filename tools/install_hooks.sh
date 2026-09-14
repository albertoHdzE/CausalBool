#!/usr/bin/env zsh
# AUDIT03-C — install the repository's git hooks.
#
# .git/hooks is NOT version-controlled, so a hook committed to the tree does
# nothing until git is told where to look. core.hooksPath points at the tracked
# githooks/ directory, so the hook travels with the repository and every clone
# gets it by running this once.
#
#   exit 0  installed and verified
#   exit 1  could not install
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

if [[ ! -d githooks ]]; then
  echo "INSTALL-HOOKS: REFUSED — no githooks/ directory in this repository."
  exit 1
fi

git config core.hooksPath githooks || exit 1
chmod +x githooks/* 2>/dev/null

configured=$(git config core.hooksPath)
if [[ "$configured" != "githooks" ]]; then
  echo "INSTALL-HOOKS: FAIL — core.hooksPath is '$configured', expected 'githooks'"
  exit 1
fi

echo "INSTALL-HOOKS: core.hooksPath -> githooks"
for h in githooks/*(N); do
  [[ -x "$h" ]] && echo "  installed: ${h:t}" || echo "  NOT EXECUTABLE: ${h:t}"
done
echo ""
echo "pre-push runs 'make ci-local' — the Wolfram tier and the 69-test MUnit"
echo "suite, neither of which CI can run. Bypass: git push --no-verify"
