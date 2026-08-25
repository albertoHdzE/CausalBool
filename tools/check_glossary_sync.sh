#!/usr/bin/env zsh
# AUDIT01/T1.4 — GLOSSARY sync check (three-state, v1.2 semantics)
#   exit 0  clean      in-repo copy body == sibling canonical body
#   exit 1  drift      both exist but bodies differ -> refresh GOVERNANCE/GLOSSARY.md
#   exit 2  SYNC-UNKNOWN  sibling absent (or no in-repo copy) -> nothing may be claimed
# Bodies are compared AFTER stripping the provenance header (lines up to first "---").
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$REPO/GOVERNANCE/GLOSSARY.md"
SIBLING="${GLOSSARY_SIBLING:-$HOME/Documents/projects/series-deconvolution/GLOSSARY.md}"
body() { awk 'found{print} /^---$/{found=1}' "$1"; }
if [[ ! -f "$SIBLING" ]]; then
  echo "SYNC-UNKNOWN: sibling absent at $SIBLING"
  exit 2
fi
if [[ ! -f "$LOCAL" ]]; then
  echo "SYNC-UNKNOWN: no in-repo copy at $LOCAL (run plan task T1.4 step 1)"
  exit 2
fi
if diff -q <(body "$LOCAL") <(body "$SIBLING") >/dev/null; then
  echo "GLOSSARY sync: clean"
  exit 0
else
  echo "GLOSSARY DRIFT detected vs $SIBLING — refresh the synchronized copy"
  exit 1
fi
