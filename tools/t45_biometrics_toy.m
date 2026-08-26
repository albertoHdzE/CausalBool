(* ::Package:: *)
(* AUDIT01/T4.5 - BioMetrics D on the shared T4.5 toy network.
   Wiring mirrors tools/t45_description_length_fixtures.py exactly:
   n=4; node1<-{2,3} AND, node2<-{3} OR, node3<-{4} XOR, node4<-{1} NOT
   (1-based WL; python fixture nodes 0..3).
   Prints a single number: BioMetrics ComputeDescriptionLength D (bits),
   NO log2(n) header - that asymmetry vs pathinfo graph_description_length
   is V5's cross-repo nonidentity finding. *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`BioMetrics`"];

cm = {
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 0, 1},
  {1, 0, 0, 0}};
dyn = {"AND", "OR", "XOR", "NOT"};
params = <||>;

res = ComputeDescriptionLength[cm, dyn, params];
d = If[AssociationQ[res], res["D"], res];
Print[d]
