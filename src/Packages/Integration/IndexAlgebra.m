BeginPackage["Integration`IndexAlgebra`"]
IndexSetUniverse::usage = "Return the universe of indices {1..2^n} for network size n";
IndexSetComplement::usage = "Return the complement of a set within the universe {1..2^n}";
IndexSetUnion::usage = "Union of index sets";
IndexSetIntersection::usage = "Intersection of index sets";
Phi::usage = "Bit-reversal mapping between MSB/LSB orderings: Phi[j,n]";
MapPhi::usage = "Map a list of indices via Phi for given n";
OneBandIndices::usage = "Indices where bit i equals 1 in ordered exhaustive inputs of length n";
ZeroBandIndices::usage = "Indices where bit i equals 0 in ordered exhaustive inputs of length n";
Begin["`Private`"]
IndexSetUniverse[n_Integer] := Range[1, 2^n]
Phi[j_Integer, n_Integer] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2]
MapPhi[set_List, n_Integer] := Phi[#, n] & /@ set
IndexSetComplement[n_Integer, set_List] := Complement[IndexSetUniverse[n], set]
IndexSetUnion[sets__List] := Union[sets]
IndexSetIntersection[sets__List] := Intersection[sets]
OneBandIndices[n_Integer, i_Integer] := Module[{inputs}, inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}]; Flatten@Position[(#[[i]] == 1) & /@ inputs, True, 1]]
ZeroBandIndices[n_Integer, i_Integer] := Module[{inputs}, inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}]; Flatten@Position[(#[[i]] == 0) & /@ inputs, True, 1]]
End[]
EndPackage[]
