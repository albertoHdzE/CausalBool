(* wolfram_equivalence.wl

   Prove that the Python forward model (index-deconvolution/src/causalbool.py)
   is equivalent to the canonical Wolfram reference CausalBoolCore.wl.

   Reads a JSON bundle of networks together with their Python-computed output
   repertoires, recomputes each repertoire with CreateRepertoiresDispatch, and
   reports whether every case matches byte for byte.

   Invocation (paths passed via environment variables):
     CB_CASES=... CB_CORE=... CB_OUT=... WolframKernel -script wolfram_equivalence.wl
*)

casesPath = Environment["CB_CASES"];
corePath  = Environment["CB_CORE"];
outPath   = Environment["CB_OUT"];

Get[corePath];

cases = Import[casesPath, "RawJSON"];

results = Table[
  Module[{case, n, cm, dynamic, paramsList, paramsAssoc, pyRep, wlRep, match},
    case = cases[[c]];
    n = case["n"];
    cm = case["C"];
    dynamic = case["gates"];
    paramsList = case["params"];
    (* Build a 1-based node -> params association.  Empty objects import as
       <||> which Lookup treats as no parameters. *)
    paramsAssoc = Association[Table[node -> paramsList[[node]], {node, 1, n}]];
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
