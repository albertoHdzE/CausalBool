#!/usr/bin/env python
"""Export the executed replication notebook's results to machine-readable JSON
(AUDIT01/T2.3 step 1).

Before this script existed, every quantitative claim in README.md /
COMPARISON.md traced only to prose and to human-readable notebook cells; there
was no machine-readable artifact at all. This exports one JSON per experiment
block from the EXECUTED notebook (paper_walkthrough.ipynb), each entry carrying
the source cell index and verbatim output text so every number keeps its
provenance. Extraction is pure parsing of committed bytes — deterministic by
construction, no re-execution needed.

Regenerate:
    .venv/bin/python scripts/export_notebook_results.py
Outputs (results/):
    fig1_separation.json          Fig. 1 strings + Fig. 1F-G CA separation
    fig2_mirror_attribution.json  index-set mirror on the Fig. 2 image
    graphs_deconvolution.json     Figs. 3C-D / 4 graph experiments
    ctm_parity.json               CTM table parity against the authors' CSV
    capability_tally.json         claim-by-claim tally parsed from COMPARISON.md
"""

from __future__ import annotations

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_PATH = os.path.join(BASE, "notebooks", "paper_walkthrough.ipynb")
COMPARISON = os.path.join(BASE, "COMPARISON.md")
RESULTS = os.path.join(BASE, "results")


def cell_text(cell):
    out_texts = []
    for out in cell.get("outputs", []):
        if out.get("output_type") == "stream":
            out_texts.append("".join(out.get("text", [])))
        elif "data" in out and "text/plain" in out.get("data", {}):
            out_texts.append("".join(out["data"]["text/plain"]))
    return "".join(out_texts)


def load_cells():
    nb = json.load(open(NB_PATH))
    cells = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        src = "".join(c.get("source", []))
        txt = cell_text(c)
        if txt.strip():
            cells.append(dict(index=i, source=src, output=txt))
    return cells


def grab(cells, pattern):
    """All cells whose OUTPUT matches `pattern`, verbatim."""
    return [dict(cell_index=c["index"], output=c["output"].strip())
            for c in cells if re.search(pattern, c["output"])]


def one(cells, pattern):
    g = grab(cells, pattern)
    if len(g) != 1:
        raise SystemExit(f"export_notebook_results: expected exactly one "
                         f"cell matching {pattern!r}, found {len(g)}")
    return g[0]


def parse_keyvalues(text):
    """`key value` lines -> dict of floats/ints when parseable."""
    kv = {}
    for line in text.splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z_0-9 ]*?)\s{2,}([0-9.eE+-]+)\s*$", line)
        if m:
            k, v = m.group(1).strip(), m.group(2)
            try:
                kv[k] = int(v) if re.fullmatch(r"-?\d+", v) else float(v)
            except ValueError:
                pass
    return kv


def write(name, payload):
    path = os.path.join(RESULTS, name)
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"wrote results/{name}")


def main():
    cells = load_cells()

    # ---- Fig. 1: strings and grossly-different CA --------------------------
    sep = one(cells, r"Cliff's delta = -0\.770")
    fig2c = grab(cells, r"Cliff's delta = \+0\.147")
    write("fig1_separation.json", dict(
        block="Fig. 1A-B strings; Fig. 1F-G CA 255 vs 110; Sup. Fig. 2c re-test",
        cliff_delta_fig1=parse_keyvalues(sep["output"]) or None,
        raw_outputs=[sep, fig2c]))

    # ---- Fig. 2 mirror ------------------------------------------------------
    mech_map = one(cells, r"accuracy_on_decided")
    col_attr = one(cells, r"columns attributed to rule 60")
    b3 = one(cells, r"cells with no surviving rule")
    b5 = one(cells, r"per-pixel attribution vs withheld ground truth")
    mm_kv = parse_keyvalues(mech_map["output"])
    b5_acc = float(re.search(r"ground truth:\s*([0-9.]+)", b5["output"]).group(1))
    b5_decided = int(re.search(r"on (\d+) decided", b5["output"]).group(1))
    no_rule_cols = int(re.search(r"no surviving rule\s*:\s*(\d+)",
                                 b3["output"]).group(1))
    write("fig2_mirror_attribution.json", dict(
        block="Part IX / Track B: index-set mirror on the rule-60/rule-110 image",
        mechanism_map=dict(cell_index=mech_map["cell_index"], parsed=mm_kv,
                           accuracy_on_decided=mm_kv.get("accuracy_on_decided"),
                           cells_decided=int(mm_kv.get("cells_decided", -1))),
        track_b=dict(cell_index=b5["cell_index"],
                     per_pixel_attribution_vs_withheld_ground_truth=b5_acc,
                     decided_columns=b5_decided,
                     columns_with_no_surviving_rule=no_rule_cols),
        note=("99.8 per cent appears nowhere in this notebook; it was the "
              "earlier SYNTHETIC-data figure (see _build_notebook.py). The "
              "executed on-figure numbers are the two accuracies above."),
        raw_outputs=[mech_map, col_attr, b3, b5]))

    # ---- Graphs -------------------------------------------------------------
    fig4 = one(cells, r"Figure 4 outcome")
    ranks = one(cells, r"ranks of the planted edges under three node orderings")
    peel = one(cells, r"internal edges explained for")
    recognisers = one(cells, r"recognisers, on graphs whose law is known")
    write("graphs_deconvolution.json", dict(
        block="Figs. 3C-D / Fig. 4 / Sec. 3.2: BDM deconvolution vs index-set law",
        figure4_outcome=parse_keyvalues(fig4["output"]),
        raw_outputs=[fig4, ranks, peel, recognisers]))

    # ---- CTM parity ---------------------------------------------------------
    ctm = one(cells, r"blocks agreeing with pybdm")
    blocks_listed = int(re.search(r"blocks listed.*?:\s*(\d+)", ctm["output"]).group(1))
    blocks_agree = int(re.search(r"blocks agreeing.*?:\s*(\d+)", ctm["output"]).group(1))
    write("ctm_parity.json", dict(
        block="Part X: authors' K-4x4.csv CTM table vs pybdm",
        blocks_listed=blocks_listed, blocks_agreeing_to_1e6=blocks_agree,
        elementwise_equal=(blocks_listed == blocks_agree == 65536),
        raw_outputs=[ctm]))

    # ---- Capability tally, parsed from COMPARISON.md ------------------------
    ctext = open(COMPARISON).read()
    m_sec = re.search(r"^## Claim by claim$(.*?)(?=^## )", ctext,
                      re.M | re.S)
    if not m_sec:
        raise SystemExit("export_notebook_results: '## Claim by claim' "
                         "section not found in COMPARISON.md")
    section = m_sec.group(1)
    rows = []
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if parts and re.fullmatch(r"\d+b?", parts[0]) and len(parts) >= 5:
            rows.append(parts)
    capability_rows = rows
    tally = dict(ours=0, both=0, theirs=0, neither=0)
    for r in capability_rows:
        verdict = r[-1].lower()
        for k in tally:
            if k in verdict:
                tally[k] += 1
                break
    write("capability_tally.json", dict(
        block="COMPARISON.md claim-by-claim capability table, machine-counted",
        n_capability_rows=len(capability_rows), tally=tally,
        row_numbers=[r[0] for r in capability_rows],
        note=("this count is the authoritative tally; README's summary must "
              "match it")))

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
