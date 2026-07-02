from __future__ import annotations

import csv
import gzip
import json
import re
import tarfile
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
    },
    "GSE43949": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
    },
    "GSE43955": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
    },
    "GSE43969": {
        "study_arm": "yosef_th17_network",
        "source_publication": "Yosef et al. 2013",
        "biological_program": "dynamic_th17_network_reconstruction",
    },
    "GSE43956": {
        "study_arm": "wu_sgk1_pathogenicity",
        "source_publication": "Wu et al. 2013",
        "biological_program": "sgk1_il23_pathogenicity",
    },
    "GSE43957": {
        "study_arm": "wu_sgk1_pathogenicity",
        "source_publication": "Wu et al. 2013",
        "biological_program": "sgk1_salt_pathogenicity",
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
