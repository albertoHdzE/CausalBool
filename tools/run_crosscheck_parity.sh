#!/usr/bin/env zsh
# AUDIT03 — run the Wolfram/Python cross-language parity the ONLY correct way.
#
# wolfram_equivalence.wl takes its three paths from environment variables. Run
# without them it used to print "cases matched: 0/0 / all match: True" -- a pass
# over nothing. The script now refuses, and this wrapper exists so nobody has to
# remember the variable names to get a meaningful run.
#
#   exit 0  every case matched
#   exit 1  a mismatch
#   exit 2  refused: could not load what it needs
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL=/Applications/Wolfram.app/Contents/MacOS/WolframKernel

"$REPO/venv/bin/python" "$REPO/index-deconvolution/crosscheck/generate_crosscheck_cases.py" || exit 2

CB_CASES="$REPO/index-deconvolution/crosscheck/cases.json" \
CB_CORE="$REPO/papers/method/code/lib/CausalBoolCore.wl" \
CB_OUT="$REPO/index-deconvolution/crosscheck/wolfram_result.json" \
HOME="$HOME" "$KERNEL" -script "$REPO/index-deconvolution/crosscheck/wolfram_equivalence.wl"
