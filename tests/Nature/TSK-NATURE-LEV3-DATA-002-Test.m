(* TSK-NATURE-LEV3-DATA-002-Test.m *)
(* Validates Phase 2: Manual Curation (Gold Standard) *)

Print["------------------------------------------------"];
Print["   Test: Phase 2 Manual Curation (DATA-002)"];
Print["------------------------------------------------"];

projectDir = DirectoryName[DirectoryName[DirectoryName[$InputFileName]]];
metadataPath = FileNameJoin[{projectDir, "data", "bio", "curated", "metadata.csv"}];
processedDir = FileNameJoin[{projectDir, "data", "bio", "processed"}];

If[!FileExistsQ[metadataPath],
    Print[">> Metadata CSV not found! FAIL"];
    Exit[1];
];

Print[">> Loading metadata from: ", metadataPath];
data = Import[metadataPath, "Dataset", HeaderLines -> 1];
rows = Length[data];
Print[">> Found ", rows, " entries."];

If[rows < 20,
    Print[">> WARNING: Less than 20 entries found (Target N=20)."];
];

files = Normal[data[All, "Filename"]];
missingFiles = {};
validFiles = 0;

Do[
    file = files[[i]];
    fullPath = FileNameJoin[{processedDir, file}];
    If[!FileExistsQ[fullPath],
        AppendTo[missingFiles, file];
        Print[">> Missing: ", file];
    ,
        (* Validate JSON Content *)
        json = Import[fullPath, "JSON"];
        nodes = Lookup[json, "nodes", {}];
        edges = Lookup[json, "edges", {}];
        
        If[Length[nodes] > 0,
            validFiles++;
        ,
            Print[">> Invalid JSON (no nodes): ", file];
        ];
    ];
, {i, Length[files]}];

Print["------------------------------------------------"];
Print["   Results"];
Print["------------------------------------------------"];
Print["Total Entries: ", rows];
Print["Valid Files:   ", validFiles];
Print["Missing Files: ", Length[missingFiles]];

If[Length[missingFiles] == 0 && validFiles >= 20,
    Print[">> STATUS: PASSED"];
    Exit[0];
,
    Print[">> STATUS: FAILED"];
    Exit[1];
];
