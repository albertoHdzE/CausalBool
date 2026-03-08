import sys
import json
import numpy as np
import os
import math

# Add src/integration to path
current_dir = os.path.dirname(os.path.abspath(__file__))
integration_dir = os.path.join(os.path.dirname(current_dir), 'integration')
sys.path.append(integration_dir)

from BDM_Wrapper import BDMWrapper

def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_bdm_batch.py <input_json_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(json.dumps({"error": f"Failed to read input file: {str(e)}"}))
        sys.exit(1)

    wrapper = BDMWrapper(ndim=1)
    results = {}

    for key, matrix_list in data.items():
        try:
            # Check if matrix is empty
            if not matrix_list or len(matrix_list) == 0:
                results[key] = 0.0
                continue
                
            matrix = np.array(matrix_list)
            
            # Flatten to 1D array for behavioral complexity
            # This treats the attractor (cycle of states) as a single sequence
            matrix = matrix.flatten()
            
            # Handle small datasets by repetition (BDM requires min length)
            L = len(matrix)
            scale = 1.0
            if L < 12:
                reps = math.ceil(12 / L)
                matrix = np.tile(matrix, reps)
                scale = float(reps)
            
            # Compute BDM
            res = wrapper.compute_bdm(matrix)
            results[key] = res['bdm_value'] / scale
        except Exception as e:
            results[key] = None
            print(f"Error processing {key}: {e}", file=sys.stderr)

    print(json.dumps(results))

if __name__ == "__main__":
    main()
