(* Integration`SelfTest` — a smoke check for the packaged core.

   AUDIT03-B. THIS FILE WAS A FOURTH ENGINE.

   It carried its own myAnd, myOr, myXor, allPosibleInputsReverse and
   runNetwork, none of which had ever been compared to
   Integration`Gates`ApplyGate. It is advertised in README.md as one of the core
   packages, and SelfTestRun was invoked by nothing.

   Both censuses missed it. The AST arm of duplication_census.py is Python-only,
   and the Wolfram arm matches normalised TEXT, so one-line definitions under
   DIFFERENT names are invisible to it. It was found by reading the orphan list.

   Measured before the collapse, by audit/AUDIT03_R2_collapse/probe_selftest_parity.wl:

     myAnd / myOr / myXor vs ApplyGate ....... 378/378 agree  (arities 1..6)
     allPosibleInputsReverse vs LSB-first .... 8/8 agree      (n = 1..8)
     runNetwork vs CreateRepertoiresDispatch . 992/992 rows agree
                                               (n = 2..6, 8 networks each,
                                                AND/OR/XOR only)

   So on the part it implemented it was an exact copy -- drift-free, and
   therefore a collapse rather than a second concept.

   BUT runNetwork's Which had branches for AND, OR and XOR only, and a
   `True -> 0` fallthrough. The other NINE families evaluated SILENTLY to zero:

     NAND 3/4 rows wrong, NOR 1/4, XNOR 2/4, NOT 2/4, IMPLIES 3/4,
     NIMPLIES 1/4, MAJORITY 1/4, KOFN 3/4, CANALISING 1/4
     -- 17 of 36 rows, no message, 9 of 9 families

   That is exactly the defect AUDIT02/P1 removed from CausalBoolCore.wl, where a
   missing CANALISING branch made a CANALISING node return 0 unnoticed. A
   "self-test" that silently mis-evaluates three quarters of the gate families
   is worse than no self-test, because its name invites trust.

   It now delegates to the owners. Guarded by tools/check_single_engine.sh so a
   fifth private copy of the gate semantics cannot appear silently. *)

Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];

(* SelfTestRun exercises the packaged core end to end and RETURNS ITS OWN
   VERDICT. It used to return only data, so its caller had nothing to judge and
   exported a literal "OK". *)

SelfTestRun[] := Module[
  {cm, dynamic, res, inputs, outputs, base, figbase, plot,
   expected, rowsOK, allOK},

  cm = {{0, 1}, {1, 0}};
  dynamic = {"AND", "XOR"};

  base = FileNameJoin[{"results", "selftest"}];
  figbase = FileNameJoin[{"figures", "selftest"}];
  If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
  If[!DirectoryQ[figbase], CreateDirectory[figbase, CreateIntermediateDirectories -> True]];

  res = Integration`Experiments`CreateRepertoiresDispatch[cm, dynamic];
  inputs = res["RepertoireInputs"];
  outputs = res["RepertoireOutputs"];

  (* The predicate, stated INDEPENDENTLY of the engine being tested: node 1 is
     AND over its single connected input (coordinate 2), node 2 is XOR over its
     single connected input (coordinate 1). A one-input AND is the identity and
     a one-input XOR is the identity, so each row must be the input reversed.
     Written out rather than assumed, so this file can now fail. *)
  expected = Reverse /@ inputs;
  rowsOK = MapThread[SameQ, {outputs, expected}];
  allOK = And @@ rowsOK && Length[inputs] === 4;

  Export[FileNameJoin[{base, "SelfTest-Inputs.csv"}], inputs, "CSV"];
  Export[FileNameJoin[{base, "SelfTest-Outputs.csv"}], outputs, "CSV"];
  Export[FileNameJoin[{base, "SelfTest-Outputs.json"}], outputs, "JSON"];

  plot = ListPlot[outputs, PlotMarkers -> Automatic, AxesLabel -> {"t", "out"}];
  Export[FileNameJoin[{figbase, "SelfTest-Plot.png"}], plot, "PNG"];

  Association[
    "Inputs" -> inputs,
    "Outputs" -> outputs,
    "Expected" -> expected,
    "RowsOK" -> rowsOK,
    "AllOK" -> allOK,
    "ResultsPath" -> base,
    "FiguresPath" -> figbase
  ]
];
