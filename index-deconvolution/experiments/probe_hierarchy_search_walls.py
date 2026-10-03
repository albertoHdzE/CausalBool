"""Post-hoc, input-only F06/F07 transfer probe; not confirmatory evidence.

Neither proposer receives labels, truth, periods, boundaries or noise masks.
Full existing archives are compared only after proposal construction. Frozen
inference and both retained runs are untouched. Four explicit proposal variants
separate first-block modelling, consensus, period coverage and patch placement.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "index-deconvolution"), str(ROOT / "src")]
from hierarchy.decode import decode_archive  # noqa: E402
from hierarchy.model import NodeFactory, count_reachable, to_model  # noqa: E402
from hierarchy.wire import encode_literal, serialize_model  # noqa: E402

RUN = ROOT / "index-deconvolution/results/hierarchy_v1/confirm-v1-r1"
OUT = ROOT / "index-deconvolution/results/hierarchy_wall_probes/noisy_consensus_v1"
OLD_PERIODS = set(range(1, 33)) | {64, 128, 256}
VARIANTS = ("first_block_original_periods_local_patches",
            "consensus_original_periods_local_patches",
            "consensus_dense_periods_local_patches",
            "consensus_dense_periods_global_patch")


def differences(bits: str, base: str) -> list[int]:
    mask = int(bits, 2) ^ int(base, 2)
    out = []
    while mask:
        k = mask.bit_length() - 1
        out.append(len(bits) - 1 - k)
        mask ^= 1 << k
    return out


def periodic_node(factory, base, period):
    copies, tail = divmod(len(base), period)
    if copies < 2:
        return factory.literal(base)
    node = factory.repeat(factory.literal(base[:period]), copies)
    return factory.concat((node, factory.literal(base[-tail:]))) if tail else node


def candidate(bits: str, word: str, local: bool) -> tuple[bytes, int, int]:
    """Existing HID format. Local patches retain min(64, floor(L/16)) cap.

    Global variant intentionally relaxes the 64 cap, still requiring errors<=n/16;
    this changes a search restriction, not the existing wire representation.
    """
    n, p = len(bits), len(word)
    base = (word * (n // p + 1))[:n]
    factory = NodeFactory()
    if not local:
        pos = differences(bits, base)
        assert len(pos) <= n // 16
        root = factory.patch(periodic_node(factory, base, p), pos)
    else:
        nodes = []
        for offset in range(0, n, 1024):
            x, b = bits[offset:offset + 1024], base[offset:offset + 1024]
            pos = differences(x, b)
            if len(pos) > min(64, len(x) // 16):
                nodes.append(factory.literal(x))
            else:
                nodes.append(factory.patch(periodic_node(factory, b, p), pos))
        root = factory.concat(nodes)
    assert count_reachable(root) <= 4096 and root.depth <= 64
    data = serialize_model(to_model(root), n)
    return data, count_reachable(root), root.depth


def propose(bits: str) -> dict:
    """The sole proposal entry point: input bits only, deterministic fixed grid."""
    t0 = time.perf_counter()
    raw = encode_literal(bits)
    best = {v: {"archive": raw, "period": None, "errors": None,
                "rules": 0, "depth": 0} for v in VARIANTS}
    counts = dict.fromkeys(VARIANTS, 0)
    n, x = len(bits), int(bits, 2)
    for p in range(1, min(256, n // 2) + 1):
        columns = [bits[j::p] for j in range(p)]
        consensus = "".join("1" if 2 * c.count("1") > len(c) else "0" for c in columns)
        words = [(consensus, [VARIANTS[2], VARIANTS[3]] +
                  ([VARIANTS[1]] if p in OLD_PERIODS else []))]
        if p in OLD_PERIODS:
            words.append((bits[:p], [VARIANTS[0]]))
        for word, variants in words:
            base = (word * (n // p + 1))[:n]
            errors = (x ^ int(base, 2)).bit_count()
            if errors > n // 16:
                continue
            cache = {}
            for variant in variants:
                local = variant != VARIANTS[3]
                if local not in cache:
                    cache[local] = candidate(bits, word, local)
                data, rules, depth = cache[local]
                counts[variant] += 1
                if (len(data), data) < (len(best[variant]["archive"]), best[variant]["archive"]):
                    best[variant] = {"archive": data, "period": p, "errors": errors,
                                     "rules": rules, "depth": depth}
    for value in best.values():
        assert decode_archive(value["archive"]) == bits
    return {"best": best, "candidate_counts": counts,
            "proposal_wall_seconds": time.perf_counter() - t0}


def main():
    rows = [json.loads(s) for s in (RUN / "cases.jsonl").read_text().splitlines()]
    cases = defaultdict(dict)
    for row in rows:
        if row["split"] == "transfer" and row["family"] in ("F06", "F07"):
            cases[row["case_id"]][row["method"]] = row
    assert len(cases) == 32
    (OUT / "archives").mkdir(parents=True, exist_ok=True)
    results = []
    for cid, methods in sorted(cases.items()):
        bits = decode_archive((RUN / methods["raw"]["archive_path"]).read_bytes())
        proposed = propose(bits)
        full, baseline = (methods[m]["archive_bits"] for m in ("hid_full", "baseline_best"))
        record = {"case_id": cid, "family": methods["raw"]["family"], "n": len(bits),
                  "frozen_full_bits": full, "baseline_best_bits": baseline,
                  "input_sha256": hashlib.sha256(bits.encode()).hexdigest(),
                  "proposal_wall_seconds": proposed["proposal_wall_seconds"],
                  "candidate_counts": proposed["candidate_counts"], "variants": {}}
        for variant, item in proposed["best"].items():
            data = item.pop("archive")
            digest = hashlib.sha256(data).hexdigest()
            (OUT / "archives" / f"{digest}.isd").write_bytes(data)
            proposed_bits = 8 * len(data)
            record["variants"][variant] = dict(
                item, proposal_bits=proposed_bits, augmented_bits=min(full, proposed_bits),
                archive_sha256=digest, decode_ok=True,
                improvement_over_frozen_bits=full - min(full, proposed_bits),
                saving_over_portfolio_bits=baseline - min(full, proposed_bits))
        results.append(record)
        print(f"{cid}: frozen {full}, local {record['variants'][VARIANTS[2]]['proposal_bits']}, "
              f"global {record['variants'][VARIANTS[3]]['proposal_bits']}, baseline {baseline}", flush=True)
    aggregates = {}
    for family in ("F06", "F07"):
        rr = [r for r in results if r["family"] == family]
        aggregates[family] = {"strings": len(rr), "variants": {}}
        for variant in VARIANTS:
            vals = [r["variants"][variant] for r in rr]
            aggregates[family]["variants"][variant] = {
                "strings_improved_over_frozen": sum(v["improvement_over_frozen_bits"] > 0 for v in vals),
                "strings_better_than_portfolio": sum(v["saving_over_portfolio_bits"] > 0 for v in vals),
                "mean_improvement_per_input_bit": sum(v["improvement_over_frozen_bits"] / r["n"]
                                                       for r, v in zip(rr, vals)) / len(rr),
                "mean_saving_vs_portfolio_per_input_bit": sum(v["saving_over_portfolio_bits"] / r["n"]
                                                              for r, v in zip(rr, vals)) / len(rr)}
    output = {"status": "posthoc exploratory probe on previously inspected inputs",
              "frozen_run": "confirm-v1-r1", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "input_only_proposal": True, "period_grid": "1..256, deterministically enumerated",
              "local_chunk_length": 1024, "maximum_global_error_fraction": "1/16",
              "limits": ["F06/F07 transfer only, no new holdout or CI claims",
                         "augmented costs compare frozen incumbent with new proposals; full search not rerun",
                         "proposal time excludes frozen search and does not establish end-to-end resource compliance",
                         "global variant relaxes search patch cap; local variants preserve the per-patch cap",
                         "all archives use unchanged wire format and exact decoding"],
              "aggregates": aggregates, "cases": results}
    (OUT / "probe.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(aggregates, indent=2))


if __name__ == "__main__":
    main()
