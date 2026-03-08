import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import requests

from integration.LogicParser import LogicParser


class GRNLoader:
    """Loader for biological gene regulatory networks (GRNs).

    Provides utilities to download or construct networks and export them
    in a standardized JSON format compatible with BioBridge/BioLink.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.base_dir = Path(base_dir)

        self.data_dir = self.base_dir / "data" / "bio"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.logic_parser = LogicParser()

    def _build_cm_from_edges(self, nodes: List[str], edges: List[Dict[str, Any]]) -> np.ndarray:
        n = len(nodes)
        cm = np.zeros((n, n), dtype=int)
        node_to_idx = {name: i for i, name in enumerate(nodes)}

        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            if source not in node_to_idx or target not in node_to_idx:
                continue
            s_idx = node_to_idx[source]
            t_idx = node_to_idx[target]
            if s_idx == t_idx:
                continue
            cm[t_idx, s_idx] = 1

        return cm

    def _standardize_network(self, name: str, definition: Dict[str, Any]) -> Dict[str, Any]:
        nodes = definition["nodes"]
        logic = definition.get("logic", {})
        edges = definition.get("edges")

        if not edges:
            edges = self._infer_edges_from_logic(nodes, logic)

        cm = self._build_cm_from_edges(nodes, edges)

        data: Dict[str, Any] = {
            "name": name,
            "nodes": nodes,
            "cm": cm.tolist(),
            "logic": logic,
            "reference": definition.get("reference"),
            "description": definition.get("description"),
            "source": definition.get("source", "published"),
        }
        
        if "essentiality" in definition:
            data["essentiality"] = definition["essentiality"]

        gates: Dict[str, Any] = {}
        gate_counter: Counter[str] = Counter()

        for i, node in enumerate(nodes):
            rule = logic.get(node)
            if not rule:
                continue

            if isinstance(rule, str) and rule.strip().upper() == "INPUT":
                gates[node] = {
                    "inputs": [],
                    "gate": "INPUT",
                    "parameters": {},
                }
                gate_counter.update(["INPUT"])
                continue

            regulators = [j for j in range(len(nodes)) if cm[i, j] == 1]
            input_names = [nodes[j] for j in regulators]

            if not input_names:
                gates[node] = {
                    "inputs": [],
                    "gate": "CUSTOM",
                    "parameters": {},
                }
                gate_counter.update(["CUSTOM"])
                continue

            try:
                info = self.logic_parser.parse_and_classify(rule, input_names)
                gate_label = info["gate"]
                params = info["parameters"]
            except Exception:
                gate_label = "CUSTOM"
                params = {}

            gates[node] = {
                "inputs": input_names,
                "gate": gate_label,
                "parameters": params,
            }
            gate_counter.update([gate_label])

        if gates:
            data["gates"] = gates
            data["gate_histogram"] = dict(gate_counter)

        data["n"] = len(nodes)
        data["n_edges"] = int(cm.sum())
        data["edges"] = edges # Keep the edge list
        data["out_degrees"] = np.sum(cm, axis=0).tolist()

        output_path = self.processed_dir / f"{name}.json"
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        data["path"] = str(output_path)
        data["cm_array"] = cm
        return data

    def _infer_edges_from_logic(self, nodes: List[str], logic: Dict[str, Any]) -> List[Dict[str, Any]]:
        node_set = set(nodes)
        gate_tokens = {
            "AND",
            "OR",
            "NOT",
            "XOR",
            "NAND",
            "NOR",
            "XNOR",
            "IMPLIES",
            "NIMPLIES",
            "KOFN",
            "CANALISING",
            "INPUT",
        }

        edges: List[Dict[str, Any]] = []

        for target in nodes:
            rule = logic.get(target)
            if not isinstance(rule, str):
                continue

            tokens = [
                tok
                for tok in re.findall(r"[A-Za-z0-9_]+", rule)
                if tok in node_set and tok not in gate_tokens and tok != target
            ]

            for src in tokens:
                edges.append({"source": src, "target": target, "type": "regulation"})

        return edges

    def build_published_models(self) -> Dict[str, Dict[str, Any]]:
        """Create standardized JSON for curated published GRN models.

        Currently includes Lambda phage, lac operon, yeast cell cycle (core),
        and T-cell activation.
        """
        models: Dict[str, Dict[str, Any]] = {}

        lambda_def = {
            "reference": "Gardner et al., Nature 2000",
            "description": "Lambda phage lysis-lysogeny genetic switch",
            "source": "CellCollective/Literature",
            "nodes": ["CI", "Cro", "CII", "N"],
            "edges": [
                {"source": "Cro", "target": "CI", "type": "repression"},
                {"source": "CI", "target": "Cro", "type": "repression"},
                {"source": "N", "target": "CII", "type": "activation"},
                {"source": "CII", "target": "CI", "type": "activation"},
            ],
            "logic": {
                "CI": "AND(CII, NOT(Cro))",
                "Cro": "NOT(CI)",
                "CII": "N",
                "N": "INPUT",
            },
            "essentiality": {
                "CI": 1, "Cro": 1, "CII": 0, "N": 0
            }
        }

        lambda_std = self._standardize_network("lambda_phage", lambda_def)
        models["lambda_phage"] = lambda_std

        lac_def = {
            "reference": "Santos-Zavaleta et al., Nucleic Acids Research 2019",
            "description": "E. coli lac operon regulatory module",
            "source": "RegulonDB/Literature",
            "nodes": ["lacI", "lacZ", "lacY", "lacA", "CRP", "glucose", "lactose"],
            "edges": [
                {"source": "lacI", "target": "lacZ", "type": "repression"},
                {"source": "lacI", "target": "lacY", "type": "repression"},
                {"source": "lacI", "target": "lacA", "type": "repression"},
                {"source": "lactose", "target": "lacI", "type": "inhibition"},
                {"source": "CRP", "target": "lacZ", "type": "activation"},
                {"source": "CRP", "target": "lacY", "type": "activation"},
                {"source": "glucose", "target": "CRP", "type": "inhibition"},
            ],
            "logic": {
                "lacZ": "AND(NOT(lacI), CRP)",
                "lacY": "AND(NOT(lacI), CRP)",
                "lacA": "NOT(lacI)",
                "lacI": "NOT(lactose)",
                "CRP": "NOT(glucose)",
            },
            "essentiality": {
                "lacI": 1, "lacZ": 1, "lacY": 1, "lacA": 0, "CRP": 1, "glucose": 0, "lactose": 0
            }
        }

        lac_std = self._standardize_network("lac_operon", lac_def)
        models["lac_operon"] = lac_std

        yeast_def = {
            "reference": "Davidich & Bornholdt, PLoS ONE 2008",
            "description": "Fission yeast cell cycle control network (core)",
            "source": "Literature",
            "nodes": [
                "Cdc2_Cdc13",
                "Ste9",
                "Rum1",
                "Slp1",
                "Cdc2_Cdc13_active",
                "Wee1_Mik1",
                "Cdc25",
                "PP",
            ],
            "logic": {
                "Cdc2_Cdc13": "NOT(Ste9)",
                "Ste9": "AND(NOT(Cdc2_Cdc13_active), Slp1)",
                "Rum1": "NOT(Cdc2_Cdc13_active)",
                "Slp1": "Cdc2_Cdc13_active",
                "Cdc2_Cdc13_active": "AND(Cdc2_Cdc13, NOT(Wee1_Mik1), Cdc25)",
                "Wee1_Mik1": "NOT(Cdc2_Cdc13_active)",
                "Cdc25": "Cdc2_Cdc13_active",
                "PP": "Slp1",
            },
            "essentiality": {
                "Cdc2_Cdc13": 1, "Ste9": 0, "Rum1": 0, "Slp1": 1, "Cdc2_Cdc13_active": 1, "Wee1_Mik1": 0, "Cdc25": 1, "PP": 1
            }
        }

        yeast_std = self._standardize_network("yeast_cell_cycle", yeast_def)
        models["yeast_cell_cycle"] = yeast_std

        tcell_def = {
            "reference": "Klamt et al., BMC Bioinformatics 2006",
            "description": "Simplified T-cell receptor signalling leading to IL-2 production",
            "source": "CellCollective/Literature",
            "nodes": [
                "TCR",
                "CD4",
                "CD28",
                "LAT",
                "ZAP70",
                "LCK",
                "FYN",
                "PLCg",
                "RasGRP",
                "NFAT",
                "AP1",
                "IL2",
            ],
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
                "IL2": "AND(NFAT, AP1, CD28)",
            },
            "essentiality": {
                "TCR": 1, "CD4": 0, "CD28": 1, "LAT": 1, "ZAP70": 1, "LCK": 1, "FYN": 0, "PLCg": 1, "RasGRP": 1, "NFAT": 1, "AP1": 1, "IL2": 1
            }
        }

        tcell_std = self._standardize_network("tcell_activation", tcell_def)
        models["tcell_activation"] = tcell_std

        return models

    def gate_histograms(self, models: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
        if models is None:
            models = self.build_published_models()

        per_network: Dict[str, Dict[str, int]] = {}
        global_counter: Counter[str] = Counter()

        for name, net in models.items():
            hist = net.get("gate_histogram")
            if not hist:
                continue
            per_network[name] = hist
            global_counter.update(hist)

        summary: Dict[str, Any] = {
            "per_network": per_network,
            "global": dict(global_counter),
        }

        output_path = self.processed_dir / "gate_histogram.json"
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        summary["path"] = str(output_path)
        return summary

    def export_essentiality_validation_data(self, models: Dict[str, Dict[str, Any]]) -> str:
        """Export essentiality data from models to CSV for validation."""
        validation_dir = self.data_dir / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)
        output_path = validation_dir / "essentiality_data.csv"
        
        with open(output_path, "w") as f:
            f.write("Gene,Network,Essentiality,Source\n")
            for name, net in models.items():
                essentiality = net.get("essentiality")
                if not essentiality:
                    continue
                
                source = "Literature/Manual"
                for gene, value in essentiality.items():
                    f.write(f"{gene},{name},{value},{source}\n")
        
        return str(output_path)

    def download_cell_collective_model(self, model_id: str) -> Dict[str, Any]:
        """Download a Cell Collective model via JSON API.

        This function follows the protocol sketch in protocol.md.
        For authenticated models, additional handling will be required.
        """
        base_url = "https://cellcollective.org/api/model"
        url = f"{base_url}/{model_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        output_path = self.raw_dir / f"cellcollective_{model_id}.json"
        with open(output_path, "w") as f:
            json.dump(data, f)

        return {"path": str(output_path), "raw": data}

    def process_raw_directory(self) -> None:
        """Process all raw data files (SBML, XML) into standardized format."""
        if not self.raw_dir.exists():
            print(f"Raw directory {self.raw_dir} does not exist.")
            return

        try:
            from integration.SBMLParser import SBMLParser
        except ImportError:
            # Fallback for direct execution
            from SBMLParser import SBMLParser

        sbml_parser = SBMLParser()
        processed_count = 0

        print(f"Scanning {self.raw_dir} for raw models...")
        
        # 1. Process SBML/XML files (BioModels, GINsim)
        # Look for both .xml and .sbml files
        raw_files = list(self.raw_dir.glob("*.xml")) + list(self.raw_dir.glob("*.sbml"))
        
        for file_path in raw_files:
                
            # Skip if already processed? No, overwrite is better for updates.
            
            try:
                model_def = sbml_parser.parse_file(file_path)
                if not model_def:
                    continue
                    
                # Filter: 5 <= Nodes <= 100
                n_nodes = len(model_def["nodes"])
                if not (5 <= n_nodes <= 100):
                    # print(f"  Skipping {file_path.name}: {n_nodes} nodes (outside 5-100 range)")
                    continue
                
                # TODO: Connected Component check
                
                self._standardize_network(model_def["name"], model_def)
                processed_count += 1
                
            except Exception as e:
                print(f"  Failed to process {file_path.name}: {e}")
                
        print(f"Processed {processed_count} models from raw directory.")


if __name__ == "__main__":
    loader = GRNLoader()
    
    # 1. Process raw files downloaded by BulkScraper
    loader.process_raw_directory()
    
    # 2. Build manually curated published models
    models = loader.build_published_models()
    print("Published models:")
    for name, info in models.items():
        print(f"  {name}: {info['n']} nodes, {info['edges']} edges → {info['path']}")

    summary = loader.gate_histograms(models)
    print("Gate histogram (global):", summary.get("global", {}))

    csv_path = loader.export_essentiality_validation_data(models)
    print(f"Exported essentiality data to: {csv_path}")
