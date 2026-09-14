"""Analysis over validated study artefacts only.

This module intentionally reports descriptive summaries rather than treating
perturbations within one base network as independent replicates.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .io import read_jsonl
from .io import read_json
from .stats import constrained_optimum


def analyse_validated_study(study_dir: str | Path, *, out_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(study_dir)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    source_hashes: dict[str, str] = {}
    for path in sorted(root.glob("*/*/catalogue.jsonl")):
        raw = path.read_bytes()
        source_hashes[str(path.relative_to(root))] = hashlib.sha256(raw).hexdigest()
        rows = [row for row in read_jsonl(path) if row.get("accepted_validation")]
        parts = path.relative_to(root).parts
        family = parts[0].split("_n", 1)[0]
        groups[(family, parts[1])].extend(rows)
    by_group = {}
    for (family, kind), rows in sorted(groups.items()):
        attacks = [row for row in rows if not str(row.get("perturbation_id", "")).endswith(":identity")]
        by_group[f"{family}/{kind}"] = {
            "n_validated_rows": len(rows), "n_attack_rows": len(attacks),
            "support_change_rate": (sum(row["support"]["support_jaccard"] > 0 for row in attacks) / len(attacks)
                                     if attacks else 0.0),
            "infinite_kl_rate": (sum(row["infinite_kl"] for row in attacks) / len(attacks)
                                 if attacks else 0.0),
            "mean_total_variation": (sum(row["total_variation"] for row in attacks) / len(attacks)
                                      if attacks else 0.0),
            "mean_jensen_shannon": (sum(row["jensen_shannon"] for row in attacks) / len(attacks)
                                     if attacks else 0.0),
            "replication_unit": "base_network",
        }
    result = {"study_dir": str(root), "source_hashes": source_hashes,
              "groups": by_group, "denominator": "accepted_validation_rows; clustered by base in inference"}
    if out_path is not None:
        Path(out_path).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def sensitivity_over_validated_study(
    study_dir: str | Path,
    *,
    budgets: tuple[float, ...] = (0.0, 0.1, 0.25, 0.5),
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Re-evaluate declared exact rows over fixed loss and KL sensitivities.

    This is a descriptive sensitivity analysis over the already enumerated
    catalogue. It never expands the catalogue and never treats perturbations
    within one base network as independent replications.
    """
    root = Path(study_dir)
    if any(budget < 0 for budget in budgets):
        raise ValueError("KL budgets must be non-negative")
    output: dict[str, Any] = {"budgets": list(budgets), "groups": {},
                              "replication_unit": "base_network",
                              "source": "accepted_exact_catalogue_rows"}
    for path in sorted(root.glob("*/*/catalogue.jsonl")):
        rows = [row for row in read_jsonl(path) if row.get("accepted_validation")]
        if not rows:
            continue
        base = read_json(path.parent / "base.json")
        baseline = base["repertoire"]
        group = str(path.relative_to(root).parent)
        target_params = next((row.get("loss_params", {}) for row in rows
                              if row.get("loss_id") == "L_SINGLE_TARGET"), {})
        output["groups"][group] = {
            "losses": {
                "L_SINGLE_TARGET": [
                    constrained_optimum(rows, baseline, budget,
                                        loss_id="L_SINGLE_TARGET",
                                        loss_params=target_params)
                    for budget in budgets
                ],
                "L_LINEAR": [
                    constrained_optimum(rows, baseline, budget,
                                        loss_id="L_LINEAR",
                                        loss_params={"weights": [1.0 / base["N"]] * base["N"]})
                    for budget in budgets
                ],
            }
        }
    if out_path is not None:
        Path(out_path).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return output
