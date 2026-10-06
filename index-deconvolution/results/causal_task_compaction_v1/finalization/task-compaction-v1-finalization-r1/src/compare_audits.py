"""task-compaction-v1 finalization -- scientific comparison of audit outputs (read-only).
Usage: python compare_audits.py <out.json> <r3 audit A> <r3 audit B> <closure r2 audit> <original audit>
Provenance keys (freeze_roots, source_identity, audit_revision) are disclosed, not compared."""
import json
import sys

PROV = {"freeze_roots", "source_identity", "audit_revision", "source_resolution"}


def sci(a):
    return {k: v for k, v in a.items() if k not in PROV}


def main(out, pa, pb, p2, p1):
    a, b, r2, r1 = (json.load(open(p)) for p in (pa, pb, p2, p1))
    diff_ab = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    rep = {"r3_A_vs_B": {"scientific_equal": sci(a) == sci(b), "differing_keys": diff_ab,
                         "differing_keys_all_provenance": set(diff_ab) <= PROV},
           "r3_vs_r2": {}, "r3_vs_original": {}}
    for k in ("status", "n_invalid", "n_missing", "intervention_refines_auto", "aggregates", "hand_fixtures",
              "fixture_FX1", "candidate_records", "tables"):
        rep["r3_vs_r2"][k] = a.get(k) == r2.get(k)
    rep["r3_vs_r2"]["cells_equal"] = a["cells"] == r2["cells"]
    shared = sorted(set(a["counts"]) & set(r2["counts"]))
    rep["r3_vs_r2"]["shared_counts"] = {k: [a["counts"][k], r2["counts"][k]] for k in shared}
    rep["r3_vs_r2"]["shared_counts_equal"] = all(a["counts"][k] == r2["counts"][k] for k in shared
                                                if k != "frozen_identities_checked")
    rep["r3_vs_r2"]["counts_only_in_r3"] = sorted(set(a["counts"]) - set(r2["counts"]))
    den = r1["denominators"]
    rep["r3_vs_original"] = {"status": [a["status"], r1["status"]],
                             "refinement_equal": a["intervention_refines_auto"] == r1["intervention_refines_auto"],
                             "hand_fixtures_equal": a["hand_fixtures"] == r1["hand_fixtures"],
                             "fixture_FX1_equal": a["fixture_FX1"] == r1["fixture_FX1"],
                             "cells_equal": a["cells"] == r1["cells"],
                             "denominators": {k: [a["counts"].get(k, {}).get("performed"), v] for k, v in sorted(den.items())}}
    rep["r3_vs_original"]["denominators_equal"] = all(x == y for k, (x, y) in rep["r3_vs_original"]["denominators"].items()
                                                      if x is not None)
    rep["ok"] = (rep["r3_A_vs_B"]["scientific_equal"] and rep["r3_A_vs_B"]["differing_keys_all_provenance"]
                 and all(v for k, v in rep["r3_vs_r2"].items() if isinstance(v, bool))
                 and rep["r3_vs_original"]["refinement_equal"] and rep["r3_vs_original"]["cells_equal"]
                 and rep["r3_vs_original"]["denominators_equal"] and a["status"] == "VALID_COMPLETE")
    json.dump(rep, open(out, "w"), indent=1, sort_keys=True)
    print(json.dumps({k: v for k, v in rep.items() if k != "r3_vs_r2"}, sort_keys=True)[:1500])
    print({k: v for k, v in rep["r3_vs_r2"].items() if isinstance(v, bool)}, "OK" if rep["ok"] else "NOT OK")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
