import requests
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src to path to import integration modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from integration.grn_data_pipeline import GRNLoader
from integration.SBMLParser import SBMLParser
from integration.BNetParser import BNetParser
from integration.GINMLParser import GINMLParser
from integration.grn_data_pipeline import GRNLoader
import networkx as nx
import json

class BulkScraper:
    def __init__(self, base_dir=None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.base_dir = Path(base_dir)
            
        self.raw_dir = self.base_dir / "data" / "bio" / "raw"
        self.processed_dir = self.base_dir / "data" / "bio" / "processed"
        
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.sbml_parser = SBMLParser()
        self.bnet_parser = BNetParser()
        self.ginml_parser = GINMLParser()
        self.loader = GRNLoader(base_dir=str(self.base_dir))

    def process_raw_files(self):
        """
        Process downloaded raw XML/SBML/BNet/GINML files, filter, and save to processed directory.
        """
        print("Processing raw files...")
        processed_count = 0
        
        files = list(self.raw_dir.glob("*.xml")) + list(self.raw_dir.glob("*.sbml")) + list(self.raw_dir.glob("*.bnet")) + list(self.raw_dir.glob("*.ginml"))
        
        for file_path in files:
            try:
                # Parse depending on extension
                if file_path.suffix == ".bnet":
                    model_data = self.bnet_parser.parse_file(file_path)
                elif file_path.suffix == ".ginml":
                    model_data = self.ginml_parser.parse_file(file_path)
                else:
                    model_data = self.sbml_parser.parse_file(file_path)
                    
                if not model_data:
                    continue
                
                # Filter by Node Count (5 <= N <= 100)
                n_nodes = len(model_data["nodes"])
                if not (5 <= n_nodes <= 100):
                    # print(f"Skipping {model_data['name']}: {n_nodes} nodes (outside 5-100 range).")
                    continue
                
                # Standardize
                std_model = self.loader._standardize_network(model_data["name"], model_data)
                
                # Check connectivity (Connected Component > 80%)
                if std_model["nodes"] and std_model["cm"]:
                    # Build graph from cm or edges
                    G = nx.DiGraph()
                    G.add_nodes_from(std_model["nodes"])
                    
                    # Edges
                    # cm is adjacency matrix (target, source)
                    cm = std_model["cm"]
                    nodes = std_model["nodes"]
                    for i, target in enumerate(nodes):
                        for j, source in enumerate(nodes):
                            if cm[i][j] == 1:
                                G.add_edge(source, target)
                                
                    # Use weakly connected components
                    if len(G) > 0:
                        largest_cc = max(nx.weakly_connected_components(G), key=len)
                        cc_ratio = len(largest_cc) / len(G)
                        
                        if cc_ratio <= 0.8:
                            print(f"Skipping {model_data['name']}: CC ratio {cc_ratio:.2f} (<= 0.8)")
                            # Remove the file created by GRNLoader
                            if "path" in std_model and Path(std_model["path"]).exists():
                                try:
                                    Path(std_model["path"]).unlink()
                                except Exception as del_err:
                                    print(f"Failed to delete {std_model['path']}: {del_err}")
                            continue
                
                # File is already saved by GRNLoader._standardize_network
                # print(f"Processed {model_data['name']}: {n_nodes} nodes.")
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                
        print(f"Processing complete. {processed_count} models saved to {self.processed_dir}")

    def scrape_biomodels(self, max_models: int = 500):
        """
        Scrape Boolean models from BioModels database (SBML-qual format).
        Uses multiple queries to maximize coverage.
        """
        print(f"Starting BioModels scrape (target: {max_models} models)...")
        
        queries = [
            '(modellingapproach:"Boolean model" OR modellingapproach:"logical model") AND modelformat:"SBML"',
            'Boolean AND modelformat:"SBML"',
            'Logical AND modelformat:"SBML"',
            'Qualitative AND modelformat:"SBML"',
            '"Cell Collective" AND modelformat:"SBML"'
        ]
        
        seen_ids = set()
        count = 0
        
        for query in queries:
            if count >= max_models:
                break
                
            print(f"Searching with query: {query}")
            search_url = f"https://www.ebi.ac.uk/biomodels/search?query={query}&format=json&numResults={max_models}"
            
            try:
                response = requests.get(search_url, headers={"Accept": "application/json"})
                response.raise_for_status()
                search_results = response.json()
            except Exception as e:
                print(f"Error searching BioModels: {e}")
                continue

            models_found = search_results.get("models", [])
            if not models_found and "matches" in search_results and isinstance(search_results["matches"], list):
                 models_found = search_results["matches"]
                 
            print(f"Found {len(models_found)} potential models.")
            
            for model_info in models_found:
                if count >= max_models:
                    break
                    
                model_id = model_info.get("id")
                if not model_id or model_id in seen_ids:
                    continue
                    
                seen_ids.add(model_id)
                
                # ... download logic ...
                download_url = f"https://www.ebi.ac.uk/biomodels/model/download/{model_id}"
                
                try:
                    # Check if file exists to save time
                    output_filename = f"biomodels_{model_id}.xml"
                    output_path = self.raw_dir / output_filename
                    if output_path.exists():
                        # print(f"Skipping {model_id} (already exists)")
                        # count += 1 # Count existing ones towards limit? 
                        # Maybe we want new ones. Let's not count existing ones if we want to reach target of *new* downloads?
                        # But max_models usually implies total dataset size.
                        # Let's count it but check content.
                        # Actually, better to skip download but count it.
                        seen_ids.add(model_id)
                        # count += 1 
                        continue

                    print(f"Downloading {model_id}...")
                    file_resp = requests.get(download_url)
                    file_resp.raise_for_status()
                    
                    content = file_resp.content
                    is_zip = content.startswith(b'PK')
                    
                    if is_zip:
                        try:
                            with zipfile.ZipFile(io.BytesIO(content)) as z:
                                # Find the main SBML file
                                # Exclude manifest.xml and metadata
                                candidates = [n for n in z.namelist() if (n.endswith('.xml') or n.endswith('.sbml')) and 'manifest.xml' not in n and 'metadata' not in n]
                                
                                if candidates:
                                    # Prioritize .sbml extension
                                    sbml_cands = [n for n in candidates if n.endswith('.sbml')]
                                    if sbml_cands:
                                        target_file = sbml_cands[0]
                                    else:
                                        target_file = candidates[0]
                                    
                                    final_content = z.read(target_file)
                                else:
                                    print(f"Skipping {model_id}: No SBML file found in zip (candidates: {z.namelist()}).")
                                    continue
                        except Exception as e:
                            print(f"Error processing zip for {model_id}: {e}")
                            continue
                    else:
                        final_content = content

                    # Save
                    with open(output_path, "wb") as f:
                        f.write(final_content)
                        
                    print(f"Saved to {output_path}")
                    count += 1
                    time.sleep(0.5) 
                    
                except Exception as e:
                    print(f"Failed to download {model_id}: {e}")


        print(f"BioModels scrape complete. Downloaded {count} models.")

    def scrape_cell_collective(self, max_models: int = 80):
        """
        Scrape models from Cell Collective.
        Note: The API endpoint /api/model/{id} seems to be deprecated or requires auth.
        We will attempt to identify a working endpoint or list.
        For now, this is a placeholder/experimental implementation.
        """
        print("Starting Cell Collective scrape...")
        # TODO: Implement working Cell Collective scraper
        # Potentially need to scrape the public models list HTML page if API is hidden
        print("Cell Collective scraping not yet fully implemented due to API access issues.")

    def scrape_ginsim(self, max_models: int = 40):
        """
        Scrape models from GINsim repository (GitHub).
        Target: https://github.com/GINsim/GINsim.github.io/tree/master/docs/models
        """
        print(f"Starting GINsim scrape (target: {max_models} models)...")
        api_url = "https://api.github.com/repos/GINsim/GINsim.github.io/contents/docs/models"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            contents = response.json()
        except Exception as e:
            print(f"Error accessing GINsim repo: {e}")
            return

        model_dirs = [item for item in contents if item["type"] == "dir"]
        print(f"Found {len(model_dirs)} model directories in GINsim repo.")
        
        count = 0
        for item in model_dirs:
            if count >= max_models:
                break
                
            model_name = item["name"]
            model_url = item["url"] # API url for the dir
            
            try:
                # Get directory contents
                dir_resp = requests.get(model_url)
                dir_resp.raise_for_status()
                dir_contents = dir_resp.json()
                
                # Find SBML file
                sbml_file = None
                for file_item in dir_contents:
                    if file_item["name"].endswith(".sbml") or file_item["name"].endswith(".xml"):
                         # Avoid potential non-SBML xmls if possible, but GINsim usually puts model.sbml
                         sbml_file = file_item
                         break
                
                if sbml_file:
                    download_url = sbml_file["download_url"]
                    print(f"Downloading {model_name} from {download_url}...")
                    
                    file_resp = requests.get(download_url)
                    file_resp.raise_for_status()
                    
                    output_filename = f"ginsim_{model_name}.sbml"
                    output_path = self.raw_dir / output_filename
                    
                    with open(output_path, "wb") as f:
                        f.write(file_resp.content)
                        
                    print(f"Saved to {output_path}")
                    count += 1
                    time.sleep(0.2)
                else:
                    print(f"No SBML file found for {model_name}, skipping.")
                    
            except Exception as e:
                print(f"Error processing {model_name}: {e}")
                
        print(f"GINsim scrape complete. Downloaded {count} models.")

    def scrape_ginsim_git(self, max_models: int = 200):
        """
        Scrape models from GINsim repository using git clone to bypass API rate limits.
        """
        print("Starting GINsim scrape via git clone...")
        import subprocess
        import shutil
        import tempfile
        
        repo_url = "https://github.com/GINsim/GINsim.github.io.git"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Cloning {repo_url} to {temp_path}...")
            
            try:
                # Clone with depth 1 for speed
                subprocess.run(["git", "clone", "--depth", "1", repo_url, str(temp_path)], check=True)
                
                # Recursively find SBML files in the whole repo
                print(f"Scanning {temp_path} for SBML/GINML files...")
                count = 0
                found_files = list(temp_path.rglob("*.sbml")) + list(temp_path.rglob("*.xml")) + list(temp_path.rglob("*.zginml"))
                
                for file_path in found_files:
                    if count >= max_models:
                        break
                        
                    # Use parent dir name as model name
                    parent_name = file_path.parent.name
                    file_stem = file_path.stem
                    
                    if parent_name.lower() in ["models", "files", "model", "file"]:
                        # Try grandparent
                        grandparent = file_path.parent.parent.name
                        if grandparent and grandparent.lower() not in [".", "root"] and not grandparent.endswith(".github.io"):
                             model_name = f"{grandparent}_{file_stem}"
                        else:
                             model_name = file_stem
                    elif file_stem.lower() == parent_name.lower():
                        model_name = parent_name
                    else:
                        model_name = f"{parent_name}_{file_stem}"
                        
                    output_filename = f"ginsim_{model_name}.sbml"
                    
                    if file_path.suffix == ".zginml":
                         # Unzip zginml
                         try:
                             import zipfile
                             with zipfile.ZipFile(file_path, 'r') as z:
                                 # Find .ginml inside (usually regulatoryGraph.ginml or similar)
                                 ginml_files = [f for f in z.namelist() if f.endswith(".ginml")]
                                 if ginml_files:
                                     # Prefer 'regulatoryGraph.ginml'
                                     target_ginml = next((f for f in ginml_files if "regulatoryGraph" in f), ginml_files[0])
                                     
                                     # Change extension to .ginml
                                     output_filename = f"ginsim_{model_name}.ginml"
                                     output_path = self.raw_dir / output_filename
                                     
                                     with z.open(target_ginml) as zf, open(output_path, 'wb') as f_out:
                                         shutil.copyfileobj(zf, f_out)
                                     print(f"Saved {output_filename} (from zginml)")
                                     count += 1
                                 else:
                                     # Fallback to finding XML if no GINML?
                                     xml_files = [f for f in z.namelist() if f.endswith(".xml")]
                                     if xml_files:
                                         target_xml = xml_files[0]
                                         output_filename = f"ginsim_{model_name}.xml" # Save as xml
                                         output_path = self.raw_dir / output_filename
                                         with z.open(target_xml) as zf, open(output_path, 'wb') as f_out:
                                             shutil.copyfileobj(zf, f_out)
                                         print(f"Saved {output_filename} (from zginml XML)")
                                         count += 1
                                     else:
                                         print(f"Skipping {file_path.name}: No GINML/XML in zginml")
                         except Exception as e:
                             print(f"Error extracting {file_path.name}: {e}")
                    else:
                        # For SBML/XML files
                        output_path = self.raw_dir / output_filename
                        shutil.copy2(file_path, output_path)
                        print(f"Saved {output_filename}")
                        count += 1
                    
                print(f"GINsim git scrape complete. Saved {count} models.")
                
            except subprocess.CalledProcessError as e:
                print(f"Git clone failed: {e}")
            except Exception as e:
                print(f"Error during GINsim git scrape: {e}")

    def scrape_pyboolnet_git(self, max_models: int = 500):
        """
        Scrape models from PyBoolNet repository using git clone.
        Repo: https://github.com/hklarner/PyBoolNet.git
        """
        print("Starting PyBoolNet scrape via git clone...")
        import subprocess
        import shutil
        import tempfile
        import re
        
        repo_url = "https://github.com/hklarner/PyBoolNet.git"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Cloning {repo_url} to {temp_path}...")
            
            try:
                # Clone
                subprocess.run(["git", "clone", repo_url, str(temp_path)], check=True)
                
                # Recursively find BNet files
                print(f"Scanning {temp_path} for .bnet files...")
                count = 0
                found_files = list(temp_path.rglob("*.bnet"))
                
                for bnet_path in found_files:
                    if count >= max_models:
                        break
                        
                    model_name = bnet_path.stem.lower()
                    
                    # Filter synthetic/random models
                    if "random" in model_name or "test" in model_name or "toy" in model_name:
                         continue
                    # Filter nXkY format (random nets) e.g. n10k2, n5s3
                    if re.match(r"n\d+[ks]\d+", model_name):
                         continue

                    # Use original casing for filename
                    model_name_orig = bnet_path.stem
                    output_filename = f"pyboolnet_{model_name_orig}.bnet"
                    output_path = self.raw_dir / output_filename
                    
                    shutil.copy2(bnet_path, output_path)
                    print(f"Saved {output_filename}")
                    count += 1
                    
                print(f"PyBoolNet git scrape complete. Saved {count} models.")
                
            except subprocess.CalledProcessError as e:
                print(f"Git clone failed: {e}")
            except Exception as e:
                print(f"Error during PyBoolNet git scrape: {e}")

if __name__ == "__main__":
    scraper = BulkScraper()
    
    # Scrape BioModels (Increased limit)
    scraper.scrape_biomodels(max_models=200)
    
    # Scrape GINsim via Git
    scraper.scrape_ginsim_git(max_models=100)
    
    # Process all
    scraper.process_raw_files()
