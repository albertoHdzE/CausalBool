import os
import json
import pandas as pd
import glob

def verify_and_link():
    # 1. Verify DATA-001
    processed_dir = "data/bio/processed"
    all_files = glob.glob(os.path.join(processed_dir, "*.json"))
    print(f"Total processed files found: {len(all_files)}")
    
    # 2. Link Metadata (DATA-002)
    metadata_path = "data/bio/curated/metadata.csv"
    df = pd.read_csv(metadata_path)
    
    # Mapping heuristics (Name in CSV -> likely part of filename)
    # I'll create a new column 'Filename'
    
    filename_map = {
        "EGFR Signaling": "egfr_signaling.json", # Heuristic or direct match if exists
        "p53-MDM2": "p53", # search for p53
        "Yeast Cell Cycle": "budding_yeast",
        "Mammalian Cell Cycle": "ginsim_2006-mammal-cell-cycle",
        "Lac Operon": "lac_operon", # might not exist, check
        "T-Cell Activation": "TCRsig40",
        "Drosophila Segment Polarity": "SP_1cell",
        "Apoptosis": "apoptosis",
        "MAPK Signaling": "MAPK_large",
        "Tumor Invasion": "tumor-invasion",
        "TLR5 Signaling": "TLR5",
        "Mammalian Cell Cycle 2016": "Traynard",
        "Bladder Tumorigenesis": "bladder-tumorigenesis",
        "Cell Cycle Control 2019": "CellCycleControl",
        "Gastric Cancer": "gastric-cancer",
        "Cell Fate Decision": "Cell_Fate",
        "Notch Pathway": "Notch__Pathway",
        "Fission Yeast Cycle": "fission-yeast",
        "Immune Checkpoints": "ImmuneCheckpoint",
        "T-LGL Leukemia": "T_LGL"
    }
    
    filenames = []
    found_count = 0
    
    for name in df['Model Name']:
        key = filename_map.get(name, name)
        match = None
        
        # Try exact match first
        if os.path.exists(os.path.join(processed_dir, key)):
            match = key
        else:
            # Search
            for f in all_files:
                fname = os.path.basename(f)
                if key.lower() in fname.lower():
                    match = fname
                    break
        
        if match:
            filenames.append(match)
            found_count += 1
        else:
            filenames.append("NOT_FOUND")
            print(f"Warning: Could not find file for {name}")

    df['Filename'] = filenames
    df.to_csv(metadata_path, index=False)
    print(f"Updated metadata.csv with {found_count}/{len(df)} filenames.")

if __name__ == "__main__":
    verify_and_link()
