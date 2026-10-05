"""Supervisor audit: saved bytes only; writes only adjacent audit_review.json.

Run from repository root: venv/bin/python -B <this file>.
No encoding, corpus generation, notebook execution, or frozen-run writes.
"""
import hashlib
import json
import sys
import tarfile
import time
from collections import defaultdict
from pathlib import Path

START = time.monotonic()
OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
REPO = ROOT.parent
RUN = ROOT / "results/hierarchy_search_v3a/search-confirm-v3a-r1"
PACKET = ROOT / "protocols/hierarchy_search_v3a"
sys.path[:0] = [str(ROOT), str(ROOT / "experiments"), str(REPO / "src")]
sys.dont_write_bytecode = True

import numpy as np
from hierarchy.decode import decode_archive
from hierarchy.freeze_v2 import canonical, closure_files, method_configs
from hierarchy.report_v3a import trace_problems
from hierarchy.study import get_study
from search_v3a.development import compatibility


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def tree(path):
    return {str(p.relative_to(path)): sha(p.read_bytes())
            for p in sorted(path.rglob("*")) if p.is_file()}


before = tree(RUN)
notebook19 = ROOT / "notebooks/19_bdm_and_index_complexity.ipynb"
nb19_sha = sha(notebook19.read_bytes())
fr = read(RUN / "freeze.json")
freeze_sha = sha(canonical(fr))
assert freeze_sha == (RUN / "freeze.sha256").read_text().strip()
assert freeze_sha == "05dd799d154e5e53a36bac7dca49f0438ca27b58b2df94c045eeca2fa6dd69e5"
groups = ("source_sha256", "protocol_sha256", "prefreeze_evidence_sha256")
for group in groups:
    for name, digest in fr[group].items():
        assert sha((REPO / name).read_bytes()) == digest, name
assert sha((RUN / "source_snapshot.tar").read_bytes()) == fr["snapshot"]["sha256"]
with tarfile.open(RUN / "source_snapshot.tar") as archive:
    assert len(archive.getmembers()) == fr["snapshot"]["members"]
    for group in groups + ("informational_sha256",):
        for name, digest in fr[group].items():
            assert sha(archive.extractfile(name).read()) == digest, name

link = read(RUN / "prefreeze/dev_fingerprint_link.json")
for kind in ("control", "treatment"):
    st = get_study("search-v3a-dev-" + kind)
    blob = {"sources": {p: sha((REPO / p).read_bytes()) for p in closure_files(st)},
            "methods": {m: v["sha256"] for m, v in method_configs(st).items()}}
    assert "dev:" + sha(canonical(blob)) == link[kind]["current"]
    blob["sources"][link["only_difference"]["file"]] = link["only_difference"]["development_time_sha256"]
    assert "dev:" + sha(canonical(blob)) == link[kind]["reconstructed"]
    paths = (RUN.parent / "development" / f"dev-v3a-{kind}-a1" / "rows").glob("*.json")
    fingerprints = {r["freeze_sha256"] for p in paths for r in read(p)}
    assert fingerprints == set(link[kind]["rows_fingerprints"])

cases = read(PACKET / "intended_cases.json")["cases"]
assert len(cases) == len({c["case_id"] for c in cases}) == 256
assert {p.stem for p in (RUN / "rows").glob("*.json")} == {c["case_id"] for c in cases}
inputs = {}
for path in RUN.glob("corpus_manifest.*.jsonl"):
    for line in path.read_text().splitlines():
        m = json.loads(line)
        for cid, digest in zip(m["case_ids"], (m["base_sha256"], m["full_sha256"])):
            assert cid not in inputs
            inputs[cid] = digest
baselines = ("raw", "rle", "gaps", "period", "bernoulli", "context", "zlib", "lzma", "pair_grammar")
methods = ("hid_full", "hid_refine4") + baselines + ("baseline_best",)
decoded, cells = {}, defaultdict(lambda: defaultdict(list))
archive_rows = trace_count = 0
for c in cases:
    rows = read(RUN / "rows" / (c["case_id"] + ".json"))
    assert len(rows) == 12 and {r["method"] for r in rows} == set(methods)
    data = {}
    for r in rows:
        assert r["status"] == "ok" and r["decode_ok"] is True
        assert r["freeze_sha256"] == freeze_sha
        assert r["case_id"] == c["case_id"] and r["n_bits"] == c["n_bits"]
        assert r["input_sha256"] == inputs[c["case_id"]]
        b = (RUN / r["archive_path"]).read_bytes()
        h = sha(b)
        assert h == r["archive_sha256"] and len(b) * 8 == r["archive_bits"]
        if h not in decoded:
            s = decode_archive(b)
            decoded[h] = len(s), sha(s.encode("ascii"))
        assert decoded[h] == (c["n_bits"], inputs[c["case_id"]])
        data[r["method"]] = b
        if r["method"] != "baseline_best":
            archive_rows += 1
            assert r["config_sha256"] == fr["method_configs"][r["method"]]["sha256"]
        if r["method"] in ("hid_full", "hid_refine4"):
            assert r["trace_status"] == "complete"
            tb = (RUN / r["trace_path"]).read_bytes()
            assert sha(tb) == r["trace_sha256"]
            assert not trace_problems(json.loads(tb), r)
            trace_count += 1
    best = min(baselines, key=lambda m: (len(data[m]), data[m][4], data[m]))
    pb = next(r for r in rows if r["method"] == "baseline_best")
    assert pb["selected_method"] == best and data["baseline_best"] == data[best]
    if c["role"] != "controls":
        key = (c["role"], c["family"], c["base_length"])
        cells[key][c["replicate"]].append(8 * (len(data["hid_full"]) - len(data["hid_refine4"])) / c["n_bits"])
assert archive_rows == 2816 and trace_count == 512
assert len(cells) == 6 and all(len(v) == 20 for v in cells.values())
assert all(len(pair) == 2 for v in cells.values() for pair in v.values())
units = {k: np.array([sum(v[r]) / 2 for r in sorted(v)]) for k, v in sorted(cells.items())}
point = float(np.mean([v.mean() for v in units.values()]))
rng = np.random.default_rng(55001)
draws = sum(v[rng.integers(0, 20, (10000, 20))].mean(axis=1) for v in units.values()) / 6
ci = np.quantile(draws, [0.005, 0.995]).tolist()
decision = read(RUN / "DECISION.json")
assert abs(point - decision["estimate_bits_per_input_bit"]) < 1e-15
assert np.allclose(ci, decision["ci99"], atol=1e-15, rtol=0)
assert ci[1] < 0 and decision["verdict"] == "HARMFUL"
comp = compatibility("dev-v3a-control-a1")
assert comp["pass"] and comp["archives_byte_identical"] == 1792

nbchecks = read(RUN / "notebook/run2.checks.json")
assert nbchecks["all_checks_pass"] and all(nbchecks["checks"].values())
assert sha((REPO / nbchecks["harness"]["path"]).read_bytes()) == nbchecks["harness"]["sha256"]
assert sha((ROOT / "notebooks/build_20.py").read_bytes()) == nbchecks["builder_sha256"]
assert (ROOT / "notebooks/20_hierarchy_search_v3a.ipynb").read_bytes() == (RUN / "notebook/run2.notebook_dir.ipynb").read_bytes()
for name in ("notebook_dir", "repository_root"):
    nb = read(RUN / f"notebook/run2.{name}.ipynb")
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) == 7 and all(c["execution_count"] is not None for c in code)
    assert not any(o["output_type"] == "error" for c in code for o in c["outputs"])
events = [json.loads(s) for s in (RUN / "ledger/resource_events.jsonl").read_text().splitlines()]
spans = {}
for category in ("development", "prospective", "report_verification"):
    starts = [e["t"] for e in events if e["category"] == category and e["event"] == "start"]
    stops = [e["t"] for e in events if e["category"] == category and e["event"] == "stop"]
    assert len(starts) == len(stops) == 1
    spans[category] = stops[0] - starts[0]
assert before == tree(RUN) and nb19_sha == sha(notebook19.read_bytes())
out = {"pass": True, "freeze_sha256": freeze_sha,
       "hashed_files": {g: len(fr[g]) for g in groups}, "snapshot_members": fr["snapshot"]["members"],
       "encoder_archive_rows_checked": archive_rows, "portfolio_rows_checked": 256,
       "distinct_archives_decoded": len(decoded), "trace_sidecars_checked": trace_count,
       "compatibility_archives_equal": comp["archives_byte_identical"],
       "compatibility_fields_equal": not comp["differences"], "development_fingerprints_reconstructed": True,
       "primary_units": 120, "estimate": point, "ci99": ci, "verdict": "HARMFUL",
       "notebook20_saved_evidence_checked_without_reexecution": True,
       "notebook19_sha256": nb19_sha, "run_files_preserved": len(before),
       "executor_closed_spans_s": spans, "executor_total_s": sum(spans.values()),
       "audit_wall_s": time.monotonic() - START}
(OUT / "audit_review.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
