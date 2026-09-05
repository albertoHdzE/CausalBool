(* AUDIT03-B — is SelfTest.m's private engine the same engine?

   src/Packages/Integration/SelfTest.m carries its OWN myAnd, myOr, myXor,
   allPosibleInputsReverse and runNetwork. It is advertised in README.md as a
   core package, SelfTestRun is invoked by nothing, and none of it has ever been
   checked against Integration`Gates`ApplyGate.

   Both censuses missed it: the AST arm is Python-only, and the Wolfram arm
   matches normalised TEXT, so one-line definitions under different names are
   invisible to it.

   This measures, elementwise, before anything is touched:

     ARM 1  myAnd / myOr / myXor      vs  ApplyGate, every arity 1..6
     ARM 2  allPosibleInputsReverse   vs  the LSB-first enumeration convention
     ARM 3  runNetwork                vs  CreateRepertoiresDispatch, over
                                          AND/OR/XOR networks, every connected
                                          subset, every row
     ARM 4  runNetwork on the NINE families it does not implement — the
            question the other arms cannot ask

   Refuses rather than reporting a pass over nothing. Prints every denominator.

     exit 0  agree everywhere the comparison is defined
     exit 1  a disagreement exists (report it; do NOT collapse on it)
     exit 2  refused
*)

repo = If[StringQ[Environment["CB_REPO"]], Environment["CB_REPO"], Directory[]];
SetDirectory[repo];

Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];
(* SelfTest.m defines into Global`, which is exactly the point. *)
Get["src/Packages/Integration/SelfTest.m"];

If[DownValues[Global`myAnd] === {} || DownValues[Global`runNetwork] === {},
  Print["REFUSED: SelfTest.m did not define its private engine after loading."];
  Exit[2]];

apply = Integration`Gates`ApplyGate;
dispatch = Integration`Experiments`CreateRepertoiresDispatch;

(* ---- ARM 1: the three gate primitives -------------------------------- *)
arm1Total = 0; arm1Diff = 0; arm1Report = {};
Do[
  Module[{rows},
    rows = Tuples[{0, 1}, d];
    Do[
      Module[{v},
        v = {{"AND", Global`myAnd[r], apply["AND", r]},
             {"OR",  Global`myOr[r],  apply["OR", r]},
             {"XOR", Global`myXor[r], apply["XOR", r]}};
        Do[
          arm1Total++;
          If[c[[2]] =!= c[[3]],
            arm1Diff++;
            AppendTo[arm1Report, {c[[1]], r, c[[2]], c[[3]]}]],
          {c, v}]],
      {r, rows}]],
  {d, 1, 6}];

Print["ARM 1  gate primitives vs ApplyGate"];
Print["       ", arm1Total - arm1Diff, "/", arm1Total, " agree, ", arm1Diff, " differ",
      "   (arities 1..6, all 2^d rows, 3 gates)"];
Do[Print["         DIFF ", r], {r, Take[arm1Report, UpTo[10]]}];

(* ---- ARM 2: the input enumeration ------------------------------------ *)
arm2Total = 0; arm2Diff = 0;
Do[
  Module[{mine, canonical},
    mine = Global`allPosibleInputsReverse[n];
    canonical = Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];
    arm2Total++;
    If[mine =!= canonical, arm2Diff++;
      Print["         DIFF at n = ", n]]],
  {n, 1, 8}];
Print["ARM 2  allPosibleInputsReverse vs the LSB-first convention"];
Print["       ", arm2Total - arm2Diff, "/", arm2Total, " agree, ", arm2Diff, " differ  (n = 1..8)"];

(* ---- ARM 3: the network update, where runNetwork claims coverage ------ *)
SeedRandom[20260904];
arm3Total = 0; arm3Diff = 0; arm3Report = {};
gates3 = {"AND", "OR", "XOR"};
Do[
  Module[{cm, dyn, inputs, mine, theirs},
    (* every node gets a non-empty connected set, so the comparison is defined *)
    cm = Table[
      Module[{row = Table[0, {n}], k},
        k = RandomInteger[{1, n}];
        Do[row[[RandomInteger[{1, n}]]] = 1, {k}];
        If[Total[row] == 0, row[[RandomInteger[{1, n}]]] = 1];
        row],
      {n}];
    dyn = Table[RandomChoice[gates3], {n}];
    inputs = Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];
    mine = Global`runNetwork[cm, dyn, #] & /@ inputs;
    theirs = dispatch[cm, dyn]["RepertoireOutputs"];
    Do[
      arm3Total++;
      If[mine[[i]] =!= theirs[[i]],
        arm3Diff++;
        If[Length[arm3Report] < 5,
          AppendTo[arm3Report, {n, trial, i, mine[[i]], theirs[[i]]}]]],
      {i, Length[inputs]}]],
  {n, 2, 6}, {trial, 1, 8}];

Print["ARM 3  runNetwork vs CreateRepertoiresDispatch, AND/OR/XOR only"];
Print["       ", arm3Total - arm3Diff, "/", arm3Total, " rows agree, ", arm3Diff, " differ",
      "   (n = 2..6, 8 random networks each, every row)"];
Do[Print["         DIFF ", r], {r, arm3Report}];

(* ---- ARM 4: the question the other arms cannot ask -------------------- *)
(* runNetwork's Which has branches for AND, OR and XOR and a `True -> 0`
   fallthrough. The other NINE families therefore evaluate SILENTLY to 0 --
   the exact defect AUDIT02/P1 removed from CausalBoolCore.wl, where a missing
   CANALISING branch made a CANALISING node return 0 without a message. *)
missing = {"NAND", "NOR", "XNOR", "NOT", "IMPLIES", "NIMPLIES",
           "MAJORITY", "KOFN", "CANALISING"};
arm4Total = 0; arm4Silent = 0; arm4Report = {};
Do[
  Module[{cm, dyn, inputs, mine, wrong},
    cm = {{1, 1}, {1, 1}};
    dyn = {g, "AND"};
    inputs = Table[Reverse[IntegerDigits[x, 2, 2]], {x, 0, 3}];
    mine = Global`runNetwork[cm, dyn, #] & /@ inputs;
    (* node 1 under gate g, as the OWNER computes it *)
    wrong = Table[
      Module[{expected},
        expected = Quiet@Check[
          apply[g, inputs[[i]], If[g === "KOFN", <|"k" -> 1|>,
             If[g === "CANALISING",
                <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 0|>,
                <||>]]], $Failed];
        arm4Total++;
        If[IntegerQ[expected] && mine[[i, 1]] =!= expected, 1, 0]],
      {i, Length[inputs]}];
    If[Total[wrong] > 0,
      arm4Silent += Total[wrong];
      AppendTo[arm4Report, {g, Total[wrong], Length[inputs]}]]],
  {g, missing}];

Print["ARM 4  the nine families runNetwork does not implement"];
Print["       ", arm4Silent, "/", arm4Total,
      " rows evaluate to a SILENT 0 that disagrees with ApplyGate"];
Do[Print["         ", r[[1]], ": ", r[[2]], " of ", r[[3]], " rows wrong, no message"],
   {r, arm4Report}];

Print[""];
Print["VERDICT"];
Print["  primitives identical : ", arm1Diff === 0];
Print["  enumeration identical: ", arm2Diff === 0];
Print["  update identical on AND/OR/XOR: ", arm3Diff === 0];
Print["  families silently wrong: ", Length[arm4Report], " of ", Length[missing]];

If[arm1Total === 0 || arm3Total === 0,
  Print["REFUSED: an arm compared zero cases."]; Exit[2]];

If[arm1Diff =!= 0 || arm2Diff =!= 0 || arm3Diff =!= 0, Exit[1]];
