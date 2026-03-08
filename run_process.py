import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from integration.BulkScraper import BulkScraper

s = BulkScraper()
s.process_raw_files()
