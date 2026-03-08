import json
import os
import pandas as pd

def validate_gold_standard():
    print("Validating Gold Standard Networks...")
    
    # Load metadata
    metadata_path = "data/bio/curated/metadata.csv"
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found.")
        return
        
    df = pd.read_csv(metadata_path)
    print(f"Loaded {len(df)} entries from metadata.")
    
    # Processed data path
    processed_path = "data/bio/processed"
    
    valid_count = 0
    missing = []
    
    for index, row in df.iterrows():
        name = row['Model Name']
        filename = row['Filename']
        filepath = os.path.join(processed_path, filename)
        
        if not os.path.exists(filepath):
            print(f"MISSING: {name} ({filename})")
            missing.append(name)
            continue
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                nodes = len(data.get('nodes', []))
                print(f"OK: {name} (Nodes: {nodes})")
                valid_count += 1
        except Exception as e:
            print(f"ERROR: {name} - {str(e)}")
            
    print("-" * 30)
    print(f"Validation Complete: {valid_count}/{len(df)} networks verified.")
    if missing:
        print(f"Missing Files: {len(missing)}")

if __name__ == "__main__":
    validate_gold_standard()
