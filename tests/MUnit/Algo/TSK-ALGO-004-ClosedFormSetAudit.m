(* AUDIT01/T4.7 - Closed-form-set sampled audit (the artifact the paper's
   validation-map needed): theorem-level evidence BEYOND exhaustive range.

   What is compared (two levels, both ELEMENTWISE - U8):
   (1) NODE level, COMPLETE (not sampled): each node's packaged closed-form one-set
       Integration`Gates`IndexSetAnalytic[n, Ic, gate, params] is MATERIALIZED,
       then projected onto its connected-input coordinates Ic, yielding an
       acceptance vector over all 2^d input patterns. That vector is compared
       entry-by-entry against direct gate evaluation (ApplyGate) over the same
       2^d patterns. This exercises the full closed-form index arithmetic
       (weights w(i)=2^(i-1), subset joins, complements) - not merely dispatch.
   (2) NETWORK level, SAMPLED: 1020 Hamming-stratified rows ({0,1,floor(n/2),
       n-1,n} x 204, seeds 301/302); the composed analytic prediction
       Y[j,i] = 1[row(j) in J_i] (via the projected acceptance vectors) is
       compared row-wise against direct synchronous evaluation. Any mismatch is
       reported as (row, node) - never counts alone.

   Scope honesty (ORDERING.md): one-set MATERIALISATION costs O(2^(n-d)); the
   audit therefore runs at n in {16,20} with in-degree <= 5, beyond the
   exhaustive-repertoire range (n <= 13). Larger-n dispatch-consistency remains
   TSK-ALGO-002-LargeSample (seeds 201/202) and carries no theorem claim. *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

base = FileNameJoin[{"results", "tests", "algo004closedformsetaudit"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {16, 20};
seeds = {301, 302};
gatesAll = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"};

drawParams[gate_String, d_Integer, rng_] :=
  Which[
    gate === "KOFN", <|"k" -> RandomInteger[{1, d}], "strict" -> RandomInteger[] == 1|>,
    gate === "CANALISING", <|"canalisingIndex" -> RandomInteger[{1, d}],
       "canalisingValue" -> RandomInteger[], "canalisedOutput" -> RandomInteger[]|>,
    True, <||>];

(* bits of repertoire row r under the canonical LSB convention (coordinate i weight 2^(i-1)) *)
lsbBits[r_Integer, n_Integer] := Reverse[IntegerDigits[r - 1, 2, n]];

runOne[n_Integer, seed_Integer] := Module[{cm, dyn, params, ics, nodeChecks, badNodes, accVecs, strata, sampleRows, netBad, tBuild, rowsChecked},
  SeedRandom[seed];
  cm = ConstantArray[0, {n, n}];
  (* Degree >= 2: the implication families require two connected inputs
     (params "pair" defaults to Ic[[;;2]]); the audited theorem space is
     multi-input gates. Mirrors ALGO-002 apart from this floor. *)
  Do[Module[{deg = RandomInteger[{2, Min[5, n - 1]}], choices},
     choices = RandomSample[Complement[Range[n], {i}], deg];
     cm[[i, choices]] = 1;], {i, n}];
  dyn = Table[RandomChoice[gatesAll], {n}];
  params = Table[drawParams[dyn[[k]], Length[Flatten@Position[cm[[k]], 1]], rng], {k, n}];
  ics = Table[Flatten@Position[cm[[k]], 1], {k, n}];

  (* ---- (1) node-level complete check: project closed-form set onto Ic ---- *)
  tBuild = AbsoluteTiming[
    nodeChecks = Table[
      Module[{d = Length[ics[[k]]], set, acc, expected, mism},
        set = Integration`Gates`IndexSetAnalytic[n, ics[[k]], dyn[[k]], params[[k]]];
        If[set === $Failed, Return[$Failed, Module]];
        acc = ConstantArray[0, 2^d];
        Do[Module[{b = lsbBits[r, n]},
           acc[[FromDigits[b[[ics[[k]]]], 2] + 1]] = 1], {r, set}];
        expected = Table[Integration`Gates`ApplyGate[dyn[[k]],
           IntegerDigits[x, 2, d], params[[k]]], {x, 0, 2^d - 1}];
        (* Index alignment (no reversal needed): acc keys and expected indices BOTH
           treat input-position 1 (coordinate Ic[[1]]) as the most significant bit -
           FromDigits[list,2] and IntegerDigits[x,2,d] share that convention. *)
        mism = Position[MapThread[Unequal, {acc, expected}], True, {1}];
        <|"node" -> k, "gate" -> dyn[[k]], "d" -> d, "|J|" -> Length[set],
          "mismatchCount" -> Length[mism],
          "mismatchPatternsIdx" -> Flatten[mism]|>],
      {k, n}]];
  badNodes = Select[nodeChecks, #["mismatchCount"] > 0 &];

  (* ---- (2) network-level sampled rows ---- *)
  strata = {0, 1, Floor[n/2], n - 1, n};
  (* Rows stay INTACT as bit vectors: Flatten would dissolve them into single
     bits (caught in execution v4 - rowsChecked counted bits, network-level
     check was vacuous). *)
  sampleRows = Catenate@Table[
     Module[{w = ww, per = 204},
      Table[Module[{pos = If[w == 0, {}, If[w == n, Range[n], RandomSample[Range[n], w]]],
             v = ConstantArray[0, n]}, v[[pos]] = 1; v], {per}]],
     {ww, strata}];
  accVecs = Table[
    (* NOTE: allocate acc in the BODY, not the init list - Module initialisation
       values evaluate before earlier locals bind, so 2^d there stays symbolic
       (caught by execution: SymbolicZerosArray errors, T4.7 session 2026-08-25). *)
    Module[{d = Length[ics[[k]]], set, acc},
      acc = ConstantArray[0, 2^d];
      set = Integration`Gates`IndexSetAnalytic[n, ics[[k]], dyn[[k]], params[[k]]];
      Do[Module[{b = lsbBits[r, n]},
         acc[[FromDigits[b[[ics[[k]]]], 2] + 1]] = 1], {r, set}];
      acc], {k, n}];
  rowsChecked = 0; netBad = {};
  MapIndexed[
   (* The sampled row IS the LSB coordinate vector (v[[pos]]=1 by coordinate);
      no lsbBits conversion - lsbBits takes an integer repertoire index and
      silently stayed symbolic when handed a list (execution v5 catch). *)
   Module[{row = #1, yAna, yApp, t = First[#2]},
     yAna = Table[accVecs[[k]][[FromDigits[row[[ics[[k]]]], 2] + 1]], {k, n}];
     yApp = Table[Integration`Gates`ApplyGate[dyn[[k]], row[[ics[[k]]]], params[[k]]], {k, n}];
     rowsChecked += 1;
     Do[If[yAna[[k]] =!= yApp[[k]], AppendTo[netBad, <|"rowIdx" -> t, "node" -> k|>]], {k, n}]] &,
   sampleRows];

  <|"n" -> n, "seed" -> seed,
    "families" -> Counts[dyn],
    "nodeAuditMismatches" -> Total[nodeChecks[[All, "mismatchCount"]]],
    "nodeLevelCompletePatterns" -> Total[Table[2^nc["d"], {nc, nodeChecks}]],
    "badNodes" -> badNodes,
    "sampledRows" -> rowsChecked,
    "networkMismatchCells" -> Length[netBad],
    "networkMismatchLocations" -> Take[netBad, UpTo[20]],
    "setMaterialisationSeconds" -> N[First[tBuild], 6]|>];

metrics = Flatten[Table[Module[{m = runOne[nn, s]},
    Print["ALGO-004 done n=", nn, " seed=", s,
      " | nodeMismatches=", m["nodeAuditMismatches"],
      " netMismatchCells=", m["networkMismatchCells"]]; m],
   {nn, sizes}, {s, seeds}], 1];
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[AllTrue[metrics, #["nodeAuditMismatches"] == 0 && #["networkMismatchCells"] == 0 &],
   "OK",
   "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Print["ALGO-004 ", status,
  " | node-level mismatched patterns: ", Total[metrics[[All, "nodeAuditMismatches"]]],
  " | network-level mismatched cells: ", Total[metrics[[All, "networkMismatchCells"]]],
  " | rows: ", Total[metrics[[All, "sampledRows"]]]]
