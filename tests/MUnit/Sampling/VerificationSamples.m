Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];

(* AUDIT03-B. This file COMPUTED THE GATE TRUTH TABLES AND CHECKED NOTHING.

   It exported XOR/XNOR, KOFN k=2, CANALISING case A and IMPLIES as "samples"
   and then wrote the literal string "OK", whatever the rows contained. It is
   the ONLY one of the eleven quarantined files whose output is referenced by an
   ACTIVE manuscript (papers/method/manuscript_formal/method_paper.tex); the
   other ten appear only in doc/newIntPaper and doc/finalpaper, which CLAUDE.md
   declares provenance archives.

   The predicate below was always available and is stated INDEPENDENTLY of
   Integration`Gates`: each sampled row is compared with the closed form written
   out here, not with the engine that produced it. Verified to fail by
   perturbing a row. *)

expectXor[x_List]  := Mod[Total[x], 2];
expectXnor[x_List] := 1 - Mod[Total[x], 2];
expectKofn[x_List, k_Integer] := Boole[Count[x, 1] >= k];
expectImplies[x_List] := Boole[x[[1]] == 0 || x[[2]] == 1];
(* GOVERNANCE/GLOSSARY.md: the NON-canalised branch is Or over the inputs,
   NOT a constant default. That distinction is what AUDIT02/P1 restored. *)
expectCanalising[x_List, i_Integer, v_Integer, out_Integer] :=
  If[x[[i]] == v, out, Boole[Count[x, 1] > 0]];

checks = {};
addCheck[label_String, x_List, got_, want_] :=
  AppendTo[checks, <|"case" -> label, "x" -> x, "got" -> got,
                     "want" -> want, "ok" -> (got === want)|>];

patternSymbol[col_List] := Module[{z = Count[col, 0], o = Count[col, 1]}, If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];

createDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "sampling"}];
createDir[base];

(* Sampling 1: XOR/XNOR, n=2, full in-degree *)
cm2 = {{1, 1}, {1, 1}};
dynXX = {"XOR", "XNOR"};
resXX = Integration`Experiments`CreateRepertoiresDispatch[cm2, dynXX];
inputsXX = resXX["RepertoireInputs"]; outputsXX = resXX["RepertoireOutputs"];
patXX = patternSymbol /@ Transpose[outputsXX];
sampleIdxXX = Take[Range[Length[inputsXX]], Min[4, Length[inputsXX]]];
samplesXX = Table[<|"j" -> j, "x" -> inputsXX[[j]], "y" -> outputsXX[[j]]|>, {j, sampleIdxXX}];
Do[addCheck["XOR", s["x"], s["y"][[1]], expectXor[s["x"]]];
   addCheck["XNOR", s["x"], s["y"][[2]], expectXnor[s["x"]]], {s, samplesXX}];
Export[FileNameJoin[{base, "XOR_XNOR_Samples.json"}], <|"cm" -> cm2, "dyn" -> dynXX, "pattern" -> patXX, "samples" -> samplesXX|>];

(* Sampling 2: KOFN, arity 3, k=2 truth table *)
ttK = Integration`Gates`TruthTable["KOFN", 3, <|"k" -> 2|>];
sampleIdxK = Range[Min[4, Length[ttK]]];
samplesK = Table[<|"j" -> sampleIdxK[[s]], "x" -> ttK[[sampleIdxK[[s]], 1]], "y" -> ttK[[sampleIdxK[[s]], 2]]|>, {s, Length[sampleIdxK]}];
Do[addCheck["KOFN k=2", s["x"], s["y"], expectKofn[s["x"], 2]], {s, samplesK}];
Export[FileNameJoin[{base, "KOFN_k2_Samples.json"}], <|"arity" -> 3, "k" -> 2, "samples" -> samplesK|>];

(* Sampling 3: CANALISING, arity 3, case A (i=1, v=1, c=0) *)
paramsA = <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 0|>;
ttC = Integration`Gates`TruthTable["CANALISING", 3, paramsA];
sampleIdxC = Range[Min[4, Length[ttC]]];
samplesC = Table[<|"j" -> sampleIdxC[[s]], "x" -> ttC[[sampleIdxC[[s]], 1]], "y" -> ttC[[sampleIdxC[[s]], 2]]|>, {s, Length[sampleIdxC]}];
Do[addCheck["CANALISING A", s["x"], s["y"], expectCanalising[s["x"], 1, 1, 0]], {s, samplesC}];
Export[FileNameJoin[{base, "CANALISING_caseA_Samples.json"}], <|"arity" -> 3, "params" -> paramsA, "samples" -> samplesC|>];

(* Sampling 4: IMPLIES truth table *)
ttI = Integration`Gates`TruthTable["IMPLIES", 2];
sampleIdxI = Range[Min[4, Length[ttI]]];
samplesI = Table[<|"j" -> sampleIdxI[[s]], "x" -> ttI[[sampleIdxI[[s]], 1]], "y" -> ttI[[sampleIdxI[[s]], 2]]|>, {s, Length[sampleIdxI]}];
Do[addCheck["IMPLIES", s["x"], s["y"], expectImplies[s["x"]]], {s, samplesI}];
Export[FileNameJoin[{base, "IMPLIES_Samples.json"}], <|"arity" -> 2, "samples" -> samplesI|>];

(* Refuse rather than pass on nothing: a verification over zero sampled rows
   is not a verification. *)
nChecks = Length[checks];
nOK = Count[checks, c_ /; TrueQ[c["ok"]]];
allOK = (nChecks >= 16) && (nOK === nChecks);

Print["VerificationSamples: ", nOK, "/", nChecks,
      " sampled rows match the closed form"];
If[!allOK,
  Print["  MISMATCHES:"];
  Do[Print["    ", c["case"], " x=", c["x"], " got=", c["got"], " want=", c["want"]],
     {c, Select[checks, !TrueQ[#["ok"]] &]}];
  If[nChecks < 16, Print["    only ", nChecks, " rows checked; expected at least 16"]]];

Export[FileNameJoin[{base, "Checks.json"}], checks, "JSON"];
Export[FileNameJoin[{base, "Status.txt"}], If[allOK, "OK", "FAIL"], "Text"];
