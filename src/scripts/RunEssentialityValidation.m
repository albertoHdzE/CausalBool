currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

(* AUDIT03 — delegated to the single owner, src/scripts/NetworkIO.m, which
   carries the AUDIT02/H "logic" correction this copy lacked. *)
Get[FileNameJoin[{DirectoryName[$InputFileName], "NetworkIO.m"}]];

essPath = FileNameJoin[{currentDir, "data", "bio", "validation", "essentiality_data.csv"}];

allEss = Integration`BioExperiments`LoadEssentialityData[essPath];

networks = {"lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"};

Do[
  netName = net;
  netPath = FileNameJoin[{currentDir, "data", "bio", "processed", netName <> ".json"}];
  Print["\n=== Network: ", netName, " ==="];
  loadedNet = LoadJSONNetwork[netPath];
  If[loadedNet === $Failed,
    Print["Skipping ", netName, ": network file not found."];
    Continue[];
  ];
  res = Integration`BioExperiments`ComputeKnockoutDeltas[loadedNet];
  crit = res["criticality"];
  behRes = Integration`BioExperiments`ComputeKnockoutBehaviorDeltas[loadedNet];
  behCrit = If[AssociationQ[behRes] && KeyExistsQ[behRes, "behavior_criticality"], behRes["behavior_criticality"], <||>];
  If[KeyExistsQ[allEss, netName],
    ess = allEss[netName];
    comparison = If[AssociationQ[behCrit] && behCrit =!= <||>,
      Integration`BioExperiments`CompareCriticalityToEssentiality[crit, ess, behCrit],
      Integration`BioExperiments`CompareCriticalityToEssentiality[crit, ess]
    ];
    If[Length[comparison] == 0,
      Print["No overlapping genes between criticality and essentiality for ", netName, "."],
      Print["Gene\tDeltaD\tDeltaB\tEssential\tPred"];
      Do[
        Print[
          row["Gene"], "\t",
          NumberForm[row["DeltaD"], {4, 2}], "\t",
          If[KeyExistsQ[row, "DeltaBehavior"], NumberForm[row["DeltaBehavior"], {4, 2}], "-"], "\t",
          row["Essentiality"], "\t\t",
          row["Prediction"]
        ],
        {row, comparison}
      ];
      correct = Count[comparison, row_ /; row["Essentiality"] == row["Prediction"]];
      total = Length[comparison];
      Print["Accuracy: ", correct, "/", total, " (", N[correct/total]*100, "%)"];
    ];
    ,
    Print["No essentiality data available for ", netName, "."]
  ];
,
{net, networks}
];
