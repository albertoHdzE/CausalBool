(* wolfram_equivalence.wl

   Prove that the Python forward model (index-deconvolution/src/causalbool.py)
   is equivalent to the canonical Wolfram reference CausalBoolCore.wl.

   Reads a JSON bundle of networks together with their Python-computed output
   repertoires, recomputes each repertoire with CreateRepertoiresDispatch, and
   reports whether every case matches byte for byte.

   Invocation (paths passed via environment variables):
     CB_CASES=... CB_CORE=... CB_OUT=... WolframKernel -script wolfram_equivalence.wl
*)

(* AUDIT03: this script REPORTED SUCCESS ON NOTHING.

   The three paths come from environment variables. Run without them,
   Environment[] returns $Failed, Import[$Failed] fails, cases becomes $Failed,
   Length[$Failed] is 0, and the summary computes all_match = (0 === 0) = True.
   The observed output was:

       cases matched: 0/0
       all match: True

   A parity harness that passes when it has loaded no cases is worse than no
   harness, because it is quoted as evidence. The AUDIT03 plan required the
   135/135 claim to be RE-RUN rather than cited, and this is why: running it
   the obvious way produced a green result that meant nothing.

   Every input is now checked before use and the script exits non-zero if it
   cannot do the work it claims to have done. *)

casesPath = Environment["CB_CASES"];
corePath  = Environment["CB_CORE"];
outPath   = Environment["CB_OUT"];

If[!StringQ[casesPath] || !StringQ[corePath] || !StringQ[outPath],
  Print["REFUSED: set CB_CASES, CB_CORE and CB_OUT to absolute paths."];
  Print["  got CB_CASES=", casesPath, " CB_CORE=", corePath, " CB_OUT=", outPath];
  Exit[2]];
If[!FileExistsQ[casesPath], Print["REFUSED: no case bundle at ", casesPath]; Exit[2]];
If[!FileExistsQ[corePath],  Print["REFUSED: no core library at ", corePath]; Exit[2]];

Get[corePath];

If[!ValueQ[CreateRepertoiresDispatch] &&
   Head[CreateRepertoiresDispatch] === Symbol &&
   DownValues[CreateRepertoiresDispatch] === {},
  Print["REFUSED: CreateRepertoiresDispatch undefined after loading ", corePath];
  Exit[2]];

cases = Import[casesPath, "RawJSON"];

If[!ListQ[cases] || Length[cases] === 0,
  Print["REFUSED: case bundle loaded as ", Head[cases],
        " with ", If[ListQ[cases], Length[cases], "no"], " cases. ",
        "A parity run over zero cases is not a pass."];
  Exit[2]];

results = Table[
  Module[{case, n, cm, dynamic, paramsList, paramsAssoc, pyRep, wlRep, match},
    case = cases[[c]];
    n = case["n"];
    cm = case["C"];
    dynamic = case["gates"];
    paramsList = case["params"];
    (* Build a 1-based node -> params association.  Empty objects import as
       <||> which Lookup treats as no parameters. *)
    (* AUDIT02/P1: canalisingIndex is a 0-BASED position within the connected
       sub-vector on the Python side and a 1-BASED position on the Wolfram side
       (myCanalising does list[[i]]).  Transporting the JSON verbatim would
       compare the two engines at different coordinates and report a divergence
       that is purely a convention offset.  Translate exactly once, here. *)
    paramsAssoc = Association[Table[
      node -> Module[{p}, p = paramsList[[node]];
        If[AssociationQ[p] && KeyExistsQ[p, "canalisingIndex"],
           Append[p, "canalisingIndex" -> p["canalisingIndex"] + 1], p]],
      {node, 1, n}]];
    pyRep = case["repertoire"];
    wlRep = CreateRepertoiresDispatch[cm, dynamic, paramsAssoc]["RepertoireOutputs"];
    match = (wlRep === pyRep);
    <|"n" -> n, "match" -> match|>
  ],
  {c, 1, Length[cases]}
];

nTotal = Length[results];
nMatch = Count[results, r_ /; r["match"] === True];

summary = <|
  "n_cases" -> nTotal,
  "n_match" -> nMatch,
  "all_match" -> (nMatch === nTotal),
  "per_case" -> results
|>;

Export[outPath, summary, "JSON"];

Print["=== Wolfram equivalence cross-check ==="];
Print["cases matched: ", nMatch, "/", nTotal];
Print["all match: ", (nMatch === nTotal)];

(* Exit non-zero on any mismatch, so a caller that only checks the status code
   cannot read a failure as a pass. *)
If[nMatch =!= nTotal,
  Print["MISMATCHES: ", Select[results, #["match"] =!= True &]];
  Exit[1]];
