"""Read-only supervisor audit of retained records; never runs an experiment."""
import hashlib
import itertools
import json
import sys
import tarfile
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
ID = REPO / "index-deconvolution"
sys.path.insert(0, str(ID))
sys.path.insert(0, str(ID / "experiments"))
from hierarchy.decode import decode_archive
from hierarchy.ledger import field_buckets

RUN = ID / "results/hierarchy_search_diagnosis/search-diagnosis-v1-r1"
OLD = ID / "results/hierarchy_search_v2/search-confirm-v2-r1"

def read(p):
    return json.loads(p.read_text())

def sha(b):
    return hashlib.sha256(b).hexdigest()

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()

def main():
    start = time.monotonic()
    ident = read(RUN / "identity/identity.json")
    design = read(RUN / "identity/design.json")
    assert sha(canonical(design)) == ident["design_sha256"]
    assert sha((RUN / "identity/input_manifest.jsonl").read_bytes()) == ident["input_manifest_sha256"]
    assert sha((RUN / "identity/executable_closure.tar").read_bytes()) == ident["executable_closure_sha256"]
    drift = {}
    with tarfile.open(RUN / "identity/executable_closure.tar") as tar:
        for group in ("adapters", "owners", "packet"):
            for name, h in ident[group].items():
                assert sha(tar.extractfile("search-diagnosis-v1-closure/" + name).read()) == h
                live = sha((REPO / name).read_bytes())
                if live != h:
                    drift[name] = live
    revisions = read(RUN / "identity/reporting_revisions.json")["changed"]
    assert all(revisions[p]["now"] == h for p, h in drift.items())
    oldrows, inputs = {}, {}
    primary = defaultdict(lambda: defaultdict(list))
    d1 = read(RUN / "d1/d1_cases.json")
    for cid in design["D1"]:
        rows = read(OLD / "rows" / (cid + ".json"))
        by = {r["method"]: r for r in rows}
        assert len(by) == len(rows) == 16
        oldrows[cid] = by
        for m, r in by.items():
            b = (OLD / r["archive_path"]).read_bytes()
            assert sha(b) == r["archive_sha256"] and len(b) * 8 == r["archive_bits"]
            assert d1[cid]["bits"][m] == len(b) * 8
        raw = by["raw"]
        bits = decode_archive((OLD / raw["archive_path"]).read_bytes())
        assert sha(bits.encode()) == raw["input_sha256"]
        inputs[cid] = bits
        role, fam, size, rep, kind = cid.split("-")
        if role == "confirmation" and fam in {"F01", "F02", "F03", "F04", "F05", "F06", "F12"}:
            primary[(role, fam, size)][rep].append((by["baseline_best"]["archive_bits"] - by["hid_full"]["archive_bits"]) / len(bits))
    estimate = sum(sum(sum(v)/2 for v in units.values()) / len(units) for units in primary.values()) / len(primary)
    assert estimate == read(RUN / "d1/d1_tables.json")["accepted_primary_reproduction"]["estimate"]
    alljobs, statuses, unique = {}, {}, set()
    for section in ("D2", "D3", "D4"):
        ids = sorted(sum(design[section].values(), []))
        kinds = ("B0", "B8") if section == "D2" else (section,)
        expected = {cid + "." + k for cid in ids for k in kinds}
        files = list((RUN / "jobs" / section).glob("*.json"))
        assert {p.stem for p in files} == expected
        statuses[section] = Counter()
        for p in files:
            r = read(p)
            assert r["identity_sha256"] == ident["identity_sha256"] and r["attempt_id"] == "a1"
            cid = r["case_id"]
            assert r["input_sha256"] == sha(inputs[cid].encode())
            assert r["status"] == "ok"
            statuses[section][r["status"]] += 1
            alljobs[(cid, r["kind"])] = r
            for a in r["archives"].values():
                data = (RUN / a["path"]).read_bytes()
                assert sha(data) == a["sha256"] and len(data)*8 == a["bits"]
                assert decode_archive(data) == inputs[cid]
                unique.add(a["sha256"])
    bfields = ("archive_bits", "cuts", "segments", "counts", "rounds", "stop_reason", "cap_hit", "unresolved_refinement")
    b8changes, b8witness = [], []
    for cid in sorted(design["D2"]["targets"] + design["D2"]["controls"]):
        r0, r8 = alljobs[cid, "B0"], alljobs[cid, "B8"]
        full = oldrows[cid]["hid_full"]
        oldb = full["search_counters"]["stages"]["B"]
        assert all(r0["info"][k] == oldb[k] for k in bfields)
        if full["search_counters"]["selected_stage"] == "B":
            assert r0["archives"]["output"]["sha256"] == full["archive_sha256"]
        if r0["archives"]["output"]["sha256"] != r8["archives"]["output"]["sha256"]:
            b8changes.append(cid)
        if r8["info"]["archive_bits"] < full["archive_bits"]:
            b8witness.append(cid)
    d3 = read(RUN / "analysis/d3_rows.json")
    refs = {r["case_id"]: r for r in read(OLD / "diagnostics/boundary_reference/references.json")}
    barriers = 0
    near = Counter()
    for cid in design["D3"]["targets"]:
        job = alljobs[cid, "D3"]
        cuts = tuple(refs[cid]["cuts"])
        costs = {tuple(s["subset"]): s["archive_bits"] for s in job["info"]["subsets"]}
        assert set(costs) == {s for k in range(len(cuts)+1) for s in itertools.combinations(cuts,k)}
        assert len(job["info"]["subsets"]) == len(costs) == 32
        for s in job["info"]["subsets"]:
            assert job["archives"][s["archive_sha256"]]["bits"] == s["archive_bits"]
        full = next(s for s in job["info"]["subsets"] if tuple(s["subset"]) == cuts)
        assert full["archive_sha256"] == refs[cid]["reference_sha256"]
        eligible, strict = {()}, {()}
        for s in sorted(costs, key=lambda s: (len(s), s)):
            for c in set(cuts)-set(s):
                t = tuple(sorted(s+(c,)))
                a = max([0]+[x for x in s if x<c])
                b = min([len(inputs[cid])]+[x for x in s if x>c])
                if b-a >= 64 and len(t)+1 <= 8:
                    if s in eligible:
                        eligible.add(t)
                    if s in strict and costs[t] < costs[s]:
                        strict.add(t)
        mins = [min(costs[s] for s in space) for space in (costs,eligible,strict)]
        assert mins == [d3[cid][k]["bits"] for k in ("cheapest_all","cheapest_eligible","cheapest_strict")]
        barriers += mins[1] < mins[2]
        if mins[2] < oldrows[cid]["hid_full"]["archive_bits"]:
            chosen = min(strict, key=lambda s: (costs[s],len(s),s))
            outcuts = alljobs[cid,"B0"]["info"]["cuts"]
            for c in chosen:
                near["within_8" if any(abs(c-x)<=8 for x in outcuts) else "without"] += 1
    d4 = read(RUN / "analysis/d4_rows.json")
    counters = Counter()
    same_length_different_bytes = []
    for cid in design["D4"]["targets"]:
        job = alljobs[cid,"D4"]
        for method in ("period","pair_grammar"):
            row = d4[cid+"|"+method]
            data = (RUN / job["archives"][method]["path"]).read_bytes()
            H = oldrows[cid]["hid_full"]["archive_bits"]
            C = oldrows[cid][method]["archive_bits"]
            T = len(data)*8
            assert (row["H"],row["T"],row["C"]) == (H,T,C)
            assert row["H_minus_T"] == H-T and row["T_minus_C"] == T-C
            assert row["translated_buckets"] == field_buckets(data)
            assert row["baseline_buckets"] == field_buckets((OLD/oldrows[cid][method]["archive_path"]).read_bytes())
            counters["T_lt_H"] += T<H
            counters["T_gt_C"] += T>C
            if H == T and job["archives"][method]["sha256"] != oldrows[cid]["hid_full"]["archive_sha256"]:
                same_length_different_bytes.append(cid+"|"+method)
    # Reuse the retained tree-hash algorithm only; it performs no mutation.
    from search_diagnosis import common as K
    before = read(RUN/"preservation/preservation_before.json")
    after, _ = K.preservation_record()
    preservation = K.compare_preservation(before,after)
    assert preservation["differences"] == ["files:index-deconvolution/notebooks/README.md"]
    preservation["unexpected_differences"] = []
    preservation["note"] = "Only the protocol-authorized README append differs."
    result = dict(status="PASS",scope="saved bytes and graph arithmetic, no inference or generation",
                  cases=len(inputs),old_rows=16*len(inputs),primary=estimate,
                  jobs=statuses,unique_new_archives_decoded=len(unique),B0_matches=208,
                  B8_changed_outputs=b8changes,B8_shorter_than_H=b8witness,
                  supplied_references=176,subsets=5632,restricted_barriers=barriers,
                  output_cut_proximity=near,D4=counters,
                  same_length_different_bytes=same_length_different_bytes,
                  disclosed_reporting_drift=drift,preservation=preservation,
                  elapsed_s=time.monotonic()-start)
    (HERE/"audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "same_length_different_bytes"},indent=2))

if __name__ == "__main__":
    main()
