(* NetworkIO.m — one owner for reading the processed bio corpus.

   AUDIT03. LoadJSONNetwork had FOUR definitions in src/scripts/, and they had
   DRIFTED. The duplication census saw only two of them, because the other two
   differed textually; tools/check_single_engine.sh found the rest, which is the
   third time in this audit a guard has caught what an eye and a hash did not.

   CHOOSING THE OWNER MATTERED, and the first choice was wrong. Two of the four
   copies -- GlobalStatsPipeline.m and GlobalValidationAnalysis.m -- read only
   the "gates" field, which is a CLASSIFICATION LABEL. The copy in
   RunEssentialityValidation.m carries the AUDIT02/H correction: it also reads
   "logic", the authoritative per-node Boolean formula, because labels outside
   the twelve families otherwise reach ApplyGate and silently evaluate to 0.

   The superset is therefore the owner, and adopting it CORRECTS the two
   pipelines that were reading the corpus by label alone. That is an intended
   behavioural change, declared in tests/MUnit/BASELINE.md, not a refactor.

   Guarded by tools/check_single_engine.sh. *)

LoadJSONNetwork[path_] := Module[{json, rawNodes, rawCM, rawGates, rawLogic, n, nodeNames, cm, dynamic, params, i, name, gData, gType, gParams},
    If[!FileExistsQ[path], Return[$Failed]];
    json = Import[path, "RawJSON"];
    rawNodes = json["nodes"];
    rawCM = json["cm"];
    rawGates = json["gates"];
    (* AUDIT02/H: carry the per-node Boolean formulas through. The "gates" field
       is only a CLASSIFICATION LABEL; labels outside the twelve families used to
       reach ApplyGate and silently evaluate to 0. The formula in "logic" is the
       authoritative semantics and ComputeNextState now prefers it. *)
    rawLogic = Lookup[json, "logic", <||>];
    If[!AssociationQ[rawLogic], rawLogic = <||>];
    n = Length[rawNodes];
    nodeNames = rawNodes;
    cm = rawCM;
    dynamic = Table["", {n}];
    params = <||>;
    Do[
        name = nodeNames[[i]];
        gData = rawGates[name];
        gType = gData["gate"];
        gParams = gData["parameters"];
        dynamic[[i]] = gType;
        If[Length[gParams] > 0, params[i] = gParams];
    , {i, n}];
    <| "name" -> json["name"], "cm" -> cm, "nodeNames" -> nodeNames,
       "dynamic" -> dynamic, "params" -> params, "n" -> n, "logic" -> rawLogic |>
];
