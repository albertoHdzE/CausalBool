
import re
import math
import sys

def parse_mathematica_list(filepath):
    """
    Parses a Mathematica list of pairs {"string", fraction} from a file.
    Returns a dictionary mapping string to -log2(probability).
    """
    lookup = {}
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Regex to find {"string", numerator/denominator}
        # Matches: {"0101", 123/456}
        regex = r'\{"([01]+)",\s*(\d+)/(\d+)\}'
        matches = re.findall(regex, content)
        
        print(f"Found {len(matches)} matches in {filepath}")
        
        for s, n, d in matches:
            prob = float(n) / float(d)
            if prob > 0:
                bdm = -math.log2(prob)
                lookup[s] = bdm
                
        return lookup
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return {}

def string_bdm(string, lookup, block_size=12, step=1):
    """
    Computes BDM for a string using the lookup table.
    If string length <= 12 (or found in lookup), returns direct value.
    Otherwise, partitions into blocks.
    """
    # 1. Direct lookup
    if string in lookup:
        return lookup[string]
        
    # 2. Partitioning (if not found directly)
    # The Mathematica code uses StringPartition[string, 12, len]
    # If len=1 (default), it's sliding window?
    # But usually BDM sums non-overlapping blocks to be additive.
    # However, the notebook code used Tally on the partition.
    # Let's assume standard BDM uses non-overlapping blocks for additivity,
    # but the notebook might be doing something else.
    # Given the user's "straightforward" comment, let's try to match the lookup first.
    
    # If string is not in lookup, we can't compute it directly.
    # For now, return None or try to decompose.
    
    # Let's try decomposing into max available block sizes if strictly needed.
    # But first let's see what's in the table.
    return None

def main():
    d5_path = '/Users/alberto/Documents/projects/CausalBoolIntegration/mathematicabdm/D5.m'
    
    print("Parsing D5.m...")
    lookup = parse_mathematica_list(d5_path)
    
    # Verify coverage
    lengths = {}
    for s in lookup:
        l = len(s)
        lengths[l] = lengths.get(l, 0) + 1
        
    print("\nString counts by length in D5.m:")
    for l in sorted(lengths.keys()):
        print(f"Length {l}: {lengths[l]} strings")
        
    # Validation of Complexity Property (Structured vs Random)
    validation_pairs = [
        ("Len 6 Low Entropy", "000000"),
        ("Len 6 High Entropy", "001011"), # User example
        ("Len 8 Low Entropy", "00000000"),
        ("Len 8 High Entropy", "01010101"), # Alternating is simple too, but let's see
        ("Len 8 Random", "11010010"),
    ]
    
    print("\n--- Validation (Structured < Random?) ---")
    for name, seq in validation_pairs:
        val = string_bdm(seq, lookup)
        if val is not None:
            print(f"{name} [{seq}]: {val:.4f} bits")
        else:
            print(f"{name} [{seq}]: Not found")

    # Test Cases
    test_cases = [
        ("User Example (Len 6)", "001011"),
        ("Lambda Phage CI (Len 4)", "1000"),
        ("Lambda Phage Cro (Len 2)", "10"),
        ("Lac Operon lacZ (Len 4)", "1001"),
        ("Yeast Cdc2 (Len 8)", "01010101"),
        ("Random Len 10", "1010101010"),
        ("Random Len 12", "101010101010"),
    ]
    
    print("\n--- String BDM Results (Direct Lookup) ---")
    for name, seq in test_cases:
        val = string_bdm(seq, lookup)
        if val is not None:
            print(f"{name} [{seq}]: {val:.4f} bits")
        else:
            print(f"{name} [{seq}]: Not found in DB")

if __name__ == "__main__":
    main()
