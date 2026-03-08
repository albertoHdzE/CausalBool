#!/usr/bin/env python3
"""
cli_dv2.py
----------
CLI Wrapper for Universal_D_v2_Encoder.
Intended to be called by Mathematica (BioBridge_v2.m) or other external tools.

Usage:
    python cli_dv2.py --matrix "[[0,1],[1,0]]"
    python cli_dv2.py --file matrix.csv

Output:
    JSON object with "dv2" and "block_details"
"""

import argparse
import json
import sys
import numpy as np
from pathlib import Path

# Add src to path to import integration
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

def parse_matrix_string(s):
    try:
        # Expecting standard JSON-like list of lists
        return json.loads(s)
    except json.JSONDecodeError:
        # Try Mathematica style {{0,1},{1,0}}
        s = s.replace("{", "[").replace("}", "]")
        return json.loads(s)

def main():
    parser = argparse.ArgumentParser(description="Calculate D_v2 for a matrix.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--matrix", type=str, help="Adjacency matrix as string (JSON or Mathematica style)")
    group.add_argument("--file", type=str, help="Path to CSV or JSON file containing matrix")
    
    args = parser.parse_args()
    
    matrix = None
    
    if args.matrix:
        matrix = parse_matrix_string(args.matrix)
    elif args.file:
        path = Path(args.file)
        if path.suffix == '.csv':
            matrix = np.loadtxt(path, delimiter=',').tolist()
        elif path.suffix == '.json':
            with open(path) as f:
                data = json.load(f)
                # Assume standard format or raw matrix
                if isinstance(data, list):
                    matrix = data
                elif "adj" in data:
                    matrix = data["adj"]
                else:
                    raise ValueError("Could not find matrix in JSON")
    
    if matrix is None:
        print(json.dumps({"error": "No matrix provided"}))
        sys.exit(1)
        
    encoder = UniversalDv2Encoder(matrix)
    result = encoder.compute()
    
    # Convert result to JSON-serializable (handle numpy types)
    def default(o):
        if isinstance(o, (np.int64, np.int32)): return int(o)
        if isinstance(o, (np.float64, np.float32)): return float(o)
        raise TypeError
        
    print(json.dumps(result, default=default))

if __name__ == "__main__":
    main()
