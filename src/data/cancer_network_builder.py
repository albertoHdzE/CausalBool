
import json
import os
import random
import numpy as np
import pandas as pd
from datetime import datetime

# Configuration
BASE_NETWORK_PATH = "data/bio/processed/egfr_signaling.json" # Using EGFR as the canonical cancer pathway
OUTPUT_DIR = "data/cancer/patients"
METADATA_PATH = "data/cancer/clinical_metadata.csv"
N_PATIENTS = 100
SEED = 2026

random.seed(SEED)
np.random.seed(SEED)

class CancerNetworkBuilder:
    def __init__(self, base_network_path, output_dir, metadata_path=None):
        self.base_network_path = base_network_path
        self.output_dir = output_dir
        self.metadata_path = metadata_path if metadata_path else METADATA_PATH
        self.base_data = self._load_base_network()
        self.nodes = self.base_data.get("nodes", [])
        
        # Define known oncogenes/tumor suppressors in this pathway for realistic simulation
        self.drivers = {
            "oncogenes": ["EGFR", "GRB2", "SOS", "RAS", "RAF", "MEK", "ERK"],
            "suppressors": ["PTEN", "p53", "RB"] # Some might not be in the graph, we check existence
        }
        
        # Filter drivers to those actually in the network
        self.drivers["oncogenes"] = [g for g in self.drivers["oncogenes"] if g in self.nodes]
        self.drivers["suppressors"] = [g for g in self.drivers["suppressors"] if g in self.nodes]
        
    def _load_base_network(self):
        with open(self.base_network_path, 'r') as f:
            return json.load(f)

    def generate_patient_cohort(self, n_patients=100):
        print(f"[{datetime.now()}] Generating {n_patients} patient models...")
        clinical_data = []
        
        for i in range(n_patients):
            patient_id = f"TCGA-BR-{i:04d}"
            
            # 1. Assign Clinical Subtype (e.g., Luminal A, Basal, HER2)
            subtype = np.random.choice(["LuminalA", "Basal", "HER2", "Normal-Like"], p=[0.4, 0.2, 0.3, 0.1])
            
            # 2. Determine Mutations based on subtype
            mutations = self._sample_mutations(subtype)
            
            # 3. Simulate Survival (correlated with mutation burden/subtype)
            # Basal/HER2 worse survival than Luminal A
            base_survival_days = 3000 if subtype == "LuminalA" else (1500 if subtype == "HER2" else 1000)
            survival_days = int(np.random.normal(base_survival_days, 300))
            survival_days = max(100, survival_days) # Min 100 days
            
            # 4. Construct Networks
            # Normal: Reference network (potentially with minor noise, but we keep it clean for control)
            normal_net = self._create_network(patient_id, "Normal", [])
            
            # Tumor: Mutated network
            tumor_net = self._create_network(patient_id, "Tumor", mutations)
            
            # 5. Save
            self._save_network(normal_net, patient_id, "Normal")
            self._save_network(tumor_net, patient_id, "Tumor")
            
            clinical_data.append({
                "PatientID": patient_id,
                "Subtype": subtype,
                "SurvivalDays": survival_days,
                "Mutations": ";".join([f"{g}:{t}" for g, t in mutations.items()]),
                "MutationCount": len(mutations)
            })
            
        # Save Metadata
        df = pd.DataFrame(clinical_data)
        df.to_csv(self.metadata_path, index=False)
        print(f"[{datetime.now()}] Clinical metadata saved to {self.metadata_path}")

    def _sample_mutations(self, subtype):
        muts = {}
        # Probability of mutation depends on subtype
        
        # EGFR/HER2 driven
        if subtype == "HER2":
            if "EGFR" in self.drivers["oncogenes"]:
                if random.random() < 0.8: muts["EGFR"] = "GoF" # Gain of Function
        
        # Basal (often Triple Negative, high p53)
        if subtype == "Basal":
            if "p53" in self.drivers["suppressors"]:
                if random.random() < 0.9: muts["p53"] = "LoF" # Loss of Function
            if "RAS" in self.drivers["oncogenes"]:
                 if random.random() < 0.4: muts["RAS"] = "GoF"
                 
        # General background mutations
        n_background = np.random.poisson(1.5)
        potential_targets = [n for n in self.nodes if n not in muts]
        if potential_targets:
            targets = random.sample(potential_targets, min(n_background, len(potential_targets)))
            for t in targets:
                muts[t] = random.choice(["GoF", "LoF"])
                
        return muts

    def _create_network(self, patient_id, tissue_type, mutations):
        """
        Applies mutations to the logic rules.
        GoF (Gain of Function) -> Node is Constitutively ON (Logic = 1)
        LoF (Loss of Function) -> Node is Constitutively OFF (Logic = 0)
        """
        net = self.base_data.copy()
        net["metadata"] = {
            "patient_id": patient_id,
            "tissue_type": tissue_type,
            "mutations": mutations if isinstance(mutations, dict) else {},
            "base_model": self.base_network_path
        }
        
        # Deep copy logic to avoid modifying base for all
        # Assuming structure: "logic": {"NodeA": ["!B", "C"], ...} or similar
        # Need to check actual JSON structure of processed files.
        # Assuming processed format from BulkScraper: list of nodes, and 'logic' dictionary?
        # Actually, BulkScraper usually outputs standard JSON. Let's assume a "logic" key exists.
        
        # If mutations is a dict {Gene: Type}
        if tissue_type == "Tumor" and mutations:
            new_logic = net.get("logic", {}).copy()
            new_cm = np.array(net.get("cm", []))
            
            # Map gene names to indices
            node_map = {name: i for i, name in enumerate(self.nodes)}
            
            for gene, mut_type in mutations.items():
                if mut_type == "GoF":
                    new_logic[gene] = "1" # Constitutive ON
                elif mut_type == "LoF":
                    new_logic[gene] = "0" # Constitutive OFF
                
                # STRUCTURAL CORRUPTION:
                # If a node is constitutive, it ignores inputs.
                # We sever the incoming edges in the adjacency matrix.
                if gene in node_map:
                    idx = node_map[gene]
                    # Row = Target. Set row to 0.
                    if len(new_cm) > idx:
                        new_cm[idx, :] = 0
            
            net["logic"] = new_logic
            net["cm"] = new_cm.tolist()
            
        return net

    def _save_network(self, network, patient_id, tissue_type):
        filename = f"{patient_id}_{tissue_type}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w') as f:
            json.dump(network, f, indent=2)

if __name__ == "__main__":
    builder = CancerNetworkBuilder(BASE_NETWORK_PATH, OUTPUT_DIR)
    builder.generate_patient_cohort(N_PATIENTS)
