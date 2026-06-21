
import os
import json
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
import sys
import re
from pathlib import Path
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
    @staticmethod
    def _log(msg: str) -> None:
        print(f"[{datetime.now()}] {msg}")

    @staticmethod
    def _sha256_file(path: str, chunk_bytes: int = 8 * 1024 * 1024) -> str:
        import hashlib

        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                b = f.read(chunk_bytes)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()

    def __init__(
        self,
        data_dir,
        depmap_path,
        depmap_model_path: str | None = None,
        depmap_oncotree_codes: list[str] | None = None,
        depmap_oncotree_lineages: list[str] | None = None,
        node_gene_map: dict[str, list[str]] | None = None,
        force_rebuild_depmap_cache: bool = False,
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
        self.force_rebuild_depmap_cache = bool(force_rebuild_depmap_cache)
        if node_gene_map is None:
            node_gene_map = {
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
                "GFs": ["EGF", "TGFA", "IGF1"],
                "RTK": ["EGFR", "ERBB2", "ERBB3"],
                "MAPK": ["MAPK1", "MAPK3"],
                "TGFBR": ["TGFBR1", "TGFBR2"],
                "MEK1_2": ["MAP2K1", "MAP2K2"],
                "MAP3K1_3": ["MAP3K1", "MAP3K3"],
                "TAK1": ["MAP3K7"],
                "MTK1": ["MAP3K4"],
                "TAOK": ["TAOK1", "TAOK2", "TAOK3"],
                "JNK": ["MAPK8", "MAPK9", "MAPK10"],
                "p38": ["MAPK14", "MAPK11", "MAPK12", "MAPK13"],
                "RSK": ["RPS6KA1", "RPS6KA2", "RPS6KA3", "RPS6KA4", "RPS6KA5", "RPS6KA6"],
                "MSK": ["RPS6KA4", "RPS6KA5"],
                "p70": ["RPS6KB1", "RPS6KB2"],
                "PKC": ["PRKCA", "PRKCB", "PRKCD", "PRKCE", "PRKCQ", "PRKCZ", "PRKCI", "PRKCG"],
                "PLCG": ["PLCG1", "PLCG2"],
                "PIP3": [],
                "FOXO3": ["FOXO3"],
                "cycE": ["CCNE1", "CCNE2"],
                "TSC": ["TSC1", "TSC2"],
                "PRAS40": ["AKT1S1"],
                "Rb": ["RB1"],
                "p53": ["TP53"],
                "p21": ["CDKN1A"],
                "p14": ["CDKN2A"],
                "SMAD": ["SMAD2", "SMAD3", "SMAD4"],
                "AP1": ["FOS", "JUN"],
                "CREB": ["CREB1"],
                "SPRY": ["SPRY1", "SPRY2", "SPRY4"],
                "GADD45": ["GADD45A", "GADD45B", "GADD45G"],
                "mTORC1": ["MTOR", "RPTOR"],
                "E2F": ["E2F1", "E2F2", "E2F3"],
                "EIF4F": ["EIF4E", "EIF4G1", "EIF4A1"],
                "S6K": ["RPS6KB1", "RPS6KB2"],
                "Proliferation": [],
            }

        canon = {}
        for node, genes in dict(node_gene_map).items():
            k = self._normalize_gene_symbol(node).strip().upper()
            gs = []
            for g in list(genes or []):
                gg = self._normalize_gene_symbol(g).strip().upper()
                if gg:
                    gs.append(gg)
            canon[k] = gs

        try:
            wl_max_nodes = int(os.environ.get("DEPMAP_WL_MAX_NODES", "2000") or "2000")
            wl_max_files = int(os.environ.get("DEPMAP_WL_MAX_FILES", "50") or "50")
        except Exception:
            wl_max_nodes = 2000
            wl_max_files = 50
        try:
            if self.data_dir and os.path.isdir(self.data_dir) and wl_max_nodes > 0 and wl_max_files > 0:
                candidates = []
                for f in sorted(os.listdir(self.data_dir)):
                    if f.endswith("_Tumor.json") or f.endswith(".json"):
                        candidates.append(os.path.join(self.data_dir, f))
                    if len(candidates) >= wl_max_files:
                        break
                added = 0
                for p in candidates:
                    try:
                        with open(p, "r", encoding="utf-8") as h:
                            net = json.load(h)
                    except Exception:
                        continue
                    for n in list(net.get("nodes", []) or []):
                        k = self._normalize_gene_symbol(n).strip().upper()
                        if not k or k in canon:
                            continue
                        canon[k] = [k]
                        added += 1
                        if added >= wl_max_nodes:
                            break
                    if added >= wl_max_nodes:
                        break
        except Exception:
            pass
        self.node_gene_map = canon
        self.depmap_data = self._load_depmap()
        self.depmap_map = (
            self.depmap_data.dropna(subset=["Gene", "Dependency"])
            .assign(Gene=lambda d: d["Gene"].map(lambda g: str(g).strip().upper()))
            .groupby("Gene")["Dependency"]
            .mean()
            .to_dict()
        )
        self.keep_model_ids = self._select_keep_model_ids()
        wl = set()
        for node, genes in self.node_gene_map.items():
            wl.add(str(node).strip().upper())
            for g in genes:
                wl.add(str(g).strip().upper())
        wl = {g for g in wl if g}
        self.depmap_expr_map = self._load_feature_map_from_matrix(self._infer_depmap_expr_path(), wl, keep_model_ids=self.keep_model_ids)
        self.depmap_cn_map = self._load_feature_map_from_matrix(self._infer_depmap_cn_path(), wl, keep_model_ids=self.keep_model_ids)
        self.gnomad_pli_map, self.gnomad_loeuf_map = self._load_gnomad_maps(wl)
        
    @staticmethod
    def _normalize_gene_symbol(name: str) -> str:
        name = str(name).strip()
        name = re.sub(r"\s*\(\d+\)$", "", name)
        return name

    @staticmethod
    def _safe_tag(s: str) -> str:
        s = str(s)
        s = s.strip().upper()
        s = re.sub(r"[^A-Z0-9._-]+", "_", s)
        s = re.sub(r"_+", "_", s)
        s = s.strip("_")
        return s or "NA"

    def _select_keep_model_ids(self) -> set[str] | None:
        if not self.depmap_model_path or not os.path.exists(self.depmap_model_path):
            return None
        keep_ids_codes = None
        keep_ids_lineage = None
        if self.depmap_oncotree_codes:
            keep_ids_codes = self._select_model_ids_for_oncotree(self.depmap_model_path, self.depmap_oncotree_codes)
        if self.depmap_oncotree_lineages:
            keep_ids_lineage = self._select_model_ids_for_lineage(self.depmap_model_path, self.depmap_oncotree_lineages)
        if keep_ids_codes is not None and keep_ids_lineage is not None:
            return set(keep_ids_codes & keep_ids_lineage)
        if keep_ids_codes is not None:
            return set(keep_ids_codes)
        if keep_ids_lineage is not None:
            return set(keep_ids_lineage)
        return None

    @staticmethod
    def _infer_depmap_expr_path() -> str | None:
        override = os.environ.get("DEPMAP_EXPR_PATH")
        if override and os.path.exists(override):
            return override
        release_dir = os.environ.get("DEPMAP_RELEASE_DIR")
        if release_dir:
            p = os.path.join(release_dir, "OmicsExpressionProteinCodingGenesTPMLogp1BatchCorrected.csv")
            if os.path.exists(p):
                return p
        candidates = [
            os.path.join("data", "DepMap", "OmicsExpressionProteinCodingGenesTPMLogp1BatchCorrected.csv"),
            os.path.join("data", "depmap", "OmicsExpressionProteinCodingGenesTPMLogp1BatchCorrected.csv"),
        ]
        return next((p for p in candidates if os.path.exists(p)), None)

    @staticmethod
    def _infer_depmap_cn_path() -> str | None:
        override = os.environ.get("DEPMAP_CN_PATH")
        if override and os.path.exists(override):
            return override
        release_dir = os.environ.get("DEPMAP_RELEASE_DIR")
        if release_dir:
            p = os.path.join(release_dir, "OmicsCNGene.csv")
            if os.path.exists(p):
                return p
        candidates = [
            os.path.join("data", "DepMap", "OmicsCNGene.csv"),
            os.path.join("data", "depmap", "OmicsCNGene.csv"),
        ]
        return next((p for p in candidates if os.path.exists(p)), None)

    @staticmethod
    def _load_feature_map_from_matrix(
        matrix_path: str | None,
        gene_whitelist: set[str],
        keep_model_ids: set[str] | None = None,
    ) -> dict[str, float]:
        if not matrix_path or not os.path.exists(matrix_path):
            return {}
        try:
            header = pd.read_csv(matrix_path, nrows=0, low_memory=False)
        except Exception:
            return {}
        cols = list(header.columns)
        if len(cols) < 2:
            return {}
        id_col = cols[0]
        gene_whitelist = {str(g).strip().upper() for g in gene_whitelist if str(g).strip()}
        symbol_to_col: dict[str, str] = {}
        for c in cols[1:]:
            sym = str(c).split(" (", 1)[0]
            sym = DepMapValidation._normalize_gene_symbol(sym).strip().upper()
            if sym and sym not in symbol_to_col:
                symbol_to_col[sym] = c
        selected_cols = [symbol_to_col[g] for g in sorted(gene_whitelist) if g in symbol_to_col]
        if not selected_cols:
            return {}
        df = pd.read_csv(matrix_path, usecols=[id_col, *selected_cols], low_memory=False)
        if keep_model_ids is not None:
            df = df[df[id_col].astype(str).isin(keep_model_ids)]
        means = df[selected_cols].mean(axis=0, skipna=True)
        out: dict[str, float] = {}
        for col in selected_cols:
            sym = str(col).split(" (", 1)[0]
            sym = DepMapValidation._normalize_gene_symbol(sym).strip().upper()
            out[sym] = float(means[col])
        return out

    @staticmethod
    def _load_gnomad_maps(gene_whitelist: set[str]) -> tuple[dict[str, float], dict[str, float]]:
        root = Path(os.environ.get("GNOMAD_DIR", os.path.join("data", "gnomAD")))
        path = root / "gnomad_v2.1.1_constraint.tsv.bgz"
        if not path.exists():
            return {}, {}
        genes = {str(g).strip().upper() for g in gene_whitelist if str(g).strip()}
        if not genes:
            return {}, {}
        pli: dict[str, float] = {}
        loeuf: dict[str, float] = {}
        try:
            reader = pd.read_csv(
                path,
                sep="\t",
                compression="gzip",
                usecols=["gene", "pLI", "oe_lof_upper"],
                chunksize=250_000,
                low_memory=False,
            )
        except Exception:
            return {}, {}
        for chunk in reader:
            chunk = chunk.rename(columns={"gene": "Gene"})
            chunk["Gene"] = chunk["Gene"].astype(str).str.strip().str.upper()
            sub = chunk[chunk["Gene"].isin(genes)]
            if len(sub) == 0:
                continue
            sub = sub.copy()
            sub["pLI"] = pd.to_numeric(sub["pLI"], errors="coerce")
            sub["oe_lof_upper"] = pd.to_numeric(sub["oe_lof_upper"], errors="coerce")
            for g, grp in sub.groupby("Gene"):
                p = float(np.nanmax(grp["pLI"].to_numpy(dtype=float, copy=False)))
                o = float(np.nanmin(grp["oe_lof_upper"].to_numpy(dtype=float, copy=False)))
                if np.isfinite(p):
                    pli[g] = max(float(pli.get(g, float("-inf"))), p)
                if np.isfinite(o):
                    loeuf[g] = min(float(loeuf.get(g, float("inf"))), o)
        return pli, loeuf

    def _dep_score_for_node(self, node: str) -> float:
        return self._dep_score_for_node_with_map(node, self.node_gene_map)

    def _feature_for_node_with_map(
        self,
        node: str,
        feature_map: dict[str, float],
        node_gene_map: dict[str, list[str]] | None,
    ) -> float:
        key = self._normalize_gene_symbol(node).strip().upper()
        direct = feature_map.get(key, np.nan)
        if not np.isnan(direct):
            return float(direct)
        genes = None
        if node_gene_map is not None:
            genes = node_gene_map.get(key)
        if not genes:
            return np.nan
        vals = []
        for g in genes:
            v = feature_map.get(str(g).strip().upper(), np.nan)
            if not np.isnan(v):
                vals.append(float(v))
        if not vals:
            return np.nan
        return float(np.mean(vals))

    def _dep_score_for_node_with_map(self, node: str, node_gene_map: dict[str, list[str]] | None) -> float:
        key = self._normalize_gene_symbol(node).strip().upper()
        direct = self.depmap_map.get(key, np.nan)
        if not np.isnan(direct):
            return float(direct)

        genes = None
        if node_gene_map is not None:
            genes = node_gene_map.get(key)
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

    def _canonicalize_node_gene_map(self, node_gene_map: dict | None) -> dict[str, list[str]]:
        if not isinstance(node_gene_map, dict):
            return {}
        out: dict[str, list[str]] = {}
        for node, genes in node_gene_map.items():
            k = self._normalize_gene_symbol(node).strip().upper()
            if not k:
                continue
            gs = []
            if isinstance(genes, (list, tuple)):
                for g in genes:
                    gg = self._normalize_gene_symbol(g).strip().upper()
                    if gg:
                        gs.append(gg)
            out[k] = gs
        return out

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
        progress_every_chunks: int = 50,
        validate_streaming: bool = False,
        validate_n_genes: int = 5,
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

        DepMapValidation._log(
            "DepMap gene-effect matrix detected: "
            f"path={gene_effect_path} id_col={id_col!r} total_gene_cols={len(all_gene_cols)} selected_gene_cols={len(gene_cols)} "
            f"whitelist_terms={len(gene_whitelist) if gene_whitelist is not None else 0} chunksize={int(chunksize)}"
        )
        if keep_model_ids is not None:
            DepMapValidation._log(f"Model filtering enabled: n_keep_model_ids={len(keep_model_ids)}")

        reader = pd.read_csv(
            gene_effect_path,
            usecols=[id_col, *gene_cols],
            chunksize=chunksize,
            low_memory=False,
        )

        sums = np.zeros(len(gene_cols), dtype=np.float64)
        counts = np.zeros(len(gene_cols), dtype=np.int64)
        n_rows_raw = 0
        n_rows_used = 0

        for chunk_idx, chunk in enumerate(reader, start=1):
            n_rows_raw += int(len(chunk))
            if keep_model_ids is not None:
                mask = chunk[id_col].isin(keep_model_ids)
                n_kept = int(mask.sum())
                if n_kept == 0:
                    if progress_every_chunks and (chunk_idx % int(progress_every_chunks) == 0):
                        DepMapValidation._log(f"Streaming progress: chunk={chunk_idx} raw_rows={n_rows_raw} used_rows={n_rows_used}")
                    continue
                n_rows_used += n_kept
                block = chunk.loc[mask, gene_cols]
            else:
                n_rows_used += int(len(chunk))
                block = chunk[gene_cols]

            sums[:] += block.sum(axis=0, skipna=True).to_numpy(dtype=np.float64, copy=False)
            counts[:] += block.count(axis=0).to_numpy(dtype=np.int64, copy=False)
            if progress_every_chunks and (chunk_idx % int(progress_every_chunks) == 0):
                DepMapValidation._log(f"Streaming progress: chunk={chunk_idx} raw_rows={n_rows_raw} used_rows={n_rows_used}")

        gene_effect_means = np.divide(sums, counts, out=np.full_like(sums, np.nan), where=counts != 0)
        genes = [DepMapValidation._normalize_gene_symbol(c) for c in gene_cols]

        DepMapValidation._log(f"Streaming complete: raw_rows={n_rows_raw} used_rows={n_rows_used}")
        n_missing = int(np.sum(counts == 0))
        if n_missing:
            DepMapValidation._log(f"Missing columns with zero observations: n={n_missing}")
        dependency = -gene_effect_means
        DepMapValidation._log(
            "Dependency summary (defined as -gene effect; higher = more essential): "
            f"n_genes={int(np.sum(~np.isnan(dependency)))} mean={float(np.nanmean(dependency)):.6g} sd={float(np.nanstd(dependency)):.6g} "
            f"p05={float(np.nanpercentile(dependency, 5)):.6g} p50={float(np.nanpercentile(dependency, 50)):.6g} p95={float(np.nanpercentile(dependency, 95)):.6g}"
        )

        if validate_streaming:
            try:
                rng = np.random.default_rng(0)
                k = int(min(int(validate_n_genes), len(gene_cols)))
                idx = rng.choice(len(gene_cols), size=k, replace=False).tolist()
                cols_check = [gene_cols[i] for i in idx]
                DepMapValidation._log(f"Validation pass enabled: recomputing means for k={k} genes")
                dfv = pd.read_csv(gene_effect_path, usecols=[id_col, *cols_check], low_memory=False)
                if keep_model_ids is not None:
                    dfv = dfv[dfv[id_col].isin(keep_model_ids)]
                recomputed = dfv[cols_check].mean(axis=0, skipna=True).to_numpy(dtype=float, copy=False)
                streamed = gene_effect_means[idx]
                diffs = np.abs(recomputed - streamed)
                DepMapValidation._log(
                    f"Validation diffs: max_abs={float(np.nanmax(diffs)):.6g} mean_abs={float(np.nanmean(diffs)):.6g}"
                )
            except Exception as e:
                DepMapValidation._log(f"Validation pass failed (non-fatal): {type(e).__name__}: {e}")

        df = pd.DataFrame({"Gene": genes, "Dependency": dependency}).dropna(subset=["Dependency"])
        df.to_csv(out_path, index=False)
        DepMapValidation._log(f"Wrote derived dependency table: {out_path} n_rows={len(df)}")
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
        Dependency is defined as -Chronos gene effect (higher = more essential).
        """
        if not os.path.exists(self.depmap_path):
            print(f"Warning: DepMap file {self.depmap_path} not found.")
            return pd.DataFrame(columns=["Gene", "Dependency"])
        try:
            header = pd.read_csv(self.depmap_path, nrows=0, low_memory=False)
        except Exception as e:
            self._log(f"Failed to read DepMap header: {type(e).__name__}: {e}")
            return pd.DataFrame(columns=["Gene", "Dependency"])

        cols = list(header.columns)
        self._log(
            f"DepMap input header: path={self.depmap_path} n_cols={len(cols)} "
            f"first_cols={cols[:5]}"
        )

        if self._is_dependency_table(header):
            df = pd.read_csv(self.depmap_path)
            df["Gene"] = df["Gene"].map(self._normalize_gene_symbol)
            self._log(f"Loaded dependency table: n_rows={len(df)}")
            return df

        wl = set()
        for node, genes in self.node_gene_map.items():
            wl.add(str(node).strip().upper())
            for g in genes:
                wl.add(str(g).strip().upper())
        wl = {g for g in wl if g}
        try:
            import hashlib

            wl_bytes = "\n".join(sorted(wl)).encode("utf-8")
            wl_hash = hashlib.sha256(wl_bytes).hexdigest()[:12]
        except Exception:
            wl_hash = "unknown"

        if self.depmap_model_path and os.path.exists(self.depmap_model_path):
            try:
                model_df = pd.read_csv(self.depmap_model_path, usecols=["ModelID"], low_memory=False)
                model_ids = set(model_df["ModelID"].astype(str).tolist())
                id_col = cols[0]
                ge_ids = pd.read_csv(self.depmap_path, usecols=[id_col], low_memory=False)[id_col].astype(str)
                ge_set = set(ge_ids.tolist())
                self._log(
                    "Model overlap check: "
                    f"gene_effect_models={len(ge_set)} model_csv_models={len(model_ids)} intersection={len(ge_set & model_ids)}"
                )
            except Exception as e:
                self._log(f"Model overlap check failed (non-fatal): {type(e).__name__}: {e}")

        keep_ids = None
        derived_suffix = ""
        if self.depmap_model_path:
            keep_ids_codes = None
            keep_ids_lineage = None
            derived_parts = []

            if self.depmap_oncotree_codes:
                keep_ids_codes = self._select_model_ids_for_oncotree(self.depmap_model_path, self.depmap_oncotree_codes)
                derived_parts.append("oncotree_" + "-".join([self._safe_tag(c) for c in self.depmap_oncotree_codes]))

            if self.depmap_oncotree_lineages:
                keep_ids_lineage = self._select_model_ids_for_lineage(self.depmap_model_path, self.depmap_oncotree_lineages)
                derived_parts.append("lineage_" + "-".join([self._safe_tag(l) for l in self.depmap_oncotree_lineages]))

            if keep_ids_codes is not None and keep_ids_lineage is not None:
                keep_ids = keep_ids_codes & keep_ids_lineage
            elif keep_ids_codes is not None:
                keep_ids = keep_ids_codes
            elif keep_ids_lineage is not None:
                keep_ids = keep_ids_lineage

            if derived_parts:
                derived_suffix = "__" + "__".join(derived_parts)
        derived_suffix = derived_suffix + f"__wl_{wl_hash}"

        cache_dir = os.environ.get("DEPMAP_CACHE_DIR")
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            derived_path = os.path.join(cache_dir, os.path.basename(self.depmap_path) + f".gene_mean{derived_suffix}.csv")
        else:
            derived_path = self.depmap_path + f".gene_mean{derived_suffix}.csv"
        if self.force_rebuild_depmap_cache or not os.path.exists(derived_path):
            self._log(f"Building gene-level dependency table from: {self.depmap_path}{derived_suffix}")
            self._build_dependency_table_from_gene_effect_matrix(
                self.depmap_path,
                derived_path,
                chunksize=500,
                keep_model_ids=keep_ids,
                gene_whitelist=wl,
                progress_every_chunks=int(os.environ.get("DEPMAP_LOG_EVERY_CHUNKS", "50") or "50"),
                validate_streaming=(os.environ.get("DEPMAP_VALIDATE_STREAMING", "0").strip() == "1"),
                validate_n_genes=int(os.environ.get("DEPMAP_VALIDATE_N_GENES", "5") or "5"),
            )

        df = pd.read_csv(derived_path)
        df["Gene"] = df["Gene"].map(self._normalize_gene_symbol)
        self._log(f"Loaded derived dependency table: path={derived_path} n_rows={len(df)}")
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
        meta_map = self._canonicalize_node_gene_map(net.get("metadata", {}).get("node_gene_map"))
        if not meta_map and nodes:
            try:
                from src.data.cancer_network_builder import CancerNetworkBuilder
                inferred = CancerNetworkBuilder.default_node_to_genes_for_nodes(list(nodes))
                meta_map = self._canonicalize_node_gene_map(inferred)
            except Exception:
                meta_map = {}
        
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
            
            delta_d = d_baseline - d_ko
            
            # Get DepMap score if available
            dep_score = self._dep_score_for_node_with_map(gene, meta_map if meta_map else self.node_gene_map)
            expr = self._feature_for_node_with_map(gene, self.depmap_expr_map, meta_map if meta_map else self.node_gene_map)
            cn = self._feature_for_node_with_map(gene, self.depmap_cn_map, meta_map if meta_map else self.node_gene_map)
            pli = self._feature_for_node_with_map(gene, self.gnomad_pli_map, meta_map if meta_map else self.node_gene_map)
            loeuf = self._feature_for_node_with_map(gene, self.gnomad_loeuf_map, meta_map if meta_map else self.node_gene_map)
                
            results[gene] = {
                "delta_d": delta_d,
                "dependency": dep_score,
                "DepMapExpr_mean": expr,
                "DepMapCN_mean": cn,
                "gnomAD_pLI": pli,
                "gnomAD_LOEUF": loeuf,
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
                        "DepMapExpr_mean": metrics.get("DepMapExpr_mean", np.nan),
                        "DepMapCN_mean": metrics.get("DepMapCN_mean", np.nan),
                        "gnomAD_pLI": metrics.get("gnomAD_pLI", np.nan),
                        "gnomAD_LOEUF": metrics.get("gnomAD_LOEUF", np.nan),
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
                "DepMapExpr_mean": float(data.get("DepMapExpr_mean", np.nan)),
                "DepMapCN_mean": float(data.get("DepMapCN_mean", np.nan)),
                "gnomAD_pLI": float(data.get("gnomAD_pLI", np.nan)),
                "gnomAD_LOEUF": float(data.get("gnomAD_LOEUF", np.nan)),
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
        predictors = [
            "Mean_Delta_D",
            "TotalDegree",
            "Betweenness",
            "PageRank",
            "EigenvectorCentrality",
            "DepMapExpr_mean",
            "DepMapCN_mean",
            "gnomAD_pLI",
            "gnomAD_LOEUF",
        ]
        out = {"univariate": {}, "incremental": {}, "conditioned": {}}
        y = df["Dependency"].to_numpy(dtype=float, copy=False)

        for col in predictors:
            if col not in df.columns:
                continue
            x = df[col].to_numpy(dtype=float, copy=False)
            out["univariate"][col] = self._corr_pair(x, y)

        candidate_base = ["TotalDegree", "Betweenness", "DepMapExpr_mean", "DepMapCN_mean", "gnomAD_pLI", "gnomAD_LOEUF"]
        available_base = [c for c in candidate_base if c in df.columns]
        df_mv = df[["Dependency", "Mean_Delta_D", *available_base]].copy()
        df_mv = df_mv.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
        n = int(len(df_mv))
        if n < 6:
            out["incremental"] = {"n": n, "status": "insufficient_rows"}
            return out

        max_p = max(1, n - 4)
        base_cols = available_base[:max_p]
        cols_full = ["Mean_Delta_D", *base_cols]

        def _ridge_loocv(y0: np.ndarray, x0: np.ndarray, lam: float) -> np.ndarray:
            yhat = np.full(len(y0), np.nan, dtype=float)
            for i in range(len(y0)):
                mask = np.ones(len(y0), dtype=bool)
                mask[i] = False
                x_tr = x0[mask]
                y_tr = y0[mask]
                x_te = x0[~mask]
                x_mean = np.nanmean(x_tr, axis=0)
                x_std = np.nanstd(x_tr, axis=0, ddof=0)
                x_std = np.where(x_std == 0, 1.0, x_std)
                x_tr_s = (x_tr - x_mean) / x_std
                x_te_s = (x_te - x_mean) / x_std
                y_mean = float(np.nanmean(y_tr))
                y_tr_c = y_tr - y_mean
                xtx = x_tr_s.T @ x_tr_s
                a = xtx + lam * np.eye(xtx.shape[0], dtype=float)
                b = x_tr_s.T @ y_tr_c
                w = np.linalg.solve(a, b)
                yhat[i] = y_mean + float((x_te_s @ w).ravel()[0])
            return yhat

        def _mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
            d = y_true - y_pred
            d = d[np.isfinite(d)]
            return float(np.mean(d ** 2)) if len(d) else float("nan")

        def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
            mask = np.isfinite(y_true) & np.isfinite(y_pred)
            y_true = y_true[mask]
            y_pred = y_pred[mask]
            if len(y_true) < 3:
                return float("nan")
            ss_res = float(np.sum((y_true - y_pred) ** 2))
            ss_tot = float(np.sum((y_true - float(np.mean(y_true))) ** 2))
            return float(0.0) if ss_tot == 0 else float(1.0 - ss_res / ss_tot)

        y_mv = df_mv["Dependency"].to_numpy(dtype=float, copy=False)
        x_base = df_mv[base_cols].to_numpy(dtype=float, copy=False)
        x_full = df_mv[cols_full].to_numpy(dtype=float, copy=False)

        lam = float(os.environ.get("DEPMAP_RIDGE_LAM", "1.0") or "1.0")
        yhat_base = _ridge_loocv(y_mv, x_base, lam)
        yhat_full = _ridge_loocv(y_mv, x_full, lam)
        mse_base = _mse(y_mv, yhat_base)
        mse_full = _mse(y_mv, yhat_full)
        improvement = float(mse_base - mse_full)
        r2_base = _r2(y_mv, yhat_base)
        r2_full = _r2(y_mv, yhat_full)

        n_perm = int(os.environ.get("DEPMAP_PERM_N", "5000") or "5000")
        rng = np.random.default_rng(int(random_state))
        imp_null = []
        for _ in range(n_perm):
            y_perm = rng.permutation(y_mv)
            yb = _ridge_loocv(y_perm, x_base, lam)
            yf = _ridge_loocv(y_perm, x_full, lam)
            imp_null.append(float(_mse(y_perm, yb) - _mse(y_perm, yf)))
        imp_null = np.array(imp_null, dtype=float)
        p_perm = float((np.sum(imp_null >= improvement) + 1.0) / (len(imp_null) + 1.0))

        out["incremental"] = {
            "n": int(n),
            "ridge_lam": lam,
            "base_cols": base_cols,
            "mse_base_loocv": mse_base,
            "mse_full_loocv": mse_full,
            "mse_improvement": improvement,
            "r2_base_loocv": r2_base,
            "r2_full_loocv": r2_full,
            "r2_delta_loocv": float(r2_full - r2_base) if np.isfinite(r2_base) and np.isfinite(r2_full) else float("nan"),
            "perm_n": int(n_perm),
            "perm_p_improvement": p_perm,
            "perm_null_improvement": imp_null.tolist(),
        }

        y_resid = y_mv - yhat_base
        x_dd = df_mv["Mean_Delta_D"].to_numpy(dtype=float, copy=False)
        mask = np.isfinite(x_dd) & np.isfinite(y_resid)
        x_dd = x_dd[mask]
        y_resid = y_resid[mask]
        n_resid = int(len(x_dd))
        if n_resid >= 3:
            pr, pp = stats.pearsonr(x_dd, y_resid)
            sr, sp = stats.spearmanr(x_dd, y_resid)
            rng2 = np.random.default_rng(int(random_state) + 1)
            null = []
            for _ in range(n_perm):
                yr = rng2.permutation(y_resid)
                null.append(float(stats.spearmanr(x_dd, yr).statistic))
            null = np.asarray(null, dtype=float)
            null = null[np.isfinite(null)]
            p_abs = float((np.sum(np.abs(null) >= abs(float(sr))) + 1.0) / (len(null) + 1.0)) if len(null) else float("nan")
            out["conditioned"] = {
                "n": int(n_resid),
                "endpoint": "dependency_residual",
                "residualizer": "ridge_loocv",
                "ridge_lam": lam,
                "base_cols": base_cols,
                "pearson_r": float(pr),
                "pearson_p": float(pp),
                "spearman_rho": float(sr),
                "spearman_p": float(sp),
                "perm_n": int(n_perm),
                "perm_p_abs_spearman": p_abs,
                "perm_null_spearman": null.tolist(),
            }
        else:
            out["conditioned"] = {"n": int(n_resid), "status": "insufficient_rows"}
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
            
        x = np.asarray(delta_ds, dtype=float)
        y = np.asarray(deps, dtype=float)

        mask = ~(np.isnan(x) | np.isnan(y))
        x = x[mask]
        y = y[mask]
        n = int(len(x))
        if n < 3:
            return CorrelationResult(
                {"n": n, "rho": 0.0, "pval": 1.0, "mi_bits": 0.0, "mi_interpretation": "Insufficient Data"}
            )
        
        # Pearson
        corr, pval = stats.pearsonr(x, y)

        spearman_corr, spearman_pval = stats.spearmanr(x, y)
        
        # Mutual Information
        mi_res = MutualInformationAnalyzer.compute_mutual_information(x.tolist(), y.tolist(), discrete_y=False)
        
        out = CorrelationResult({
            "n": n,
            'rho': corr,
            'pval': pval,
            'spearman_rho': spearman_corr,
            'spearman_pval': spearman_pval,
            'mi_bits': mi_res['MI_bits'],
            'mi_interpretation': mi_res['interpretation']
        })
        if not isinstance(results, dict) and isinstance(results, pd.DataFrame):
            try:
                out["predictor_benchmark"] = self.compare_predictors(results)
            except Exception:
                pass
        return out

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
        ax.set_xlabel("Mean ΔD (node removal)")
        ax.set_ylabel("DepMap essentiality (−gene effect)")
        ax.set_title(f"ΔD vs DepMap (n={len(x)})")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return out_path

    @staticmethod
    def save_benchmark_plot(df: pd.DataFrame, stats_res: dict, out_path: str) -> str | None:
        if plt is None:
            return None
        if df is None or len(df) == 0:
            return None
        bench = None
        if isinstance(stats_res, dict):
            bench = stats_res.get("predictor_benchmark", {}).get("incremental", {})
        null = bench.get("perm_null_improvement") if isinstance(bench, dict) else None
        obs = bench.get("mse_improvement") if isinstance(bench, dict) else None
        if null is None or obs is None:
            return None
        null = np.asarray(null, dtype=float)
        null = null[np.isfinite(null)]
        if null.size == 0 or not np.isfinite(float(obs)):
            return None
        fig = plt.figure(figsize=(8, 3.6), dpi=200)
        ax1 = fig.add_subplot(1, 2, 1)
        x = df["Mean_Delta_D"].to_numpy(dtype=float, copy=False)
        y = df["Dependency"].to_numpy(dtype=float, copy=False)
        mask = ~(np.isnan(x) | np.isnan(y))
        ax1.scatter(x[mask], y[mask], s=35, alpha=0.85)
        ax1.set_xlabel("Mean ΔD (node removal)")
        ax1.set_ylabel("DepMap dependency (−gene effect)")
        ax1.set_title("Pilot scatter")

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.hist(null, bins=40, color="#4C72B0", alpha=0.85, density=True)
        ax2.axvline(float(obs), color="#C44E52", linewidth=2.0)
        ax2.set_xlabel("LOOCV MSE improvement (base − full)")
        ax2.set_ylabel("Density")
        p = bench.get("perm_p_improvement", np.nan)
        ax2.set_title(f"Permutation null (p={p:.3g})")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return out_path

    @staticmethod
    def save_conditioned_plot(df: pd.DataFrame, stats_res: dict, out_path: str) -> str | None:
        if plt is None:
            return None
        if df is None or len(df) == 0:
            return None
        bench = None
        if isinstance(stats_res, dict):
            bench = stats_res.get("predictor_benchmark", {}).get("conditioned", {})
        null = bench.get("perm_null_spearman") if isinstance(bench, dict) else None
        obs = bench.get("spearman_rho") if isinstance(bench, dict) else None
        if null is None or obs is None:
            return None
        null = np.asarray(null, dtype=float)
        null = null[np.isfinite(null)]
        if null.size == 0 or not np.isfinite(float(obs)):
            return None
        fig = plt.figure(figsize=(8, 3.6), dpi=200)
        ax1 = fig.add_subplot(1, 2, 1)
        x = df["Mean_Delta_D"].to_numpy(dtype=float, copy=False)
        y = df["Dependency"].to_numpy(dtype=float, copy=False)
        mask = ~(np.isnan(x) | np.isnan(y))
        ax1.scatter(x[mask], y[mask], s=35, alpha=0.85)
        ax1.set_xlabel("Mean ΔD (node removal)")
        ax1.set_ylabel("DepMap dependency (raw proxy)")
        ax1.set_title("Raw endpoint (reference)")

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.hist(np.abs(null), bins=40, color="#4C72B0", alpha=0.85, density=True)
        ax2.axvline(abs(float(obs)), color="#C44E52", linewidth=2.0)
        ax2.set_xlabel("|Spearman ρ| under null")
        ax2.set_ylabel("Density")
        p = bench.get("perm_p_abs_spearman", np.nan)
        ax2.set_title(f"Conditioned endpoint (p={p:.3g})")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return out_path

def _audit_depmap_release(depmap_dir: str, model_csv_path: str | None, files: list[str]) -> int:
    DepMapValidation._log(f"DepMap audit start: depmap_dir={depmap_dir}")
    model_ids: set[str] | None = None
    if model_csv_path and os.path.exists(model_csv_path):
        try:
            dfm = pd.read_csv(model_csv_path, usecols=["ModelID"], low_memory=False)
            model_ids = set(dfm["ModelID"].astype(str).tolist())
            DepMapValidation._log(f"Loaded Model.csv IDs: n={len(model_ids)}")
        except Exception as e:
            DepMapValidation._log(f"Failed loading Model.csv IDs (non-fatal): {type(e).__name__}: {e}")

    failures = 0
    for fname in files:
        path = os.path.join(depmap_dir, fname)
        if not os.path.exists(path):
            DepMapValidation._log(f"Missing file: {path}")
            failures += 1
            continue

        try:
            size_bytes = os.path.getsize(path)
        except Exception:
            size_bytes = -1

        try:
            header = pd.read_csv(path, nrows=0, low_memory=False)
            cols = list(header.columns)
        except Exception as e:
            DepMapValidation._log(f"Unreadable header: path={path} err={type(e).__name__}: {e}")
            failures += 1
            continue

        DepMapValidation._log(f"File: {fname} size_bytes={size_bytes} n_cols={len(cols)} first_cols={cols[:5]}")
        if len(cols) < 2:
            DepMapValidation._log(f"Schema warning: <2 columns for {fname}")
            failures += 1
            continue

        id_col = cols[0]
        try:
            ids_preview = pd.read_csv(path, usecols=[id_col], nrows=2000, low_memory=False)[id_col].astype(str)
            uniq = int(ids_preview.nunique(dropna=False))
            DepMapValidation._log(
                f"ID column: name={id_col!r} preview_rows={len(ids_preview)} unique_ids={uniq} first_ids={ids_preview.head(3).tolist()}"
            )
            if model_ids is not None:
                s = set(ids_preview.tolist())
                DepMapValidation._log(
                    f"ID overlap with Model.csv: intersection={len(s & model_ids)}/{len(s)} "
                    f"({(len(s & model_ids) / max(len(s), 1)):.3f})"
                )
        except Exception as e:
            DepMapValidation._log(f"ID sampling failed (non-fatal): file={fname} err={type(e).__name__}: {e}")

        sample_cols = cols[1:6]
        try:
            dfv = pd.read_csv(path, usecols=[id_col, *sample_cols], nrows=200, low_memory=False)
            numeric_ok = 0
            for c in sample_cols:
                v = pd.to_numeric(dfv[c], errors="coerce")
                frac = float(np.mean(~np.isnan(v.to_numpy(dtype=float, copy=False))))
                if frac > 0.5:
                    numeric_ok += 1
                DepMapValidation._log(f"Sample col parse: file={fname} col={c!r} numeric_frac={frac:.3f}")
            if numeric_ok == 0 and len(cols) > 20:
                DepMapValidation._log(f"Schema note: wide file with low numeric parse rate in sample cols (may be categorical): {fname}")
        except Exception as e:
            DepMapValidation._log(f"Value sampling failed (non-fatal): file={fname} err={type(e).__name__}: {e}")

    DepMapValidation._log(f"DepMap audit complete: failures={failures}")
    return 0 if failures == 0 else 2

if __name__ == "__main__":
    DATA_DIR = os.environ.get("DEPMAP_DATA_DIR", "data/cancer/patients")
    DEPMAP_PATH = os.environ.get("DEPMAP_PATH", "data/depmap/CRISPRGeneEffect.csv")
    DEPMAP_MODEL_PATH = os.environ.get("DEPMAP_MODEL_PATH")
    DEPMAP_ONCOTREE_CODES = os.environ.get("DEPMAP_ONCOTREE_CODES")
    DEPMAP_ONCOTREE_LINEAGES = os.environ.get("DEPMAP_ONCOTREE_LINEAGES")
    DEPMAP_ONCOTREE_LINEAGE_SWEEP = os.environ.get("DEPMAP_ONCOTREE_LINEAGE_SWEEP") or os.environ.get("DEPMAP_ONCOTREE_LINEAGES_SWEEP")
    N_PATIENTS = os.environ.get("DEPMAP_N_PATIENTS")
    RECURSIVE = os.environ.get("DEPMAP_RECURSIVE", "0").strip() == "1"
    FORCE_REBUILD = os.environ.get("DEPMAP_FORCE_REBUILD", "0").strip() == "1"
    OUT_PREFIX = os.environ.get("DEPMAP_OUT_PREFIX", "results/cancer/depmap_validation")
    AUDIT = os.environ.get("DEPMAP_AUDIT", "0").strip() == "1"
    AUDIT_DIR = os.environ.get("DEPMAP_AUDIT_DIR", "data/depmap")
    AUDIT_FILES = os.environ.get("DEPMAP_AUDIT_FILES")

    def first_existing(paths: list[str | None]) -> str | None:
        for p in paths:
            if not p:
                continue
            if os.path.exists(p):
                return p
        return None

    def infer_depmap_from_release_dir(release_dir: str) -> tuple[str | None, str | None]:
        rd = str(release_dir)
        gene_effect = first_existing([
            os.path.join(rd, "CRISPRGeneEffect.csv"),
            os.path.join(rd, "raw", "CRISPRGeneEffect.csv"),
        ])
        model = first_existing([
            os.path.join(rd, "Model.csv"),
            os.path.join(rd, "raw", "Model.csv"),
        ])
        return gene_effect, model

    if not os.path.exists(DEPMAP_PATH):
        release_dir = os.environ.get("DEPMAP_RELEASE_DIR")
        if release_dir:
            inferred_path, inferred_model = infer_depmap_from_release_dir(release_dir)
            if inferred_path:
                DEPMAP_PATH = inferred_path
                DEPMAP_MODEL_PATH = DEPMAP_MODEL_PATH or inferred_model
        else:
            for candidate in ("data/depmap", "data/depmap/24Q4"):
                inferred_path, inferred_model = infer_depmap_from_release_dir(candidate)
                if inferred_path:
                    DEPMAP_PATH = inferred_path
                    DEPMAP_MODEL_PATH = DEPMAP_MODEL_PATH or inferred_model
                    break

    if AUDIT:
        model_csv = DEPMAP_MODEL_PATH or os.path.join(AUDIT_DIR, "Model.csv")
        if AUDIT_FILES:
            audit_files = [f.strip() for f in str(AUDIT_FILES).split(",") if f.strip()]
        else:
            audit_files = [
                "CRISPRGeneEffect.csv",
                "CRISPRGeneDependency.csv",
                "OmicsExpressionProteinCodingGenesTPMLogp1.csv",
                "OmicsCNGene.csv",
                "OmicsSomaticMutationsProfile.csv",
                "OmicsFusionFiltered.csv",
            ]
        sys.exit(_audit_depmap_release(AUDIT_DIR, model_csv, audit_files))

    allow_synth = os.environ.get("DEPMAP_ALLOW_SYNTHETIC", "0").strip() == "1"
    if not os.path.exists(DEPMAP_PATH):
        if not allow_synth:
            raise SystemExit(
                "DepMap input not found. Set DEPMAP_PATH to a dependency table (Gene,Dependency) or to CRISPRGeneEffect.csv, "
                "or set DEPMAP_RELEASE_DIR to a DepMap release directory. For smoke tests only, set DEPMAP_ALLOW_SYNTHETIC=1."
            )

        os.makedirs("results/cancer", exist_ok=True)
        synth_path = "results/cancer/depmap_synthetic.csv"
        print(f"DepMap input not found. Generating synthetic dependency table at {synth_path} (smoke test only).")
        sample_file = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")][0]
        with open(os.path.join(DATA_DIR, sample_file)) as f:
            genes = json.load(f)["nodes"]
        df = pd.DataFrame({"Gene": genes, "Dependency": np.random.normal(0.5, 1.0, len(genes))})
        df.to_csv(synth_path, index=False)
        DEPMAP_PATH = synth_path
        
    oncotree_codes = None
    if DEPMAP_ONCOTREE_CODES:
        oncotree_codes = [c.strip() for c in str(DEPMAP_ONCOTREE_CODES).split(",") if c.strip()]

    lineages = None
    if DEPMAP_ONCOTREE_LINEAGES:
        lineages = [l.strip() for l in str(DEPMAP_ONCOTREE_LINEAGES).split(",") if l.strip()]

    n_patients = int(N_PATIENTS) if N_PATIENTS else None

    if DEPMAP_ONCOTREE_LINEAGE_SWEEP:
        sweep_lineages = [l.strip() for l in str(DEPMAP_ONCOTREE_LINEAGE_SWEEP).split(",") if l.strip()]
        rows = []
        for lin in sweep_lineages:
            keep_ids = None
            if DEPMAP_MODEL_PATH:
                keep_ids = DepMapValidation._select_model_ids_for_lineage(DEPMAP_MODEL_PATH, [lin])
            v = DepMapValidation(
                DATA_DIR,
                DEPMAP_PATH,
                depmap_model_path=DEPMAP_MODEL_PATH,
                depmap_oncotree_codes=oncotree_codes,
                depmap_oncotree_lineages=[lin],
                force_rebuild_depmap_cache=FORCE_REBUILD,
            )
            cohort_results = v.run_cohort_analysis(n_patients=n_patients, recursive=RECURSIVE)
            try:
                x = cohort_results["Mean_Delta_D"].to_numpy(dtype=float, copy=False)
                y = cohort_results["Dependency"].to_numpy(dtype=float, copy=False)
                n_nodes_used = int(np.sum(~(np.isnan(x) | np.isnan(y))))
            except Exception:
                n_nodes_used = 0
            stats_res = v.compute_correlation(cohort_results)
            inc = {}
            try:
                inc = dict(stats_res.get("predictor_benchmark", {}).get("incremental", {}) or {})
            except Exception:
                inc = {}
            cond = {}
            try:
                cond = dict(stats_res.get("predictor_benchmark", {}).get("conditioned", {}) or {})
            except Exception:
                cond = {}
            row = {
                "Lineage": str(lin),
                "N_DepMap_Models": int(len(keep_ids)) if keep_ids is not None else 0,
                "N_Nodes_Used": int(n_nodes_used),
                "Pearson_r": float(stats_res.get("rho", 0.0)),
                "Pearson_p": float(stats_res.get("pval", 1.0)),
                "Spearman_rho": float(stats_res.get("spearman_rho", 0.0)),
                "Spearman_p": float(stats_res.get("spearman_pval", 1.0)),
                "MI_bits": float(stats_res.get("mi_bits", 0.0)),
                "MI_interpretation": str(stats_res.get("mi_interpretation", "")),
                "MSE_improvement": float(inc.get("mse_improvement", float("nan"))),
                "Perm_p_improvement": float(inc.get("perm_p_improvement", float("nan"))),
                "LOOCV_R2_delta": float(inc.get("r2_delta_loocv", float("nan"))),
                "Conditioned_n": int(cond.get("n", 0)) if isinstance(cond.get("n", None), (int, float)) else 0,
                "Conditioned_spearman_rho": float(cond.get("spearman_rho", float("nan"))),
                "Conditioned_perm_p_abs_spearman": float(cond.get("perm_p_abs_spearman", float("nan"))),
            }
            rows.append(row)

        out_csv = OUT_PREFIX + "__lineage_sweep_summary.csv"
        out_json = OUT_PREFIX + "__lineage_sweep_summary.json"
        df_out = pd.DataFrame(rows)
        df_out.to_csv(out_csv, index=False)
        with open(out_json, "w") as f:
            json.dump({"rows": rows}, f, indent=4)
        print(f"Wrote {out_csv}")
        print(f"Wrote {out_json}")
        try:
            if plt is not None and len(df_out):
                fig = plt.figure(figsize=(9.5, 3.5), dpi=200)
                ax1 = fig.add_subplot(1, 2, 1)
                ax2 = fig.add_subplot(1, 2, 2)

                xs = np.arange(len(df_out))
                ax1.bar(xs, df_out["Spearman_rho"].to_numpy(dtype=float, copy=False), color="#4C72B0", alpha=0.9)
                ax1.axhline(0.0, color="gray", linestyle="--", linewidth=1.0)
                ax1.set_xticks(xs)
                ax1.set_xticklabels(df_out["Lineage"].astype(str).tolist(), rotation=45, ha="right")
                ax1.set_ylabel("Spearman ρ (ΔD vs dependency)")
                ax1.set_title("Lineage sweep: association")

                ax2.bar(xs, df_out["Perm_p_improvement"].to_numpy(dtype=float, copy=False), color="#55A868", alpha=0.9)
                ax2.axhline(0.05, color="gray", linestyle="--", linewidth=1.0)
                ax2.set_xticks(xs)
                ax2.set_xticklabels(df_out["Lineage"].astype(str).tolist(), rotation=45, ha="right")
                ax2.set_ylabel("Permutation p (ΔD incremental)")
                ax2.set_title("Lineage sweep: incremental value")

                fig.tight_layout()
                out_png = OUT_PREFIX + "__lineage_sweep.png"
                fig.savefig(out_png)
                plt.close(fig)
                print(f"Wrote {out_png}")
        except Exception:
            pass
        sys.exit(0)

    validator = DepMapValidation(
        DATA_DIR,
        DEPMAP_PATH,
        depmap_model_path=DEPMAP_MODEL_PATH,
        depmap_oncotree_codes=oncotree_codes,
        depmap_oncotree_lineages=lineages,
        force_rebuild_depmap_cache=FORCE_REBUILD,
    )
    cohort_results = validator.run_cohort_analysis(n_patients=n_patients, recursive=RECURSIVE)
    
    # Save
    out_csv = OUT_PREFIX + ".csv"
    out_dir = os.path.dirname(out_csv)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
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

    bench_path = OUT_PREFIX + "_benchmark.png"
    saved_bench = DepMapValidation.save_benchmark_plot(cohort_results, dict(stats_res), bench_path)
    if saved_bench:
        print(f"Benchmark plot saved to {saved_bench}")

    conditioned_path = OUT_PREFIX + "_conditioned.png"
    saved_cond = DepMapValidation.save_conditioned_plot(cohort_results, dict(stats_res), conditioned_path)
    if saved_cond:
        print(f"Conditioned plot saved to {saved_cond}")
    
