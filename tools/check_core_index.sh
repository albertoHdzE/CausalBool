#!/usr/bin/env zsh
# AUDIT03 (monolithic-code) — GOVERNANCE/CORE.md must not rot.
#
# CORE.md is the index a reader uses to answer "which code computed this
# number". An index naming a path that no longer exists is worse than no index,
# because it is believed. This asserts that every path CORE.md names is real.
#
# It extracts paths from backtick-quoted spans, so the check tracks the document
# rather than a hand-maintained second list — a second list would itself be a
# duplicate of the kind this whole programme is removing.
#
#   exit 0  every named path exists
#   exit 1  at least one is missing
#   exit 2  refused: found nothing to check
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
DOC="GOVERNANCE/CORE.md"

[[ -f "$DOC" ]] || { echo "CORE-INDEX: REFUSED  $DOC does not exist"; exit 2; }

# Backticked tokens that look like repository paths: contain a '/' and end in a
# known extension, or are a directory reference ending in '/'.
paths=$(grep -oE '`[A-Za-z0-9_./*-]+`' "$DOC" \
        | tr -d '`' \
        | grep -E '/' \
        | grep -E '(\.(m|wl|py|sh|md|json|tex)$|/$)' \
        | grep -vE '^(GOVERNANCE/CORE\.md)$' \
        | sort -u)

count=$(printf '%s\n' "$paths" | grep -c . || true)
if [[ "$count" -eq 0 ]]; then
  echo "CORE-INDEX: REFUSED  extracted 0 paths from $DOC."
  echo "  A pass over zero paths is not a pass — the extraction pattern is broken."
  exit 2
fi

STATUS=0
missing=0
for p in ${(f)paths}; do
  # Globs (level*/) and directory references are checked by expansion.
  if [[ "$p" == *'*'* ]]; then
    if ! ls -d ${~p} >/dev/null 2>&1; then
      echo "CORE-INDEX: MISSING  $p  (glob matches nothing)"; missing=$((missing+1)); STATUS=1
    fi
  elif [[ ! -e "$p" ]]; then
    echo "CORE-INDEX: MISSING  $p"; missing=$((missing+1)); STATUS=1
  fi
done

echo "CORE-INDEX: $((count - missing))/${count} paths named in $DOC exist"
if [[ "$STATUS" -ne 0 ]]; then
  echo "CORE-INDEX: fix the path or remove the entry — an index that lies is worse than none"
fi
exit $STATUS
