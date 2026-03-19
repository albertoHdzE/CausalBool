
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
        
    @staticmethod
    def default_node_to_genes_for_nodes(nodes: list[str]) -> dict[str, list[str]]:
        node_set = set(nodes)
        if {"EGF", "EGFR", "GRB2", "SOS", "Ras", "Raf", "MEK", "ERK", "PI3K", "AKT"}.issubset(node_set):
            return {
                "EGF": ["EGF"],
                "EGFR": ["EGFR"],
                "GRB2": ["GRB2"],
                "SOS": ["SOS1", "SOS2"],
                "Ras": ["KRAS", "NRAS", "HRAS"],
                "Raf": ["BRAF", "RAF1"],
                "MEK": ["MAP2K1", "MAP2K2"],
                "ERK": ["MAPK1", "MAPK3"],
                "PI3K": ["PIK3CA", "PIK3CB", "PIK3CD"],
                "AKT": ["AKT1", "AKT2", "AKT3"],
            }

        if {"RTK", "RAS", "PI3K", "MAPK", "AKT", "FOXO3"}.issubset(node_set):
            return {
                "GFs": ["EGF", "TGFA", "IGF1"],
                "RTK": ["EGFR", "ERBB2", "ERBB3"],
                "RAS": ["KRAS", "NRAS", "HRAS"],
                "PI3K": ["PIK3CA", "PIK3CB", "PIK3CD"],
                "PIP3": [],
                "AKT": ["AKT1", "AKT2", "AKT3"],
                "FOXO3": ["FOXO3"],
                "MAPK": ["MAPK1", "MAPK3"],
                "cycE": ["CCNE1", "CCNE2"],
                "TSC": ["TSC1", "TSC2"],
                "PRAS40": ["AKT1S1"],
                "Rb": ["RB1"],
                "mTORC1": ["MTOR", "RPTOR"],
                "E2F": ["E2F1", "E2F2", "E2F3"],
                "EIF4F": ["EIF4E", "EIF4G1", "EIF4A1"],
                "S6K": ["RPS6KB1", "RPS6KB2"],
                "Proliferation": [],
            }

        return {}

    def _load_base_network(self):
        with open(self.base_network_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def _read_counts_matrix(path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        if "gene_name" not in df.columns:
            raise ValueError(f"counts matrix missing gene_name column: {path}")
        df = df.set_index("gene_name")
        df.index = df.index.astype(str)
        return df

    @staticmethod
    def _safe_log2_counts(x: pd.Series) -> pd.Series:
        x = pd.to_numeric(x, errors="coerce").fillna(0.0)
        x = x.clip(lower=0.0)
        return np.log2(x + 1.0)

    @staticmethod
    def _hgnc_gene_expr(log_df: pd.DataFrame, gene: str) -> pd.Series:
        if gene not in log_df.index:
            return pd.Series([np.nan] * log_df.shape[1], index=log_df.columns, dtype=float)
        return pd.to_numeric(log_df.loc[gene], errors="coerce")

    @staticmethod
    def _node_expr_from_genes(log_df: pd.DataFrame, genes: list[str], agg: str) -> pd.Series:
        if not genes:
            return pd.Series([np.nan] * log_df.shape[1], index=log_df.columns, dtype=float)
        xs = [CancerNetworkBuilder._hgnc_gene_expr(log_df, g) for g in genes]
        m = pd.concat(xs, axis=1)
        if agg == "max":
            return m.max(axis=1, skipna=True)
        if agg == "mean":
            return m.mean(axis=1, skipna=True)
        raise ValueError(f"unsupported agg: {agg}")

    def generate_tcga_expression_cohort(
        self,
        project: str,
        counts_tumor_csv: str,
        counts_normal_csv: str,
        out_dir: str,
        manifest_csv: str | None = None,
        n_tumor: int = 5,
        n_normal: int = 5,
        log2_fc_threshold: float = 1.0,
        agg: str = "max",
        node_to_genes: dict[str, list[str]] | None = None,
    ) -> pd.DataFrame:
        os.makedirs(out_dir, exist_ok=True)
        tumor_df = self._read_counts_matrix(counts_tumor_csv)
        normal_df = self._read_counts_matrix(counts_normal_csv)

        tumor_log = tumor_df.apply(self._safe_log2_counts, axis=0)
        normal_log = normal_df.apply(self._safe_log2_counts, axis=0)

        if node_to_genes is None:
            node_to_genes = self.default_node_to_genes_for_nodes(list(self.nodes))
        node_to_genes = {k: list(v) for k, v in dict(node_to_genes).items() if k in self.nodes}

        normal_expr = {node: self._node_expr_from_genes(normal_log, genes, agg=agg) for node, genes in node_to_genes.items()}
        normal_median = {}
        for node, s in normal_expr.items():
            a = s.to_numpy(dtype=float, copy=False)
            if np.all(np.isnan(a)):
                normal_median[node] = float("nan")
            else:
                normal_median[node] = float(np.nanmedian(a))

        file_id_to_case: dict[str, str] = {}
        if manifest_csv:
            mf = pd.read_csv(manifest_csv)
            if "file_id" in mf.columns and "case_submitter_id" in mf.columns:
                mf = mf.dropna(subset=["file_id", "case_submitter_id"])
                file_id_to_case = {
                    str(row["file_id"]): str(row["case_submitter_id"])
                    for _, row in mf.iterrows()
                }

        def case_id_for_sample(sample_name: str) -> str | None:
            if not sample_name:
                return None
            file_id = str(sample_name).split("__")[0]
            if not file_id:
                return None
            return file_id_to_case.get(file_id)

        tumor_cols_all = list(tumor_log.columns)
        normal_cols_all = list(normal_log.columns)

        tumor_cols = tumor_cols_all[: int(n_tumor)]
        normal_cols = normal_cols_all[: int(n_normal)]
        if file_id_to_case:
            tumor_case_to_sample: dict[str, str] = {}
            for s in tumor_cols_all:
                cid = case_id_for_sample(str(s))
                if cid and cid not in tumor_case_to_sample:
                    tumor_case_to_sample[cid] = str(s)

            normal_case_to_sample: dict[str, str] = {}
            for s in normal_cols_all:
                cid = case_id_for_sample(str(s))
                if cid and cid not in normal_case_to_sample:
                    normal_case_to_sample[cid] = str(s)

            common_cases = sorted(set(tumor_case_to_sample.keys()) & set(normal_case_to_sample.keys()))
            n_pairs = min(int(n_tumor), int(n_normal))
            selected = common_cases[:n_pairs]
            tumor_cols = [tumor_case_to_sample[cid] for cid in selected]
            normal_cols = [normal_case_to_sample[cid] for cid in selected]

        rows = []

        for sample_name in normal_cols:
            cid = case_id_for_sample(str(sample_name))
            patient_id = f"{project}__{cid}" if cid else f"{project}__{str(sample_name).split('__')[0]}"
            net = self._create_network(patient_id, "Normal", {})
            net["metadata"] = {
                **net.get("metadata", {}),
                "project": project,
                "sample_name": sample_name,
                "cohort_source": "TCGA_GDC_STAR_Counts",
                "binarization": {
                    "space": "log2(count+1)",
                    "baseline": "median_across_normals",
                    "threshold": float(log2_fc_threshold),
                    "agg": agg,
                },
                "node_gene_map": node_to_genes,
            }
            self._save_network_to_dir(net, out_dir, patient_id, "Normal")
            rows.append({"project": project, "patient_id": patient_id, "tissue_type": "Normal", "sample_name": sample_name, "mutation_count": 0})

        for sample_name in tumor_cols:
            cid = case_id_for_sample(str(sample_name))
            patient_id = f"{project}__{cid}" if cid else f"{project}__{str(sample_name).split('__')[0]}"

            mutations = {}
            for node, genes in node_to_genes.items():
                tumor_val = float(self._node_expr_from_genes(tumor_log[[sample_name]], genes, agg=agg).iloc[0])
                base = normal_median.get(node, np.nan)
                if not np.isfinite(tumor_val) or not np.isfinite(base):
                    continue
                delta = tumor_val - base
                if delta >= log2_fc_threshold:
                    mutations[node] = "GoF"
                elif delta <= -log2_fc_threshold:
                    mutations[node] = "LoF"

            net = self._create_network(patient_id, "Tumor", mutations)
            net["metadata"] = {
                **net.get("metadata", {}),
                "project": project,
                "sample_name": sample_name,
                "cohort_source": "TCGA_GDC_STAR_Counts",
                "binarization": {
                    "space": "log2(count+1)",
                    "baseline": "median_across_normals",
                    "threshold": float(log2_fc_threshold),
                    "agg": agg,
                },
                "node_gene_map": node_to_genes,
            }
            self._save_network_to_dir(net, out_dir, patient_id, "Tumor")
            rows.append({"project": project, "patient_id": patient_id, "tissue_type": "Tumor", "sample_name": sample_name, "mutation_count": len(mutations)})

        return pd.DataFrame(rows)

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

    @staticmethod
    def _save_network_to_dir(network, out_dir: str, patient_id: str, tissue_type: str) -> str:
        filename = f"{patient_id}_{tissue_type}.json"
        path = os.path.join(out_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(network, f, indent=2)
        return path

if __name__ == "__main__":
    builder = CancerNetworkBuilder(BASE_NETWORK_PATH, OUTPUT_DIR)
    builder.generate_patient_cohort(N_PATIENTS)
