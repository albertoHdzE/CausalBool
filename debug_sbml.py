from integration.SBMLParser import SBMLParser
from pathlib import Path

parser = SBMLParser()
raw_dir = Path("data/bio/raw")
files = list(raw_dir.glob("biomodels_MODEL*.xml"))[:5]

for f in files:
    print(f"Testing {f.name}...")
    try:
        model = parser.parse_file(f)
        if model:
            print(f"  Success: {len(model['nodes'])} nodes")
        else:
            print(f"  Failed to parse (None returned)")
    except Exception as e:
        print(f"  Exception: {e}")
