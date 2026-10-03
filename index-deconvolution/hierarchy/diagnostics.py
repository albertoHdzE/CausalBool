"""BDM diagnostics through the shared owner (benchmark annex B5). Never a code length.

For ten confirmation objects (replicate 1000, base length 1024, non-ragged) and
199 marginal-preserving bit permutations each, every configuration in the
full-coverage matrix is scored by ``src/description_lengths.py``:

    block b in {4, 8, 9, 12}
    boundary "recursive" (aligned, every bit scored) or "sliding" (shift 1, raise)
    input circular right rotation r in the distinct set {0, 1, b-1}

Setting selection is calibrated SYMMETRICALLY: every row, observed or null, gets
T_i = min_c u_ic with u_ic its inclusive lower-tail rank fraction within
configuration c, and the adaptive p is count(T_i <= T_0)/200, never zero.
Scores are rounded to ten decimals before ranking. The rotation is applied to the
diagnostic object; it is not a free operation in the compression arm.
"""
from __future__ import annotations

import sys
from pathlib import Path

DIAG_FAMILIES = ("F01", "F02", "F03", "F04", "F05", "F06", "F12", "F07", "F08", "F09")
BLOCKS = (4, 8, 9, 12)
BOUNDARIES = ("recursive", "sliding")
NULL_DRAWS = 199
REPLICATE, BASE_LENGTH = 1000, 1024


def _owner():
    src = str(Path(__file__).resolve().parents[2] / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import description_lengths as dl
    got = Path(dl.__file__).resolve()
    if got != Path(src, "description_lengths.py").resolve():
        raise ImportError(f"description_lengths resolved to {got}")
    return dl


def configurations() -> list[dict]:
    out = []
    for b in BLOCKS:
        for boundary in BOUNDARIES:
            for r in sorted({0, 1, b - 1}):
                out.append({"block": b, "boundary": boundary, "rotation": r})
    return out


def rotate(s: str, r: int) -> str:
    return s[-r:] + s[:-r] if r else s


def score(dl, s: str, cfg: dict) -> tuple[float, int]:
    x = rotate(s, cfg["rotation"])
    if cfg["boundary"] == "recursive":
        d = dl.bdm_1d_partition(x, block=cfg["block"], remainder="recursive")
    else:
        d = dl.bdm_1d_partition(x, block=cfg["block"], shift=1, remainder="raise")
    return d["score"], d["covered_bits"]


def null_strings(bits: str, family: str, split: str = "confirmation",
                 replicate: int = REPLICATE) -> list[str]:
    from .corpus import stream_rng
    out = []
    for draw in range(NULL_DRAWS):
        rng = stream_rng(split, family, BASE_LENGTH, replicate, f"bdm_null_{draw}")
        lst = list(bits)
        rng.shuffle(lst)
        out.append("".join(lst))
    return out


def adaptive(matrix: list[list[float]]) -> dict:
    """matrix[i][c], row 0 observed. Returns adaptive and fixed-setting p-values."""
    rows = len(matrix)
    cols = len(matrix[0])
    rounded = [[round(v, 10) for v in row] for row in matrix]
    u = [[0.0] * cols for _ in range(rows)]
    for c in range(cols):
        col = [rounded[i][c] for i in range(rows)]
        for i in range(rows):
            u[i][c] = sum(1 for v in col if v <= col[i]) / rows
    t = [min(u[i]) for i in range(rows)]
    adaptive_p = sum(1 for i in range(rows) if t[i] <= t[0]) / rows
    fixed = [u[0][c] for c in range(cols)]           # inclusive lower tail of the observed row
    selected = min(range(cols), key=lambda c: (u[0][c], c))
    return {"adaptive_p": adaptive_p, "T0": t[0], "fixed_p": fixed, "selected_config": selected,
            "r_null_at_or_below": sum(1 for i in range(1, rows) if t[i] <= t[0])}


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    order = sorted(pvals, key=lambda k: (pvals[k], k))
    m = len(order)
    out = {}
    running = 0.0
    still = True
    for i, k in enumerate(order):
        adj = min(1.0, (m - i) * pvals[k])
        running = max(running, adj)
        reject = still and pvals[k] <= alpha / (m - i)
        if not reject:
            still = False
        out[k] = {"p": pvals[k], "holm_adjusted": running, "reject_at_0.05": reject}
    return out


def run(workers: int = 2, log=print, split: str = "confirmation", replicate: int = REPLICATE,
        families=DIAG_FAMILIES) -> dict:
    """``split``/``replicate``/``families`` differ from the annex only for development
    smoke runs of the pipeline, which must not touch confirmation data."""
    from concurrent.futures import ProcessPoolExecutor

    from .corpus import generate_unit
    dl = _owner()
    cfgs = configurations()
    objects = {}
    for fam in families:
        bits, _ = generate_unit(split, fam, BASE_LENGTH, replicate)
        objects[fam] = bits[:BASE_LENGTH]
    jobs = [(fam, objects[fam], split, replicate) for fam in families]
    with ProcessPoolExecutor(workers) as ex:
        results = list(ex.map(_family_matrix, jobs))
    out = {"owner": str(Path(dl.__file__).resolve()), "pybdm_pin": dl.PYBDM_PIN,
           "split": split, "replicate": replicate, "base_length": BASE_LENGTH, "ragged": False,
           "configurations": cfgs, "null_draws": NULL_DRAWS,
           "null": "uniform bit permutation (preserves n and number of ones); seeds from "
                   "stream bdm_null_<draw> of the confirmation unit",
           "objects": {}}
    for (fam, bits, _s, _r), (matrix, coverage) in zip(jobs, results):
        a = adaptive(matrix)
        out["objects"][fam] = {
            "n_bits": len(bits), "ones": bits.count("1"),
            "observed_scores": matrix[0], "coverage_bits": coverage,
            "null_score_quantiles": [
                [float(q) for q in _quantiles([row[c] for row in matrix[1:]])]
                for c in range(len(cfgs))],
            "adaptive_p": a["adaptive_p"], "T0": a["T0"], "fixed_setting_p": a["fixed_p"],
            "selected_config": cfgs[a["selected_config"]],
            "r_null_at_or_below": a["r_null_at_or_below"]}
        log(f"diagnostics {fam}: adaptive p = {a['adaptive_p']:.3f}")
    h = holm({f: v["adaptive_p"] for f, v in out["objects"].items()})
    out["holm"] = h
    structured = [f for f in ("F01", "F02", "F03", "F04", "F05", "F06", "F12") if f in h]
    rej = [f for f in structured if h[f]["reject_at_0.05"]]
    out["claim_status"] = ("supported" if len(rej) == len(structured)
                           else "inconclusive" if rej else "not_supported")
    out["claim_detail"] = {"structured_rejected_after_holm": rej}
    out["scope_note"] = ("The null preserves only n and the number of ones. A low p on F09 "
                         "is not evidence of structure beyond its first-order Markov "
                         "generator; the context-code baseline answers that question.")
    return out


def _quantiles(vals):
    s = sorted(vals)
    n = len(s)
    return [s[0], s[n // 4], s[n // 2], s[(3 * n) // 4], s[-1]]


def _family_matrix(job):
    fam, bits, split, replicate = job
    dl = _owner()
    cfgs = configurations()
    rows = [bits] + null_strings(bits, fam, split, replicate)
    matrix = []
    coverage = None
    for s in rows:
        vals = []
        cov = []
        for cfg in cfgs:
            v, c = score(dl, s, cfg)
            vals.append(v)
            cov.append(c)
        matrix.append(vals)
        if coverage is None:
            coverage = cov
    return matrix, coverage


def historical_audit(out_path: Path) -> dict:
    """Rerun the bitacora-33 audit script to a NEW path (its original JSON is kept)."""
    import json
    import subprocess
    script = Path(__file__).resolve().parents[1] / "experiments" / "audit_shifted_zero_generalization.py"
    subprocess.run([sys.executable, str(script), "--output", str(out_path), "--quiet"],
                   check=True)
    return json.loads(out_path.read_text())

