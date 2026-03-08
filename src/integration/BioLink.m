(* ::Package:: *)

(* :Title: BioLink *)
(* :Context: Integration`BioLink` *)
(* :Author: Alberto Hernández & Oxford Collaboration *)
(* :Summary: JSON Interchange for Biological Networks *)
(* :Date: January 2026 *)

BeginPackage["Integration`BioLink`"];

ImportNetworkJSON::usage = "ImportNetworkJSON[file] imports a biological network definition from a JSON file.";
ExportResultsJSON::usage = "ExportResultsJSON[file, data] exports analysis results to a JSON file.";
BioBridgePath::usage = "BioBridgePath[] returns the configured data directory.";

Begin["`Private`"];

(* Helper to locate data directory relative to this package *)
(* Assuming structure: src/Packages/Integration/BioLink.m or src/integration/BioLink.m *)
(* Adjusting to project root *)

FindProjectRoot[] := Module[{dir},
    dir = DirectoryName[$InputFileName];
    (* Walk up to find 'data' folder *)
    If[FileExistsQ[FileNameJoin[{dir, "..", "..", "data", "bio"}]],
        FileNameJoin[{dir, "..", ".."}],
        (* Fallback: Assume we are in src/integration *)
        FileNameJoin[{dir, "..", ".."}]
    ]
];

BioBridgePath[] := FileNameJoin[{FindProjectRoot[], "data", "bio", "processed"}];

ImportNetworkJSON[filename_String] := Module[
    {path, json, cm, nodes, gates},
    
    path = If[FileExistsQ[filename], filename, FileNameJoin[{BioBridgePath[], filename}]];
    
    If[!FileExistsQ[path],
        Return[$Failed]
    ];
    
    json = Import[path, "JSON"];
    
    (* Extract fields *)
    (* Expecting: "nodes", "cm" (optional), "logic" (optional) *)
    
    <|
        "name" -> FileBaseName[filename],
        "nodes" -> Lookup[json, "nodes", {}],
        "cm" -> Lookup[json, "cm", {}],
        "logic" -> Association[Lookup[json, "logic", {}]],
        "raw" -> json
    |>
];

ExportResultsJSON[filename_String, data_] := Module[
    {path},
    
    path = FileNameJoin[{BioBridgePath[], filename}];
    
    Export[path, data, "JSON"];
    
    path
];

End[];

EndPackage[];
