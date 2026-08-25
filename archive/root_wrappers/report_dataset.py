
import json
from pathlib import Path
import sys

def report():
    processed_dir = Path("data/bio/processed")
    files = list(processed_dir.glob("*.json"))
    
    print(f"Total processed files: {len(files)}")
    
    sources = {}
    valid_count = 0
    
    for f in files:
        if f.name in ["gate_histogram.json", "truth_tables.json", "model_id.json"]:
            continue
            
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
                
            n = data.get("n", 0)
            name = data.get("name", f.stem)
            
            # Determine source
            if name.startswith("biomodels_") or name.startswith("MODEL"):
                source = "BioModels"
            elif name.startswith("ginsim_"):
                source = "GINsim"
            elif name.startswith("pyboolnet_"):
                source = "PyBoolNet"
            else:
                source = "Other"
                
            if source not in sources:
                sources[source] = {"count": 0, "valid_5_100": 0, "avg_n": 0}
            
            sources[source]["count"] += 1
            sources[source]["avg_n"] += n
            
            if 5 <= n <= 100:
                sources[source]["valid_5_100"] += 1
                valid_count += 1
                
        except Exception as e:
            print(f"Error reading {f}: {e}")

    print("\nDataset Breakdown:")
    print(f"{'Source':<15} | {'Total':<5} | {'Valid (5-100 nodes)':<20} | {'Avg Nodes':<10}")
    print("-" * 60)
    
    for source, stats in sources.items():
        avg = stats["avg_n"] / stats["count"] if stats["count"] > 0 else 0
        print(f"{source:<15} | {stats['count']:<5} | {stats['valid_5_100']:<20} | {avg:.1f}")
        
    print("-" * 60)
    print(f"Total Valid Models: {valid_count}")

if __name__ == "__main__":
    report()
