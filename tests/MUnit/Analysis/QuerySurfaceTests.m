(* AUDIT02/P4b — regression coverage for the ANALYTIC QUERY SURFACE.

   Subject: createRepertoireByResult[gate, length, res, params] — the exhaustive
   baseline for "which inputs produce this output", and the reference against
   which the closed-form IndexSet / IndexSetAnalytic results are compared in the
   manuscripts.

   This test exists because two defects lived in that function undetected:
     (i)  eight of the twelve families (NAND NOR XNOR NOT IMPLIES NIMPLIES KOFN
          CANALISING) matched no Which branch and returned Null SILENTLY;
     (ii) MAJORITY ignored the requested res. At arity 3 the res=0 and res=1 sets
          have EQUAL SIZE (4 and 4), so any count-based check passes while the
          elementwise symmetric difference is all 8 inputs.

   Judgement is therefore ELEMENTWISE and ORDER-SENSITIVE (===), never by count:
   the enumeration order is LSB-first and is load-bearing for the downstream
   "DecRep" decimal encoding. Symmetric differences are reported with their
   location (convention U8).

   Arity scope: IMPLIES and NIMPLIES are binary in Integration`Gates`ApplyGate
   (they read inputs[[2]]), so they are exercised from arity 2 upward; every
   other family from arity 1. *)

Get["src/integration/Alpha.m"];
Get["src/Packages/Integration/Gates.m"];

families = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT",
            "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"};
params = <|"k" -> 2|>;
arities[g_] := If[MemberQ[{"IMPLIES", "NIMPLIES"}, g], {2, 3, 4}, {1, 2, 3, 4}];

records = Flatten[Table[
   Table[
    Module[{got, truth, sd},
     got = createRepertoireByResult[g, ar, res, params];
     truth = Select[Reverse[Reverse[#] & /@ Tuples[{1, 0}, ar]],
                    Integration`Gates`ApplyGate[g, #, params] === res &];
     sd = Union[Complement[got, truth], Complement[truth, got]];
     <|"Gate" -> g, "Arity" -> ar, "Res" -> res,
       "GotCount" -> Length[got], "TruthCount" -> Length[truth],
       "CountsAgree" -> (Length[got] === Length[truth]),
       "Equal" -> (got === truth),
       "SymDiff" -> sd|>
    ],
    {ar, arities[g]}, {res, {0, 1}}
   ], {g, families}], 2];

failures = Select[records, Not[#["Equal"]] &];

(* The specific historical trap: counts agreeing while the sets differ. *)
countTrap = Select[records, #["CountsAgree"] && Not[#["Equal"]] &];

(* Unsupported gates must fail loudly, never return Null. *)
unsupported = Quiet[createRepertoireByResult["NOSUCH", 3, 1]];
unsupportedOk = (Head[unsupported] === Failure);

ok = (failures === {}) && unsupportedOk;

CreateDirectory["results/tests/analysis_querysurface", CreateIntermediateDirectories -> True];
Export["results/tests/analysis_querysurface/QuerySurface.json",
  <|"casesChecked" -> Length[records],
    "families" -> Length[families],
    "failures" -> Length[failures],
    "countTrapCases" -> Length[countTrap],
    "unsupportedGateReturnsFailure" -> unsupportedOk,
    "failingCases" -> failures,
    "ok" -> ok|>];
Export["results/tests/analysis_querysurface/Status.txt", If[ok, "PASS", "FAIL"]];
Export["results/tests/analysis_querysurface/Debug.txt", StringJoin[
  "cases=", ToString[Length[records]], "\n",
  "failures=", ToString[Length[failures]], "\n",
  "unsupportedGateReturnsFailure=", ToString[unsupportedOk], "\n",
  If[failures === {}, "",
     "FAILING:\n" <> StringRiffle[
       (ToString[#["Gate"]] <> " ar=" <> ToString[#["Arity"]] <>
        " res=" <> ToString[#["Res"]] <>
        " counts=" <> ToString[#["GotCount"]] <> "/" <> ToString[#["TruthCount"]] <>
        " symDiff=" <> ToString[#["SymDiff"]]) & /@ failures, "\n"]]
]];
