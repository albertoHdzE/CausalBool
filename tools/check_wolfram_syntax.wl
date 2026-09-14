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

   AUDIT04-F, 2026-09-08 — the check itself could HANG, and it did, for three
   hours inside a pre-push hook. It parsed with

       ToExpression["Hold[\n" <> text <> "\n]", InputForm, Hold]

   and ToExpression distinguishes two failures that this script treated as one.
   A file with a SURPLUS bracket, f[x]], is an error: the parser rejects it and
   ToExpression returns $Failed, so the script exits 1 as intended. A file with
   an UNCLOSED bracket, f[x, is not an error but an INCOMPLETE expression: the
   parser has consumed every character and still wants more, so it reads stdin.
   Under a git hook stdin is a pipe that never delivers, and the kernel blocks
   for ever at 0 % CPU. The push never happened and nothing was printed.

   SyntaxQ answers the same question and cannot ask for more input. Measured on
   this kernel:

       "f[x"           SyntaxQ False  SyntaxLength  5 >= StringLength  3
       unclosed-opener SyntaxQ False  SyntaxLength 15 >= StringLength 15
       "f[x]]"         SyntaxQ False  SyntaxLength  4 <  StringLength  5
       "x=1;\ny=2;"    SyntaxQ True   SyntaxLength  9 == StringLength  9

   so SyntaxLength >= StringLength on a failing file is exactly the case that
   used to hang, and it is now reported by name instead of being suffered.

   The second row cannot be written literally here. Wolfram comments NEST, so
   an unaccompanied comment-opener inside this very comment opens a nested one
   that never closes, and the rest of the file is swallowed. Writing that row
   out is how this fix first broke itself: the kernel then read the whole file
   as an unterminated comment, executed nothing, printed nothing, and exited 0
   on a closed stdin or hung for ever on an open one. Both symptoms, from one
   character pair. Do not restore the literal.

   Every file is announced BEFORE it is parsed, because a checker that prints
   nothing until the end cannot be diagnosed when it stalls: three hours of
   silence named no file. The announcements go to stderr so that stdout stays
   the machine-readable verdict.

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

rel[f_] := StringReplace[f, repo ~~ "/" -> ""];

bad = {};
Do[
  Module[{text, ok, sl, len},
    WriteString[Streams["stderr"], "  parsing ", rel[f], "\n"];
    text = Quiet@Import[f, "Text"];
    If[!StringQ[text],
      AppendTo[bad, {f, "unreadable"}],
      (* SyntaxQ never requests continuation input, so it cannot block. *)
      ok = Quiet@Check[SyntaxQ[text], $Failed];
      If[ok =!= True,
        len = StringLength[text];
        sl = Quiet@Check[SyntaxLength[text], len];
        AppendTo[bad, {f,
          If[IntegerQ[sl] && sl >= len,
            "INCOMPLETE — the parser consumed all " <> ToString[len] <>
              " characters and still wants more; this is the form that used to hang",
            "syntax error at character " <> ToString[sl]]}]]]],
  {f, files}];

Print["WL-SYNTAX: ", Length[files] - Length[bad], "/", Length[files],
      " Wolfram files parse"];
If[Length[bad] > 0,
  Print["WL-SYNTAX: FAIL — these do not parse:"];
  Do[Print["  ", rel[b[[1]]], "  (", b[[2]], ")"], {b, bad}];
  Exit[1]];
