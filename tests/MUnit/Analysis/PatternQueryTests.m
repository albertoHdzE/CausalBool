(* AUDIT02/P4d — the analytic partial-pattern query and its exhaustive baseline.

   Three assertions, all elementwise with symmetric difference (U8):

   A. PatternIndices == brute-force scan of the exhaustive MSB input table.
      This is the analytic-over-exhaustive claim at the level of a partial
      pattern: the closed form never builds the 2^n table.

   B. PatternIndices reproduces findPatternIndices from the retired exploratory
      file archive/causal-exploratory/CausalBool.m under Phi transport. That file is being
      archived, so its behaviour is pinned here rather than lost. The original
      is transcribed verbatim below, in LSB run arithmetic, so the two
      derivations remain genuinely independent.

   C. FilterRepertoireByOutput agrees with IndexSetNetwork on a real dispatched
      network: the rows it selects, mapped through Phi, are exactly the analytic
      one-set. This closes the loop from repertoire to closed form. *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`IndexAlgebra`"];
Needs["Integration`Gates`"];
Needs["Integration`Experiments`"];

phi[j_, n_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];

(* verbatim transcription of the retired findPatternIndices (LSB convention) *)
islandPattern[nodes_, wantedPatt_, sizeCM_] := Module[
  {n, m, limit, locations, i, ki, pi, period, numSequences, seqStarts, indices},
  n = sizeCM; m = Length[nodes]; limit = 2^n; locations = {};
  Do[ ki = nodes[[i]]; pi = wantedPatt[[i]];
      period = 2^(ki - 1); numSequences = limit/period;
      seqStarts = If[pi == 1, Range[1, numSequences - 1, 2], Range[0, numSequences - 2, 2]];
      indices = Flatten[Table[Range[p*period + 1, (p + 1)*period], {p, seqStarts}]];
      locations = If[locations === {}, indices, Intersection[locations, indices]],
    {i, 1, m}];
  Sort[locations]];

(* ---- A and B ---- *)
recordsAB = Flatten[Table[
   Table[
    Table[
     Module[{analytic, brute, island, inputs, sdA, sdB},
      analytic = Integration`IndexAlgebra`PatternIndices[n, nodeset, patt];
      inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
      brute = Sort@Flatten@Position[
        (And @@ MapThread[Function[{k, b}, #[[k]] === b], {nodeset, patt}]) & /@ inputs, True, 1];
      island = islandPattern[nodeset, patt, n];
      sdA = Union[Complement[analytic, brute], Complement[brute, analytic]];
      sdB = Union[Complement[island, Sort[phi[#, n] & /@ analytic]],
                  Complement[Sort[phi[#, n] & /@ analytic], island]];
      <|"n" -> n, "Nodes" -> nodeset, "Pattern" -> patt,
        "EqualToBruteForce" -> (analytic === brute), "SymDiffA" -> sdA,
        "EqualToIslandViaPhi" -> (island === Sort[phi[#, n] & /@ analytic]), "SymDiffB" -> sdB|>
     ], {patt, Tuples[{0, 1}, Length[nodeset]]}],
    {nodeset, Select[Subsets[Range[n], {1, Min[3, n]}], # =!= {} &]}],
   {n, {2, 3, 4}}], 2];

failA = Select[recordsAB, Not[#["EqualToBruteForce"]] &];
failB = Select[recordsAB, Not[#["EqualToIslandViaPhi"]] &];

(* ---- C: repertoire filter vs analytic one-set on a real network ---- *)
nC = 3; cmC = {{0, 1, 1}, {0, 0, 0}, {0, 0, 0}}; dynC = {"AND", "OR", "XOR"};
dispatchC = Integration`Experiments`CreateRepertoiresDispatch[cmC, dynC];
inRepC = Normal@dispatchC["RepertoireInputs"];
outRepC = Normal@dispatchC["RepertoireOutputs"];
filtC = Integration`IndexAlgebra`FilterRepertoireByOutput[inRepC, outRepC, 1, 1];
mappedC = Sort[phi[#, nC] & /@ filtC["Indices"]];
analyticC = Sort[Integration`Gates`IndexSetNetwork["AND", nC, {2, 3}, <||>]];
sdC = Union[Complement[mappedC, analyticC], Complement[analyticC, mappedC]];
okC = (mappedC === analyticC);

ok = (failA === {}) && (failB === {}) && okC;

CreateDirectory["results/tests/analysis_patternquery", CreateIntermediateDirectories -> True];
Export["results/tests/analysis_patternquery/PatternQuery.json",
  <|"casesAB" -> Length[recordsAB],
    "failuresVsBruteForce" -> Length[failA],
    "failuresVsIslandPhi" -> Length[failB],
    "filterMatchesAnalytic" -> okC, "filterSymDiff" -> sdC,
    "failingA" -> failA, "failingB" -> failB,
    "ok" -> ok|>];
Export["results/tests/analysis_patternquery/Status.txt", If[ok, "PASS", "FAIL"]];
Export["results/tests/analysis_patternquery/Debug.txt", StringJoin[
  "casesAB=", ToString[Length[recordsAB]], "\n",
  "failuresVsBruteForce=", ToString[Length[failA]], "\n",
  "failuresVsIslandPhi=", ToString[Length[failB]], "\n",
  "filterMatchesAnalytic=", ToString[okC], "  symDiff=", ToString[sdC], "\n"
]];
