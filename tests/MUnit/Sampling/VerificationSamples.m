Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];

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
Export[FileNameJoin[{base, "XOR_XNOR_Samples.json"}], <|"cm" -> cm2, "dyn" -> dynXX, "pattern" -> patXX, "samples" -> samplesXX|>];

(* Sampling 2: KOFN, arity 3, k=2 truth table *)
ttK = Integration`Gates`TruthTable["KOFN", 3, <|"k" -> 2|>];
sampleIdxK = Range[Min[4, Length[ttK]]];
samplesK = Table[<|"j" -> sampleIdxK[[s]], "x" -> ttK[[sampleIdxK[[s]], 1]], "y" -> ttK[[sampleIdxK[[s]], 2]]|>, {s, Length[sampleIdxK]}];
Export[FileNameJoin[{base, "KOFN_k2_Samples.json"}], <|"arity" -> 3, "k" -> 2, "samples" -> samplesK|>];

(* Sampling 3: CANALISING, arity 3, case A (i=1, v=1, c=0) *)
paramsA = <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 0|>;
ttC = Integration`Gates`TruthTable["CANALISING", 3, paramsA];
sampleIdxC = Range[Min[4, Length[ttC]]];
samplesC = Table[<|"j" -> sampleIdxC[[s]], "x" -> ttC[[sampleIdxC[[s]], 1]], "y" -> ttC[[sampleIdxC[[s]], 2]]|>, {s, Length[sampleIdxC]}];
Export[FileNameJoin[{base, "CANALISING_caseA_Samples.json"}], <|"arity" -> 3, "params" -> paramsA, "samples" -> samplesC|>];

(* Sampling 4: IMPLIES truth table *)
ttI = Integration`Gates`TruthTable["IMPLIES", 2];
sampleIdxI = Range[Min[4, Length[ttI]]];
samplesI = Table[<|"j" -> sampleIdxI[[s]], "x" -> ttI[[sampleIdxI[[s]], 1]], "y" -> ttI[[sampleIdxI[[s]], 2]]|>, {s, Length[sampleIdxI]}];
Export[FileNameJoin[{base, "IMPLIES_Samples.json"}], <|"arity" -> 2, "samples" -> samplesI|>];

Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];
