import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))

from integration.BulkScraper import BulkScraper

def main():
    scraper = BulkScraper()
    # Scrape BioModels with expanded queries (High limit to find valid ones)
    scraper.scrape_biomodels(max_models=2000)
    
    # Run GINsim scrape (git clone) - retrieves pre-converted SBMLs
    scraper.scrape_ginsim_git(max_models=500)
    
    # Scrape PyBoolNet (git clone)
    scraper.scrape_pyboolnet_git(max_models=1000)
    
    # Process raw files
    scraper.process_raw_files()

if __name__ == "__main__":
    main()
