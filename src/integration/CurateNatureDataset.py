
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path to import integration modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from integration.grn_data_pipeline import GRNLoader

class NatureDatasetCurator:
    """
    Curates the 'Tri-Phylum' dataset for the Nature protocol.
    Categories:
    1. Maintainers (Homeostasis): Cell Cycles, Metabolic operons.
    2. Deciders (Fate): Differentiation, Switches.
    3. Processors (Signaling): Immune response, Signal transduction.
    """
    
    def __init__(self):
        self.loader = GRNLoader()
        self.output_dir = self.loader.processed_dir
        self.categories = {
            "lac_operon": "Maintainer",
            "yeast_cell_cycle": "Maintainer",
            "lambda_phage": "Decider",
            "tcell_activation": "Processor",
            "mammalian_cell_cycle": "Maintainer",
            "drosophila_sp": "Decider",
            "th_differentiation": "Decider",
            "egfr_signaling": "Processor",
            "p53_mdm2": "Maintainer",
            "arabidopsis_cc": "Maintainer"
        }

    def run(self):
        print(">>> Starting Nature Dataset Curation...")
        
        # 1. Load existing base models
        models = self.loader.build_published_models()
        
        # 2. Add Extended Models (Real Data from Literature)
        self._add_mammalian_cell_cycle(models)
        self._add_drosophila_sp(models)
        self._add_th_differentiation(models)
        self._add_egfr_signaling(models)
        self._add_p53_mdm2(models)
        self._add_arabidopsis_cc(models)
        
        # 3. Process and Save
        for name, data in models.items():
            category = self.categories.get(name, "Unclassified")
            data["category"] = category
            
            # Remove non-serializable fields if present
            if "cm_array" in data:
                del data["cm_array"]
            
            # Save to processed directory
            output_path = self.output_dir / f"{name}.json"
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Processed {name} [{category}]: {len(data['nodes'])} nodes, {data.get('edges', 0)} edges")
            
        print(f"\n>>> Curation Complete. {len(models)} networks ready in {self.output_dir}")

    def _add_mammalian_cell_cycle(self, models: Dict[str, Any]):
        """Faure et al., Bioinformatics 2006"""
        nodes = ["CycD", "Rb", "E2F", "CycE", "CycA", "p27", "CycB", "Cdc20", "Cdh1", "UbcH10"]
        logic = {
            "CycD": "INPUT", 
            "Rb": "NOT(OR(CycD, CycE, CycB, CycA))",
            "E2F": "AND(NOT(Rb), NOT(CycA), NOT(CycB))",
            "CycE": "AND(E2F, NOT(Rb))",
            "CycA": "AND(E2F, NOT(Rb), NOT(Cdc20), NOT(Cdh1))", # Simplified
            "p27": "AND(NOT(CycD), NOT(CycE), NOT(CycA), NOT(CycB))",
            "CycB": "AND(NOT(Cdc20), NOT(Cdh1))",
            "Cdc20": "CycB",
            "Cdh1": "AND(NOT(CycA), NOT(CycB))",
            "UbcH10": "OR(Cdc20, CycA, CycB)"
        }
        models["mammalian_cell_cycle"] = self.loader._standardize_network(
            "mammalian_cell_cycle",
            {
                "nodes": nodes,
                "logic": logic,
                "reference": "Faure et al., 2006",
                "description": "Mammalian Cell Cycle Core",
                "source": "Literature"
            }
        )

    def _add_drosophila_sp(self, models: Dict[str, Any]):
        """Albert & Othmer, J Theor Biol 2003 (Simplified Segment Polarity)"""
        nodes = ["SLP", "wg", "Wg", "en", "En", "hh", "Hh", "ptc", "Ptc", "ci", "Ci", "CN", "CIA"]
        # Simplified intra-cellular logic for single cell context (ignoring neighbors for boolean simplicity)
        # Note: Real SP requires neighbor interactions. Here we model a single parasegment unit.
        logic = {
            "SLP": "INPUT",
            "wg": "AND(CIA, SLP, NOT(CN))", # Activated by Wingless pathway
            "Wg": "wg",
            "en": "NOT(SLP)",
            "En": "en",
            "hh": "En",
            "Hh": "hh",
            "ptc": "AND(NOT(En), NOT(CN))",
            "Ptc": "AND(ptc, NOT(Hh))",
            "ci": "NOT(En)",
            "Ci": "ci",
            "CN": "Ptc", # Repressor form of Ci
            "CIA": "NOT(Ptc)" # Activator form
        }
        models["drosophila_sp"] = self.loader._standardize_network(
            "drosophila_sp",
            {
                "nodes": nodes,
                "logic": logic,
                "reference": "Albert & Othmer, 2003",
                "description": "Drosophila Segment Polarity (Single Cell Projection)",
                "source": "Literature"
            }
        )

    def _add_th_differentiation(self, models: Dict[str, Any]):
        """Mendoza & Xenarios, Theor Biol Med Model 2006"""
        nodes = ["GATA3", "Tbet", "IL4", "IFNg", "STAT6", "STAT1", "SOCS1"]
        logic = {
            "GATA3": "AND(STAT6, NOT(Tbet))",
            "Tbet": "AND(STAT1, NOT(GATA3))",
            "IL4": "AND(GATA3, NOT(STAT1))",
            "IFNg": "AND(Tbet, NOT(STAT6))",
            "STAT6": "IL4",
            "STAT1": "IFNg",
            "SOCS1": "OR(Tbet, STAT1)"
        }
        models["th_differentiation"] = self.loader._standardize_network(
            "th_differentiation",
            {
                "nodes": nodes,
                "logic": logic,
                "reference": "Mendoza & Xenarios, 2006",
                "description": "Th1/Th2 Differentiation Switch",
                "source": "Literature"
            }
        )

    def _add_egfr_signaling(self, models: Dict[str, Any]):
        """Samaga et al., 2009 (Core Pathway)"""
        nodes = ["EGF", "EGFR", "GRB2", "SOS", "Ras", "Raf", "MEK", "ERK", "PI3K", "AKT"]
        logic = {
            "EGF": "INPUT",
            "EGFR": "EGF",
            "GRB2": "EGFR",
            "SOS": "AND(GRB2, NOT(ERK))", # Negative feedback
            "Ras": "SOS",
            "Raf": "AND(Ras, NOT(AKT))", # Cross-talk inhibition
            "MEK": "Raf",
            "ERK": "MEK",
            "PI3K": "EGFR",
            "AKT": "PI3K"
        }
        models["egfr_signaling"] = self.loader._standardize_network(
            "egfr_signaling",
            {
                "nodes": nodes,
                "logic": logic,
                "reference": "Samaga et al., 2009",
                "description": "EGFR/MAPK/PI3K Core Signaling",
                "source": "Literature"
            }
        )
        
    def _add_p53_mdm2(self, models: Dict[str, Any]):
        """Choi et al., 2012 (DNA Damage Response)"""
        nodes = ["DNA_Damage", "ATM", "p53", "Mdm2", "Wip1"]
        logic = {
            "DNA_Damage": "INPUT",
            "ATM": "AND(DNA_Damage, NOT(Wip1))",
            "p53": "AND(ATM, NOT(Mdm2))",
            "Mdm2": "AND(p53, NOT(ATM))", # ATM inhibits Mdm2
            "Wip1": "p53"
        }
        models["p53_mdm2"] = self.loader._standardize_network(
            "p53_mdm2",
            {
                "nodes": nodes,
                "logic": logic,
                "reference": "Choi et al., 2012",
                "description": "p53-Mdm2 Oscillator",
                "source": "Literature"
            }
        )

    def _add_arabidopsis_cc(self, models: Dict[str, Any]):
        """Menges et al., 2005 (Plant Cell Cycle)"""
        nodes = ["CycD3", "E2Fa", "RBR", "CycA", "CycB", "CDKB", "KRP"]
        logic = {
            "CycD3": "INPUT",
            "E2Fa": "AND(CycD3, NOT(RBR))",
            "RBR": "AND(NOT(CycD3), NOT(CycA), NOT(CycB))",
            "CycA": "E2Fa",
            "CycB": "AND(CycA, NOT(KRP))",
            "CDKB": "CycB",
            "KRP": "NOT(CDKB)"
        }
        models["arabidopsis_cc"] = self.loader._standardize_network(
            "arabidopsis_cc",
            {
                "nodes": nodes,
                "logic": logic,
                "reference": "Menges et al., 2005",
                "description": "Arabidopsis Cell Cycle Core",
                "source": "Literature"
            }
        )

if __name__ == "__main__":
    curator = NatureDatasetCurator()
    curator.run()
