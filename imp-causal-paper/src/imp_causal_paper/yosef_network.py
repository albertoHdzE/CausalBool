"""Parse Yosef et al. 2013 (Nature 496, 461-468) Supplementary Table S3
into three time-window directed regulatory networks.

Source: doi:10.1038/nature11981, MOESM14 (Table S3).
The table contains regulatory interactions in three temporal windows:
  - Early   (0.5-2 h)   → Zenil's "EarlyNet"
  - Intermediate (4-16 h)  → Zenil's "IntermediateNet"
  - Late    (20-72 h)  → Zenil's "FinalNet"

Each row is a directed edge TF → Gene with evidence codes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import xlrd

SHEET_TO_ZENIL = {
    "Early": "EarlyNet",
    "Intermediate": "IntermediateNet",
    "Late": "FinalNet",
}

DEFAULT_XLS = Path(__file__).resolve().parents[2] / "data" / "raw" / "yosef_network" / "table_s3_regulatory_interactions.xls"


@dataclass(frozen=True)
class YosefNetwork:
    """A single time-window regulatory sub-network."""
    zenil_name: str
    yosef_sheet: str
    graph: nx.DiGraph
    edge_count: int
    tf_count: int
    target_count: int
    node_count: int


def parse_yosef_networks(xls_path: Path | str | None = None) -> dict[str, YosefNetwork]:
    """Parse the three time-window networks from Table S3.

    Returns a dict keyed by Zenil name: EarlyNet, IntermediateNet, FinalNet.
    """
    path = Path(xls_path) if xls_path else DEFAULT_XLS
    if not path.exists():
        raise FileNotFoundError(
            f"Yosef Table S3 not found at {path}. "
            "Download from https://www.nature.com/articles/nature11981 "
            "(Supplementary Table 3, MOESM14)."
        )

    wb = xlrd.open_workbook(str(path))
    networks: dict[str, YosefNetwork] = {}

    for sheet_name, zenil_name in SHEET_TO_ZENIL.items():
        sh = wb.sheet_by_name(sheet_name)
        G = nx.DiGraph()
        tfs: set[str] = set()
        targets: set[str] = set()

        for r in range(1, sh.nrows):
            tf = str(sh.cell_value(r, 0)).strip()
            gene = str(sh.cell_value(r, 1)).strip()
            if not tf or not gene:
                continue
            G.add_edge(tf, gene)
            tfs.add(tf)
            targets.add(gene)

        networks[zenil_name] = YosefNetwork(
            zenil_name=zenil_name,
            yosef_sheet=sheet_name,
            graph=G,
            edge_count=G.number_of_edges(),
            tf_count=len(tfs),
            target_count=len(targets),
            node_count=G.number_of_nodes(),
        )

    return networks
