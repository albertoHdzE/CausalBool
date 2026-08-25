from __future__ import annotations

import csv
import gzip
import json
import re
import tarfile
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GeoSeriesMatrix:
    series_id: str
    metadata: pd.DataFrame
    expression: pd.DataFrame | None


TH17_SERIES_CONTEXT: dict[str, dict[str, str]] = {
    "GSE43948": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
        "assay_modality": "rna_seq",
        "experimental_axis": "perturbation_screen",
    },
    "GSE43949": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
        "assay_modality": "chip_seq",
        "experimental_axis": "chip_binding",
    },
    "GSE43955": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
        "assay_modality": "microarray",
        "experimental_axis": "time_course",
    },
    "GSE43969": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
        "assay_modality": "microarray",
        "experimental_axis": "genotype_time_course",
    },
    "GSE43956": {
        "study_arm": "wu_sgk1_pathogenicity",
        "source_publication": "Wu et al. 2013",
        "biological_program": "sgk1_il23_pathogenicity",
        "assay_modality": "microarray",
        "experimental_axis": "sgk1_pathogenicity",
    },
    "GSE43957": {
        "study_arm": "wu_sgk1_pathogenicity",
        "source_publication": "Wu et al. 2013",
        "biological_program": "sgk1_salt_pathogenicity",
        "assay_modality": "microarray",
        "experimental_axis": "salt_pathogenicity",
    },
}


def _series_context(series_id: str) -> dict[str, str]:
    return TH17_SERIES_CONTEXT.get(series_id, {})


def _annotate_dataset_context(dataset: GeoSeriesMatrix) -> GeoSeriesMatrix:
    context = _series_context(dataset.series_id)
    if not context:
        return dataset

    metadata = dataset.metadata.copy()
    for key, value in context.items():
        metadata[key] = value
    return GeoSeriesMatrix(series_id=dataset.series_id, metadata=metadata, expression=dataset.expression)


def _normalize_key(raw: str) -> str:
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def _parse_line(line: str) -> list[str]:
    return next(csv.reader([line.rstrip("\n")], delimiter="\t", quotechar='"'))


def _coerce_length(values: list[str], expected: int) -> list[str]:
    if len(values) == expected:
        return values
    if len(values) < expected:
        return values + [""] * (expected - len(values))
    return values[:expected]


def _split_characteristic(value: str) -> tuple[str, str]:
    if ":" not in value:
        return "value", value.strip()
    key, payload = value.split(":", 1)
    return _normalize_key(key), payload.strip()


def _build_sample_metadata(sample_ids: list[str], sample_fields: dict[str, list[list[str]]]) -> pd.DataFrame:
    metadata = pd.DataFrame(index=pd.Index(sample_ids, name="sample_id"))

    for raw_key, rows in sample_fields.items():
        key = raw_key.removeprefix("!Sample_")
        normalized_key = _normalize_key(key)

        if normalized_key == "characteristics_ch1":
            grouped: dict[str, list[str]] = {}
            for position, values in enumerate(rows, start=1):
                coerced = _coerce_length(values, len(sample_ids))
                parsed = [_split_characteristic(value) for value in coerced]
                keys = {name for name, _ in parsed}
                if len(keys) == 1 and "value" not in keys:
                    group_key = next(iter(keys))
                else:
                    group_key = f"characteristic_{position}"
                grouped[group_key] = [payload for _, payload in parsed]
            for group_key, values in grouped.items():
                metadata[group_key] = values
            continue

        for position, values in enumerate(rows, start=1):
            column_name = normalized_key if len(rows) == 1 else f"{normalized_key}_{position}"
            metadata[column_name] = _coerce_length(values, len(sample_ids))

    if "geo_accession" in metadata.columns:
        metadata.insert(0, "geo_accession", metadata.pop("geo_accession"))
        if metadata["geo_accession"].tolist() != sample_ids:
            raise ValueError("Sample accessions in metadata do not match the expression-table header.")

    if "time_hr" in metadata.columns:
        metadata["time_hr"] = metadata["time_hr"].astype(float)

    return metadata.reset_index()


def parse_geo_series_matrix(path: Path) -> GeoSeriesMatrix:
    sample_fields: dict[str, list[list[str]]] = {}
    table_header: list[str] | None = None
    feature_ids: list[str] = []
    rows: list[list[float]] = []
    in_table = False

    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not in_table:
                if line.startswith("!series_matrix_table_begin"):
                    in_table = True
                    continue
                if line.startswith("!Sample_"):
                    parsed = _parse_line(line)
                    sample_fields.setdefault(parsed[0], []).append(parsed[1:])
                continue

            if line.startswith("!series_matrix_table_end"):
                break

            parsed = _parse_line(line)
            if table_header is None:
                table_header = parsed
                continue

            feature_ids.append(parsed[0])
            rows.append([float(value) for value in parsed[1:]])

    if table_header is None:
        raise ValueError(f"No expression table found in {path}")

    sample_ids = table_header[1:]
    metadata = _build_sample_metadata(sample_ids, sample_fields)
    expression: pd.DataFrame | None
    if rows:
        expression = pd.DataFrame(np.asarray(rows, dtype=float), index=feature_ids, columns=sample_ids)
        expression.index.name = "id_ref"
    else:
        expression = None

    return GeoSeriesMatrix(
        series_id=path.name.replace("_series_matrix.txt.gz", ""),
        metadata=metadata,
        expression=expression,
    )


def _write_dataset_payload(dataset: GeoSeriesMatrix, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "sample_metadata.csv"
    features_path = output_dir / "feature_metadata.csv"
    expression_path = output_dir / "expression_matrix.tsv.gz"
    summary_path = output_dir / "summary.json"

    dataset.metadata.to_csv(metadata_path, index=False)
    if dataset.expression is not None:
        pd.DataFrame({"id_ref": dataset.expression.index}).to_csv(features_path, index=False)
        dataset.expression.to_csv(expression_path, sep="\t", compression="gzip")

    data_row_count_values = []
    if "data_row_count" in dataset.metadata.columns:
        numeric_counts = pd.to_numeric(dataset.metadata["data_row_count"], errors="coerce").dropna()
        data_row_count_values = sorted(int(value) for value in numeric_counts.unique().tolist())

    sample_types = []
    if "type" in dataset.metadata.columns:
        sample_types = sorted(dataset.metadata["type"].dropna().astype(str).unique().tolist())

    library_strategies = []
    if "library_strategy" in dataset.metadata.columns:
        library_strategies = sorted(dataset.metadata["library_strategy"].dropna().astype(str).unique().tolist())

    context = _series_context(dataset.series_id)
    summary = {
        "series_id": dataset.series_id,
        "study_arm": context.get("study_arm"),
        "source_publication": context.get("source_publication"),
        "biological_program": context.get("biological_program"),
        "sample_count": int(dataset.metadata.shape[0]),
        "feature_count": int(dataset.expression.shape[0]) if dataset.expression is not None else 0,
        "has_expression_matrix": dataset.expression is not None,
        "sample_ids": dataset.metadata["sample_id"].tolist(),
        "time_hr_min": float(dataset.metadata["time_hr"].min()) if "time_hr" in dataset.metadata.columns else None,
        "time_hr_max": float(dataset.metadata["time_hr"].max()) if "time_hr" in dataset.metadata.columns else None,
        "treatments": sorted(dataset.metadata["treatment"].dropna().astype(str).unique().tolist()) if "treatment" in dataset.metadata.columns else [],
        "genotypes": sorted(dataset.metadata["genotype"].dropna().astype(str).unique().tolist()) if "genotype" in dataset.metadata.columns else [],
        "sample_types": sample_types,
        "library_strategies": library_strategies,
        "reported_data_row_count_values": data_row_count_values,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _infer_asset_kind(name: str) -> str:
    lowered = name.lower()
    if lowered.endswith(".rsem.txt.gz"):
        return "rsem_gene_expression"
    if lowered.endswith(".tdf"):
        return "igv_tdf_track"
    if lowered.endswith(".cel.gz"):
        return "affymetrix_cel"
    if lowered.endswith(".tar"):
        return "tar_archive"
    return "other"


def _extract_geo_accession(name: str) -> str | None:
    match = re.match(r"^(GSM\d+)", name)
    return match.group(1) if match is not None else None


def _build_sample_to_series_map(raw_dir: Path) -> dict[str, str]:
    sample_to_series: dict[str, str] = {}
    for path in sorted(raw_dir.glob("GSE*_series_matrix.txt.gz")):
        dataset = parse_geo_series_matrix(path)
        for sample_id in dataset.metadata["sample_id"].astype(str):
            sample_to_series[sample_id] = dataset.series_id
    return sample_to_series


def prepare_geo_supplementary_manifest(
    filelist_path: Path,
    output_dir: Path,
    sample_to_series: dict[str, str],
) -> dict:
    if not filelist_path.exists():
        raise FileNotFoundError(f"Could not find {filelist_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    with filelist_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            name = (row.get("Name") or "").strip()
            geo_accession = _extract_geo_accession(name)
            resolved_series = sample_to_series.get(geo_accession) if geo_accession is not None else None
            size_bytes = int(row["Size"]) if row.get("Size") else 0
            records.append(
                {
                    "entry_scope": (row.get("#Archive/File") or "").strip(),
                    "name": name,
                    "timestamp": (row.get("Time") or "").strip(),
                    "size_bytes": size_bytes,
                    "declared_type": (row.get("Type") or "").strip(),
                    "asset_kind": _infer_asset_kind(name),
                    "geo_accession": geo_accession,
                    "resolved_series_id": resolved_series,
                }
            )

    manifest = pd.DataFrame.from_records(records)
    manifest.to_csv(output_dir / "manifest.csv", index=False)

    asset_kind_counts = (
        manifest.groupby("asset_kind").size().sort_index().astype(int).to_dict() if not manifest.empty else {}
    )
    resolved_series_counts = (
        manifest.loc[manifest["resolved_series_id"].notna()].groupby("resolved_series_id").size().sort_index().astype(int).to_dict()
        if not manifest.empty
        else {}
    )
    resolved_study_arm_counts = (
        manifest.loc[manifest["resolved_series_id"].notna(), "resolved_series_id"]
        .map(lambda value: _series_context(str(value)).get("study_arm", "unclassified"))
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict()
        if not manifest.empty
        else {}
    )
    unresolved_sample_accessions = (
        sorted(manifest.loc[manifest["geo_accession"].notna() & manifest["resolved_series_id"].isna(), "geo_accession"].unique().tolist())
        if not manifest.empty
        else []
    )

    summary = {
        "series_id": filelist_path.name.replace("_filelist.txt", ""),
        "entry_count": int(manifest.shape[0]),
        "archive_entry_count": int((manifest["entry_scope"] == "Archive").sum()) if not manifest.empty else 0,
        "file_entry_count": int((manifest["entry_scope"] == "File").sum()) if not manifest.empty else 0,
        "asset_kind_counts": asset_kind_counts,
        "resolved_series_counts": resolved_series_counts,
        "resolved_study_arm_counts": resolved_study_arm_counts,
        "unresolved_sample_accessions": unresolved_sample_accessions,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_geo_tar_manifest(
    tar_path: Path,
    output_dir: Path,
    sample_to_series: dict[str, str],
) -> dict:
    if not tar_path.exists():
        raise FileNotFoundError(f"Could not find {tar_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    with tarfile.open(tar_path) as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            if not member.isfile():
                continue
            name = member.name
            geo_accession = _extract_geo_accession(name)
            resolved_series = sample_to_series.get(geo_accession) if geo_accession is not None else None
            records.append(
                {
                    "entry_scope": "File",
                    "name": name,
                    "timestamp": "",
                    "size_bytes": int(member.size),
                    "declared_type": Path(name).suffix.removeprefix(".").upper(),
                    "asset_kind": _infer_asset_kind(name),
                    "geo_accession": geo_accession,
                    "resolved_series_id": resolved_series,
                }
            )

    manifest = pd.DataFrame.from_records(records)
    manifest.to_csv(output_dir / "manifest.csv", index=False)

    asset_kind_counts = (
        manifest.groupby("asset_kind").size().sort_index().astype(int).to_dict() if not manifest.empty else {}
    )
    resolved_series_counts = (
        manifest.loc[manifest["resolved_series_id"].notna()].groupby("resolved_series_id").size().sort_index().astype(int).to_dict()
        if not manifest.empty
        else {}
    )
    resolved_study_arm_counts = (
        manifest.loc[manifest["resolved_series_id"].notna(), "resolved_series_id"]
        .map(lambda value: _series_context(str(value)).get("study_arm", "unclassified"))
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict()
        if not manifest.empty
        else {}
    )
    unresolved_sample_accessions = (
        sorted(manifest.loc[manifest["geo_accession"].notna() & manifest["resolved_series_id"].isna(), "geo_accession"].unique().tolist())
        if not manifest.empty
        else []
    )

    summary = {
        "series_id": tar_path.name.replace("_RAW.tar", ""),
        "archive_file_name": tar_path.name,
        "entry_count": int(manifest.shape[0]),
        "archive_entry_count": 1,
        "file_entry_count": int(manifest.shape[0]),
        "asset_kind_counts": asset_kind_counts,
        "resolved_series_counts": resolved_series_counts,
        "resolved_study_arm_counts": resolved_study_arm_counts,
        "unresolved_sample_accessions": unresolved_sample_accessions,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _parse_gse43948_filename(name: str) -> dict[str, object]:
    stem = name.removesuffix(".rsem.txt.gz")
    parts = stem.split("_")
    sample_id = parts[0]
    time_index = next((idx for idx, part in enumerate(parts) if part.endswith("h") and part[:-1].isdigit()), None)
    if time_index is not None:
        time_hr = float(parts[time_index][:-1])
        target_raw = parts[time_index + 1]
    else:
        # The archived filenames are not fully uniform, but the GEO series design is a 48 h screen.
        time_hr = 48.0
        target_raw = parts[-3] if len(parts) >= 4 and parts[-3].lower() == "nt" else parts[-2]
    is_control = target_raw.lower() == "nt"
    return {
        "sample_id": sample_id,
        "source_filename": name,
        "time_hr": time_hr,
        "perturbation_target_raw": target_raw,
        "perturbation_target": "NT" if is_control else target_raw.upper(),
        "is_non_targeting_control": is_control,
    }


def prepare_th17_perturbation_rnaseq(supp_dir: Path, output_dir: Path) -> dict:
    tar_path = supp_dir / "GSE43948_RAW.tar"
    if not tar_path.exists():
        raise FileNotFoundError(f"Could not find {tar_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    sample_records: list[dict[str, object]] = []
    matrices: list[pd.Series] = []
    context = _series_context("GSE43948")

    with tarfile.open(tar_path) as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            if not member.name.endswith(".rsem.txt.gz"):
                continue
            metadata = _parse_gse43948_filename(member.name)
            payload = archive.extractfile(member)
            if payload is None:
                continue
            text = gzip.decompress(payload.read()).decode("utf-8", "ignore")
            df = pd.read_csv(
                BytesIO(text.encode("utf-8")),
                sep="\t",
                header=None,
                names=["gene_symbol", metadata["sample_id"]],
            )
            series = df.set_index("gene_symbol")[metadata["sample_id"]]
            matrices.append(series)
            sample_records.append({**metadata, **context})

    if not matrices:
        raise ValueError(f"No .rsem.txt.gz members found in {tar_path}")

    expression = pd.concat(matrices, axis=1)
    expression.index.name = "gene_symbol"
    metadata = pd.DataFrame(sample_records)

    metadata.to_csv(output_dir / "sample_metadata.csv", index=False)
    pd.DataFrame({"gene_symbol": expression.index}).to_csv(output_dir / "feature_metadata.csv", index=False)
    expression.to_csv(output_dir / "expression_matrix.tsv.gz", sep="\t", compression="gzip")

    targets = sorted(metadata.loc[~metadata["is_non_targeting_control"], "perturbation_target"].unique().tolist())
    summary = {
        "series_id": "GSE43948",
        "study_arm": context.get("study_arm"),
        "source_publication": context.get("source_publication"),
        "biological_program": context.get("biological_program"),
        "sample_count": int(metadata.shape[0]),
        "feature_count": int(expression.shape[0]),
        "control_sample_count": int(metadata["is_non_targeting_control"].sum()),
        "perturbed_sample_count": int((~metadata["is_non_targeting_control"]).sum()),
        "perturbation_targets": targets,
        "time_hr_values": sorted(x for x in metadata["time_hr"].dropna().unique().tolist()),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _expression_artifact_for_series(series_id: str, dataset: GeoSeriesMatrix, supp_dir: Path | None) -> str | None:
    if series_id == "GSE43948" and supp_dir is not None and (supp_dir / "GSE43948_RAW.tar").exists():
        return "GSE43948_rnaseq"
    if dataset.expression is not None:
        return f"{series_id}_series"
    return None


def prepare_th17_study_arm_cohorts(
    datasets: list[GeoSeriesMatrix],
    output_dir: Path,
    supp_dir: Path | None = None,
) -> dict[str, dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, dict] = {}

    study_arms = sorted({dataset.metadata["study_arm"].iloc[0] for dataset in datasets if "study_arm" in dataset.metadata.columns})
    for study_arm in study_arms:
        arm_datasets = [dataset for dataset in datasets if dataset.metadata["study_arm"].iloc[0] == study_arm]
        if not arm_datasets:
            continue

        cohort_dir = output_dir / f"{study_arm}_cohort"
        cohort_dir.mkdir(parents=True, exist_ok=True)

        sample_frames: list[pd.DataFrame] = []
        series_records: list[dict[str, object]] = []
        for dataset in arm_datasets:
            metadata = dataset.metadata.copy()
            metadata.insert(1, "series_id", dataset.series_id)
            sample_frames.append(metadata)
            series_records.append(
                {
                    "series_id": dataset.series_id,
                    "study_arm": study_arm,
                    "source_publication": _series_context(dataset.series_id).get("source_publication"),
                    "biological_program": _series_context(dataset.series_id).get("biological_program"),
                    "sample_count": int(metadata.shape[0]),
                    "has_series_expression_matrix": dataset.expression is not None,
                    "expression_artifact": _expression_artifact_for_series(dataset.series_id, dataset, supp_dir),
                }
            )

        sample_metadata = pd.concat(sample_frames, ignore_index=True, sort=False)
        sample_metadata.to_csv(cohort_dir / "sample_metadata.csv", index=False)

        series_metadata = pd.DataFrame.from_records(series_records).sort_values("series_id")
        series_metadata.to_csv(cohort_dir / "series_metadata.csv", index=False)

        summary = {
            "study_arm": study_arm,
            "source_publications": sorted(series_metadata["source_publication"].dropna().astype(str).unique().tolist()),
            "biological_programs": sorted(series_metadata["biological_program"].dropna().astype(str).unique().tolist()),
            "series_ids": series_metadata["series_id"].tolist(),
            "series_count": int(series_metadata.shape[0]),
            "sample_count": int(sample_metadata.shape[0]),
            "expression_artifacts": sorted(series_metadata["expression_artifact"].dropna().astype(str).unique().tolist()),
            "metadata_only_series": sorted(
                series_metadata.loc[series_metadata["expression_artifact"].isna(), "series_id"].astype(str).tolist()
            ),
        }
        (cohort_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        payload[f"{study_arm}_cohort"] = summary

    return payload


def _standardize_cell_type(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip()
    if raw in {"Th17", "Th17 cells"}:
        return "Th17"
    return raw


def _standardize_treatment(series_id: str, value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip()
    mapping = {
        "Tgfb+Il6": "TGFb+IL6",
        "Tgfb+Il6+Il23": "TGFb+IL6+IL23",
        "Tgfb+IL6": "TGFb+IL6",
        "Tgfb+IL6+IL23": "TGFb+IL6+IL23",
        "Th0": "Th0",
    }
    if series_id == "GSE43948":
        return "non_targeting_control" if "non-targeting control" in raw.lower() else "targeted_knockdown"
    return mapping.get(raw, raw)


def _standardize_genotype(value: object) -> str:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "not_reported"
    raw = str(value).strip()
    mapping = {
        "WT": "WT",
        "IL23R knockout": "IL23R_KO",
    }
    return mapping.get(raw, raw)


def _load_expression_matrix(artifact_dir: Path) -> pd.DataFrame:
    return pd.read_csv(artifact_dir / "expression_matrix.tsv.gz", sep="\t", index_col=0)


def _load_matrix(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", index_col=0)


def _safe_log2_fold_change(sample: pd.Series, baseline: pd.Series) -> pd.Series:
    return np.log2(sample.astype(float) + 1.0) - np.log2(baseline.astype(float) + 1.0)


def _sanitize_label(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value)
    return cleaned.strip("_")


def _extract_geo_platform_aliases(row: pd.Series) -> list[str]:
    aliases: set[str] = set()
    for field in ["gene_symbol", "target_description"]:
        value = row.get(field)
        if value is None or pd.isna(value):
            continue
        text = str(value)
        if field == "gene_symbol" and text.strip():
            aliases.add(text.strip().upper())
        for pattern in [r"/GEN=([A-Za-z0-9_-]+)", r"/UG_GENE=([A-Za-z0-9_-]+)"]:
            for match in re.findall(pattern, text):
                aliases.add(match.strip().upper())
    return sorted(aliases)


def ensure_geo_platform_text(platform_id: str, platform_dir: Path) -> Path:
    platform_dir.mkdir(parents=True, exist_ok=True)
    destination = platform_dir / f"{platform_id}_full.txt"
    if destination.exists():
        return destination

    url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={platform_id}&targ=self&form=text&view=full"
    urllib.request.urlretrieve(url, destination)
    return destination


def parse_geo_platform_text(path: Path) -> pd.DataFrame:
    records: list[dict[str, str]] = []
    header: list[str] | None = None
    in_table = False

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line == "!platform_table_begin":
                in_table = True
                continue
            if line == "!platform_table_end":
                break
            if not in_table:
                continue

            parsed = _parse_line(line)
            if header is None:
                header = parsed
                continue
            records.append(dict(zip(header, parsed, strict=False)))

    if header is None:
        raise ValueError(f"No platform table found in {path}")

    table = pd.DataFrame.from_records(records)
    rename_map = {
        "ID": "probe_id",
        "Gene Symbol": "gene_symbol",
        "Gene Title": "gene_title",
        "ENTREZ_GENE_ID": "entrez_gene_id",
        "RefSeq Transcript ID": "refseq_transcript_id",
        "Representative Public ID": "representative_public_id",
        "GB_ACC": "gb_acc",
        "Target Description": "target_description",
        "Annotation Date": "annotation_date",
    }
    table = table.rename(columns=rename_map)
    return table


def prepare_yosef_th17_network_design(
    datasets: list[GeoSeriesMatrix],
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    yosef_datasets = [dataset for dataset in datasets if dataset.metadata.get("study_arm", pd.Series(dtype=str)).eq("yosef_th17_network").any()]
    if not yosef_datasets:
        raise ValueError("No Yosef Th17 datasets are available for design-table generation.")

    rnaseq_path = output_dir.parent / "GSE43948_rnaseq" / "sample_metadata.csv"
    rnaseq_metadata = pd.read_csv(rnaseq_path) if rnaseq_path.exists() else pd.DataFrame()
    rnaseq_lookup = (
        rnaseq_metadata.set_index("sample_id")[
            ["source_filename", "time_hr", "perturbation_target_raw", "perturbation_target", "is_non_targeting_control"]
        ].to_dict(orient="index")
        if not rnaseq_metadata.empty
        else {}
    )

    records: list[dict[str, object]] = []
    for dataset in sorted(yosef_datasets, key=lambda item: item.series_id):
        context = _series_context(dataset.series_id)
        expression_artifact = (
            "GSE43948_rnaseq"
            if dataset.series_id == "GSE43948" and rnaseq_path.exists()
            else (f"{dataset.series_id}_series" if dataset.expression is not None else None)
        )
        for row in dataset.metadata.to_dict(orient="records"):
            sample_id = str(row["sample_id"])
            rnaseq_row = rnaseq_lookup.get(sample_id, {})
            time_hr = rnaseq_row.get("time_hr", row.get("time_hr"))
            exact_48h = bool(pd.notna(time_hr) and float(time_hr) == 48.0)
            perturbation_target = rnaseq_row.get("perturbation_target")
            is_non_targeting_control = rnaseq_row.get("is_non_targeting_control")
            records.append(
                {
                    "sample_id": sample_id,
                    "series_id": dataset.series_id,
                    "study_arm": context.get("study_arm"),
                    "source_publication": context.get("source_publication"),
                    "biological_program": context.get("biological_program"),
                    "assay_modality": context.get("assay_modality"),
                    "experimental_axis": context.get("experimental_axis"),
                    "metadata_artifact": f"{dataset.series_id}_series",
                    "expression_artifact": expression_artifact,
                    "has_expression_artifact": expression_artifact is not None,
                    "title": row.get("title"),
                    "cell_type_raw": row.get("cell_type"),
                    "cell_type_standardized": _standardize_cell_type(row.get("cell_type")),
                    "treatment_raw": row.get("treatment"),
                    "treatment_standardized": _standardize_treatment(dataset.series_id, row.get("treatment")),
                    "genotype_raw": row.get("genotype"),
                    "genotype_standardized": _standardize_genotype(row.get("genotype")),
                    "time_hr": float(time_hr) if pd.notna(time_hr) else None,
                    "is_exact_48h": exact_48h,
                    "perturbation_target": perturbation_target,
                    "is_non_targeting_control": bool(is_non_targeting_control) if pd.notna(is_non_targeting_control) else None,
                    "chip_antibody": row.get("chip_antibody"),
                    "in_regulator_ranking_panel": dataset.series_id == "GSE43948" and expression_artifact is not None,
                    "in_chip_binding_panel": dataset.series_id == "GSE43949",
                    "in_dynamic_timecourse_panel": dataset.series_id in {"GSE43955", "GSE43969"} and expression_artifact is not None,
                    "in_exact_48h_expression_panel": exact_48h and expression_artifact is not None,
                }
            )

    design = pd.DataFrame.from_records(records).sort_values(["series_id", "sample_id"]).reset_index(drop=True)
    design.to_csv(output_dir / "sample_design.csv", index=False)

    perturbation_screen = design.loc[design["in_regulator_ranking_panel"]].copy()
    perturbation_screen.to_csv(output_dir / "perturbation_screen_design.csv", index=False)

    chip_binding = design.loc[design["in_chip_binding_panel"]].copy()
    chip_binding.to_csv(output_dir / "chip_binding_design.csv", index=False)

    dynamic_timecourse = design.loc[design["in_dynamic_timecourse_panel"]].copy()
    dynamic_timecourse.to_csv(output_dir / "dynamic_timecourse_design.csv", index=False)

    exact_48h_expression = design.loc[design["in_exact_48h_expression_panel"]].copy()
    exact_48h_expression.to_csv(output_dir / "exact_48h_expression_design.csv", index=False)

    perturbation_expression = _load_expression_matrix(output_dir.parent / "GSE43948_rnaseq")
    perturbation_columns = perturbation_screen["sample_id"].tolist()
    perturbation_expression.loc[:, perturbation_columns].to_csv(
        output_dir / "perturbation_screen_expression_matrix.tsv.gz",
        sep="\t",
        compression="gzip",
    )
    pd.read_csv(output_dir.parent / "GSE43948_rnaseq" / "feature_metadata.csv").to_csv(
        output_dir / "perturbation_screen_feature_metadata.csv",
        index=False,
    )

    gse43955_expression = _load_expression_matrix(output_dir.parent / "GSE43955_series")
    gse43969_expression = _load_expression_matrix(output_dir.parent / "GSE43969_series")
    if gse43955_expression.index.tolist() != gse43969_expression.index.tolist():
        raise ValueError("GSE43955 and GSE43969 do not share the same feature ordering, so a combined dynamic panel cannot be formed safely.")
    dynamic_columns = dynamic_timecourse["sample_id"].tolist()
    dynamic_expression = pd.concat([gse43955_expression, gse43969_expression], axis=1).loc[:, dynamic_columns]
    dynamic_expression.to_csv(
        output_dir / "dynamic_timecourse_expression_matrix.tsv.gz",
        sep="\t",
        compression="gzip",
    )
    pd.read_csv(output_dir.parent / "GSE43955_series" / "feature_metadata.csv").to_csv(
        output_dir / "dynamic_timecourse_feature_metadata.csv",
        index=False,
    )

    exact_48h_expression_manifest = exact_48h_expression[
        ["sample_id", "series_id", "expression_artifact", "assay_modality", "experimental_axis", "time_hr"]
    ].copy()
    exact_48h_expression_manifest.to_csv(output_dir / "exact_48h_expression_manifest.csv", index=False)

    summary = {
        "study_arm": "yosef_th17_network",
        "sample_count": int(design.shape[0]),
        "series_ids": sorted(design["series_id"].astype(str).unique().tolist()),
        "assay_modality_counts": design["assay_modality"].value_counts().sort_index().astype(int).to_dict(),
        "experimental_axis_counts": design["experimental_axis"].value_counts().sort_index().astype(int).to_dict(),
        "expression_artifact_counts": design.loc[design["expression_artifact"].notna(), "expression_artifact"]
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict(),
        "perturbation_screen_sample_count": int(perturbation_screen.shape[0]),
        "chip_binding_sample_count": int(chip_binding.shape[0]),
        "dynamic_timecourse_sample_count": int(dynamic_timecourse.shape[0]),
        "exact_48h_expression_sample_count": int(exact_48h_expression.shape[0]),
        "exact_48h_expression_series_counts": exact_48h_expression["series_id"].value_counts().sort_index().astype(int).to_dict(),
        "exact_48h_expression_artifact_counts": exact_48h_expression["expression_artifact"].value_counts().sort_index().astype(int).to_dict(),
        "perturbation_screen_feature_count": int(perturbation_expression.shape[0]),
        "dynamic_timecourse_feature_count": int(dynamic_expression.shape[0]),
        "perturbation_target_counts": perturbation_screen["perturbation_target"].fillna("UNSPECIFIED").value_counts().sort_index().astype(int).to_dict(),
        "genotype_standardized_counts": design["genotype_standardized"].value_counts().sort_index().astype(int).to_dict(),
        "treatment_standardized_counts": design["treatment_standardized"].fillna("UNSPECIFIED").value_counts().sort_index().astype(int).to_dict(),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_yosef_th17_network_evidence(processed_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    design_dir = processed_dir / "yosef_th17_network_design"
    design = pd.read_csv(design_dir / "sample_design.csv")

    perturbation_design = pd.read_csv(design_dir / "perturbation_screen_design.csv")
    perturbation_expression = _load_matrix(design_dir / "perturbation_screen_expression_matrix.tsv.gz")
    control_samples = perturbation_design.loc[perturbation_design["is_non_targeting_control"], "sample_id"].astype(str).tolist()
    target_design = perturbation_design.loc[~perturbation_design["is_non_targeting_control"]].copy()
    target_samples = target_design["sample_id"].astype(str).tolist()

    control_expression = perturbation_expression.loc[:, control_samples]
    control_mean = control_expression.mean(axis=1)
    control_std = control_expression.std(axis=1, ddof=1)
    target_expression = perturbation_expression.loc[:, target_samples]
    delta_matrix = target_expression.sub(control_mean, axis=0)
    log2_fc_matrix = target_expression.apply(lambda column: _safe_log2_fold_change(column, control_mean), axis=0)

    control_reference = pd.DataFrame(
        {
            "gene_symbol": perturbation_expression.index.astype(str),
            "control_mean_expression": control_mean.values,
            "control_std_expression": control_std.values,
        }
    )
    control_reference.to_csv(output_dir / "perturbation_control_reference.csv", index=False)
    target_design.to_csv(output_dir / "perturbation_target_design.csv", index=False)
    target_expression.to_csv(output_dir / "perturbation_target_expression_matrix.tsv.gz", sep="\t", compression="gzip")
    delta_matrix.to_csv(output_dir / "perturbation_target_delta_matrix.tsv.gz", sep="\t", compression="gzip")
    log2_fc_matrix.to_csv(output_dir / "perturbation_target_log2_fc_matrix.tsv.gz", sep="\t", compression="gzip")

    upper_gene_symbols = {str(symbol).upper(): str(symbol) for symbol in perturbation_expression.index}
    self_response_records: list[dict[str, object]] = []
    for row in target_design.to_dict(orient="records"):
        target = str(row["perturbation_target"])
        gene_symbol = upper_gene_symbols.get(target)
        self_response_records.append(
            {
                "sample_id": row["sample_id"],
                "perturbation_target": target,
                "matched_gene_symbol": gene_symbol,
                "target_gene_observed": gene_symbol is not None,
                "target_expression": float(target_expression.loc[gene_symbol, row["sample_id"]]) if gene_symbol is not None else None,
                "control_mean_expression": float(control_mean.loc[gene_symbol]) if gene_symbol is not None else None,
                "delta_expression": float(delta_matrix.loc[gene_symbol, row["sample_id"]]) if gene_symbol is not None else None,
                "log2_fold_change": float(log2_fc_matrix.loc[gene_symbol, row["sample_id"]]) if gene_symbol is not None else None,
            }
        )
    self_response = pd.DataFrame.from_records(self_response_records)
    self_response.to_csv(output_dir / "perturbation_self_response.csv", index=False)

    dynamic_design = pd.read_csv(design_dir / "dynamic_timecourse_design.csv")
    dynamic_expression = _load_matrix(design_dir / "dynamic_timecourse_expression_matrix.tsv.gz")
    late_time_design = dynamic_design.loc[dynamic_design["time_hr"] >= 48.0].copy()
    late_time_design.to_csv(output_dir / "late_time_gpl8321_design.csv", index=False)
    late_time_columns = late_time_design["sample_id"].astype(str).tolist()
    dynamic_expression.loc[:, late_time_columns].to_csv(
        output_dir / "late_time_gpl8321_expression_matrix.tsv.gz",
        sep="\t",
        compression="gzip",
    )

    exact_48h_microarray = dynamic_design.loc[dynamic_design["time_hr"] == 48.0].copy()
    exact_48h_microarray.to_csv(output_dir / "exact_48h_gpl8321_design.csv", index=False)
    exact_48h_microarray_columns = exact_48h_microarray["sample_id"].astype(str).tolist()
    dynamic_expression.loc[:, exact_48h_microarray_columns].to_csv(
        output_dir / "exact_48h_gpl8321_expression_matrix.tsv.gz",
        sep="\t",
        compression="gzip",
    )

    summary = {
        "study_arm": "yosef_th17_network",
        "perturbation_gene_count": int(perturbation_expression.shape[0]),
        "perturbation_control_sample_count": len(control_samples),
        "perturbation_target_sample_count": len(target_samples),
        "perturbation_target_count": int(target_design["perturbation_target"].nunique()),
        "target_self_observed_count": int(self_response["target_gene_observed"].sum()),
        "target_self_missing": sorted(
            self_response.loc[~self_response["target_gene_observed"], "perturbation_target"].astype(str).unique().tolist()
        ),
        "late_time_gpl8321_sample_count": int(late_time_design.shape[0]),
        "late_time_gpl8321_series_counts": late_time_design["series_id"].value_counts().sort_index().astype(int).to_dict(),
        "late_time_gpl8321_time_counts": late_time_design["time_hr"].value_counts().sort_index().astype(int).to_dict(),
        "exact_48h_gpl8321_sample_count": int(exact_48h_microarray.shape[0]),
        "exact_48h_gpl8321_series_counts": exact_48h_microarray["series_id"].value_counts().sort_index().astype(int).to_dict(),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_gpl8321_annotation(raw_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    platform_path = ensure_geo_platform_text("GPL8321", raw_dir.parent / "platforms")
    annotation = parse_geo_platform_text(platform_path)
    selected_columns = [
        "probe_id",
        "gene_symbol",
        "gene_title",
        "entrez_gene_id",
        "refseq_transcript_id",
        "representative_public_id",
        "gb_acc",
        "annotation_date",
        "target_description",
    ]
    annotation["platform_symbol_aliases"] = annotation.apply(_extract_geo_platform_aliases, axis=1).map("|".join)
    available_columns = [column for column in selected_columns if column in annotation.columns]
    annotation.loc[:, available_columns + ["platform_symbol_aliases"]].to_csv(output_dir / "probe_annotation.csv", index=False)

    gene_symbol_series = annotation["gene_symbol"].fillna("").astype(str).str.strip()
    summary = {
        "platform_id": "GPL8321",
        "platform_file": platform_path.name,
        "probe_count": int(annotation.shape[0]),
        "nonempty_gene_symbol_probe_count": int(gene_symbol_series.ne("").sum()),
        "unique_gene_symbol_count": int(gene_symbol_series[gene_symbol_series.ne("")].nunique()),
        "nonempty_entrez_probe_count": int(annotation["entrez_gene_id"].fillna("").astype(str).str.strip().ne("").sum()),
        "annotation_date_values": sorted(annotation["annotation_date"].dropna().astype(str).unique().tolist()),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_yosef_th17_regulator_summary(processed_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = processed_dir / "yosef_th17_network_evidence"
    annotation_dir = processed_dir / "GPL8321_annotation"

    target_design = pd.read_csv(evidence_dir / "perturbation_target_design.csv")
    target_expression = _load_matrix(evidence_dir / "perturbation_target_expression_matrix.tsv.gz")
    delta_matrix = _load_matrix(evidence_dir / "perturbation_target_delta_matrix.tsv.gz")
    log2_fc_matrix = _load_matrix(evidence_dir / "perturbation_target_log2_fc_matrix.tsv.gz")
    control_reference = pd.read_csv(evidence_dir / "perturbation_control_reference.csv").set_index("gene_symbol")
    self_response = pd.read_csv(evidence_dir / "perturbation_self_response.csv").set_index("perturbation_target")
    gpl8321_annotation = pd.read_csv(annotation_dir / "probe_annotation.csv")

    rnaseq_target_records: list[dict[str, object]] = []
    for row in target_design.to_dict(orient="records"):
        sample_id = str(row["sample_id"])
        target = str(row["perturbation_target"])
        sample_log2_fc = log2_fc_matrix[sample_id]
        max_positive_gene = str(sample_log2_fc.idxmax())
        max_negative_gene = str(sample_log2_fc.idxmin())
        max_abs_gene = str(sample_log2_fc.abs().idxmax())
        self_row = self_response.loc[target]
        rnaseq_target_records.append(
            {
                "sample_id": sample_id,
                "perturbation_target": target,
                "matched_gene_symbol": self_row["matched_gene_symbol"] if pd.notna(self_row["matched_gene_symbol"]) else None,
                "target_gene_observed": bool(self_row["target_gene_observed"]),
                "self_target_expression": self_row["target_expression"],
                "self_control_mean_expression": self_row["control_mean_expression"],
                "self_delta_expression": self_row["delta_expression"],
                "self_log2_fold_change": self_row["log2_fold_change"],
                "mean_abs_log2_fc_all_genes": float(sample_log2_fc.abs().mean()),
                "median_abs_log2_fc_all_genes": float(sample_log2_fc.abs().median()),
                "max_positive_gene_symbol": max_positive_gene,
                "max_positive_log2_fc": float(sample_log2_fc.loc[max_positive_gene]),
                "max_negative_gene_symbol": max_negative_gene,
                "max_negative_log2_fc": float(sample_log2_fc.loc[max_negative_gene]),
                "max_abs_gene_symbol": max_abs_gene,
                "max_abs_log2_fc": float(sample_log2_fc.loc[max_abs_gene]),
            }
        )
    rnaseq_target_summary = pd.DataFrame.from_records(rnaseq_target_records).sort_values("perturbation_target")
    rnaseq_target_summary.to_csv(output_dir / "rnaseq_target_summary.csv", index=False)

    late_time_design = pd.read_csv(evidence_dir / "late_time_gpl8321_design.csv")
    late_time_expression = _load_matrix(evidence_dir / "late_time_gpl8321_expression_matrix.tsv.gz")

    contrast_specs: list[dict[str, object]] = []
    for time_hr in [48.0, 50.0, 52.0, 60.0, 72.0]:
        contrast_specs.append(
            {
                "contrast_family": "gse43955_treatment_vs_th0",
                "series_id": "GSE43955",
                "time_hr": time_hr,
                "lhs_treatment": "TGFb+IL6",
                "rhs_treatment": "Th0",
                "lhs_genotype": "not_reported",
                "rhs_genotype": "not_reported",
            }
        )
    for time_hr in [50.0, 52.0, 60.0, 72.0]:
        contrast_specs.append(
            {
                "contrast_family": "gse43955_il23_effect",
                "series_id": "GSE43955",
                "time_hr": time_hr,
                "lhs_treatment": "TGFb+IL6+IL23",
                "rhs_treatment": "TGFb+IL6",
                "lhs_genotype": "not_reported",
                "rhs_genotype": "not_reported",
            }
        )
    for time_hr in [48.0, 49.0, 54.0, 65.0, 72.0]:
        contrast_specs.append(
            {
                "contrast_family": "gse43969_wt_vs_il23rko_tgfb_il6",
                "series_id": "GSE43969",
                "time_hr": time_hr,
                "lhs_treatment": "TGFb+IL6",
                "rhs_treatment": "TGFb+IL6",
                "lhs_genotype": "WT",
                "rhs_genotype": "IL23R_KO",
            }
        )
    for time_hr in [49.0, 54.0, 65.0, 72.0]:
        contrast_specs.append(
            {
                "contrast_family": "gse43969_wt_vs_il23rko_tgfb_il6_il23",
                "series_id": "GSE43969",
                "time_hr": time_hr,
                "lhs_treatment": "TGFb+IL6+IL23",
                "rhs_treatment": "TGFb+IL6+IL23",
                "lhs_genotype": "WT",
                "rhs_genotype": "IL23R_KO",
            }
        )
    for genotype in ["WT", "IL23R_KO"]:
        for time_hr in [49.0, 54.0, 65.0, 72.0]:
            contrast_specs.append(
                {
                    "contrast_family": f"gse43969_il23_effect_{genotype.lower()}",
                    "series_id": "GSE43969",
                    "time_hr": time_hr,
                    "lhs_treatment": "TGFb+IL6+IL23",
                    "rhs_treatment": "TGFb+IL6",
                    "lhs_genotype": genotype,
                    "rhs_genotype": genotype,
                }
            )

    contrast_records: list[dict[str, object]] = []
    contrast_series: list[pd.Series] = []
    contrast_summary_records: list[dict[str, object]] = []
    for spec in contrast_specs:
        lhs = late_time_design.loc[
            (late_time_design["series_id"] == spec["series_id"])
            & (late_time_design["time_hr"] == spec["time_hr"])
            & (late_time_design["treatment_standardized"] == spec["lhs_treatment"])
            & (late_time_design["genotype_standardized"] == spec["lhs_genotype"])
        ].copy()
        rhs = late_time_design.loc[
            (late_time_design["series_id"] == spec["series_id"])
            & (late_time_design["time_hr"] == spec["time_hr"])
            & (late_time_design["treatment_standardized"] == spec["rhs_treatment"])
            & (late_time_design["genotype_standardized"] == spec["rhs_genotype"])
        ].copy()
        if lhs.empty or rhs.empty:
            raise ValueError(f"Missing samples for contrast specification: {spec}")

        label = _sanitize_label(
            f"{spec['contrast_family']}__{spec['series_id']}__{spec['time_hr']}h__{spec['lhs_treatment']}__{spec['lhs_genotype']}__vs__{spec['rhs_treatment']}__{spec['rhs_genotype']}"
        )
        lhs_mean = late_time_expression.loc[:, lhs["sample_id"].astype(str).tolist()].mean(axis=1)
        rhs_mean = late_time_expression.loc[:, rhs["sample_id"].astype(str).tolist()].mean(axis=1)
        delta = lhs_mean - rhs_mean
        delta.name = label
        contrast_series.append(delta)
        contrast_records.append(
            {
                "contrast_label": label,
                "contrast_family": spec["contrast_family"],
                "series_id": spec["series_id"],
                "time_hr": float(spec["time_hr"]),
                "lhs_treatment": spec["lhs_treatment"],
                "rhs_treatment": spec["rhs_treatment"],
                "lhs_genotype": spec["lhs_genotype"],
                "rhs_genotype": spec["rhs_genotype"],
                "lhs_sample_count": int(lhs.shape[0]),
                "rhs_sample_count": int(rhs.shape[0]),
                "lhs_sample_ids": "|".join(lhs["sample_id"].astype(str).tolist()),
                "rhs_sample_ids": "|".join(rhs["sample_id"].astype(str).tolist()),
            }
        )
        contrast_summary_records.append(
            {
                "contrast_label": label,
                "contrast_family": spec["contrast_family"],
                "series_id": spec["series_id"],
                "time_hr": float(spec["time_hr"]),
                "mean_abs_delta": float(delta.abs().mean()),
                "median_abs_delta": float(delta.abs().median()),
                "max_positive_probe_id": str(delta.idxmax()),
                "max_positive_delta": float(delta.max()),
                "max_negative_probe_id": str(delta.idxmin()),
                "max_negative_delta": float(delta.min()),
                "max_abs_probe_id": str(delta.abs().idxmax()),
                "max_abs_delta": float(delta.loc[delta.abs().idxmax()]),
            }
        )

    contrast_manifest = pd.DataFrame.from_records(contrast_records).sort_values(["series_id", "contrast_family", "time_hr"])
    contrast_manifest.to_csv(output_dir / "gpl8321_late_time_contrast_manifest.csv", index=False)
    contrast_summary = pd.DataFrame.from_records(contrast_summary_records).sort_values(["series_id", "contrast_family", "time_hr"])
    contrast_summary.to_csv(output_dir / "gpl8321_late_time_contrast_summary.csv", index=False)
    contrast_matrix = pd.concat(contrast_series, axis=1)
    contrast_matrix.to_csv(output_dir / "gpl8321_late_time_contrast_matrix.tsv.gz", sep="\t", compression="gzip")

    gpl8321_symbol_to_probes: dict[str, set[str]] = {}
    for row in gpl8321_annotation.to_dict(orient="records"):
        probe_id = str(row["probe_id"])
        aliases = {token for token in str(row.get("platform_symbol_aliases", "")).split("|") if token}
        for alias in aliases:
            gpl8321_symbol_to_probes.setdefault(alias, set()).add(probe_id)

    candidate_regulators = sorted(
        set(rnaseq_target_summary["perturbation_target"].astype(str).tolist()) | {"STAT6", "TCFEB", "TRIM24"}
    )
    upper_gene_symbols = {str(symbol).upper(): str(symbol) for symbol in target_expression.index}
    paper_highlighted = {"STAT6", "TCFEB", "TRIM24"}
    targeted = set(rnaseq_target_summary["perturbation_target"].astype(str).tolist())
    candidate_records: list[dict[str, object]] = []
    for regulator in candidate_regulators:
        matched_gene_symbol = upper_gene_symbols.get(regulator)
        microarray_probe_ids = sorted(gpl8321_symbol_to_probes.get(regulator, set()))
        target_row = rnaseq_target_summary.loc[rnaseq_target_summary["perturbation_target"] == regulator]
        gene_observed = matched_gene_symbol is not None
        candidate_records.append(
            {
                "regulator": regulator,
                "is_rnaseq_perturbation_target": regulator in targeted,
                "is_paper_finalnet_negative_48h_candidate": regulator in paper_highlighted,
                "matched_rnaseq_gene_symbol": matched_gene_symbol,
                "rnaseq_gene_observed": gene_observed,
                "rnaseq_self_target_observed": bool(target_row["target_gene_observed"].iloc[0]) if not target_row.empty else False,
                "rnaseq_self_log2_fold_change": float(target_row["self_log2_fold_change"].iloc[0]) if not target_row.empty and pd.notna(target_row["self_log2_fold_change"].iloc[0]) else None,
                "rnaseq_self_delta_expression": float(target_row["self_delta_expression"].iloc[0]) if not target_row.empty and pd.notna(target_row["self_delta_expression"].iloc[0]) else None,
                "rnaseq_control_mean_expression": float(control_reference.loc[matched_gene_symbol, "control_mean_expression"]) if gene_observed else None,
                "rnaseq_mean_abs_log2_fc_across_targets": float(log2_fc_matrix.loc[matched_gene_symbol].abs().mean()) if gene_observed else None,
                "rnaseq_max_abs_log2_fc_across_targets": float(log2_fc_matrix.loc[matched_gene_symbol].abs().max()) if gene_observed else None,
                "gpl8321_exact_symbol_probe_count": len(microarray_probe_ids),
                "gpl8321_exact_symbol_probe_ids": "|".join(microarray_probe_ids),
                "microarray_probe_mapping_available": len(microarray_probe_ids) > 0,
                "direct_gpl8321_gene_level_support_available": len(microarray_probe_ids) > 0,
                "evidence_note": (
                    "GPL8321 support uses exact GEO platform gene-symbol mappings only; unresolved aliases remain unsupported."
                ),
            }
        )
    candidate_evidence = pd.DataFrame.from_records(candidate_records).sort_values("regulator")
    candidate_evidence.to_csv(output_dir / "candidate_regulator_evidence.csv", index=False)

    summary = {
        "study_arm": "yosef_th17_network",
        "rnaseq_target_summary_count": int(rnaseq_target_summary.shape[0]),
        "target_self_observed_count": int(rnaseq_target_summary["target_gene_observed"].sum()),
        "late_time_gpl8321_contrast_count": int(contrast_manifest.shape[0]),
        "late_time_gpl8321_contrast_family_counts": contrast_manifest["contrast_family"].value_counts().sort_index().astype(int).to_dict(),
        "candidate_regulator_count": int(candidate_evidence.shape[0]),
        "paper_finalnet_negative_candidates": sorted(paper_highlighted),
        "paper_finalnet_negative_candidates_observed_in_rnaseq": sorted(
            candidate_evidence.loc[
                candidate_evidence["is_paper_finalnet_negative_48h_candidate"] & candidate_evidence["rnaseq_gene_observed"],
                "regulator",
            ].astype(str).tolist()
        ),
        "paper_finalnet_negative_candidates_with_exact_gpl8321_probe_support": sorted(
            candidate_evidence.loc[
                candidate_evidence["is_paper_finalnet_negative_48h_candidate"]
                & candidate_evidence["microarray_probe_mapping_available"],
                "regulator",
            ].astype(str).tolist()
        ),
        "candidate_regulators_with_exact_gpl8321_probe_support": sorted(
            candidate_evidence.loc[candidate_evidence["microarray_probe_mapping_available"], "regulator"].astype(str).tolist()
        ),
        "candidate_regulators_without_rnaseq_gene_match": sorted(
            candidate_evidence.loc[~candidate_evidence["rnaseq_gene_observed"], "regulator"].astype(str).tolist()
        ),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_yosef_th17_ranking_input(processed_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    regulator_dir = processed_dir / "yosef_th17_network_regulator_summary"

    candidate_evidence = pd.read_csv(regulator_dir / "candidate_regulator_evidence.csv")
    contrast_manifest = pd.read_csv(regulator_dir / "gpl8321_late_time_contrast_manifest.csv")
    contrast_matrix = _load_matrix(regulator_dir / "gpl8321_late_time_contrast_matrix.tsv.gz")

    terminal_proxy_manifest = contrast_manifest.copy()
    terminal_proxy_manifest["proxy_scope"] = np.where(
        terminal_proxy_manifest["time_hr"] == 48.0,
        "strict_exact_48h",
        "broad_late_time",
    )
    terminal_proxy_manifest.to_csv(output_dir / "terminal_proxy_manifest.csv", index=False)

    exact_48h_manifest = terminal_proxy_manifest.loc[terminal_proxy_manifest["proxy_scope"] == "strict_exact_48h"].copy()
    exact_48h_manifest.to_csv(output_dir / "strict_exact_48h_proxy_manifest.csv", index=False)
    exact_48h_labels = exact_48h_manifest["contrast_label"].astype(str).tolist()

    probe_feature_records: list[dict[str, object]] = []
    ranking_records: list[dict[str, object]] = []

    for row in candidate_evidence.to_dict(orient="records"):
        regulator = str(row["regulator"])
        probe_ids = [probe for probe in str(row["gpl8321_exact_symbol_probe_ids"]).split("|") if probe and probe != "nan"]
        regulator_probe_features: list[dict[str, object]] = []

        for probe_id in probe_ids:
            values = contrast_matrix.loc[probe_id]
            late_top_label = str(values.abs().idxmax())
            late_top_meta = contrast_manifest.loc[contrast_manifest["contrast_label"] == late_top_label].iloc[0]
            exact_48h_values = values.loc[exact_48h_labels] if exact_48h_labels else pd.Series(dtype=float)
            exact_48h_top_label = str(exact_48h_values.abs().idxmax()) if not exact_48h_values.empty else None
            exact_48h_top_meta = (
                exact_48h_manifest.loc[exact_48h_manifest["contrast_label"] == exact_48h_top_label].iloc[0]
                if exact_48h_top_label is not None
                else None
            )

            record = {
                "regulator": regulator,
                "probe_id": probe_id,
                "mean_abs_delta_all_late": float(values.abs().mean()),
                "max_abs_delta_all_late": float(values.abs().max()),
                "top_late_contrast_label": late_top_label,
                "top_late_signed_delta": float(values.loc[late_top_label]),
                "top_late_abs_delta": float(abs(values.loc[late_top_label])),
                "top_late_contrast_family": str(late_top_meta["contrast_family"]),
                "top_late_time_hr": float(late_top_meta["time_hr"]),
                "mean_abs_delta_exact_48h": float(exact_48h_values.abs().mean()) if not exact_48h_values.empty else None,
                "max_abs_delta_exact_48h": float(exact_48h_values.abs().max()) if not exact_48h_values.empty else None,
                "top_exact_48h_contrast_label": exact_48h_top_label,
                "top_exact_48h_signed_delta": (
                    float(exact_48h_values.loc[exact_48h_top_label]) if exact_48h_top_label is not None else None
                ),
                "top_exact_48h_abs_delta": (
                    float(abs(exact_48h_values.loc[exact_48h_top_label])) if exact_48h_top_label is not None else None
                ),
                "top_exact_48h_contrast_family": (
                    str(exact_48h_top_meta["contrast_family"]) if exact_48h_top_meta is not None else None
                ),
                "top_exact_48h_time_hr": float(exact_48h_top_meta["time_hr"]) if exact_48h_top_meta is not None else None,
            }
            regulator_probe_features.append(record)
            probe_feature_records.append(record)

        if regulator_probe_features:
            regulator_probe_frame = pd.DataFrame.from_records(regulator_probe_features)
            best_probe_all_late = regulator_probe_frame.sort_values(
                ["max_abs_delta_all_late", "mean_abs_delta_all_late"],
                ascending=False,
            ).iloc[0]
            best_probe_exact_48h = regulator_probe_frame.sort_values(
                ["max_abs_delta_exact_48h", "mean_abs_delta_exact_48h"],
                ascending=False,
                na_position="last",
            ).iloc[0]
            ranking_records.append(
                {
                    **row,
                    "strict_exact_48h_proxy_available": True,
                    "broad_late_time_proxy_available": True,
                    "gpl8321_probe_feature_count": int(regulator_probe_frame.shape[0]),
                    "gpl8321_mean_abs_delta_all_late_across_probes": float(
                        regulator_probe_frame["mean_abs_delta_all_late"].mean()
                    ),
                    "gpl8321_max_abs_delta_all_late_across_probes": float(
                        regulator_probe_frame["max_abs_delta_all_late"].max()
                    ),
                    "gpl8321_best_probe_all_late": str(best_probe_all_late["probe_id"]),
                    "gpl8321_best_probe_mean_abs_delta_all_late": float(best_probe_all_late["mean_abs_delta_all_late"]),
                    "gpl8321_best_probe_max_abs_delta_all_late": float(best_probe_all_late["max_abs_delta_all_late"]),
                    "gpl8321_best_probe_top_late_contrast_label": str(best_probe_all_late["top_late_contrast_label"]),
                    "gpl8321_best_probe_top_late_contrast_family": str(best_probe_all_late["top_late_contrast_family"]),
                    "gpl8321_best_probe_top_late_time_hr": float(best_probe_all_late["top_late_time_hr"]),
                    "gpl8321_best_probe_top_late_signed_delta": float(best_probe_all_late["top_late_signed_delta"]),
                    "gpl8321_mean_abs_delta_exact_48h_across_probes": float(
                        regulator_probe_frame["mean_abs_delta_exact_48h"].mean()
                    ),
                    "gpl8321_max_abs_delta_exact_48h_across_probes": float(
                        regulator_probe_frame["max_abs_delta_exact_48h"].max()
                    ),
                    "gpl8321_best_probe_exact_48h": str(best_probe_exact_48h["probe_id"]),
                    "gpl8321_best_probe_mean_abs_delta_exact_48h": float(best_probe_exact_48h["mean_abs_delta_exact_48h"]),
                    "gpl8321_best_probe_max_abs_delta_exact_48h": float(best_probe_exact_48h["max_abs_delta_exact_48h"]),
                    "gpl8321_best_probe_top_exact_48h_contrast_label": str(
                        best_probe_exact_48h["top_exact_48h_contrast_label"]
                    ),
                    "gpl8321_best_probe_top_exact_48h_contrast_family": str(
                        best_probe_exact_48h["top_exact_48h_contrast_family"]
                    ),
                    "gpl8321_best_probe_top_exact_48h_time_hr": float(best_probe_exact_48h["top_exact_48h_time_hr"]),
                    "gpl8321_best_probe_top_exact_48h_signed_delta": float(
                        best_probe_exact_48h["top_exact_48h_signed_delta"]
                    ),
                }
            )
        else:
            ranking_records.append(
                {
                    **row,
                    "strict_exact_48h_proxy_available": False,
                    "broad_late_time_proxy_available": False,
                    "gpl8321_probe_feature_count": 0,
                    "gpl8321_mean_abs_delta_all_late_across_probes": None,
                    "gpl8321_max_abs_delta_all_late_across_probes": None,
                    "gpl8321_best_probe_all_late": None,
                    "gpl8321_best_probe_mean_abs_delta_all_late": None,
                    "gpl8321_best_probe_max_abs_delta_all_late": None,
                    "gpl8321_best_probe_top_late_contrast_label": None,
                    "gpl8321_best_probe_top_late_contrast_family": None,
                    "gpl8321_best_probe_top_late_time_hr": None,
                    "gpl8321_best_probe_top_late_signed_delta": None,
                    "gpl8321_mean_abs_delta_exact_48h_across_probes": None,
                    "gpl8321_max_abs_delta_exact_48h_across_probes": None,
                    "gpl8321_best_probe_exact_48h": None,
                    "gpl8321_best_probe_mean_abs_delta_exact_48h": None,
                    "gpl8321_best_probe_max_abs_delta_exact_48h": None,
                    "gpl8321_best_probe_top_exact_48h_contrast_label": None,
                    "gpl8321_best_probe_top_exact_48h_contrast_family": None,
                    "gpl8321_best_probe_top_exact_48h_time_hr": None,
                    "gpl8321_best_probe_top_exact_48h_signed_delta": None,
                }
            )

    probe_feature_table = pd.DataFrame.from_records(probe_feature_records).sort_values(["regulator", "probe_id"])
    probe_feature_table.to_csv(output_dir / "candidate_probe_feature_table.csv", index=False)

    ranking_input = pd.DataFrame.from_records(ranking_records).sort_values("regulator")
    for column in [
        "rnaseq_max_abs_log2_fc_across_targets",
        "gpl8321_best_probe_max_abs_delta_all_late",
        "gpl8321_best_probe_max_abs_delta_exact_48h",
    ]:
        ranking_input[f"{column}_rank_desc"] = ranking_input[column].rank(method="min", ascending=False)

    ranking_input["evidence_dimension_count"] = (
        ranking_input[
            [
                "rnaseq_max_abs_log2_fc_across_targets",
                "gpl8321_best_probe_max_abs_delta_all_late",
                "gpl8321_best_probe_max_abs_delta_exact_48h",
            ]
        ]
        .notna()
        .sum(axis=1)
        .astype(int)
    )
    ranking_input.to_csv(output_dir / "candidate_ranking_input.csv", index=False)

    paper_candidates = ranking_input.loc[ranking_input["is_paper_finalnet_negative_48h_candidate"]].copy()
    summary = {
        "study_arm": "yosef_th17_network",
        "candidate_count": int(ranking_input.shape[0]),
        "candidate_probe_feature_row_count": int(probe_feature_table.shape[0]),
        "strict_exact_48h_proxy_contrast_count": int(exact_48h_manifest.shape[0]),
        "strict_exact_48h_proxy_contrast_families": sorted(
            exact_48h_manifest["contrast_family"].astype(str).unique().tolist()
        ),
        "broad_late_time_proxy_contrast_count": int(terminal_proxy_manifest.shape[0]),
        "candidate_count_with_strict_exact_48h_support": int(ranking_input["strict_exact_48h_proxy_available"].sum()),
        "candidate_count_with_broad_late_time_support": int(ranking_input["broad_late_time_proxy_available"].sum()),
        "paper_finalnet_negative_candidates": sorted(paper_candidates["regulator"].astype(str).tolist()),
        "paper_finalnet_negative_candidates_with_strict_exact_48h_support": sorted(
            paper_candidates.loc[paper_candidates["strict_exact_48h_proxy_available"], "regulator"].astype(str).tolist()
        ),
        "paper_finalnet_negative_candidates_best_exact_48h_probe": {
            str(row["regulator"]): str(row["gpl8321_best_probe_exact_48h"])
            for row in paper_candidates.to_dict(orient="records")
        },
        "paper_finalnet_negative_candidates_top_exact_48h_contrast_label": {
            str(row["regulator"]): str(row["gpl8321_best_probe_top_exact_48h_contrast_label"])
            for row in paper_candidates.to_dict(orient="records")
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_yosef_th17_prioritization(processed_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    ranking_dir = processed_dir / "yosef_th17_network_ranking_input"
    priority = pd.read_csv(ranking_dir / "candidate_ranking_input.csv")

    view_specs = {
        "strict_exact_48h_consensus": {
            "rank_columns": [
                "rnaseq_max_abs_log2_fc_across_targets_rank_desc",
                "gpl8321_best_probe_max_abs_delta_exact_48h_rank_desc",
            ],
            "value_columns": [
                "rnaseq_max_abs_log2_fc_across_targets",
                "gpl8321_best_probe_max_abs_delta_exact_48h",
            ],
        },
        "broad_late_time_consensus": {
            "rank_columns": [
                "rnaseq_max_abs_log2_fc_across_targets_rank_desc",
                "gpl8321_best_probe_max_abs_delta_all_late_rank_desc",
            ],
            "value_columns": [
                "rnaseq_max_abs_log2_fc_across_targets",
                "gpl8321_best_probe_max_abs_delta_all_late",
            ],
        },
        "three_axis_consensus": {
            "rank_columns": [
                "rnaseq_max_abs_log2_fc_across_targets_rank_desc",
                "gpl8321_best_probe_max_abs_delta_all_late_rank_desc",
                "gpl8321_best_probe_max_abs_delta_exact_48h_rank_desc",
            ],
            "value_columns": [
                "rnaseq_max_abs_log2_fc_across_targets",
                "gpl8321_best_probe_max_abs_delta_all_late",
                "gpl8321_best_probe_max_abs_delta_exact_48h",
            ],
        },
    }

    view_outputs: dict[str, dict[str, object]] = {}
    for view_name, spec in view_specs.items():
        available_col = f"{view_name}_available"
        rank_sum_col = f"{view_name}_rank_sum"
        rank_col = f"{view_name}_rank"
        pareto_col = f"{view_name}_pareto_front"
        top5_col = f"{view_name}_top5"

        priority[available_col] = priority[spec["rank_columns"]].notna().all(axis=1)
        priority[rank_sum_col] = np.where(priority[available_col], priority[spec["rank_columns"]].sum(axis=1), np.nan)
        priority[rank_col] = priority[rank_sum_col].rank(method="min", ascending=True)
        priority[top5_col] = priority[rank_col].le(5).fillna(False)
        priority[pareto_col] = False

        available_rows = priority.loc[priority[available_col]].copy()
        metric_frame = available_rows.loc[:, spec["value_columns"]].astype(float)
        pareto_members: list[bool] = []
        for idx, row in metric_frame.iterrows():
            dominated = False
            for other_idx, other in metric_frame.iterrows():
                if idx == other_idx:
                    continue
                if bool((other >= row).all()) and bool((other > row).any()):
                    dominated = True
                    break
            pareto_members.append(not dominated)
        priority.loc[available_rows.index, pareto_col] = pareto_members

        ranking_view = priority.loc[priority[available_col]].copy()
        ranking_view = ranking_view.sort_values([rank_sum_col, "regulator"])
        ranking_view.to_csv(output_dir / f"{view_name}.csv", index=False)

        pareto_view = priority.loc[priority[pareto_col]].copy()
        pareto_view = pareto_view.sort_values(spec["value_columns"], ascending=[False] * len(spec["value_columns"]))
        pareto_view.to_csv(output_dir / f"{view_name}_pareto_front.csv", index=False)

        view_outputs[view_name] = {
            "available_col": available_col,
            "rank_sum_col": rank_sum_col,
            "rank_col": rank_col,
            "pareto_col": pareto_col,
            "top5_col": top5_col,
            "top5_regulators": ranking_view.head(5)["regulator"].astype(str).tolist(),
            "pareto_front_regulators": pareto_view["regulator"].astype(str).tolist(),
        }

    priority.to_csv(output_dir / "candidate_priority_table.csv", index=False)

    paper_candidates = priority.loc[priority["is_paper_finalnet_negative_48h_candidate"]].copy()
    paper_audit = paper_candidates.loc[
        :,
        [
            "regulator",
            "rnaseq_max_abs_log2_fc_across_targets",
            "rnaseq_max_abs_log2_fc_across_targets_rank_desc",
            "gpl8321_best_probe_max_abs_delta_all_late",
            "gpl8321_best_probe_max_abs_delta_all_late_rank_desc",
            "gpl8321_best_probe_max_abs_delta_exact_48h",
            "gpl8321_best_probe_max_abs_delta_exact_48h_rank_desc",
        ],
    ].copy()
    for view_name, metadata in view_outputs.items():
        paper_audit[metadata["rank_sum_col"]] = paper_candidates[metadata["rank_sum_col"]].tolist()
        paper_audit[metadata["rank_col"]] = paper_candidates[metadata["rank_col"]].tolist()
        paper_audit[metadata["top5_col"]] = paper_candidates[metadata["top5_col"]].tolist()
        paper_audit[metadata["pareto_col"]] = paper_candidates[metadata["pareto_col"]].tolist()
    paper_audit.to_csv(output_dir / "paper_finalnet_claim_audit.csv", index=False)

    summary = {
        "study_arm": "yosef_th17_network",
        "candidate_count": int(priority.shape[0]),
        "paper_finalnet_negative_candidate_count": int(paper_candidates.shape[0]),
        "paper_finalnet_negative_candidates": sorted(paper_candidates["regulator"].astype(str).tolist()),
    }
    for view_name, metadata in view_outputs.items():
        view_rank_col = str(metadata["rank_col"])
        view_pareto_col = str(metadata["pareto_col"])
        view_top5_col = str(metadata["top5_col"])
        available_col = str(metadata["available_col"])
        summary[f"{view_name}_candidate_count"] = int(priority[available_col].sum())
        summary[f"{view_name}_top5_regulators"] = metadata["top5_regulators"]
        summary[f"{view_name}_pareto_front_regulators"] = metadata["pareto_front_regulators"]
        summary[f"paper_finalnet_negative_candidates_{view_name}_rank"] = {
            str(row["regulator"]): int(row[view_rank_col]) if pd.notna(row[view_rank_col]) else None
            for row in paper_candidates.to_dict(orient="records")
        }
        summary[f"paper_finalnet_negative_candidates_{view_name}_top5"] = sorted(
            paper_candidates.loc[paper_candidates[view_top5_col], "regulator"].astype(str).tolist()
        )
        summary[f"paper_finalnet_negative_candidates_{view_name}_pareto_front"] = sorted(
            paper_candidates.loc[paper_candidates[view_pareto_col], "regulator"].astype(str).tolist()
        )
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def prepare_th17_series(raw_dir: Path, output_dir: Path, supp_dir: Path | None = None) -> dict[str, dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, dict] = {}
    sample_to_series = _build_sample_to_series_map(raw_dir)
    annotated_datasets: list[GeoSeriesMatrix] = []

    for path in sorted(raw_dir.glob("GSE*_series_matrix.txt.gz")):
        dataset = _annotate_dataset_context(parse_geo_series_matrix(path))
        annotated_datasets.append(dataset)
        payload[f"{dataset.series_id}_series"] = _write_dataset_payload(dataset, output_dir / f"{dataset.series_id}_series")

    if supp_dir is not None:
        for filelist_path in sorted(supp_dir.glob("GSE*_filelist.txt")):
            series_id = filelist_path.name.replace("_filelist.txt", "")
            payload[f"{series_id}_bundle_manifest"] = prepare_geo_supplementary_manifest(
                filelist_path,
                output_dir / f"{series_id}_bundle_manifest",
                sample_to_series,
            )

        for tar_path in sorted(supp_dir.glob("GSE*_RAW.tar")):
            if tar_path.name == "GSE43948_RAW.tar":
                continue
            series_id = tar_path.name.replace("_RAW.tar", "")
            if f"{series_id}_bundle_manifest" in payload:
                continue
            payload[f"{series_id}_bundle_manifest"] = prepare_geo_tar_manifest(
                tar_path,
                output_dir / f"{series_id}_bundle_manifest",
                sample_to_series,
            )

        if (supp_dir / "GSE43948_RAW.tar").exists():
            payload["GSE43948_rnaseq"] = prepare_th17_perturbation_rnaseq(supp_dir, output_dir / "GSE43948_rnaseq")

    payload.update(prepare_th17_study_arm_cohorts(annotated_datasets, output_dir, supp_dir))
    payload["yosef_th17_network_design"] = prepare_yosef_th17_network_design(
        annotated_datasets,
        output_dir / "yosef_th17_network_design",
    )
    payload["yosef_th17_network_evidence"] = prepare_yosef_th17_network_evidence(
        output_dir,
        output_dir / "yosef_th17_network_evidence",
    )
    payload["GPL8321_annotation"] = prepare_gpl8321_annotation(
        raw_dir,
        output_dir / "GPL8321_annotation",
    )
    payload["yosef_th17_network_regulator_summary"] = prepare_yosef_th17_regulator_summary(
        output_dir,
        output_dir / "yosef_th17_network_regulator_summary",
    )
    payload["yosef_th17_network_ranking_input"] = prepare_yosef_th17_ranking_input(
        output_dir,
        output_dir / "yosef_th17_network_ranking_input",
    )
    payload["yosef_th17_network_prioritization"] = prepare_yosef_th17_prioritization(
        output_dir,
        output_dir / "yosef_th17_network_prioritization",
    )

    combined = {
        "datasets": payload,
        "dataset_order": sorted(payload),
        "study_arm_dataset_counts": pd.Series(
            [summary["study_arm"] for summary in payload.values() if summary.get("study_arm") is not None]
        ).value_counts().sort_index().astype(int).to_dict()
        if payload
        else {},
    }
    (output_dir / "summary.json").write_text(json.dumps(combined, indent=2, sort_keys=True))
    return payload
