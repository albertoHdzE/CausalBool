
import os
import json
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
import sys
import re
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder
from stats.Mutual_Information_Analyzer import MutualInformationAnalyzer
try:
    import networkx as nx
except Exception:
    nx = None

class CorrelationResult(dict):
    def __iter__(self):
        yield self.get("rho", 0.0)
        yield self.get("pval", 1.0)

class DepMapValidation:
    def __init__(
        self,
        data_dir,
        depmap_path,
        depmap_model_path: str | None = None,
        depmap_oncotree_codes: list[str] | None = None,
        depmap_oncotree_lineages: list[str] | None = None,
    ):
        """
        Initialize the DepMap Validation pipeline.
        
        Args:
            data_dir (str): Directory containing patient networks (JSON).
            depmap_path (str): Path to DepMap CRISPR essentiality data (CSV).
            depmap_model_path (str | None): Path to DepMap Model.csv (for model filtering).
            depmap_oncotree_codes (list[str] | None): Filter to these OncotreeCode values.
            depmap_oncotree_lineages (list[str] | None): Filter to these OncotreeLineage values.
        """
        self.data_dir = data_dir
        self.depmap_path = depmap_path
        self.depmap_model_path = depmap_model_path
        self.depmap_oncotree_codes = depmap_oncotree_codes
        self.depmap_oncotree_lineages = depmap_oncotree_lineages
        self.node_gene_map = {
            "EGF": ["EGF"],
            "EGFR": ["EGFR"],
            "GRB2": ["GRB2"],
            "SOS": ["SOS1", "SOS2"],
            "RAS": ["KRAS", "NRAS", "HRAS"],
            "RAF": ["BRAF", "RAF1"],
            "MEK": ["MAP2K1", "MAP2K2"],
            "ERK": ["MAPK1", "MAPK3"],
            "PI3K": ["PIK3CA", "PIK3CB", "PIK3CD"],
            "AKT": ["AKT1", "AKT2", "AKT3"],
        }
        self.depmap_data = self._load_depmap()
        self.depmap_map = (
            self.depmap_data.dropna(subset=["Gene", "Dependency"])
            .assign(Gene=lambda d: d["Gene"].map(lambda g: str(g).strip().upper()))
            .groupby("Gene")["Dependency"]
            .mean()
            .to_dict()
        )
        
    @staticmethod
    def _normalize_gene_symbol(name: str) -> str:
        name = str(name).strip()
        name = re.sub(r"\s*\(\d+\)$", "", name)
        return name

    def _dep_score_for_node(self, node: str) -> float:
        key = self._normalize_gene_symbol(node).strip().upper()
        direct = self.depmap_map.get(key, np.nan)
        if not np.isnan(direct):
            return float(direct)

        genes = self.node_gene_map.get(key)
        if not genes:
            return np.nan

        vals = []
        for g in genes:
            v = self.depmap_map.get(str(g).strip().upper(), np.nan)
            if not np.isnan(v):
                vals.append(float(v))
        if not vals:
            return np.nan
        return float(np.mean(vals))

    @staticmethod
    def _is_dependency_table(df: pd.DataFrame) -> bool:
        cols = set(map(str, df.columns))
        return "Gene" in cols and "Dependency" in cols and len(cols) <= 4

    @staticmethod
    def _build_dependency_table_from_gene_effect_matrix(
        gene_effect_path: str,
        out_path: str,
        chunksize: int = 500,
        keep_model_ids: set[str] | None = None,
        gene_whitelist: set[str] | None = None,
    ) -> str:
        header = pd.read_csv(gene_effect_path, nrows=0)
        cols = list(header.columns)
        if len(cols) < 2:
            pd.DataFrame(columns=["Gene", "Dependency"]).to_csv(out_path, index=False)
            return out_path

        id_col = cols[0]
        all_gene_cols = cols[1:]
        if gene_whitelist is None:
            gene_cols = all_gene_cols
        else:
            wl = {DepMapValidation._normalize_gene_symbol(g).strip().upper() for g in gene_whitelist}
            keep = []
            for c in all_gene_cols:
                g = DepMapValidation._normalize_gene_symbol(c).strip().upper()
                if g in wl:
                    keep.append(c)
            gene_cols = keep

        if not gene_cols:
            pd.DataFrame(columns=["Gene", "Dependency"]).to_csv(out_path, index=False)
            return out_path

        reader = pd.read_csv(
            gene_effect_path,
            usecols=[id_col, *gene_cols],
            chunksize=chunksize,
            low_memory=False,
        )

        sums = np.zeros(len(gene_cols), dtype=np.float64)
        counts = np.zeros(len(gene_cols), dtype=np.int64)

        def ingest(chunk: pd.DataFrame) -> None:
            if keep_model_ids is not None:
                chunk = chunk[chunk[id_col].isin(keep_model_ids)]
                if len(chunk) == 0:
                    return
            block = chunk[gene_cols]
            sums[:] += block.sum(axis=0, skipna=True).to_numpy(dtype=np.float64, copy=False)
            counts[:] += block.count(axis=0).to_numpy(dtype=np.int64, copy=False)

        for chunk in reader:
            ingest(chunk)

        means = np.divide(sums, counts, out=np.full_like(sums, np.nan), where=counts != 0)
        genes = [DepMapValidation._normalize_gene_symbol(c) for c in gene_cols]

        df = pd.DataFrame({"Gene": genes, "Dependency": means}).dropna(subset=["Dependency"])
        df.to_csv(out_path, index=False)
        return out_path

    @staticmethod
    def _select_model_ids_for_oncotree(model_csv_path: str, oncotree_codes: list[str]) -> set[str]:
        if not model_csv_path or not os.path.exists(model_csv_path):
            return set()
        if not oncotree_codes:
            return set()
        codes = {str(c).strip().upper() for c in oncotree_codes}
        df = pd.read_csv(model_csv_path, low_memory=False)
        if "ModelID" not in df.columns or "OncotreeCode" not in df.columns:
            return set()
        keep = df[df["OncotreeCode"].astype(str).str.upper().isin(codes)]["ModelID"].astype(str)
        return set(keep.tolist())

    @staticmethod
    def _select_model_ids_for_lineage(model_csv_path: str, lineages: list[str]) -> set[str]:
        if not model_csv_path or not os.path.exists(model_csv_path):
            return set()
        if not lineages:
            return set()
        ls = {str(l).strip().upper() for l in lineages if str(l).strip()}
        if not ls:
            return set()
        df = pd.read_csv(model_csv_path, low_memory=False)
        if "ModelID" not in df.columns or "OncotreeLineage" not in df.columns:
            return set()
        lineage_col = df["OncotreeLineage"].astype(str).str.strip().str.upper()
        keep = df[lineage_col.isin(ls)]["ModelID"].astype(str)
        return set(keep.tolist())

    def _load_depmap(self):
        """
        Load DepMap data. 
        Expects CSV with columns 'Gene' and 'Dependency'.
        Dependency Score < -1 implies Essentiality.
        """
        if not os.path.exists(self.depmap_path):
            print(f"Warning: DepMap file {self.depmap_path} not found.")
            return pd.DataFrame(columns=["Gene", "Dependency"])
        try:
            preview = pd.read_csv(self.depmap_path, nrows=5)
        except Exception:
            return pd.DataFrame(columns=["Gene", "Dependency"])

        if self._is_dependency_table(preview):
            df = pd.read_csv(self.depmap_path)
            df["Gene"] = df["Gene"].map(self._normalize_gene_symbol)
            return df

        wl = set()
        for node, genes in self.node_gene_map.items():
            wl.add(str(node).strip().upper())
            for g in genes:
                wl.add(str(g).strip().upper())

        keep_ids = None
        derived_suffix = ""
        if self.depmap_model_path:
            keep_ids_codes = None
            keep_ids_lineage = None
            derived_parts = []

            if self.depmap_oncotree_codes:
                keep_ids_codes = self._select_model_ids_for_oncotree(self.depmap_model_path, self.depmap_oncotree_codes)
                derived_parts.append("oncotree_" + "-".join([str(c).strip().upper() for c in self.depmap_oncotree_codes]))

            if self.depmap_oncotree_lineages:
                keep_ids_lineage = self._select_model_ids_for_lineage(self.depmap_model_path, self.depmap_oncotree_lineages)
                derived_parts.append("lineage_" + "-".join([str(l).strip().upper() for l in self.depmap_oncotree_lineages]))

            if keep_ids_codes is not None and keep_ids_lineage is not None:
                keep_ids = keep_ids_codes & keep_ids_lineage
            elif keep_ids_codes is not None:
                keep_ids = keep_ids_codes
            elif keep_ids_lineage is not None:
                keep_ids = keep_ids_lineage

            if derived_parts:
                derived_suffix = "__" + "__".join(derived_parts)

        derived_path = self.depmap_path + f".gene_mean{derived_suffix}.csv"
        if not os.path.exists(derived_path):
            print(f"[{datetime.now()}] Building gene-level dependency table from: {self.depmap_path}{derived_suffix}")
            self._build_dependency_table_from_gene_effect_matrix(
                self.depmap_path,
                derived_path,
                chunksize=500,
                keep_model_ids=keep_ids,
                gene_whitelist=wl,
            )

        df = pd.read_csv(derived_path)
        df["Gene"] = df["Gene"].map(self._normalize_gene_symbol)
        return df

    def compute_d_v2(self, cm):
        """Compute D_v2 for an adjacency matrix."""
        if cm is None:
            return 0.0
        cm = np.asarray(cm)
        if cm.size == 0:
            return 0.0
        encoder = UniversalDv2Encoder(cm.astype(int, copy=False), block_sizes=[4, 5, 6])
        result = encoder.compute()
        return float(result["dv2"])

    @staticmethod
    def _row_stochastic(a: np.ndarray, eps: float = 1e-12) -> np.ndarray:
        a = np.asarray(a, dtype=float)
        rs = a.sum(axis=1, keepdims=True)
        rs = np.where(rs <= eps, 1.0, rs)
        return a / rs

    @staticmethod
    def _pagerank_from_cm(cm: np.ndarray, alpha: float = 0.85, max_iter: int = 200, tol: float = 1e-10) -> np.ndarray:
        cm = np.asarray(cm, dtype=float)
        n = cm.shape[0]
        if n == 0:
            return np.array([], dtype=float)

        adj = (cm != 0).astype(float)
        out = adj.sum(axis=0)
        p = np.full(n, 1.0 / n, dtype=float)

        teleport = (1.0 - alpha) / n
        dangling = (out == 0)

        for _ in range(max_iter):
            p_prev = p
            contrib = np.zeros(n, dtype=float)
            nz = out != 0
            if np.any(nz):
                contrib = (adj[:, nz] @ (p_prev[nz] / out[nz]))
            dangling_mass = p_prev[dangling].sum() if np.any(dangling) else 0.0
            p = teleport + alpha * (contrib + dangling_mass / n)
            if np.linalg.norm(p - p_prev, ord=1) < tol:
                break
        return p

    @staticmethod
    def _eigenvector_centrality_from_cm(cm: np.ndarray, max_iter: int = 200, tol: float = 1e-10) -> np.ndarray:
        cm = np.asarray(cm, dtype=float)
        n = cm.shape[0]
        if n == 0:
            return np.array([], dtype=float)
        a = (cm != 0).astype(float)
        v = np.full(n, 1.0 / np.sqrt(n), dtype=float)
        for _ in range(max_iter):
            v_prev = v
            v = a @ v_prev
            norm = np.linalg.norm(v)
            if norm == 0:
                return np.zeros(n, dtype=float)
            v = v / norm
            if np.linalg.norm(v - v_prev) < tol:
                break
        v = np.abs(v)
        return v

    @staticmethod
    def _betweenness_from_cm(cm: np.ndarray) -> np.ndarray:
        if nx is None:
            return np.full(cm.shape[0], np.nan, dtype=float)

        cm = np.asarray(cm)
        n = cm.shape[0]
        g = nx.DiGraph()
        g.add_nodes_from(range(n))
        for tgt in range(n):
            for src in range(n):
                if cm[tgt, src] != 0:
                    g.add_edge(src, tgt)
        bt = nx.betweenness_centrality(g, normalized=True)
        return np.array([float(bt.get(i, 0.0)) for i in range(n)], dtype=float)

    def compute_structural_predictors(self, nodes, cm: np.ndarray) -> dict:
        nodes = list(nodes)
        cm = np.asarray(cm)
        in_deg = cm.sum(axis=1).astype(float)
        out_deg = cm.sum(axis=0).astype(float)
        total_deg = in_deg + out_deg

        pr_vec = self._pagerank_from_cm(cm) if cm.size else np.full(len(nodes), np.nan, dtype=float)
        ev_vec = self._eigenvector_centrality_from_cm(cm) if cm.size else np.full(len(nodes), np.nan, dtype=float)
        bt_vec = self._betweenness_from_cm(cm) if cm.size else np.full(len(nodes), np.nan, dtype=float)

        feats = {}
        for i, gene in enumerate(nodes):
            feats[gene] = {
                "InDegree": float(in_deg[i]),
                "OutDegree": float(out_deg[i]),
                "TotalDegree": float(total_deg[i]),
                "Betweenness": float(bt_vec[i]) if i < len(bt_vec) else np.nan,
                "PageRank": float(pr_vec[i]) if i < len(pr_vec) else np.nan,
                "EigenvectorCentrality": float(ev_vec[i]) if i < len(ev_vec) else np.nan,
            }
        return feats

    def analyze_single_network(self, network_path):
        """
        Perform in-silico knockout for all genes in a single network
        and compute Delta D (Impact).
        """
        with open(network_path, 'r') as f:
            net = json.load(f)
            
        nodes = net.get("nodes", [])
        cm = np.array(net.get("cm", []))
        
        if len(cm) == 0:
            return {}
            
        # Baseline D
        d_baseline = self.compute_d_v2(cm)
        feats = self.compute_structural_predictors(nodes, cm)
        
        results = {}
        
        for i, gene in enumerate(nodes):
            # In-silico Knockout: Remove node i
            # We create a sub-matrix by deleting row i and col i
            cm_ko = np.delete(np.delete(cm, i, axis=0), i, axis=1)
            
            d_ko = self.compute_d_v2(cm_ko)
            
            # Delta D = D_baseline - D_knockout
            # Positive Delta D means the node contributed structural information (Complexity dropped)
            # Negative Delta D means the node was "noise" (Complexity increased)
            delta_d = d_baseline - d_ko
            
            # Get DepMap score if available
            dep_score = self._dep_score_for_node(gene)
                
            results[gene] = {
                "delta_d": delta_d,
                "dependency": dep_score,
                **feats.get(gene, {})
            }
            
        return results

    def _find_network_paths(self, suffix: str, recursive: bool = False) -> list:
        if recursive:
            out = []
            for root, _, files in os.walk(self.data_dir):
                for f in files:
                    if f.endswith(suffix):
                        out.append(os.path.join(root, f))
            return sorted(out)

        return sorted(
            [
                os.path.join(self.data_dir, f)
                for f in os.listdir(self.data_dir)
                if f.endswith(suffix)
            ]
        )

    def run_cohort_analysis(self, n_patients=None, recursive: bool = False):
        """
        Run knockout analysis on all tumor networks in data_dir.
        """
        print(f"[{datetime.now()}] Starting DepMap Validation...")
        
        files = self._find_network_paths("_Tumor.json", recursive=recursive)
        if n_patients:
            files = files[:n_patients]
            
        aggregated_results = {} # Gene -> [Delta_D values across patients]
        
        for path in files:
            res = self.analyze_single_network(path)
            
            for gene, metrics in res.items():
                if gene not in aggregated_results:
                    aggregated_results[gene] = {
                        "delta_ds": [],
                        "dep_score": metrics["dependency"],
                        "InDegree": [],
                        "OutDegree": [],
                        "TotalDegree": [],
                        "Betweenness": [],
                        "PageRank": [],
                        "EigenvectorCentrality": [],
                    }
                aggregated_results[gene]["delta_ds"].append(metrics["delta_d"])
                aggregated_results[gene]["InDegree"].append(metrics.get("InDegree", np.nan))
                aggregated_results[gene]["OutDegree"].append(metrics.get("OutDegree", np.nan))
                aggregated_results[gene]["TotalDegree"].append(metrics.get("TotalDegree", np.nan))
                aggregated_results[gene]["Betweenness"].append(metrics.get("Betweenness", np.nan))
                aggregated_results[gene]["PageRank"].append(metrics.get("PageRank", np.nan))
                aggregated_results[gene]["EigenvectorCentrality"].append(metrics.get("EigenvectorCentrality", np.nan))
                
        # Summarize
        summary = []
        for gene, data in aggregated_results.items():
            mean_delta_d = np.mean(data["delta_ds"])
            summary.append({
                "Gene": gene,
                "Mean_Delta_D": mean_delta_d,
                "Dependency": data["dep_score"],
                "InDegree": float(np.nanmean(data["InDegree"])) if len(data["InDegree"]) else np.nan,
                "OutDegree": float(np.nanmean(data["OutDegree"])) if len(data["OutDegree"]) else np.nan,
                "TotalDegree": float(np.nanmean(data["TotalDegree"])) if len(data["TotalDegree"]) else np.nan,
                "Betweenness": float(np.nanmean(data["Betweenness"])) if len(data["Betweenness"]) else np.nan,
                "PageRank": float(np.nanmean(data["PageRank"])) if len(data["PageRank"]) else np.nan,
                "EigenvectorCentrality": float(np.nanmean(data["EigenvectorCentrality"])) if len(data["EigenvectorCentrality"]) else np.nan,
                "N_Patients": int(len(data["delta_ds"])),
            })
            
        return pd.DataFrame(summary)

    def run_directory_analysis(self, suffix=".json", limit=None, min_nodes=3):
        files = [f for f in os.listdir(self.data_dir) if f.endswith(suffix)]
        files = sorted(files)
        if limit is not None:
            files = files[: int(limit)]

        aggregated = {}
        for f in files:
            path = os.path.join(self.data_dir, f)
            try:
                with open(path, "r") as h:
                    net = json.load(h)
            except Exception:
                continue

            nodes = net.get("nodes", [])
            cm = np.array(net.get("cm", []))
            if len(nodes) < min_nodes or len(cm) == 0:
                continue

            res = self.analyze_single_network(path)
            for gene, metrics in res.items():
                if gene not in aggregated:
                    aggregated[gene] = {
                        "delta_ds": [],
                        "dep_score": metrics.get("dependency", np.nan),
                        "InDegree": [],
                        "OutDegree": [],
                        "TotalDegree": [],
                        "Betweenness": [],
                        "PageRank": [],
                        "EigenvectorCentrality": [],
                        "n_networks": 0,
                    }
                aggregated[gene]["delta_ds"].append(metrics.get("delta_d", np.nan))
                aggregated[gene]["InDegree"].append(metrics.get("InDegree", np.nan))
                aggregated[gene]["OutDegree"].append(metrics.get("OutDegree", np.nan))
                aggregated[gene]["TotalDegree"].append(metrics.get("TotalDegree", np.nan))
                aggregated[gene]["Betweenness"].append(metrics.get("Betweenness", np.nan))
                aggregated[gene]["PageRank"].append(metrics.get("PageRank", np.nan))
                aggregated[gene]["EigenvectorCentrality"].append(metrics.get("EigenvectorCentrality", np.nan))

            for gene in res.keys():
                aggregated[gene]["n_networks"] += 1

        rows = []
        for gene, data in aggregated.items():
            rows.append({
                "Gene": gene,
                "Mean_Delta_D": float(np.nanmean(data["delta_ds"])) if len(data["delta_ds"]) else np.nan,
                "Dependency": data["dep_score"],
                "InDegree": float(np.nanmean(data["InDegree"])) if len(data["InDegree"]) else np.nan,
                "OutDegree": float(np.nanmean(data["OutDegree"])) if len(data["OutDegree"]) else np.nan,
                "TotalDegree": float(np.nanmean(data["TotalDegree"])) if len(data["TotalDegree"]) else np.nan,
                "Betweenness": float(np.nanmean(data["Betweenness"])) if len(data["Betweenness"]) else np.nan,
                "PageRank": float(np.nanmean(data["PageRank"])) if len(data["PageRank"]) else np.nan,
                "EigenvectorCentrality": float(np.nanmean(data["EigenvectorCentrality"])) if len(data["EigenvectorCentrality"]) else np.nan,
                "N_Networks": int(data["n_networks"]),
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _corr_pair(x: np.ndarray, y: np.ndarray) -> dict:
        mask = ~(np.isnan(x) | np.isnan(y))
        x = x[mask]
        y = y[mask]
        if len(x) < 3:
            return {"pearson_r": 0.0, "pearson_p": 1.0, "spearman_r": 0.0, "spearman_p": 1.0, "n": int(len(x))}
        pr, pp = stats.pearsonr(x, y)
        sr, sp = stats.spearmanr(x, y)
        return {"pearson_r": float(pr), "pearson_p": float(pp), "spearman_r": float(sr), "spearman_p": float(sp), "n": int(len(x))}

    def compare_predictors(self, df: pd.DataFrame, random_state: int = 2026) -> dict:
        predictors = ["Mean_Delta_D", "InDegree", "OutDegree", "TotalDegree", "Betweenness", "PageRank", "EigenvectorCentrality"]
        out = {"univariate": {}, "multivariate": {}}
        y = df["Dependency"].to_numpy(dtype=float, copy=False)

        for col in predictors:
            x = df[col].to_numpy(dtype=float, copy=False)
            out["univariate"][col] = self._corr_pair(x, y)

        base_cols = ["InDegree", "OutDegree", "TotalDegree", "Betweenness", "PageRank", "EigenvectorCentrality"]
        df_mv = df[["Dependency", "Mean_Delta_D", *base_cols]].copy()
        df_mv = df_mv.replace([np.inf, -np.inf], np.nan).dropna()
        if len(df_mv) < 20:
            out["multivariate"] = {"n": int(len(df_mv))}
            return out

        df_mv = df_mv.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
        y_mv = df_mv["Dependency"].to_numpy(dtype=float, copy=False)

        x_base = df_mv[base_cols].to_numpy(dtype=float, copy=False)
        x_full = df_mv[["Mean_Delta_D", *base_cols]].to_numpy(dtype=float, copy=False)

        def standardize(x, mean, std):
            return (x - mean) / std

        def fit_predict(x_tr, y_tr, x_te):
            mean = x_tr.mean(axis=0, keepdims=True)
            std = x_tr.std(axis=0, keepdims=True)
            std = np.where(std == 0, 1.0, std)
            x_tr_z = standardize(x_tr, mean, std)
            x_te_z = standardize(x_te, mean, std)
            x_tr_z = np.column_stack([np.ones(len(x_tr_z)), x_tr_z])
            x_te_z = np.column_stack([np.ones(len(x_te_z)), x_te_z])
            beta, *_ = np.linalg.lstsq(x_tr_z, y_tr, rcond=None)
            return x_tr_z @ beta, x_te_z @ beta

        def r2(y_true, y_pred):
            ss_res = float(np.sum((y_true - y_pred) ** 2))
            ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
            if ss_tot == 0:
                return 0.0
            return 1.0 - ss_res / ss_tot

        n = len(df_mv)
        k = 5
        fold_sizes = [(n + i) // k for i in range(k)]
        idx = 0
        base_scores = []
        full_scores = []
        base_in = []
        full_in = []
        for fs in fold_sizes:
            te_idx = np.arange(idx, idx + fs)
            tr_idx = np.concatenate([np.arange(0, idx), np.arange(idx + fs, n)])
            idx += fs

            y_tr, y_te = y_mv[tr_idx], y_mv[te_idx]
            pred_tr, pred_te = fit_predict(x_base[tr_idx], y_tr, x_base[te_idx])
            base_in.append(r2(y_tr, pred_tr))
            base_scores.append(r2(y_te, pred_te))

            pred_tr, pred_te = fit_predict(x_full[tr_idx], y_tr, x_full[te_idx])
            full_in.append(r2(y_tr, pred_tr))
            full_scores.append(r2(y_te, pred_te))

        out["multivariate"] = {
            "n": int(n),
            "cv5_r2_base_mean": float(np.mean(base_scores)),
            "cv5_r2_full_mean": float(np.mean(full_scores)),
            "cv5_r2_delta_mean": float(np.mean(full_scores) - np.mean(base_scores)),
            "in_sample_r2_base_mean": float(np.mean(base_in)),
            "in_sample_r2_full_mean": float(np.mean(full_in)),
        }
        return out

    def compute_correlation(self, results):
        """
        Compute correlation and Mutual Information between Delta D and Dependency Score.
        Args:
            results: DataFrame or Dict
        """
        if isinstance(results, dict):
            # Convert dict from analyze_single_network to DF-like lists
            delta_ds = [v["delta_d"] for v in results.values()]
            deps = [v["dependency"] for v in results.values()]
        else:
            delta_ds = results["Mean_Delta_D"]
            deps = results["Dependency"]
            
        # Remove NaNs
        valid_indices = [i for i in range(len(deps)) if not np.isnan(deps[i])]
        if len(valid_indices) < 3:
            return CorrelationResult({'rho': 0.0, 'pval': 1.0, 'mi_bits': 0.0, 'mi_interpretation': "Insufficient Data"})
            
        delta_ds = [delta_ds[i] for i in valid_indices]
        deps = [deps[i] for i in valid_indices]
        
        # Pearson
        corr, pval = stats.pearsonr(delta_ds, deps)

        spearman_corr, spearman_pval = stats.spearmanr(delta_ds, deps)
        
        # Mutual Information
        mi_res = MutualInformationAnalyzer.compute_mutual_information(delta_ds, deps, discrete_y=False)
        
        return CorrelationResult({
            'rho': corr,
            'pval': pval,
            'spearman_rho': spearman_corr,
            'spearman_pval': spearman_pval,
            'mi_bits': mi_res['MI_bits'],
            'mi_interpretation': mi_res['interpretation']
        })

    @staticmethod
    def save_scatter_plot(df: pd.DataFrame, out_path: str) -> str | None:
        if plt is None:
            return None
        if df is None or len(df) == 0:
            return None
        if "Mean_Delta_D" not in df.columns or "Dependency" not in df.columns:
            return None
        x = df["Mean_Delta_D"].to_numpy(dtype=float, copy=False)
        y = df["Dependency"].to_numpy(dtype=float, copy=False)
        mask = ~(np.isnan(x) | np.isnan(y))
        x = x[mask]
        y = y[mask]
        if len(x) == 0:
            return None
        fig = plt.figure(figsize=(5, 4), dpi=200)
        ax = fig.add_subplot(111)
        ax.scatter(x, y, s=30, alpha=0.85)
        ax.set_xlabel("Mean ΔD (in-silico KO)")
        ax.set_ylabel("DepMap CRISPR gene effect")
        ax.set_title(f"ΔD vs DepMap (n={len(x)})")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return out_path

if __name__ == "__main__":
    # Example Usage
    DATA_DIR = os.environ.get("DEPMAP_DATA_DIR", "data/cancer/patients")
    DEPMAP_PATH = os.environ.get("DEPMAP_PATH", "data/cancer/depmap_crispr.csv")
    DEPMAP_MODEL_PATH = os.environ.get("DEPMAP_MODEL_PATH")
    DEPMAP_ONCOTREE_CODES = os.environ.get("DEPMAP_ONCOTREE_CODES")
    DEPMAP_ONCOTREE_LINEAGES = os.environ.get("DEPMAP_ONCOTREE_LINEAGES")
    N_PATIENTS = os.environ.get("DEPMAP_N_PATIENTS")
    RECURSIVE = os.environ.get("DEPMAP_RECURSIVE", "0").strip() == "1"
    OUT_PREFIX = os.environ.get("DEPMAP_OUT_PREFIX", "results/cancer/depmap_validation")
    os.makedirs("results/cancer", exist_ok=True)
    
    # Check if DepMap exists, if not create dummy
    if not os.path.exists(DEPMAP_PATH):
        print("DepMap file not found. Generating synthetic DepMap data for testing...")
        # Create dummy based on genes in a random file
        sample_file = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")][0]
        with open(os.path.join(DATA_DIR, sample_file)) as f:
            genes = json.load(f)["nodes"]
            
        df = pd.DataFrame({
            "Gene": genes,
            "Dependency": np.random.normal(-0.5, 1.0, len(genes)) # Mix of essential (-1.5) and non-essential (0)
        })
        # Force some essential genes
        essentials = ["EGFR", "GRB2", "RAS", "MEK", "ERK"]
        for g in essentials:
            if g in genes:
                df.loc[df["Gene"] == g, "Dependency"] = -2.0 # Highly essential
                
        df.to_csv(DEPMAP_PATH, index=False)
        
    oncotree_codes = None
    if DEPMAP_ONCOTREE_CODES:
        oncotree_codes = [c.strip() for c in str(DEPMAP_ONCOTREE_CODES).split(",") if c.strip()]

    lineages = None
    if DEPMAP_ONCOTREE_LINEAGES:
        lineages = [l.strip() for l in str(DEPMAP_ONCOTREE_LINEAGES).split(",") if l.strip()]

    n_patients = int(N_PATIENTS) if N_PATIENTS else 20

    validator = DepMapValidation(
        DATA_DIR,
        DEPMAP_PATH,
        depmap_model_path=DEPMAP_MODEL_PATH,
        depmap_oncotree_codes=oncotree_codes,
        depmap_oncotree_lineages=lineages,
    )
    cohort_results = validator.run_cohort_analysis(n_patients=n_patients, recursive=RECURSIVE)
    
    # Save
    out_csv = OUT_PREFIX + ".csv"
    cohort_results.to_csv(out_csv, index=False)
    
    # Correlation
    stats_res = validator.compute_correlation(cohort_results)
    print(f"Global Correlation (Delta D vs Dependency): r={stats_res['rho']:.2f}, p={stats_res['pval']:.2e}")
    print(f"Mutual Information: {stats_res['mi_bits']:.2f} bits ({stats_res['mi_interpretation']})")
    
    # Save Stats
    stats_path = OUT_PREFIX + "_stats.json"
    with open(stats_path, 'w') as f:
        json.dump(stats_res, f, indent=4)
    print(f"Stats saved to {stats_path}")

    plot_path = OUT_PREFIX + "_scatter.png"
    saved_plot = DepMapValidation.save_scatter_plot(cohort_results, plot_path)
    if saved_plot:
        print(f"Plot saved to {saved_plot}")
    
    # Expect negative correlation: High Delta D (Important Structure) <-> Low Dependency Score (Essential)
    # Wait, Dependency Score is usually "Effect Size", where -2 is lethal.
    # So "Essential" = Negative Score.
    # "Important Structure" = High Delta D (Removing it destroys structure).
    # So High Delta D should map to Negative Score.
    # Correlation should be NEGATIVE.
