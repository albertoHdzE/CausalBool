from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from imp_causal_paper.bio_ingestion import (
    parse_geo_series_matrix,
    prepare_geo_supplementary_manifest,
    prepare_geo_tar_manifest,
    prepare_th17_perturbation_rnaseq,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_TH17_DIR = PROJECT_ROOT / "data" / "raw" / "th17_geo"
RAW_TH17_SUPP_DIR = PROJECT_ROOT / "data" / "raw" / "th17_geo_supp"


def require_th17_raw() -> None:
    if not RAW_TH17_DIR.exists():
        pytest.skip("Th17 GEO raw matrices are not available in data/raw/th17_geo")


def require_th17_supp() -> None:
    if not (RAW_TH17_SUPP_DIR / "GSE43948_RAW.tar").exists():
        pytest.skip("Th17 supplementary RNA-seq tarball is not available in data/raw/th17_geo_supp")


def test_parse_gse43955_series_matrix_real_data() -> None:
    require_th17_raw()
    dataset = parse_geo_series_matrix(RAW_TH17_DIR / "GSE43955_series_matrix.txt.gz")
    assert dataset.series_id == "GSE43955"
    assert dataset.expression is not None
    assert dataset.metadata.shape[0] == 58
    assert dataset.expression.shape == (22690, 58)
    assert dataset.metadata["time_hr"].min() == 0.5
    assert dataset.metadata["time_hr"].max() == 72.0
    assert {"Th0", "Tgfb+Il6", "Tgfb+Il6+Il23"}.issubset(set(dataset.metadata["treatment"]))


def test_parse_gse43949_series_matrix_metadata_only_real_data() -> None:
    require_th17_raw()
    dataset = parse_geo_series_matrix(RAW_TH17_DIR / "GSE43949_series_matrix.txt.gz")
    assert dataset.series_id == "GSE43949"
    assert dataset.expression is None
    assert dataset.metadata.shape[0] == 2
    assert set(dataset.metadata["title"]) == {"TSC22D3", "WCE"}
    assert set(dataset.metadata["library_strategy"]) == {"ChIP-Seq"}
    assert set(dataset.metadata["chip_antibody"]) == {"TSC22D3", "none"}
    assert dataset.metadata["data_row_count"].astype(int).tolist() == [0, 0]


def test_parse_gse43956_series_matrix_real_data() -> None:
    require_th17_raw()
    dataset = parse_geo_series_matrix(RAW_TH17_DIR / "GSE43956_series_matrix.txt.gz")
    assert dataset.series_id == "GSE43956"
    assert dataset.expression is not None
    assert dataset.metadata.shape[0] == 4
    assert dataset.expression.shape == (45101, 4)
    assert set(dataset.metadata["genotype"]) == {"Sgk1-/-", "WT"}
    assert set(dataset.metadata["title"]) == {"WT-IL23 rep1", "WT-IL23 rep2", "SGK1-IL23 rep1", "SGK1-IL23 rep2"}


def test_parse_gse43957_series_matrix_real_data() -> None:
    require_th17_raw()
    dataset = parse_geo_series_matrix(RAW_TH17_DIR / "GSE43957_series_matrix.txt.gz")
    assert dataset.series_id == "GSE43957"
    assert dataset.expression is not None
    assert dataset.metadata.shape[0] == 4
    assert dataset.expression.shape == (45101, 4)
    assert set(dataset.metadata["treatment"]) == {"Th0", "Th0+NaCl"}
    assert set(dataset.metadata["title"]) == {"Th0_Ctrl1", "Th0_Ctrl2", "Th0_NaCl1", "Th0_NaCl2"}


def test_cli_th17_prepare_creates_processed_outputs(tmp_path: Path) -> None:
    require_th17_raw()
    output_dir = tmp_path / "processed_th17"
    command = [
        sys.executable,
        "-m",
        "imp_causal_paper.cli",
        "th17-prepare",
        "--raw-dir",
        str(RAW_TH17_DIR),
        "--output-dir",
        str(output_dir),
    ]
    if RAW_TH17_SUPP_DIR.exists():
        command.extend(["--supp-dir", str(RAW_TH17_SUPP_DIR)])
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)
    summary = json.loads((output_dir / "summary.json").read_text())
    assert {
        "GSE43948_series",
        "GSE43949_series",
        "GSE43955_series",
        "GSE43956_series",
        "GSE43957_series",
        "GSE43969_series",
        "wu_sgk1_pathogenicity_cohort",
        "yosef_th17_network_cohort",
        "yosef_th17_network_design",
        "yosef_th17_network_evidence",
        "yosef_th17_network_regulator_summary",
    }.issubset(set(summary["dataset_order"]))
    assert summary["study_arm_dataset_counts"] == {
        "wu_sgk1_pathogenicity": 3,
        "yosef_th17_network": 9,
    }

    gse43969_summary = json.loads((output_dir / "GSE43969_series" / "summary.json").read_text())
    assert gse43969_summary["sample_count"] == 20
    assert gse43969_summary["feature_count"] == 22690
    assert gse43969_summary["has_expression_matrix"] is True
    assert gse43969_summary["study_arm"] == "yosef_th17_network"

    metadata = pd.read_csv(output_dir / "GSE43969_series" / "sample_metadata.csv")
    assert set(metadata["genotype"]) == {"IL23R knockout", "WT"}
    assert {"Tgfb+IL6", "Tgfb+IL6+IL23"}.issubset(set(metadata["treatment"]))
    assert metadata["time_hr"].tolist()[:3] == [24.0, 48.0, 49.0]
    assert set(metadata["study_arm"]) == {"yosef_th17_network"}

    yosef_cohort_summary = json.loads((output_dir / "yosef_th17_network_cohort" / "summary.json").read_text())
    assert yosef_cohort_summary["study_arm"] == "yosef_th17_network"
    assert yosef_cohort_summary["series_ids"] == ["GSE43948", "GSE43949", "GSE43955", "GSE43969"]
    assert yosef_cohort_summary["series_count"] == 4
    assert yosef_cohort_summary["sample_count"] == 112
    assert yosef_cohort_summary["expression_artifacts"] == ["GSE43948_rnaseq", "GSE43955_series", "GSE43969_series"]
    assert yosef_cohort_summary["metadata_only_series"] == ["GSE43949"]

    yosef_cohort_metadata = pd.read_csv(output_dir / "yosef_th17_network_cohort" / "sample_metadata.csv")
    assert set(yosef_cohort_metadata["study_arm"]) == {"yosef_th17_network"}
    assert set(yosef_cohort_metadata["series_id"]) == {"GSE43948", "GSE43949", "GSE43955", "GSE43969"}

    yosef_design_summary = json.loads((output_dir / "yosef_th17_network_design" / "summary.json").read_text())
    assert yosef_design_summary["study_arm"] == "yosef_th17_network"
    assert yosef_design_summary["sample_count"] == 112
    assert yosef_design_summary["series_ids"] == ["GSE43948", "GSE43949", "GSE43955", "GSE43969"]
    assert yosef_design_summary["assay_modality_counts"] == {
        "chip_seq": 2,
        "microarray": 78,
        "rna_seq": 32,
    }
    assert yosef_design_summary["experimental_axis_counts"] == {
        "chip_binding": 2,
        "genotype_time_course": 20,
        "perturbation_screen": 32,
        "time_course": 58,
    }
    assert yosef_design_summary["expression_artifact_counts"] == {
        "GSE43948_rnaseq": 32,
        "GSE43955_series": 58,
        "GSE43969_series": 20,
    }
    assert yosef_design_summary["perturbation_screen_sample_count"] == 32
    assert yosef_design_summary["chip_binding_sample_count"] == 2
    assert yosef_design_summary["dynamic_timecourse_sample_count"] == 78
    assert yosef_design_summary["exact_48h_expression_sample_count"] == 36
    assert yosef_design_summary["exact_48h_expression_series_counts"] == {
        "GSE43948": 32,
        "GSE43955": 2,
        "GSE43969": 2,
    }
    assert yosef_design_summary["exact_48h_expression_artifact_counts"] == {
        "GSE43948_rnaseq": 32,
        "GSE43955_series": 2,
        "GSE43969_series": 2,
    }
    assert yosef_design_summary["perturbation_screen_feature_count"] == 27723
    assert yosef_design_summary["dynamic_timecourse_feature_count"] == 22690
    assert yosef_design_summary["genotype_standardized_counts"] == {
        "IL23R_KO": 10,
        "WT": 10,
        "not_reported": 92,
    }
    assert yosef_design_summary["perturbation_target_counts"]["NT"] == 20
    assert yosef_design_summary["perturbation_target_counts"]["TSC22D3"] == 1

    yosef_design = pd.read_csv(output_dir / "yosef_th17_network_design" / "sample_design.csv")
    assert set(yosef_design["study_arm"]) == {"yosef_th17_network"}
    assert set(yosef_design["cell_type_standardized"].dropna()) == {"Th17"}
    assert set(yosef_design["series_id"]) == {"GSE43948", "GSE43949", "GSE43955", "GSE43969"}
    gse43948_design = yosef_design.loc[yosef_design["series_id"] == "GSE43948"]
    assert set(gse43948_design["expression_artifact"]) == {"GSE43948_rnaseq"}
    assert gse43948_design["in_regulator_ranking_panel"].all()
    assert int(gse43948_design["is_non_targeting_control"].sum()) == 20

    perturbation_matrix = pd.read_csv(
        output_dir / "yosef_th17_network_design" / "perturbation_screen_expression_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert perturbation_matrix.shape == (27723, 32)

    dynamic_matrix = pd.read_csv(
        output_dir / "yosef_th17_network_design" / "dynamic_timecourse_expression_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert dynamic_matrix.shape == (22690, 78)

    exact_48h_manifest = pd.read_csv(output_dir / "yosef_th17_network_design" / "exact_48h_expression_manifest.csv")
    assert exact_48h_manifest.shape[0] == 36
    assert exact_48h_manifest["time_hr"].eq(48.0).all()
    assert exact_48h_manifest["expression_artifact"].value_counts().sort_index().to_dict() == {
        "GSE43948_rnaseq": 32,
        "GSE43955_series": 2,
        "GSE43969_series": 2,
    }

    yosef_evidence_summary = json.loads((output_dir / "yosef_th17_network_evidence" / "summary.json").read_text())
    assert yosef_evidence_summary["study_arm"] == "yosef_th17_network"
    assert yosef_evidence_summary["perturbation_gene_count"] == 27723
    assert yosef_evidence_summary["perturbation_control_sample_count"] == 20
    assert yosef_evidence_summary["perturbation_target_sample_count"] == 12
    assert yosef_evidence_summary["perturbation_target_count"] == 12
    assert yosef_evidence_summary["target_self_observed_count"] == 11
    assert yosef_evidence_summary["target_self_missing"] == ["POU2F1A"]
    assert yosef_evidence_summary["late_time_gpl8321_sample_count"] == 38
    assert yosef_evidence_summary["late_time_gpl8321_series_counts"] == {
        "GSE43955": 20,
        "GSE43969": 18,
    }
    assert yosef_evidence_summary["exact_48h_gpl8321_sample_count"] == 4
    assert yosef_evidence_summary["exact_48h_gpl8321_series_counts"] == {
        "GSE43955": 2,
        "GSE43969": 2,
    }

    perturbation_delta = pd.read_csv(
        output_dir / "yosef_th17_network_evidence" / "perturbation_target_delta_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert perturbation_delta.shape == (27723, 12)

    perturbation_log2_fc = pd.read_csv(
        output_dir / "yosef_th17_network_evidence" / "perturbation_target_log2_fc_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert perturbation_log2_fc.shape == (27723, 12)

    self_response = pd.read_csv(output_dir / "yosef_th17_network_evidence" / "perturbation_self_response.csv")
    assert self_response.shape[0] == 12
    assert int(self_response["target_gene_observed"].sum()) == 11
    assert self_response.loc[~self_response["target_gene_observed"], "perturbation_target"].tolist() == ["POU2F1A"]

    late_time_microarray = pd.read_csv(
        output_dir / "yosef_th17_network_evidence" / "late_time_gpl8321_expression_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert late_time_microarray.shape == (22690, 38)

    exact_48h_microarray = pd.read_csv(
        output_dir / "yosef_th17_network_evidence" / "exact_48h_gpl8321_expression_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert exact_48h_microarray.shape == (22690, 4)

    regulator_summary = json.loads((output_dir / "yosef_th17_network_regulator_summary" / "summary.json").read_text())
    assert regulator_summary["study_arm"] == "yosef_th17_network"
    assert regulator_summary["rnaseq_target_summary_count"] == 12
    assert regulator_summary["target_self_observed_count"] == 11
    assert regulator_summary["late_time_gpl8321_contrast_count"] == 26
    assert regulator_summary["late_time_gpl8321_contrast_family_counts"] == {
        "gse43955_il23_effect": 4,
        "gse43955_treatment_vs_th0": 5,
        "gse43969_il23_effect_il23r_ko": 4,
        "gse43969_il23_effect_wt": 4,
        "gse43969_wt_vs_il23rko_tgfb_il6": 5,
        "gse43969_wt_vs_il23rko_tgfb_il6_il23": 4,
    }
    assert regulator_summary["candidate_regulator_count"] == 15
    assert regulator_summary["paper_finalnet_negative_candidates"] == ["STAT6", "TCFEB", "TRIM24"]
    assert regulator_summary["paper_finalnet_negative_candidates_observed_in_rnaseq"] == ["STAT6", "TCFEB", "TRIM24"]
    assert regulator_summary["candidate_regulators_without_rnaseq_gene_match"] == ["POU2F1A"]

    rnaseq_target_summary = pd.read_csv(
        output_dir / "yosef_th17_network_regulator_summary" / "rnaseq_target_summary.csv"
    )
    assert rnaseq_target_summary.shape[0] == 12
    assert int(rnaseq_target_summary["target_gene_observed"].sum()) == 11
    assert rnaseq_target_summary.loc[
        rnaseq_target_summary["perturbation_target"] == "TSC22D3", "self_log2_fold_change"
    ].iloc[0] > 2.0

    contrast_manifest = pd.read_csv(
        output_dir / "yosef_th17_network_regulator_summary" / "gpl8321_late_time_contrast_manifest.csv"
    )
    assert contrast_manifest.shape[0] == 26
    assert set(contrast_manifest["series_id"]) == {"GSE43955", "GSE43969"}

    contrast_matrix = pd.read_csv(
        output_dir / "yosef_th17_network_regulator_summary" / "gpl8321_late_time_contrast_matrix.tsv.gz",
        sep="\t",
        index_col=0,
    )
    assert contrast_matrix.shape == (22690, 26)

    candidate_evidence = pd.read_csv(
        output_dir / "yosef_th17_network_regulator_summary" / "candidate_regulator_evidence.csv"
    )
    assert candidate_evidence.shape[0] == 15
    stat6_row = candidate_evidence.loc[candidate_evidence["regulator"] == "STAT6"].iloc[0]
    assert bool(stat6_row["is_paper_finalnet_negative_48h_candidate"]) is True
    assert bool(stat6_row["rnaseq_gene_observed"]) is True
    assert bool(stat6_row["is_rnaseq_perturbation_target"]) is False
    pou2f1a_row = candidate_evidence.loc[candidate_evidence["regulator"] == "POU2F1A"].iloc[0]
    assert bool(pou2f1a_row["is_rnaseq_perturbation_target"]) is True
    assert bool(pou2f1a_row["rnaseq_gene_observed"]) is False

    wu_cohort_summary = json.loads((output_dir / "wu_sgk1_pathogenicity_cohort" / "summary.json").read_text())
    assert wu_cohort_summary["study_arm"] == "wu_sgk1_pathogenicity"
    assert wu_cohort_summary["series_ids"] == ["GSE43956", "GSE43957"]
    assert wu_cohort_summary["series_count"] == 2
    assert wu_cohort_summary["sample_count"] == 8
    assert wu_cohort_summary["expression_artifacts"] == ["GSE43956_series", "GSE43957_series"]
    assert wu_cohort_summary["metadata_only_series"] == []

    gse43949_summary = json.loads((output_dir / "GSE43949_series" / "summary.json").read_text())
    assert gse43949_summary["sample_count"] == 2
    assert gse43949_summary["feature_count"] == 0
    assert gse43949_summary["has_expression_matrix"] is False
    assert gse43949_summary["library_strategies"] == ["ChIP-Seq"]
    assert gse43949_summary["study_arm"] == "yosef_th17_network"

    if RAW_TH17_SUPP_DIR.exists():
        gse43956_manifest_summary = json.loads((output_dir / "GSE43956_bundle_manifest" / "summary.json").read_text())
        assert gse43956_manifest_summary["archive_file_name"] == "GSE43956_RAW.tar"
        assert gse43956_manifest_summary["entry_count"] == 4
        assert gse43956_manifest_summary["asset_kind_counts"] == {"affymetrix_cel": 4}
        assert gse43956_manifest_summary["resolved_series_counts"] == {"GSE43956": 4}
        assert gse43956_manifest_summary["resolved_study_arm_counts"] == {"wu_sgk1_pathogenicity": 4}
        assert gse43956_manifest_summary["unresolved_sample_accessions"] == []

        gse43957_manifest_summary = json.loads((output_dir / "GSE43957_bundle_manifest" / "summary.json").read_text())
        assert gse43957_manifest_summary["archive_file_name"] == "GSE43957_RAW.tar"
        assert gse43957_manifest_summary["entry_count"] == 4
        assert gse43957_manifest_summary["asset_kind_counts"] == {"affymetrix_cel": 4}
        assert gse43957_manifest_summary["resolved_series_counts"] == {"GSE43957": 4}
        assert gse43957_manifest_summary["resolved_study_arm_counts"] == {"wu_sgk1_pathogenicity": 4}
        assert gse43957_manifest_summary["unresolved_sample_accessions"] == []

        manifest_summary = json.loads((output_dir / "GSE43970_bundle_manifest" / "summary.json").read_text())
        assert manifest_summary["asset_kind_counts"] == {
            "affymetrix_cel": 86,
            "igv_tdf_track": 2,
            "rsem_gene_expression": 32,
            "tar_archive": 1,
        }
        assert manifest_summary["resolved_series_counts"] == {
            "GSE43948": 32,
            "GSE43949": 2,
            "GSE43955": 58,
            "GSE43956": 4,
            "GSE43957": 4,
            "GSE43969": 20,
        }
        assert manifest_summary["resolved_study_arm_counts"] == {
            "wu_sgk1_pathogenicity": 8,
            "yosef_th17_network": 112,
        }
        assert manifest_summary["unresolved_sample_accessions"] == []


def test_prepare_gse43948_perturbation_rnaseq_real_data(tmp_path: Path) -> None:
    require_th17_supp()
    summary = prepare_th17_perturbation_rnaseq(RAW_TH17_SUPP_DIR, tmp_path / "GSE43948")
    assert summary["series_id"] == "GSE43948"
    assert summary["sample_count"] == 32
    assert summary["feature_count"] == 27723
    assert summary["control_sample_count"] == 20
    assert summary["perturbed_sample_count"] == 12
    assert summary["time_hr_values"] == [48.0]
    assert {"EGR2", "ETV6", "FAS", "IKZF4", "IRF8", "MINA", "POU2F1A", "PROCR", "SMARCA4", "SP4", "TSC22D3", "ZEB1"} == set(summary["perturbation_targets"])


def test_prepare_gse43970_manifest_real_data(tmp_path: Path) -> None:
    require_th17_raw()
    if not (RAW_TH17_SUPP_DIR / "GSE43970_filelist.txt").exists():
        pytest.skip("GSE43970 file list is not available in data/raw/th17_geo_supp")

    sample_to_series = {}
    for name in [
        "GSE43948_series_matrix.txt.gz",
        "GSE43949_series_matrix.txt.gz",
        "GSE43955_series_matrix.txt.gz",
        "GSE43956_series_matrix.txt.gz",
        "GSE43957_series_matrix.txt.gz",
        "GSE43969_series_matrix.txt.gz",
    ]:
        dataset = parse_geo_series_matrix(RAW_TH17_DIR / name)
        sample_to_series.update({sample_id: dataset.series_id for sample_id in dataset.metadata["sample_id"].astype(str)})

    summary = prepare_geo_supplementary_manifest(
        RAW_TH17_SUPP_DIR / "GSE43970_filelist.txt",
        tmp_path / "GSE43970_bundle_manifest",
        sample_to_series,
    )
    assert summary["series_id"] == "GSE43970"
    assert summary["entry_count"] == 121
    assert summary["archive_entry_count"] == 1
    assert summary["file_entry_count"] == 120
    assert summary["asset_kind_counts"] == {
        "affymetrix_cel": 86,
        "igv_tdf_track": 2,
        "rsem_gene_expression": 32,
        "tar_archive": 1,
    }
    assert summary["resolved_series_counts"] == {
        "GSE43948": 32,
        "GSE43949": 2,
        "GSE43955": 58,
        "GSE43956": 4,
        "GSE43957": 4,
        "GSE43969": 20,
    }
    assert summary["resolved_study_arm_counts"] == {
        "wu_sgk1_pathogenicity": 8,
        "yosef_th17_network": 112,
    }
    assert summary["unresolved_sample_accessions"] == []


def test_prepare_gse43956_tar_manifest_real_data(tmp_path: Path) -> None:
    require_th17_raw()
    if not (RAW_TH17_SUPP_DIR / "GSE43956_RAW.tar").exists():
        pytest.skip("GSE43956 raw tarball is not available in data/raw/th17_geo_supp")

    sample_to_series = {}
    for name in [
        "GSE43948_series_matrix.txt.gz",
        "GSE43949_series_matrix.txt.gz",
        "GSE43955_series_matrix.txt.gz",
        "GSE43956_series_matrix.txt.gz",
        "GSE43957_series_matrix.txt.gz",
        "GSE43969_series_matrix.txt.gz",
    ]:
        dataset = parse_geo_series_matrix(RAW_TH17_DIR / name)
        sample_to_series.update({sample_id: dataset.series_id for sample_id in dataset.metadata["sample_id"].astype(str)})

    summary = prepare_geo_tar_manifest(
        RAW_TH17_SUPP_DIR / "GSE43956_RAW.tar",
        tmp_path / "GSE43956_bundle_manifest",
        sample_to_series,
    )
    assert summary["series_id"] == "GSE43956"
    assert summary["archive_file_name"] == "GSE43956_RAW.tar"
    assert summary["entry_count"] == 4
    assert summary["archive_entry_count"] == 1
    assert summary["file_entry_count"] == 4
    assert summary["asset_kind_counts"] == {"affymetrix_cel": 4}
    assert summary["resolved_series_counts"] == {"GSE43956": 4}
    assert summary["resolved_study_arm_counts"] == {"wu_sgk1_pathogenicity": 4}
    assert summary["unresolved_sample_accessions"] == []


def test_prepare_gse43957_tar_manifest_real_data(tmp_path: Path) -> None:
    require_th17_raw()
    if not (RAW_TH17_SUPP_DIR / "GSE43957_RAW.tar").exists():
        pytest.skip("GSE43957 raw tarball is not available in data/raw/th17_geo_supp")

    sample_to_series = {}
    for name in [
        "GSE43948_series_matrix.txt.gz",
        "GSE43949_series_matrix.txt.gz",
        "GSE43955_series_matrix.txt.gz",
        "GSE43956_series_matrix.txt.gz",
        "GSE43957_series_matrix.txt.gz",
        "GSE43969_series_matrix.txt.gz",
    ]:
        dataset = parse_geo_series_matrix(RAW_TH17_DIR / name)
        sample_to_series.update({sample_id: dataset.series_id for sample_id in dataset.metadata["sample_id"].astype(str)})

    summary = prepare_geo_tar_manifest(
        RAW_TH17_SUPP_DIR / "GSE43957_RAW.tar",
        tmp_path / "GSE43957_bundle_manifest",
        sample_to_series,
    )
    assert summary["series_id"] == "GSE43957"
    assert summary["archive_file_name"] == "GSE43957_RAW.tar"
    assert summary["entry_count"] == 4
    assert summary["archive_entry_count"] == 1
    assert summary["file_entry_count"] == 4
    assert summary["asset_kind_counts"] == {"affymetrix_cel": 4}
    assert summary["resolved_series_counts"] == {"GSE43957": 4}
    assert summary["resolved_study_arm_counts"] == {"wu_sgk1_pathogenicity": 4}
    assert summary["unresolved_sample_accessions"] == []
