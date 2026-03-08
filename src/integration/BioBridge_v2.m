(* ::Package:: *)

(* :Title: BioBridgeV2 *)
(* :Context: Integration`BioBridgeV2` *)
(* :Author: Alberto Hernández & Oxford Collaboration *)
(* :Summary: Mathematica Wrapper for Universal D_v2 Encoder (Python) *)
(* :Date: January 2026 *)

BeginPackage["Integration`BioBridgeV2`"];

UniversalDv2::usage = "UniversalDv2[adjMatrix] calls the Python Universal_D_v2_Encoder to compute structural complexity.";
VerifyBridge::usage = "VerifyBridge[] runs a self-test.";

Begin["`Private`"];

(* Capture directory at load time *)
PackageDir = DirectoryName[$InputFileName];

(* Helper to locate the CLI script *)
FindCLIScript[] := FileNameJoin[{PackageDir, "cli_dv2.py"}];

UniversalDv2[adj_?MatrixQ] := Module[
    {script, cmd, jsonStr, result, proc, output},
    
    script = FindCLIScript[];
    
    (* Convert matrix to string format compatible with CLI *)
    (* JSON format is safest: [[1,0],[0,1]] *)
    jsonStr = ExportString[adj, "JSON", "Compact"->True];
    
    (* Construct command *)
    (* Assuming python3 is available in PATH. Adjust if necessary. *)
    cmd = {"python3", script, "--matrix", jsonStr};
    
    (* Run Process *)
    proc = RunProcess[cmd];
    
    If[proc["ExitCode"] =!= 0,
        Print["[BioBridgeV2] Error executing Python script:"];
        Print[proc["StandardError"]];
        Return[$Failed]
    ];
    
    output = proc["StandardOutput"];
    
    (* Parse JSON result *)
    result = ImportString[output, "JSON"];
    
    (* Return the 'dv2' value and full details *)
    <|
        "dv2" -> Lookup[result, "dv2"],
        "block_details" -> Lookup[result, "block_details"]
    |>
];

VerifyBridge[] := Module[{testAdj, res},
    Print["[BioBridgeV2] Verifying bridge..."];
    testAdj = {{0, 1, 0, 1}, {1, 0, 1, 0}, {0, 1, 0, 1}, {1, 0, 1, 0}};
    res = UniversalDv2[testAdj];
    
    If[res === $Failed,
        Print["[BioBridgeV2] FAILED."];
        False,
        Print["[BioBridgeV2] SUCCESS. D_v2 = ", res["dv2"]];
        True
    ]
];

End[];

EndPackage[];
