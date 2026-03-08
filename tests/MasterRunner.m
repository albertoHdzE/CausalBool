(* MasterRunner.m *)
(* Orchestrates comprehensive validation for Nature Protocol Level 3 *)

Print["================================================================="];
Print["   CAUSAL BOOLEAN INTEGRATION - MASTER VALIDATION SUITE"];
Print["   Protocol: Nature Level 3 (2D-BDM, N=200)"];
Print["================================================================="];
Print[""];

projectDir = DirectoryName[DirectoryName[$InputFileName]];
testsDir = FileNameJoin[{projectDir, "tests", "Nature"}];

(* Helper to run script *)
RunScript[name_, script_] := Module[{code, cmd},
    Print["Running Test: ", name, "..."];
    cmd = "/Applications/Wolfram.app/Contents/MacOS/WolframKernel -script " <> script;
    code = Run[cmd];
    If[code == 0,
        Print["[PASSED] ", name];
        Return[True];
    ,
        Print["[FAILED] ", name, " (Exit Code: ", code, ")"];
        Return[False];
    ];
];

RunPython[name_, script_] := Module[{code, cmd},
    Print["Running Test: ", name, "..."];
    cmd = "python3 " <> script;
    code = Run[cmd];
    If[code == 0,
        Print["[PASSED] ", name];
        Return[True];
    ,
        Print["[FAILED] ", name, " (Exit Code: ", code, ")"];
        Return[False];
    ];
];

results = {};

(* Phase 1: Foundation *)
AppendTo[results, RunScript["Phase 1: 2D-BDM Encoder (Mathematica Bridge)", FileNameJoin[{testsDir, "TSK-NATURE-LEV3-SETUP-002-Test.m"}]]];

(* Phase 2: Data *)
AppendTo[results, RunPython["Phase 2: Automated Dataset (N=96)", FileNameJoin[{testsDir, "TSK-NATURE-LEV3-DATA-001-Test.py"}]]];
AppendTo[results, RunScript["Phase 2: Manual Curation (N=20)", FileNameJoin[{testsDir, "TSK-NATURE-LEV3-DATA-002-Test.m"}]]];


Print[""];
Print["================================================================="];
Print["   SUMMARY"];
Print["================================================================="];

passed = Count[results, True];
total = Length[results];

Print["Tests Passed: ", passed, "/", total];

If[passed == total,
    Print["OVERALL STATUS: SUCCESS"];
    Exit[0];
,
    Print["OVERALL STATUS: FAILURE"];
    Exit[1];
];
