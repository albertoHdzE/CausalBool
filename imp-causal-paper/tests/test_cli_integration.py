from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_cli_all_creates_expected_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"
    plots_dir = tmp_path / "plots"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "imp_causal_paper.cli",
            "all",
            "--output-dir",
            str(output_dir),
            "--plots-dir",
            str(plots_dir),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert (output_dir / "graphs" / "summary.json").exists()
    assert (output_dir / "ca" / "summary.json").exists()
    assert (output_dir / "boolean" / "summary.json").exists()
    assert (plots_dir / "graphs" / "paper_fig4_graph_signature.png").exists()
    assert (plots_dir / "ca" / "paper_fig3_ca_reconstruction.png").exists()
    assert (plots_dir / "boolean" / "paper_fig4_boolean_perturbations.png").exists()
    ca_summary = json.loads((output_dir / "ca" / "summary.json").read_text())
    assert ca_summary["exact_match"] is True
