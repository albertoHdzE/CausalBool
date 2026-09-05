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

(* AUDIT03-C — THE INTERPRETER MUST BE DECLARED, NOT INHERITED.
   
   This package used to shell out to a bare "python3", taken from PATH. The
   mutation harness caught the consequence by running the suite in a clean git
   worktree, where TSK-NATURE-LEV3-SETUP-002 FAILED while passing in the working
   tree. Root cause, measured:
   
       repo root      python3 -> ~/.pyenv/versions/3.13.12/bin/python3   (numpy)
       /tmp/worktree  python3 -> ~/.pyenv/versions/3.11.10/bin/python3   (no numpy)
   
   pyenv resolves the shim per directory, so the SAME test gave a different
   verdict depending on where it was run from. A test whose result depends on
   the ambient environment is not a test of this repository.
   
   The repository's own venv is now preferred and the fallback is announced
   rather than silent, so an inherited interpreter is a visible decision. *)

FindPythonInterpreter[] := Module[{root, candidate},
    root = PackageDir;
    (* PackageDir is <repo>/src/integration/; the venv sits at <repo>/venv *)
    candidate = FileNameJoin[{ParentDirectory[ParentDirectory[root]], "venv", "bin", "python"}];
    If[FileExistsQ[candidate], candidate,
        Message[UniversalDv2::ambientpython, candidate];
        "python3"]
];

UniversalDv2::ambientpython = "AUDIT03-C: no interpreter at `1`; falling back to whatever \"python3\" means on PATH. That resolution is directory-dependent under pyenv and has already produced a different verdict for the same test in two directories.";

UniversalDv2[adj_?MatrixQ] := Module[
    {script, cmd, jsonStr, result, proc, output},
    
    script = FindCLIScript[];
    
    (* Convert matrix to string format compatible with CLI *)
    (* JSON format is safest: [[1,0],[0,1]] *)
    jsonStr = ExportString[adj, "JSON", "Compact"->True];
    
    (* Construct command. The interpreter is DECLARED (see
       FindPythonInterpreter), not inherited from PATH. *)
    cmd = {FindPythonInterpreter[], script, "--matrix", jsonStr};
    
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
