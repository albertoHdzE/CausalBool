(* AUDIT03 — every Wolfram source in the tree must PARSE.

   Written because the test suite could not see a syntax error. A collapse in
   019ff70 left an orphan tail from the replaced body in FOUR files:

       computeCompression[...] := Integration`BioMetrics`ComputeFormulaComponents[...];
         Total@Table[compressionWeight[...], {i, n}]     <- orphan
       ];                                                <- orphan, a syntax error

   Three of the four were COLLECTED by the runner and reported green. The kernel
   prints Syntax::sntx, skips the malformed expression, continues, and exits 0 —
   so the script still exported "OK" and the suite counted it as a pass. The
   fourth (TSK-ALGO-003) was silently fatal: no status file was written at all,
   and because that file is one the runner never collects, nobody saw it.

   Reading each file as text and parsing it is the only check that catches this.

     exit 0  every file parses
     exit 1  at least one does not
     exit 2  refused: nothing to check
*)

repo = If[StringQ[Environment["CB_REPO"]], Environment["CB_REPO"], Directory[]];
SetDirectory[repo];

skip = {"archive", "venv", ".venv", "node_modules", "src/external/ccapi",
        "reference", "vendor", ".git"};

files = Select[
  FileNames[{"*.m", "*.wl"}, repo, Infinity],
  Function[f,
    Module[{rel = StringReplace[f, repo ~~ "/" -> ""]},
      NoneTrue[skip, StringContainsQ[rel, # <> "/"] &]]]];

If[Length[files] === 0,
  Print["WL-SYNTAX: REFUSED — found 0 Wolfram files under ", repo];
  Print["  A pass over zero files is not a pass."];
  Exit[2]];

bad = {};
Do[
  Module[{text, parsed},
    text = Quiet@Import[f, "Text"];
    If[!StringQ[text], AppendTo[bad, {f, "unreadable"}],
      parsed = Quiet@Check[
        ToExpression["Hold[\n" <> text <> "\n]", InputForm, Hold], $Failed];
      If[parsed === $Failed || parsed === Null,
        AppendTo[bad, {f, "syntax"}]]]],
  {f, files}];

Print["WL-SYNTAX: ", Length[files] - Length[bad], "/", Length[files],
      " Wolfram files parse"];
If[Length[bad] > 0,
  Print["WL-SYNTAX: FAIL — these do not parse:"];
  Do[Print["  ", StringReplace[b[[1]], repo ~~ "/" -> ""], "  (", b[[2]], ")"], {b, bad}];
  Exit[1]];
