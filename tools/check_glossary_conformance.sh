#!/usr/bin/env zsh
# AUDIT02/P5.2 — GLOSSARY code-conformance check.
#
# Companion to check_glossary_sync.sh, which compares our GOVERNANCE/GLOSSARY.md
# against the sibling copy and therefore verifies DOCUMENT MIRRORING ONLY. It is
# green whether or not the code matches the glossary. This script closes that
# gap from the other side: it asserts that terms the glossary has RETIRED do not
# appear in live (non-archived) source.
#
# Retired senses and their replacements, per GOVERNANCE/GLOSSARY.md sec.1:
#   pivot / pivots / currentPivot  ->  decimalAnchor, sequenceStarts
#   mechaPivot / purPivot          ->  wholeSystemMechanism
#
# THIS SCRIPT CONTAINED THE DEFECT IT EXISTS TO CATCH. Until 2026-09-07 its own
# header read:
#
#   ""pivot" in its FINANCIAL sense is legitimate and is confined to the
#    index-deconvolution and imp-prices programmes, which are EXCLUDED below."
#
# and its scope was two Wolfram directories. The Python side of the Boolean
# indexing method lives in index-deconvolution, so the guard exempted, by name,
# the tree that still held the defect -- and then reported clean. Measured
# 2026-09-07: 178 occurrences of the word repo-wide, of which 17 in 7 files were
# method-sense, including the dict key `pivots_essential_bits`, the filename
# `exp01_pivots_sumandos.py` that GLOSSARY sec.1c quotes as the source of the
# confusion, and one paper-code file the paper sweep had already declared clean.
#
# GLOSSARY sec.1e, AUTHOR RULING 2026-09-07 -- *PIVOT* IS A FINANCE TERM. It
# names nothing inside the Boolean indexing method, whose six objects are
# connected inputs, essential variables, decimal anchor, decimal family, free
# coordinates and sumandos. The word is retired from the method trees entirely:
# prose, identifiers, filenames and JSON keys alike, and the ordinary-English
# action codes with it (PIVOT_HYBRID -> SWITCH_TO_HYBRID_ENCODING), because
# adjudicating which sense was meant is the work the ruling abolishes.
#
#   exit 0  no retired term in live engine/package/method source
#   exit 1  a retired term reappeared
#   exit 2  REFUSED: a scan found zero files, so "clean" would mean nothing

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

# Scope: the Wolfram engine and packaged API. Archived provenance is exempt by
# design.
SCOPE=(src/Packages src/integration)

# The trees that implement the BOOLEAN INDEXING METHOD, in either language. The
# word must not appear in any sense here: there is no finance in these files, so
# there is nothing to adjudicate.
#
# GOVERNANCE and the live manuscripts are IN scope. They were added on
# 2026-09-07 after a plant into GOVERNANCE/DESCRIPTION_LENGTHS.md sailed through
# a scan that already covered .md -- the file type was right and the directory
# was missing, which is the same comfortable-denominator miss in a third guise.
METHOD_SCOPE=(src index-deconvolution/src index-deconvolution/level3
              index-deconvolution/experiments index-deconvolution/tests
              papers/method/code papers/method/manuscript_formal
              papers/method/manuscript_computational
              GOVERNANCE tools tests)

# Declared exceptions, each with its reason. A file is exempt only if it is
# named here; a directory is never exempt wholesale, because that is exactly how
# the row above came to clear a tree it had not scanned.
#
#   *_pivot_distribution.py     Level 3/4 FINANCE experiments that happen to sit
#                               under a method tree; they study occurrences in a
#                               price series, which is sec.1b's financial pivot.
#   Contingency_Monitor.py      records the retired action codes in
#                               RETIRED_ACTION_CODES so stored artefacts can be
#                               read; it quotes the error to forbid it.
#   GLOSSARY/conformance files  quote the forbidden phrasing in order to ban it.
#   deconvolution.py, behaviour_table.py,
#   exp01_connected_inputs_and_sumandos.py
#                               state the ruling in their own docstrings, which
#                               requires naming the word being retired. Each was
#                               checked to be forbidding the usage, not using it.
EXEMPT_RE='(exp1[14]_pivot_distribution\.py|Contingency_Monitor\.py|check_glossary_conformance\.sh|test_sumandos_definition\.py|GLOSSARY\.md|index-deconvolution/src/deconvolution\.py|index-deconvolution/level3/behaviour_table\.py|exp01_connected_inputs_and_sumandos\.py)'

RETIRED=(currentPivot mechaPivot purPivot)
STATUS=0

for term in $RETIRED; do
  hits=$(grep -rn "\b${term}\b" $SCOPE --include='*.m' --include='*.wl' 2>/dev/null || true)
  if [[ -n "$hits" ]]; then
    echo "GLOSSARY-CONFORMANCE: FAIL  retired identifier '${term}' present in live source:"
    printf '  %s\n' ${(f)hits}
    STATUS=1
  fi
done

# The bare technical senses: a local named `pivot`, or an output key "Pivot".
tech=$(grep -rnE '(\bpivot[[:space:]]*=|"Pivot")' $SCOPE --include='*.m' --include='*.wl' 2>/dev/null || true)
if [[ -n "$tech" ]]; then
  echo "GLOSSARY-CONFORMANCE: FAIL  technical-sense 'pivot' present in live source"
  echo "  (use decimalAnchor / DecimalAnchor, or sequenceStarts for block offsets)"
  printf '  %s\n' ${(f)tech}
  STATUS=1
fi

# --- GLOSSARY sec.1d: sumandos are NOT "the disconnected coordinates" ----------
# Settled 2026-07-09, re-adopted and re-settled four times since; the recurrence
# is always a reader promoting allOffsets' implementation into the definition.
# The special case may be ILLUSTRATED; it may never be stated AS the definition.
# Scope is wide on purpose (manuscripts and companion code, not just src/), since
# every recurrence so far has been in prose rather than in an identifier.
#
# index-deconvolution added 2026-09-07. It was absent, and the omission had cost
# already: level2/schema_pockets.py called the uncovered days "the residual (the
# sumandos of this level)", which crosses the two decompositions in the exact way
# sec.1c forbids -- a residual is what causality cannot reach, the sumandos are
# enumerable offsets in an exact reconstruction, and equating them inverts the
# epistemic status of both.
DEFN_SCOPE=(papers/method/manuscript_computational papers/method/manuscript_formal
            papers/method/code src/Packages src/integration
            index-deconvolution/src index-deconvolution/level2
            index-deconvolution/level3 index-deconvolution/level4
            index-deconvolution/level5 index-deconvolution/experiments)
badexcl='CAUTION|special case|not the definition|section 1d|sec\.1d|GLOSSARY'
bad=$(grep -rnEi \
  '(sumandos?|offset family|omega)[^.]{0,80}(are|is|=|corresponds? to|generated by)[^.]{0,40}(the )?(disconnected|coordinates that do not feed|nodes that do not feed)' \
  $DEFN_SCOPE --include='*.tex' --include='*.wl' --include='*.m' --include='*.py' \
  2>/dev/null | grep -Ev "$badexcl" || true)
if [[ -n "$bad" ]]; then
  echo "GLOSSARY-CONFORMANCE: FAIL  Omega/sumandos defined as the disconnected coordinates"
  echo "  Rule 110 has three inputs, all CONNECTED, and decomposes as 01*, 10*, *10."
  echo "  Free is per SCHEMA, not per node. See GOVERNANCE/GLOSSARY.md sec.1d."
  printf '  %s\n' ${(f)bad}
  STATUS=1
fi

# --- GLOSSARY sec.1e: *pivot* is a finance term ------------------------------
# Scanned over BOTH languages and over prose as well as code, because the
# recurrences have been in a filename, a dict key, a docstring and a shell
# comment in turn. Every file is counted and the denominator is printed: a scan
# that reports "clean" over zero files is the failure this whole audit removes.
pivot_files=()
for d in $METHOD_SCOPE; do
  [[ -d "$d" ]] || continue
  while IFS= read -r f; do
    [[ "$f" =~ $EXEMPT_RE ]] && continue
    pivot_files+=("$f")
  done < <(find "$d" -type f \( -name '*.py' -o -name '*.m' -o -name '*.wl' \
             -o -name '*.sh' -o -name '*.md' -o -name '*.tex' \) \
             ! -path '*/__pycache__/*' 2>/dev/null)
done

if (( ${#pivot_files} == 0 )); then
  echo "GLOSSARY-CONFORMANCE: REFUSED  sec.1e scan matched 0 files under ${METHOD_SCOPE}"
  echo "  A guard that reports clean over an empty denominator proves nothing."
  exit 2
fi

# Line-level exemption, the same device the sec.1d block above already uses. A
# document that RECORDS a rename has to name what was renamed, so a line that
# cites the ruling is quoting the error rather than committing it. The exemption
# is per LINE, never per file: everything else in the same file is still
# scanned, which is what the old file-level tree exemption failed to do.
#
# It is verified by the plants: a bare "the pivot coordinates" with no citation
# goes red in .py, .sh and .md alike.
pivot_ok='sec\.1e|§1e|GLOSSARY|financial pivot|RETIRED_ACTION_CODES'
pivots=$(grep -nEi '\bpivot' "${pivot_files[@]}" 2>/dev/null | grep -Ev "$pivot_ok" || true)
if [[ -n "$pivots" ]]; then
  echo "GLOSSARY-CONFORMANCE: FAIL  'pivot' present in the method trees (sec.1e)"
  echo "  It is a FINANCE term. Inside the Boolean indexing method the six names are:"
  echo "    connected inputs · essential variables · decimal anchor ·"
  echo "    decimal family · free coordinates · sumandos"
  printf '  %s\n' ${(f)pivots}
  STATUS=1
fi

if [[ "$STATUS" -eq 0 ]]; then
  echo "GLOSSARY-CONFORMANCE: clean  (no retired term in ${SCOPE}; sec.1d respected;"
  echo "  sec.1e: 0 occurrences of 'pivot' over ${#pivot_files} files in the method trees)"
else
  echo "GLOSSARY-CONFORMANCE: retired terminology reappeared — see GOVERNANCE/GLOSSARY.md sec.1"
fi
exit $STATUS
