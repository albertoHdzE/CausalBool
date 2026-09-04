(* src/scripts/RunKnockoutDemo.m *)

(* 1. Set up Environment *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

(* Force reload to ensure latest changes *)
Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

Print["Packages loaded."];

(* 2. Helper to load and format the network from JSON *)
(* AUDIT03 — delegated to the single owner, src/scripts/NetworkIO.m, which
   carries the AUDIT02/H "logic" correction this copy lacked. *)
Get[FileNameJoin[{DirectoryName[$InputFileName], "NetworkIO.m"}]];

(* 3. Run Demo on Lambda Phage *)
netPath = FileNameJoin[{currentDir, "data", "bio", "processed", "lambda_phage.json"}];
Print["Loading network from: ", netPath];

net = LoadJSONNetwork[netPath];

If[net === $Failed, Exit[]];

Print["Network Loaded: ", net["name"]];
Print["Nodes: ", net["nodeNames"]];
Print["Gates: ", net["dynamic"]];
Print["Baseline Description Length (D): ", Integration`BioMetrics`ComputeDescriptionLength[net]["D"]];

Print["\nComputing Knockout Deltas..."];
result = Integration`BioExperiments`ComputeKnockoutDeltas[net];

(* 4. Display Results *)
Print["\n--- Causal Criticality Profile (Delta D) ---"];
crit = result["criticality"];
nodes = Keys[crit];
Do[
    Print[nodes[[i]], " -> ", crit[nodes[[i]]]];
, {i, Length[nodes]}];

(* 5. Export Results *)
outDir = FileNameJoin[{currentDir, "results", "bio", "knockouts"}];
If[!DirectoryQ[outDir], CreateDirectory[outDir]];
outPath = FileNameJoin[{outDir, "lambda_phage_criticality.json"}];

Export[outPath, result, "JSON"];
Print["\nFull results exported to: ", outPath];
