import re
import math
import numpy as np

def parse_mathematica_table(filepath):
    """
    Parses the Mathematica table file squares2Dsize1to4.m
    Returns a dictionary mapping matrix tuples to BDM values.
    """
    lookup = {}
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    print(f"Read {len(content)} characters from {filepath}")
    
    # Regex to find all entries
    # Pattern:
    # Look for matrix structure: { ... } followed by , Log[ ... ]/Log[2]
    # The matrix structure only contains digits, commas, spaces, braces.
    
    # We capture two groups:
    # 1. The matrix string (e.g. "{{{{0}}")
    # 2. The fraction string inside Log (e.g. "109083841447/20171875000")
    
    # Note: re.DOTALL is not needed if we don't use .
    # But whitespace \s matches newlines.
    
    regex = r'(\{(?:[\d,\s\{\}]+)\}),\s*Log\[(.*?)\]/Log\[2\]'
    
    matches = re.findall(regex, content)
    print(f"Found {len(matches)} matches using regex.")
    
    count = 0
    for i, (matrix_str, fraction_str) in enumerate(matches):
        try:
            # Clean matrix string: replace { -> [, } -> ]
            py_str = matrix_str.replace('{', '[').replace('}', ']')
            
            # Balance brackets
            while py_str.count('[') > py_str.count(']'):
                py_str = py_str.replace('[', '', 1)
            while py_str.count(']') > py_str.count('['):
                py_str = py_str[::-1].replace(']', '', 1)[::-1]
            
            # Now eval
            try:
                data = eval(py_str)
            except:
                continue

            matrix = data
            # Unwrap
            while isinstance(matrix, list) and len(matrix) > 0 and isinstance(matrix[0], list) and isinstance(matrix[0][0], list):
                matrix = matrix[0]
                
            # Now matrix should be [[0]] or [[0,0],[0,0]]
            if isinstance(matrix, list) and isinstance(matrix[0], list):
                matrix_tuple = tuple(tuple(row) for row in matrix)
                
                # Parse value
                if '/' in fraction_str:
                    n, d = fraction_str.split('/')
                    val = math.log2(float(n)/float(d))
                else:
                    val = math.log2(float(fraction_str))
                    
                lookup[matrix_tuple] = val
                count += 1
                
        except Exception as e:
            if count == 0:
                 print(f"Error parsing candidate: {candidate if 'candidate' in locals() else 'No candidate'} : {e}")
                 # pass
            continue
            
    print(f"Successfully parsed {count} entries.")
    return lookup

def compute_micro_bdm(binary_string, lookup):
    """
    Computes BDM for a short binary string using the lookup table.
    """
    n = len(binary_string)
    
    # Strategy for Length 4 -> 2x2
    if n == 4:
        # [[a,b], [c,d]]
        matrix = (tuple(binary_string[0:2]), tuple(binary_string[2:4]))
        if matrix in lookup:
            return -lookup[matrix] # Return positive complexity

    # Strategy for Length 8 -> Two 2x2
    if n == 8:
        m1 = (tuple(binary_string[0:2]), tuple(binary_string[2:4]))
        m2 = (tuple(binary_string[4:6]), tuple(binary_string[6:8]))
        
        val1 = lookup.get(m1)
        val2 = lookup.get(m2)
        
        if val1 is not None and val2 is not None:
            return -(val1 + val2)
        
    # Strategy for Length 2 -> Two 1x1
    if n == 2:
        # [[a]], [[b]]
        m1 = ((binary_string[0],),)
        m2 = ((binary_string[1],),)
        
        val1 = lookup.get(m1)
        val2 = lookup.get(m2)
        
        if val1 is not None and val2 is not None:
            return -(val1 + val2)

    return None

def main():
    table_path = '/Users/alberto/Documents/projects/CausalBoolIntegration/mat-bdm/squares2Dsize1to4.m'
    lookup = parse_mathematica_table(table_path)
    
    # Verify table contents
    print(f"Loaded {len(lookup)} matrices.")
    print("Sample 1x1:", lookup.get(((0,),)))
    print("Sample 2x2:", lookup.get(((0,0),(0,0))))
    
    # Test Cases (from bioProcess.tex)
    # Lambda Phage CI (k=2, len=4) -> "1000" (or similar, need actual truth table)
    # Let's use the actual truth tables from json or hardcode them if we know them.
    # Based on verify_bdm_small_strings.py logic, we can construct them.
    
    test_cases = [
        ("Lambda Phage CI (Len 4)", [1, 0, 0, 0]), # Example
        ("Lambda Phage Cro (Len 2)", [1, 0]),      # Example
        ("Lac Operon lacZ (Len 4)", [1, 0, 0, 1]), # Example
        ("Yeast Cdc2 (Len 8)", [0, 1, 0, 1, 0, 1, 0, 1]), # Example
    ]
    
    # Note: Table values are log2(P). Complexity K = -log2(P).
    # So if table gives -20, K = 20.
    
    print("\n--- BDM Calculation Results ---")
    for name, seq in test_cases:
        # Check if 1x1, 2x2 exists in table
        # We need to know if the table has negative values (log2(P) is usually negative).
        
        val = compute_micro_bdm(seq, lookup)
        
        if val is not None:
            # Table value is log2(P).
            # If length 4 (2x2), we look up one block.
            # If length 8, we sum two blocks.
            # But wait, compute_micro_bdm returns -(val1+val2) or -val1?
            # In compute_micro_bdm for len 4, I returned lookup[matrix].
            # This is log2(P). Complexity is -log2(P).
            # So I should Negate it.
            
            # Let's fix compute_micro_bdm logic inside main loop or function.
            # Actually, let's fix the function to always return Complexity (positive bits).
            pass
            
    # Check for 1xN matrices
    count_1x4 = 0
    for k in lookup:
        if len(k) == 1 and len(k[0]) == 4:
            count_1x4 += 1
            
    print(f"Found {count_1x4} 1x4 matrices in table.")
    
    # Redefine logic for display
    # Length 4
    seq4 = [1, 0, 0, 0]
    
    # Try 1x4 lookup
    m4_1x4 = (tuple(seq4),)
    if m4_1x4 in lookup:
        k = lookup[m4_1x4] # It's already complexity
        print(f"Len 4 [1,0,0,0] (as 1x4): K = {k:.2f} bits")
    else:
        # Try 2x2 lookup
        m4_2x2 = (tuple(seq4[0:2]), tuple(seq4[2:4]))
        if m4_2x2 in lookup:
            k = lookup[m4_2x2]
            print(f"Len 4 [1,0,0,0] (as 2x2): K = {k:.2f} bits")
        else:
            print(f"Len 4 [1,0,0,0]: Not found")
            
    # Length 2
    seq2 = [1, 0]
    # Try 1x2
    m2_1x2 = (tuple(seq2),)
    if m2_1x2 in lookup:
        k = lookup[m2_1x2]
        print(f"Len 2 [1,0] (as 1x2): K = {k:.2f} bits")
    else:
        # Split into two 1x1
        m2_1 = ((seq2[0],),)
        m2_2 = ((seq2[1],),)
        if m2_1 in lookup and m2_2 in lookup:
            k = lookup[m2_1] + lookup[m2_2]
            print(f"Len 2 [1,0] (sum of 1x1): K = {k:.2f} bits")
        else:
            print(f"Len 2 [1,0]: Not found")
        
    # Length 8
    seq8 = [0, 1, 0, 1, 1, 0, 1, 0]
    
    # Try two 1x4
    m8_1x4_1 = (tuple(seq8[0:4]),)
    m8_1x4_2 = (tuple(seq8[4:8]),)
    
    if m8_1x4_1 in lookup and m8_1x4_2 in lookup:
        k = lookup[m8_1x4_1] + lookup[m8_1x4_2]
        print(f"Len 8 [0,1...] (sum of two 1x4): K = {k:.2f} bits")
    else:
        # Try two 2x2
        m8_2x2_1 = (tuple(seq8[0:2]), tuple(seq8[2:4]))
        m8_2x2_2 = (tuple(seq8[4:6]), tuple(seq8[6:8]))
        if m8_2x2_1 in lookup and m8_2x2_2 in lookup:
            k = lookup[m8_2x2_1] + lookup[m8_2x2_2]
            print(f"Len 8 [0,1...] (sum of two 2x2): K = {k:.2f} bits")
        else:
            print(f"Len 8 [0,1...]: Not found")

    # Length 10 Random Test
    # Example: 1010101010
    seq10 = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    print(f"\nLen 10 {seq10}:")
    
    # Strategy: Two 2x2 blocks (8 bits) + Two 1x1 blocks (2 bits)
    # Block 1: seq10[0:4] -> [[1,0],[1,0]]
    m10_1 = (tuple(seq10[0:2]), tuple(seq10[2:4]))
    # Block 2: seq10[4:8] -> [[1,0],[1,0]]
    m10_2 = (tuple(seq10[4:6]), tuple(seq10[6:8]))
    # Block 3: seq10[8] -> [[1]]
    m10_3 = ((seq10[8],),)
    # Block 4: seq10[9] -> [[0]]
    m10_4 = ((seq10[9],),)
    
    k_total = 0
    if m10_1 in lookup: k_total += lookup[m10_1]
    if m10_2 in lookup: k_total += lookup[m10_2]
    if m10_3 in lookup: k_total += lookup[m10_3]
    if m10_4 in lookup: k_total += lookup[m10_4]
    
    print(f"K = {k_total:.2f} bits (using 2x2 + 2x2 + 1x1 + 1x1)")
    
if __name__ == "__main__":
    main()
