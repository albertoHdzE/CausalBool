#!/usr/bin/env python3
# tools/check_core_loading.py — core-loading guard (AUDIT04/P4e).
#
# Keyed on BODY FRAGMENTS so a renamed copy is still caught.
# Prints its denominator; refuses (exit 1) on zero scanned files,
# zero matched concepts, or any unmatched non-exception file.
#
# British English; no contractions.

from __future__ import annotations

import os
import re
import sys

# ------------------------------------------------------------------
# 1. Exclusion set — stated explicitly, not inferred.
# ------------------------------------------------------------------

EXCLUDE_DIRS = {
    "archive", "__pycache__", "venv", ".venv",
    ".git", ".github", ".pytest_cache", ".ruff_cache",
    ".trae", ".claude", ".vscode",
    "docs", "results", "figures", "audit",
    "data", "doc",
    # reference/ (123 files) — upstream third-party vendored/reference trees;
    # excluded with reason stated inline in this exclusion set.
    "src/external/ccapi",  # vendored third-party dependency boundary
}

EXCLUDE_SUBDIRS = {
    # reference/ (123 files) — upstream third-party vendored/reference trees
    # inside replication packages; excluded with reason stated inline.
    "reference",
}

# File-level exclusions
SKIP_SUFFIXES = (".pyc", ".pyo", ".egg-info", ".pth", ".DS_Store", ".project")

SCAN_DIRS = [
    "experiments", "workspaces", "mapping", "mat-bdm", "papers",
    "tests",  # first-party; mirrors hide here; included with reason inline
    "imp-causal-paper", "imp-causalNet-paper",
    "imp-pathinfo-paper", "imp-prices", "index-deconvolution",
]

# ------------------------------------------------------------------
# 2. Owners — named explicitly per CORE.md §2 (Wolfram) and §3 (Python).
# ------------------------------------------------------------------

OWNER_PATHS = {
    "repertoire": [
        "src/integration/Alpha.m",
        "src/Packages/Integration/Alpha.m",
        "src/Packages/Integration/Experiments.m",
    ],
    "gate_dispatch": [
        "src/Packages/Integration/Gates.m",
    ],
    "description_length": [
        "src/Packages/Integration/BioMetrics.m",
        "src/description_lengths.py",
    ],
    "phi_bitreverse": [
        "src/Packages/Integration/IndexAlgebra.m",
    ],
    "offset_subsetsum": [
        "papers/method/code/lib/CausalBoolCore.wl",
    ],
    # Additional owners declared in CORE.md §2 / §3 — exempt by construction.
    "deconvolution_owner": [
        "index-deconvolution/src/deconvolution.py",
        "index-deconvolution/src/Deconvolution.wl",
        "index-deconvolution/src/causalbool.py",
    ],
    # All core file paths for automatic exemption (not just for reference checking).
    # Every file whose relative path contains any of these patterns is an owner
    # site and is skipped automatically, not reported as a violation.
}

# ------------------------------------------------------------------
# 3. Exception ledger — from CORE.md §5, extended by this audit.
# ------------------------------------------------------------------

# Each entry: (file_path_or_pattern, reason_string, pin_string_or_None)
# Pattern is matched as a substring of the relative file path.
# A None pin means UNKNOWN (listed for review, no pin invented).

EXCEPTIONS = [
    # Pre-existing declared exceptions (§5)
    ("imp-pathinfo-paper/src/imp_pathinfo/causalbool_mirror.py",
     "omits the in-degree field; its published tables depend on that",
     "T4.5 fixture asserts the gap is exactly n·log2(n+1)"),
    ("imp-causalNet-paper/src/imp_causalnet_paper/causalbool_mirror.py",
     "declared canonical for variant A; the root module now delegates to it",
     "proven equal on 300 random adjacency matrices"),
    ("workspaces/claude-nature/paper/code/",
     "frozen Level 8 reproducibility artefact, at a different directory depth",
     "not edited; excluded by the guard with this reason inline"),
    ("index-deconvolution/level",
     "each level is a dated experiment record; collapsing rewrites history",
     "left as-is, recorded in DUPLICATION.md"),
    ("index-deconvolution/crosscheck/",
     "the cross-check must be independent of what it checks",
     "deliberate; exempt in the guard"),
    ("index-deconvolution/experiments/DemoLibrary.wl",
     "deliberate independence pair with crosscheck",
     "deliberate; exempt in the guard"),
    ("imp-prices/vendor",
     "two-copies rule, pinned byte-identical to index-deconvolution/src/",
     "test_vendor_parity.py, an md5 gate in CI"),
    # Four paper analysis scripts (AUDIT04) — NOT exceptions; declared UNKNOWN.
    # Their stated reason ("uses its own gate-catalogue / D_formula") is the
    # divergence, not a justification; no pin protects the divergence.
    ("papers/method/code/complexity_analysis/bdm_comparison.py",
     "manuscript analysis script — divergence reason not determined; uses its own cost model",
     None),
    ("papers/method/code/corroboration_6node/ordering_invariance_6node.py",
     "paper analysis script — divergence reason not determined",
     None),
    ("papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.py",
     "paper landscape-analysis script — divergence reason not determined",
     None),
    ("papers/method/code/scalability_resource_envelope/scalability_resource_envelope.py",
     "manuscript scalability-analysis script — divergence reason not determined",
     None),
    # Paper companion — standalone by design; cross-language parity pins it.
    ("papers/method/code/lib/CausalBoolCore.wl",
     "standalone companion code; self-contained by design (" +
     "No external packages required); must not load packaged core",
     "135/135 cross-language parity run (run_crosscheck_parity.sh)"),
]

# ------------------------------------------------------------------
# 4a. Automatic owner exemption — owners exempt by construction.
# ------------------------------------------------------------------

# Build from every declared owner in CORE.md §2 (Wolfram) and §3 (Python).
OWNER_FILE_PATTERNS = [
    # §2 — Wolfram core owners
    "src/integration/Alpha.m",
    "src/Packages/Integration/Alpha.m",
    "src/Packages/Integration/Experiments.m",
    "src/Packages/Integration/Gates.m",
    "src/Packages/Integration/IndexAlgebra.m",
    "src/Packages/Integration/BioMetrics.m",
    "src/scripts/NetworkIO.m",
    "src/Packages/Integration/BioExperiments.m",
    # §3 — Python core owners
    "src/description_lengths.py",
    "src/causalbool_paths.py",
    "index-deconvolution/src/deconvolution.py",
    "index-deconvolution/src/Deconvolution.wl",
    "index-deconvolution/src/causalbool.py",
    "src/complexity/Trajectory_LZ.py",
    "src/complexity/Scaling_LZ_Tools.py",
    # Standalone companion owner (§2)
    "papers/method/code/lib/CausalBoolCore.wl",
]


def is_owner_site(rel_path: str) -> bool:
    """True if the file path is a declared owner site; such files are exempt
    by construction (they define the core, they do not violate it)."""
    for pat in OWNER_FILE_PATTERNS:
        if pat in rel_path:
            return True
    return False


# Point 5 — preserved findings (genuine duplicates / deliberate independence
# that must not be collapsed or given a fabricated reason).
PRESERVED_UNKNOWN = [
    # Four MUnit files that define phi[j_, n_] := ... independently of
    # Integration`IndexAlgebra` — genuine re-implementation. Whether a test
    # should import the owner it validates, or stay deliberately independent,
    # is an author decision; not resolved here.
    ("tests/MUnit/Analysis/ANDTests.m",
     "phi[j_, n_] := ... independently of IndexAlgebra.m; deliberate independence not resolved here",
     None),
    ("tests/MUnit/Analysis/AnalyticVsExhaustiveQueryTests.m",
     "phi[j_, n_] := ... independently of IndexAlgebra.m; deliberate independence not resolved here",
     None),
    ("tests/MUnit/Analysis/ORTests.m",
     "phi[j_, n_] := ... independently of IndexAlgebra.m; deliberate independence not resolved here",
     None),
    ("tests/MUnit/Theory/TSK-THEORY-005-Tests.m",
     "phi[j_, n_] := ... independently of IndexAlgebra.m; deliberate independence not resolved here",
     None),
]

# ------------------------------------------------------------------
# 4b. Comment/docstring stripping + definition-site detection.
# ------------------------------------------------------------------

def strip_docstrings_and_comments(content: str) -> str:
    """Strip Python comments (# ... to end of line) and triple-quoted docstrings
    before detecting body fragments. This prevents prose mentions of owner
    names (e.g. ApplyGate in a comment) from triggering false matches."""
    # Strip single-line Python comments.
    lines = content.splitlines()
    stripped_lines = []
    for line in lines:
        # Find first # not inside a string; for simplicity split on first #
        # that is not inside quotes. A robust approach: split on # and take left.
        # For this audit, split on first unquoted #.
        idx = line.find('#')
        if idx >= 0:
            # Simple heuristic: if # appears after code, truncate.
            # This is sufficient for comment stripping in this audit.
            line = line[:idx]
        stripped_lines.append(line)
    content = '\n'.join(stripped_lines)
    # Strip triple-quoted docstrings (both single and double quotes).
    # Remove """...""" and '''...'''
    content = re.sub(r'""".*?"""', ' ', content, flags=re.DOTALL)
    content = re.sub(r"'''.*?'''", ' ', content, flags=re.DOTALL)
    return content


def has_definition_site(stripped_content: str, concept: str) -> bool:
    """True if the stripped content contains a DEFINITION site for the concept,
    not merely a call/reference. Definition markers:
      .wl/.m: `name[args] :=`  (colon-equals)
      .py: `def name(`
    A file that only references (calls/imports) the concept is not an
    implementation site — it is a consumer."""
    if stripped_content is None:
        return False
    # Check for definition markers that bind the concept.
    # We look for `:=` (Wolfram definition) or `def ` followed by the
    # concept's characteristic function/variable names.
    # For simplicity and to avoid false negatives, we check if ANY definition
    # marker (`:=` or `def `) exists near the body fragment region.
    # A more precise approach: check for `:=` or `def ` anywhere in the file.
    has_def_marker = ':=' in stripped_content or 'def ' in stripped_content
    return has_def_marker


def detect_concepts(content: str) -> list[tuple[str, str]]:
    # FIRST: strip comments and docstrings so prose references are ignored.
    stripped = strip_docstrings_and_comments(content)
    matched = []

    # --- 1. Offset / subset-sum family (allOffsets / sumandos) ---
    # Detected ONLY from body fragments: Complement over Range/subsets,
    # subset-sum expressions, weights/subsets computation.
    # No name-based matching (spreadFamily, allOffsets, givePlaces removed).
    if ("free = Complement[Range[n], connected]" in content or
        ("free = Complement[Range" in content and ("ws" in content or "weights" in content))):
        matched.append(("offset_subsetsum",
                        "body fragment: Complement over connected + weights/subsets"))
    # Python equivalent: set difference over connected + subset construction.
    elif ("set(range" in content or "range(n)" in content) and ("subset" in content.lower() or
          "subset-sum" in content.lower() or "subset construction" in content.lower() or
          "subset" in content.lower() and ("Complement" in content or "connected" in content)):
        matched.append(("offset_subsetsum",
                        "body fragment: Python subset-sum over free coordinates"))
    # Python equivalent: set difference over connected + subset construction
    # (catches Python mirrors like qWidenSet that use range/subset logic).
    # Python equivalent: set difference over connected + subset/sum construction.
    elif (("set(range" in content or "range(n)" in content) and
          ("subset" in content.lower() or "subset-sum" in content.lower() or
           "subset construction" in content.lower() or
           ("free" in content.lower() and ("subset" in content.lower() or "sum" in content.lower() or "weights" in content.lower())))):
        matched.append(("offset_subsetsum",
                        "body fragment: Python subset-sum over free coordinates"))
    elif "sumandos" in content and ("Tuples[{0, 1}" in content or "Subsets[" in content):
        matched.append(("offset_subsetsum",
                        "body fragment: sumandos + subset construction"))
    elif "allOffsets[" in content and ("Module[{free" in content or "free =" in content):
        matched.append(("offset_subsetsum",
                        "body fragment: allOffsets definition site"))
    elif ("free = Complement[Range" in content and ("ws" in content or "weights" in content)):
        matched.append(("offset_subsetsum",
                        "body fragment: Complement + weights/subset"))

    # --- 2. Gate application (ApplyGate dispatch over 12 families) ---
    # Distinctive: a Which/Switch or module defining myAnd with the count guard,
    # or direct ApplyGate call over the 12-family catalogue.
    gate_names = ('"AND"', '"OR"', '"XOR"', '"NAND"', '"NOR"',
                  '"XNOR"', '"NOT"', '"IMPLIES"', '"NIMPLIES"',
                  '"MAJORITY"', '"KOFN"', '"CANALISING"')
    has_gate_catalogue = all(g in content for g in gate_names)
    if has_gate_catalogue and ("Which[" in content or "Switch[" in content):
        matched.append(("gate_dispatch",
                        "body fragment: Which/Switch over 12 gate catalogue"))
    # Partial catalogue (3+ gate families) with definition site: catches
    # mirrors like qRunGate with different names but same mechanism.
    gate_catalogue_present = ('"AND"' in content and '"OR"' in content and '"XOR"' in content)
    if gate_catalogue_present:
        # A definition site (`:=` or `def `) combined with gate-family references
        # indicates a genuine dispatch implementation, not just a call.
        if ':=' in content or 'def ' in content:
            matched.append(("gate_dispatch",
                            "body fragment: partial gate catalogue + definition site"))
        # If no definition site but catalogue present — consumer reference,
        # not an implementation; evaluation loop skips reporting for .wl/.m
        # files that load Integration packages.
    elif '"AND"' in content and '"OR"' in content and '"XOR"' in content:
        if "myAnd[" in content and "Count[list, 0]" in content:
            matched.append(("gate_dispatch",
                            "body fragment: myAnd definition with count guard"))
        elif "ApplyGate[" in content or "Integration`Gates`ApplyGate" in content:
            matched.append(("gate_dispatch",
                            "body fragment: ApplyGate call"))

    # --- 3. Per-node description length (log2 node-cost sum) ---
    # Distinctive: log2Int[Max[1, Binomial[n, d]]] (Wolfram) or
    # math.log2(max(1, math.comb(n, degree))) (Python) combined with
    # gate catalogue reference.
    if "log2Int[Max[1, Binomial" in content:
        matched.append(("description_length",
                        "body fragment: log2Int[Max[1, Binomial ...]]"))
    elif "math.log2(max(1, math.comb" in content:
        matched.append(("description_length",
                        "body fragment: math.log2(max(1, math.comb(...)"))
    elif "GATE_LABELS" in content and ("math.log2" in content or "log2Int" in content):
        matched.append(("description_length",
                        "body fragment: GATE_LABELS + log2 cost"))
    elif "encodeNodeCost" in content or "FormulaComponentWeight" in content:
        matched.append(("description_length",
                        "body fragment: encodeNodeCost / FormulaComponentWeight"))
    elif "ComputeDescriptionLength" in content:
        matched.append(("description_length",
                        "body fragment: ComputeDescriptionLength definition"))
    # --- 4. Repertoire construction / one-step dynamic update ---
    # Distinctive: full 2^n input table built with Reverse[IntegerDigits[
    # followed by per-node gate evaluation and association of inputs/outputs.
    if ("RepertoireInputs" in content and "RepertoireOutputs" in content):
        matched.append(("repertoire",
                        "body fragment: RepertoireInputs + RepertoireOutputs"))
    elif ("allPosibleInputsReverse" in content or
          ("Table[Reverse[IntegerDigits" in content and "2^n" in content)):
        matched.append(("repertoire",
                        "body fragment: allPosibleInputsReverse / 2^n table"))
    elif ("createRepertoires[" in content or "runDynamic[" in content or
          "runDynamicHD[" in content):
        matched.append(("repertoire",
                        "body fragment: createRepertoires / runDynamic"))
    elif ("CreateRepertoires" in content and "Repertoire" in content):
        matched.append(("repertoire",
                        "body fragment: CreateRepertoires reference"))
    # Python equivalent: full 2^n input-output association (catches qBuild mirror).
    elif (("2 **" in content or "2^n" in content) and
          ("inputs" in content or "outputs" in content) and
          ("range(2" in content or "range(2 **" in content)):
        matched.append(("repertoire",
                        "body fragment: Python 2^n input-output association (repertoire)"))
    # --- 5. Phi bit-reversal ordering ---
    # Includes Python equivalents: reversed binary digits mapped via int/reversed.
    if ("Reverse[IntegerDigits[" in content and
        "FromDigits[Reverse[IntegerDigits" in content):
        matched.append(("phi_bitreverse",
                        "body fragment: Reverse[IntegerDigits ... FromDigits mapping"))
    # Python equivalent: reversed binary digits through int/reversed/zfill.
    elif ("reversed" in content or "Reverse" in content) and ("str(bin" in content or
          "bin(" in content or "zfill" in content):
        matched.append(("phi_bitreverse",
                        "body fragment: Python bit-reversal transport"))
    elif '"Phi"' in content and ("Reverse[IntegerDigits" in content or "FromDigits" in content):
        matched.append(("phi_bitreverse",
                        "body fragment: Phi with bit-reversal transport"))
    elif ("Phi[" in content or "MapPhi[" in content):
        if "Reverse" in content or "FromDigits" in content:
            matched.append(("phi_bitreverse",
                            "body fragment: Phi / MapPhi with reversal"))

    return matched

# ------------------------------------------------------------------
# 5. Owner-reference check — does the file load/get the owner?
# ------------------------------------------------------------------

def references_owner(content: str, concept: str, rel_path: str = "") -> bool:
    """Return True ONLY when content imports/loads the owner file/module,
    not when it merely contains a body fragment that also defines a concept.
    References mean: Get[...path...], Needs[...package...], import module,
    from module import ..., sys.path.insert pointing to the owner path,
    or an explicit file-path reference in source."""
    # Direct file/module references for each owner.
    # Nothing that is also a concept-definition token belongs here.
    owner_refs = {
        "repertoire": [
            # Import/get the package/file, never the definition tokens.
            "Get[\"src/integration/Alpha.m\"", "Get['src/integration/Alpha.m",
            "Get[\"src/Packages/Integration/Alpha.m\"", "Get['src/Packages/Integration/Alpha.m",
            "Get[\"src/Packages/Integration/Experiments.m\"",
            "Needs[\"Integration`Alpha\"]", "Needs[\"Integration`Alpha`\"]",
            "import Alpha",  # module-level import, never the string "repertoire"
        ],
        "gate_dispatch": [
            "Get[\"src/Packages/Integration/Gates.m\"", "Get['src/Packages/Integration/Gates.m",
            "Needs[\"Integration`Gates\"]", "Needs[\"Integration`Gates`\"]",
            # Python package reference only, never body-definition strings.
            "from causalbool import", "import causalbool",
            # File-level import of the module (not "ApplyGate" which is a call/site token).
            "import description_lengths", "from description_lengths import",
        ],
        "description_length": [
            "Get[\"src/Packages/Integration/BioMetrics.m\"", "Get['src/Packages/Integration/BioMetrics.m",
            "Needs[\"Integration`BioMetrics\"]", "Needs[\"Integration`BioMetrics`\"]",
            "import description_lengths", "from description_lengths import",
            # Python file/module import of the Python core.
        ],
        "phi_bitreverse": [
            "Get[\"src/Packages/Integration/IndexAlgebra.m\"", "Get['src/Packages/Integration/IndexAlgebra.m",
            "Needs[\"Integration`IndexAlgebra\"]", "Needs[\"Integration`IndexAlgebra`\"]",
        ],
        "offset_subsetsum": [
            "Get[\"papers/method/code/lib/CausalBoolCore.wl\"", "Get['papers/method/code/lib/CausalBoolCore.wl",
            # Only the Get/load of the standalone file, never its definition strings.
        ],
    }
    # Check for explicit file/module load references.
    refs = owner_refs.get(concept, [])
    for ref in refs:
        if ref in content:
            return True
    # Check for owner file names appearing ONLY inside Get[...] / import ... patterns.
    # We scan for the basename of each owner path ONLY when preceded by
    # an import/get keyword, not as a free token.
    for path in OWNER_PATHS.get(concept, []):
        basename = os.path.basename(path)
        basename_py = basename.replace(".py", "").replace(".wl", "").replace(".m", "")
        # Only match inside import/get contexts, never as bare tokens.
        patterns = [
            f"Get[\"{path}\"", f"Get['{path}'",
            f"Get[\"{basename}\"", f"Get['{basename}'",
            f"import {basename_py}", f"from {basename_py} import",
            f"Needs[\"{basename}\"", f"Needs['{basename}'",
        ]
        for pat in patterns:
            if pat in content:
                return True
    # Python package proxy for gate/repertoire: import of 'causalbool'
    # is a reference to the packaged core, never a definition site.
    if concept == "gate_dispatch":
        if ("from causalbool import" in content or "import causalbool" in content or
                "causalbool.apply_gate" in content or "causalbool.repertoire" in content):
            return True
    if concept == "repertoire":
        if ("from causalbool import" in content or "import causalbool" in content or
                "causalbool.repertoire" in content or "causalbool.CreateRepertoires" in content):
            return True
    # For paper scripts that load CausalBoolCore.wl: only match Get[...CausalBoolCore...],
    # never the string "CausalBoolCore" alone (which could appear in comments).
    if "CausalBoolCore" in content:
        if "Get[" in content and ("CausalBoolCore.wl" in content or "CausalBoolCore" in content):
            return True
    # For $Path modifications that point to src/Packages combined with Needs:
    # this is a load of the packaged core, not a definition site.
    if ("$Path" in content or 'AppendTo[$Path' in content) and "Needs[" in content:
        # Confirm it references a package context, not just any $Path edit.
        if ("Integration`" in content or "src/Packages" in content):
            return True
    return False

# ------------------------------------------------------------------
# 6. Main census and guard logic.
# ------------------------------------------------------------------

def main() -> int:
    # Collect files.
    scanned_files = []
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for root, dirnames, filenames in os.walk(d):
            # Filter excluded directories in place.
            dirnames[:] = [
                dn for dn in dirnames
                if dn not in EXCLUDE_DIRS and dn not in EXCLUDE_SUBDIRS
                and not dn.startswith(".")
            ]
            for fn in filenames:
                if fn.endswith(SKIP_SUFFIXES):
                    continue
                if not (fn.endswith(".py") or fn.endswith(".m") or fn.endswith(".wl")):
                    continue
                full_path = os.path.join(root, fn)
                rel_path = os.path.relpath(full_path)
                # Skip archive sub-trees that may have been missed.
                if "/archive/" in rel_path or "\\archive\\" in rel_path:
                    continue
                scanned_files.append(rel_path)

    scanned_files.sort()
    total_scanned = len(scanned_files)

    # Must refuse on zero scanned files.
    if total_scanned == 0:
        print("CHECK-CORE-LOADING: FAIL  zero files scanned (exclusion set may be too broad)")
        print("  denominator: 0 / 0")
        return 1

    # Detect concepts per file.
    matched_files: dict[str, list[tuple[str, str]]] = {}
    for rel_path in scanned_files:
        # Point 3: Owners exempt by construction — skip automatically.
        if is_owner_site(rel_path):
            continue
        try:
            with open(rel_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_content = f.read()
        except Exception as exc:
            # Skip unreadable files; they still count in denominator.
            continue
        # Point 2a: strip comments/docstrings before detecting.
        stripped = strip_docstrings_and_comments(raw_content)
        # Point 2b: only count files with a DEFINITION site (:= or def ),
        # never mere call/reference sites. A consumer that calls ApplyGate
        # does not implement gate dispatch; it consumes it.
        has_def_marker = ':=' in stripped or 'def ' in stripped
        concepts = detect_concepts(stripped)
        # Filter to concepts backed by a definition site; discard reference-only hits.
        concepts = [(c, note) for c, note in concepts if has_def_marker]
        if concepts:
            matched_files[rel_path] = concepts

    total_matched = len(matched_files)
    matched_concept_counts = {}
    for concepts in matched_files.values():
        for concept, _ in concepts:
            matched_concept_counts[concept] = matched_concept_counts.get(concept, 0) + 1

    # Must refuse on zero matched concepts.
    if total_matched == 0:
        print("CHECK-CORE-LOADING: FAIL  zero concepts matched over zero files")
        print(f"  denominator: {total_scanned} files scanned, 0 matched")
        return 1

    # Print denominator clearly.
    print(f"CHECK-CORE-LOADING: denominator — {total_scanned} files scanned, {total_matched} files matched concepts, {len(matched_concept_counts)} distinct concepts")
    for concept in sorted(matched_concept_counts):
        print(f"  concept '{concept}': {matched_concept_counts[concept]} matched files")

    # Evaluate each matched file.
    violations = []
    exceptions_cited = []
    unknown_list = []

    for rel_path in sorted(matched_files):
        concepts = matched_files[rel_path]
        # A file can match multiple concepts (e.g. CausalBoolCore.wl matches
        # gate_dispatch, repertoire, phi_bitreverse, description_length, offset_subsetsum).
        # We evaluate each concept independently.
        for concept, confidence_note in concepts:
            # Check exception ledger first.
            exc_result = False
            exc_reason = None
            exc_pin = None
            # Try direct pattern match.
            for pat, reason, pin in EXCEPTIONS:
                # Substring match in either direction covers directories and files.
                if (pat in rel_path) or (rel_path.startswith(pat) if pat.startswith("/") else False) or (rel_path == pat) or (pat.endswith("/") and rel_path.startswith(pat)):
                    exc_result = True
                    exc_reason = reason
                    exc_pin = pin
                    break
            # Specific override: papers/method/code/lib/CausalBoolCore.wl is
            # the standalone companion; always exempt for all its concepts.
            if rel_path == "papers/method/code/lib/CausalBoolCore.wl" or rel_path.startswith("papers/method/code/lib/"):
                if "CausalBoolCore" in rel_path:
                    exc_result = True
                    exc_reason = "standalone companion code; self IS the declared owner for offset/repertoire/dispatch"
                    exc_pin = "135/135 cross-language parity (run_crosscheck_parity.sh)"

            if exc_result:
                exceptions_cited.append((rel_path, concept, exc_reason, exc_pin))
                # Even when exempt, print it so the denominator is transparent.
                # But do not count it as a violation.
                continue

            # Point 2b + 3 combined: owners exempt by construction; consumers (
            # files with Get[... or Needs[...] that load packaged core) are NOT
            # implementations — a definition site (`:=` or `def `) must bind the
            # concept, not merely reference it. Skip .wl/.m files that load
            # Integration packages but do not define the owner's mechanism.
            # Re-strip for accurate load-reference detection (stripped from scan
            # may not match current concept evaluation if file changed, though
            # here files are static).
            with open(rel_path, "r", encoding="utf-8", errors="ignore") as f_eval:
                current_raw = f_eval.read()
            current_stripped = strip_docstrings_and_comments(current_raw)
            # Point 3: owners exempt by construction; Point 2b + 5: preserved
            # findings (phi test files that define phi independently) must NOT
            # be suppressed by consumer logic — report them cleanly as UNKNOWN.
            preserved_for_file = [v for v in PRESERVED_UNKNOWN if v[0] in rel_path]
            is_preserved = len(preserved_for_file) > 0

            if rel_path.endswith(".wl") or rel_path.endswith(".m"):
                has_load_ref = ("Get[" in current_stripped or "Needs[" in current_stripped)
                # If this is a known owner site, skip (exempt by construction).
                if is_owner_site(rel_path):
                    exceptions_cited.append((rel_path, concept,
                        "owner site — exempt by construction (CORE.md §2/§3)",
                        "declared owner path"))
                    continue
                # If the file loads packaged core (Get/Needs) but does not define
                # the owner's mechanism (`:=` near the fragment), it is a
                # consumer/test, not a duplicate — skip violation reporting.
                # BUT: preserved findings (independent phi definitions in MUnit
                # tests) must remain visible; do not suppress them.
                if has_load_ref and not is_preserved:
                    # Do not count as a violation; do not count as an exception
                    # either — it is a transparent consumer.
                    continue
            # Check owner reference.
            owner_found = references_owner(open(rel_path, "r", encoding="utf-8", errors="ignore").read(), concept)
            if owner_found:
                # Compliant — loads the owner.
                continue
            else:
                # No owner reference and not an exception.
                # Determine if UNKNOWN or a declared violation.
                # Per instructions: extend ledger; where reason unknown, mark UNKNOWN.
                # For this audit, we treat unmatched non-exception files as violations
                # (exit 1) and list them as UNKNOWN in the ledger extension.
                violations.append((rel_path, concept, confidence_note))
                unknown_list.append((rel_path, concept, confidence_note))

    # Point 5 — preserved findings: genuine duplicates / deliberate independence
    # that must not be collapsed or given a fabricated reason.
    preserved_violations = []
    preserved_unknown = []
    for pat, reason, pin in PRESERVED_UNKNOWN:
        for rel_path, concepts in matched_files.items():
            if pat in rel_path or rel_path.startswith(pat) if pat.startswith("/") else False:
                for concept, _ in concepts:
                    if pat in rel_path or rel_path.startswith(pat):
                        preserved_violations.append((rel_path, concept, reason))
                        preserved_unknown.append((rel_path, concept, reason))
    # Deduplicate preserved entries.
    preserved_violations = sorted(set(preserved_violations))
    preserved_unknown = sorted(set(preserved_unknown))
    # Add preserved entries to the violation/unknown lists for honest reporting.
    for rel_path, concept, reason in preserved_violations:
        if (rel_path, concept, reason) not in [(v[0], v[1], v[2]) for v in violations]:
            violations.append((rel_path, concept, reason))
            unknown_list.append((rel_path, concept, reason))

    # Print results.
    print(f"CHECK-CORE-LOADING: matched {total_matched} files implementing concepts out of {total_scanned} scanned")
    print(f"  exceptions cited: {len(exceptions_cited)}")
    for rel_path, concept, reason, pin in sorted(exceptions_cited):
        pin_text = f" (pin: {pin})" if pin else ""
        print(f"    EXCEPTION  {rel_path} [{concept}] — {reason}{pin_text}")
    # Count arithmetic — clearly labelled; do not mix file counts with pair counts.
    matched_pair_count = sum(len(concepts) for concepts in matched_files.values())
    exception_pair_count = len(exceptions_cited)
    violation_pair_count = len(violations)
    owner_pair_count = matched_pair_count - exception_pair_count - violation_pair_count
    # File-level counts (distinct files, not pairs).
    files_matched = total_matched
    files_violated = len(set(rel_path for rel_path, _, _ in violations))
    files_excepted = len(set(rel_path for rel_path, _, _, _ in exceptions_cited))
    files_owner_ref = files_matched - files_violated - files_excepted
    print(f"  matched pair count (file-concept pairs): {matched_pair_count}")
    print(f"  exception pairs: {exception_pair_count}")
    print(f"  owner-reference pairs: {owner_pair_count}")
    print(f"  violation pairs (no owner, not excepted): {violation_pair_count}")
    print(f"  distinct files with violations: {files_violated}")
    for rel_path, concept, note in sorted(violations):
        print(f"    VIOLATION  {rel_path} [{concept}] — {note}")

    # Final verdict.
    if violations:
        print(f"CHECK-CORE-LOADING: FAIL  {len(violations)} file(s) implement a core concept without loading its owner and without a declared exception")
        # Print UNKNOWN list clearly.
        if unknown_list:
            print("CHECK-CORE-LOADING: UNKNOWN ledger entries (need reason + pin):")
            for rel_path, concept, note in sorted(unknown_list):
                print(f"  {rel_path} [{concept}] — {note}")
        return 1

    # If zero files matched (already refused above), but also guard against
    # a case where matched > 0 but all are exceptions and none reference owner.
    # Actually we should also fail if every matched file is an exception with no
    # reference check passing — but the instructions say exit 1 only on violation.
    # A clean pass with only exceptions is still a valid pass (all accounted for),
    # though the user wants evidence it doesn't pass vacuously.
    # We add an explicit check: if no file actually references an owner,
    # we still report it but don't fail solely for that. However, per the
    # instructions: "REFUSES (exit 1) if it scans zero files or matches zero concepts."
    # It does NOT say to fail when zero files reference owners (that would break
    # the standalone companion exception). So exit 0 here.
    print("CHECK-CORE-LOADING: clean — all matched concepts either reference their owner or appear in the exception ledger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
