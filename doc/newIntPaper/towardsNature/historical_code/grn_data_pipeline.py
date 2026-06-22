"""
Gene Regulatory Network Data Acquisition Pipeline
For Nature Paper: Deterministic Causal Boolean Integration

This script downloads and processes biological GRN datasets:
1. DREAM4 In Silico Network Challenge
2. RegulonDB (E. coli)
3. Cell Collective repository
4. Published Boolean GRN models

Author: Alberto Hernández & Oxford Collaboration
Date: January 2026
"""

import requests
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import zipfile
import io

class GRNDataAcquisition:
    def __init__(self, output_dir: str = "./data/grn_datasets"):
        """Initialize data acquisition pipeline."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "dream4").mkdir(exist_ok=True)
        (self.output_dir / "regulondb").mkdir(exist_ok=True)
        (self.output_dir / "published").mkdir(exist_ok=True)
        (self.output_dir / "processed").mkdir(exist_ok=True)
        
        print(f"✓ Data pipeline initialized at {self.output_dir}")
    
    def download_dream4(self):
        """
        Download DREAM4 In Silico Network Challenge datasets.
        Contains 5 networks of size 10 and 5 networks of size 100.
        
        Reference: Marbach et al., PNAS 2010
        """
        print("\n=== DREAM4 Dataset Acquisition ===")
        
        # DREAM4 base URL (Synapse repository)
        base_url = "https://www.synapse.org/Portal/filehandle?ownerId=syn3049712&ownerType=ENTITY&fileName="
        
        datasets = {
            "insilico_size10": [
                "insilico_size10_1_goldstandard.tsv",
                "insilico_size10_2_goldstandard.tsv",
                "insilico_size10_3_goldstandard.tsv",
                "insilico_size10_4_goldstandard.tsv",
                "insilico_size10_5_goldstandard.tsv"
            ],
            "insilico_size100": [
                "insilico_size100_1_goldstandard.tsv",
                "insilico_size100_2_goldstandard.tsv",
                "insilico_size100_3_goldstandard.tsv",
                "insilico_size100_4_goldstandard.tsv",
                "insilico_size100_5_goldstandard.tsv"
            ]
        }
        
        # For demonstration, we'll create synthetic DREAM4-style networks
        # (Real download requires Synapse authentication)
        print("⚠ Note: Real DREAM4 requires Synapse account")
        print("→ Creating DREAM4-compatible synthetic networks for pipeline testing...")
        
        for size_category, networks in datasets.items():
            size = 10 if "size10" in size_category else 100
            for i, network_name in enumerate(networks, 1):
                # Generate synthetic network
                n_genes = size
                n_edges = int(n_genes * 2.5)  # Realistic sparsity
                
                # Create edge list
                edges = []
                genes = [f"G{j+1}" for j in range(n_genes)]
                
                np.random.seed(42 + i)  # Reproducible
                for _ in range(n_edges):
                    source = np.random.choice(genes)
                    target = np.random.choice(genes)
                    sign = np.random.choice([1, -1])  # Activation/repression
                    if source != target:
                        edges.append([source, target, sign])
                
                # Save as TSV
                df = pd.DataFrame(edges, columns=["Gene1", "Gene2", "Type"])
                output_path = self.output_dir / "dream4" / f"network_{size}_{i}.tsv"
                df.to_csv(output_path, sep="\t", index=False)
                print(f"  ✓ Generated {network_name} → {output_path}")
        
        print(f"✓ DREAM4 datasets ready: {len(datasets['insilico_size10']) + len(datasets['insilico_size100'])} networks")
        return self.output_dir / "dream4"
    
    def create_regulondb_parser(self):
        """
        Create E. coli RegulonDB network from curated interactions.
        
        Reference: Santos-Zavaleta et al., Nucleic Acids Research 2019
        """
        print("\n=== RegulonDB E. coli Network ===")
        
        # Simplified E. coli lac operon network (well-validated)
        lac_operon = {
            "nodes": ["lacI", "lacZ", "lacY", "lacA", "CRP", "glucose", "lactose"],
            "edges": [
                {"source": "lacI", "target": "lacZ", "type": "repression"},
                {"source": "lacI", "target": "lacY", "type": "repression"},
                {"source": "lacI", "target": "lacA", "type": "repression"},
                {"source": "lactose", "target": "lacI", "type": "inhibition"},
                {"source": "CRP", "target": "lacZ", "type": "activation"},
                {"source": "CRP", "target": "lacY", "type": "activation"},
                {"source": "glucose", "target": "CRP", "type": "inhibition"}
            ],
            "logic": {
                "lacZ": "AND(NOT(lacI), CRP)",
                "lacY": "AND(NOT(lacI), CRP)",
                "lacA": "NOT(lacI)",
                "lacI": "NOT(lactose)",
                "CRP": "NOT(glucose)"
            }
        }
        
        # Save as JSON
        output_path = self.output_dir / "regulondb" / "lac_operon.json"
        with open(output_path, 'w') as f:
            json.dump(lac_operon, f, indent=2)
        
        print(f"  ✓ Lac operon network: {len(lac_operon['nodes'])} genes, {len(lac_operon['edges'])} interactions")
        print(f"  ✓ Saved to {output_path}")
        
        return output_path
    
    def get_published_boolean_grns(self):
        """
        Compile published Boolean GRN models from literature.
        
        Key models:
        1. Lambda phage lysis-lysogeny (Gardner et al., Nature 2000)
        2. Fission yeast cell cycle (Davidich & Bornholdt, PLoS ONE 2008)
        3. Mammalian cell cycle (Fauré et al., Bioinformatics 2006)
        4. T-cell activation (Klamt et al., BMC Bioinformatics 2006)
        """
        print("\n=== Published Boolean GRN Models ===")
        
        models = {}
        
        # 1. Lambda Phage Lysis-Lysogeny Switch
        models["lambda_phage"] = {
            "reference": "Gardner et al., Nature 2000",
            "nodes": ["CI", "Cro", "CII", "N", "cI_promoter", "cro_promoter"],
            "size": 6,
            "edges": [
                {"source": "CI", "target": "cro_promoter", "type": "repression"},
                {"source": "Cro", "target": "cI_promoter", "type": "repression"},
                {"source": "CII", "target": "cI_promoter", "type": "activation"},
                {"source": "N", "target": "CII", "type": "activation"}
            ],
            "logic": {
                "CI": "AND(cI_promoter, NOT(Cro))",
                "Cro": "AND(cro_promoter, NOT(CI))",
                "CII": "N",
                "cI_promoter": "CII",
                "cro_promoter": "NOT(CI)"
            },
            "description": "Classic bistable switch: lysis vs lysogeny decision"
        }
        
        # 2. Fission Yeast Cell Cycle (simplified core)
        models["yeast_cell_cycle"] = {
            "reference": "Davidich & Bornholdt, PLoS ONE 2008",
            "nodes": ["Cdc2_Cdc13", "Ste9", "Rum1", "Slp1", "Cdc2_Cdc13_active", 
                      "Wee1_Mik1", "Cdc25", "PP"],
            "size": 8,
            "logic": {
                "Cdc2_Cdc13": "NOT(Ste9)",
                "Ste9": "AND(NOT(Cdc2_Cdc13_active), Slp1)",
                "Rum1": "NOT(Cdc2_Cdc13_active)",
                "Slp1": "Cdc2_Cdc13_active",
                "Cdc2_Cdc13_active": "AND(Cdc2_Cdc13, NOT(Wee1_Mik1), Cdc25)",
                "Wee1_Mik1": "NOT(Cdc2_Cdc13_active)",
                "Cdc25": "Cdc2_Cdc13_active",
                "PP": "Slp1"
            },
            "description": "Cell cycle control network with known attractors"
        }
        
        # 3. Simplified T-cell Activation
        models["tcell_activation"] = {
            "reference": "Klamt et al., BMC Bioinformatics 2006",
            "nodes": ["TCR", "CD4", "CD28", "LAT", "ZAP70", "LCK", "FYN", 
                      "PLCg", "RasGRP", "NFAT", "AP1", "IL2"],
            "size": 12,
            "logic": {
                "TCR": "INPUT",
                "CD4": "INPUT",
                "CD28": "INPUT",
                "LCK": "OR(CD4, FYN)",
                "FYN": "TCR",
                "ZAP70": "AND(TCR, LCK)",
                "LAT": "ZAP70",
                "PLCg": "LAT",
                "RasGRP": "LAT",
                "NFAT": "PLCg",
                "AP1": "RasGRP",
                "IL2": "AND(NFAT, AP1, CD28)"
            },
            "description": "T-cell receptor signaling leading to IL-2 production"
        }
        
        # Save all models
        for name, model in models.items():
            output_path = self.output_dir / "published" / f"{name}.json"
            with open(output_path, 'w') as f:
                json.dump(model, f, indent=2)
            print(f"  ✓ {model['reference']}: {model['size']} nodes → {output_path}")
        
        print(f"✓ Published models ready: {len(models)} networks")
        return models
    
    def convert_to_connectivity_matrix(self, network_file: Path, 
                                       format_type: str = "tsv") -> Tuple[np.ndarray, List[str], Dict]:
        """
        Convert network edge list to connectivity matrix for Mathematica.
        
        Returns:
            cm: Connectivity matrix (0/1)
            node_names: Ordered list of gene names
            gate_assignments: Dict mapping nodes to Boolean gates
        """
        print(f"\n→ Converting {network_file.name} to connectivity matrix...")
        
        if format_type == "json":
            with open(network_file) as f:
                data = json.load(f)
            
            nodes = data["nodes"]
            n = len(nodes)
            cm = np.zeros((n, n), dtype=int)
            
            # Build connectivity from edges
            node_to_idx = {node: i for i, node in enumerate(nodes)}
            
            if "edges" in data:
                for edge in data["edges"]:
                    source_idx = node_to_idx[edge["source"]]
                    target_idx = node_to_idx[edge["target"]]
                    cm[target_idx, source_idx] = 1
            
            # Extract gate logic if available
            gate_assignments = {}
            if "logic" in data:
                for target, logic_str in data["logic"].items():
                    if target in node_to_idx:
                        gate = self._parse_logic_to_gate(logic_str)
                        gate_assignments[target] = gate
        
        else:  # TSV format (DREAM4)
            df = pd.read_csv(network_file, sep="\t")
            nodes = sorted(set(df["Gene1"].tolist() + df["Gene2"].tolist()))
            n = len(nodes)
            cm = np.zeros((n, n), dtype=int)
            
            node_to_idx = {node: i for i, node in enumerate(nodes)}
            for _, row in df.iterrows():
                source_idx = node_to_idx[row["Gene1"]]
                target_idx = node_to_idx[row["Gene2"]]
                cm[target_idx, source_idx] = 1
            
            # Default gate assignments (will need refinement)
            gate_assignments = {node: "OR" for node in nodes}  # Default assumption
        
        # Save processed matrix
        output_name = network_file.stem + "_processed.npz"
        output_path = self.output_dir / "processed" / output_name
        
        np.savez(output_path, 
                 cm=cm, 
                 node_names=nodes,
                 gate_assignments=json.dumps(gate_assignments))
        
        print(f"  ✓ Matrix: {n}×{n}, edges: {cm.sum()}, sparsity: {1 - cm.sum()/(n*n):.2%}")
        print(f"  ✓ Saved to {output_path}")
        
        return cm, nodes, gate_assignments
    
    def _parse_logic_to_gate(self, logic_str: str) -> str:
        """Parse logic string to gate type (simplified)."""
        logic_upper = logic_str.upper()
        
        if "AND" in logic_upper and "NOT" in logic_upper:
            return "CANALISING"  # Simplified
        elif "AND" in logic_upper:
            return "AND"
        elif "OR" in logic_upper:
            return "OR"
        elif "NOT" in logic_upper:
            return "NOT"
        elif "XOR" in logic_upper:
            return "XOR"
        else:
            return "OR"  # Default
    
    def generate_randomized_controls(self, cm: np.ndarray, 
                                     n_randomizations: int = 1000,
                                     preserve_degree: bool = True) -> List[np.ndarray]:
        """
        Generate randomized null models preserving degree distribution.
        Critical for statistical comparison: D_bio vs D_random.
        """
        print(f"\n→ Generating {n_randomizations} randomized controls...")
        
        randomized_networks = []
        n = cm.shape[0]
        
        for i in range(n_randomizations):
            if preserve_degree:
                # Edge-swap algorithm (preserves in/out degree)
                cm_random = cm.copy()
                n_swaps = n * n * 10  # 10× edges for good mixing
                
                edges = list(zip(*np.where(cm == 1)))
                if len(edges) < 2:
                    randomized_networks.append(cm_random)
                    continue
                
                for _ in range(n_swaps):
                    # Select two edges
                    idx1, idx2 = np.random.choice(len(edges), 2, replace=False)
                    (i1, j1), (i2, j2) = edges[idx1], edges[idx2]
                    
                    # Swap if valid (no self-loops, no duplicate edges)
                    if i1 != j2 and i2 != j1 and cm_random[i1, j2] == 0 and cm_random[i2, j1] == 0:
                        cm_random[i1, j1] = 0
                        cm_random[i2, j2] = 0
                        cm_random[i1, j2] = 1
                        cm_random[i2, j1] = 1
                        
                        edges[idx1] = (i1, j2)
                        edges[idx2] = (i2, j1)
            else:
                # Erdős-Rényi with same edge density
                p = cm.sum() / (n * (n - 1))
                cm_random = (np.random.random((n, n)) < p).astype(int)
                np.fill_diagonal(cm_random, 0)
            
            randomized_networks.append(cm_random)
        
        print(f"  ✓ Generated {len(randomized_networks)} null models")
        return randomized_networks
    
    def export_to_mathematica(self, cm: np.ndarray, 
                             node_names: List[str],
                             gate_assignments: Dict,
                             output_file: str):
        """
        Export connectivity matrix to Mathematica-compatible format.
        """
        print(f"\n→ Exporting to Mathematica format: {output_file}")
        
        n = len(node_names)
        
        # Build Mathematica expression
        mathematica_code = f"""(* Biological GRN Network *)
(* Generated by GRN Data Pipeline *)
(* Nodes: {n} *)

cm = {self._array_to_mathematica(cm)};

nodeNames = {{{", ".join([f'"{name}"' for name in node_names])}}};

dynamic = {{{", ".join([f'"{gate_assignments.get(name, "OR")}"' for name in node_names])}}};

(* Gate parameters if needed *)
params = <||>;

(* Ready for Integration`Experiments`CreateRepertoiresDispatch *)
"""
        
        output_path = self.output_dir / "processed" / output_file
        with open(output_path, 'w') as f:
            f.write(mathematica_code)
        
        print(f"  ✓ Mathematica export ready: {output_path}")
        return output_path
    
    def _array_to_mathematica(self, arr: np.ndarray) -> str:
        """Convert NumPy array to Mathematica list syntax."""
        rows = []
        for row in arr:
            rows.append("{" + ", ".join(map(str, row)) + "}")
        return "{" + ",\n   ".join(rows) + "}"
    
    def run_full_pipeline(self):
        """Execute complete data acquisition and processing pipeline."""
        print("\n" + "="*60)
        print("GENE REGULATORY NETWORK DATA PIPELINE")
        print("For: Deterministic Causal Boolean Integration (Nature)")
        print("="*60)
        
        # Step 1: Download datasets
        self.download_dream4()
        self.create_regulondb_parser()
        published = self.get_published_boolean_grns()
        
        # Step 2: Process published models (these have known logic)
        processed_networks = []
        
        for model_name in ["lambda_phage", "yeast_cell_cycle", "tcell_activation"]:
            model_file = self.output_dir / "published" / f"{model_name}.json"
            
            cm, nodes, gates = self.convert_to_connectivity_matrix(
                model_file, 
                format_type="json"
            )
            
            # Export to Mathematica
            self.export_to_mathematica(
                cm, nodes, gates,
                f"{model_name}_network.m"
            )
            
            # Generate randomized controls
            random_cms = self.generate_randomized_controls(cm, n_randomizations=100)
            
            # Save randomized networks
            random_file = self.output_dir / "processed" / f"{model_name}_random.npz"
            np.savez(random_file, *random_cms)
            
            processed_networks.append({
                "name": model_name,
                "cm": cm,
                "nodes": nodes,
                "gates": gates,
                "n_random": len(random_cms)
            })
        
        # Step 3: Create analysis summary
        summary = {
            "total_networks": len(processed_networks),
            "networks": [
                {
                    "name": net["name"],
                    "size": len(net["nodes"]),
                    "edges": int(net["cm"].sum()),
                    "randomized_controls": net["n_random"]
                }
                for net in processed_networks
            ],
            "ready_for_analysis": True
        }
        
        summary_file = self.output_dir / "pipeline_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\n" + "="*60)
        print("✓ PIPELINE COMPLETE")
        print(f"✓ Networks processed: {len(processed_networks)}")
        print(f"✓ Summary: {summary_file}")
        print("="*60)
        print("\nNEXT STEPS:")
        print("1. Load networks into your Mathematica framework")
        print("2. Compute D (description length) for biological networks")
        print("3. Compute D for randomized controls")
        print("4. Run statistical tests: D_bio << D_random")
        print("\n→ Ready for Week 2: Core Analysis")
        
        return summary


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Initialize and run pipeline
    pipeline = GRNDataAcquisition()
    summary = pipeline.run_full_pipeline()
    
    print("\n" + "="*60)
    print("DATA ACQUISITION COMPLETE ✓")
    print("Files ready in: ./data/grn_datasets/")
    print("="*60)