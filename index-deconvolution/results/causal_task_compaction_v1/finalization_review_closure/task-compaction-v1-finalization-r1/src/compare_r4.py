"""task-compaction-v1 final audit closure -- r4 versus the saved r3 historical-root audit (read-only).
Usage: python compare_r4.py <out.json> <r4 audit A> <r4 audit B> <saved r3 audit>
Scientific keys must be equal; provenance and the two revised checks (integrity, fixture_FX1) are
reported separately as new coverage, never as scientific values."""
import json
import sys

SCI = ("status", "n_invalid", "n_missing", "cells", "aggregates", "intervention_refines_auto",
       "candidate_records", "tables", "hand_fixtures", "mode")
REVISED = {"integrity", "fixture_FX1", "seal_authority", "fixture_declaration"}
PROV = {"freeze_roots", "source_identity", "audit_revision", "source_resolution"}
NEW_COUNTS = {"seal_entries_agreeing", "fixtures_checked", "fixture_certificate_checks"}


def main(out, pa, pb, p3):
    a, b, r3 = (json.load(open(p)) for p in (pa, pb, p3))
    sci = {k: a.get(k) == r3.get(k) for k in SCI}
    shared = sorted(set(a["counts"]) & set(r3["counts"]))
    counts = {k: [a["counts"][k], r3["counts"][k]] for k in shared}
    anchors = {k: a["counts"][k]["performed"] for k in ("cells", "candidate_decisions_checked",
                                                         "transition_entries_owner_checked")}
    rep = {"r4_A_vs_B_identical": a == b, "scientific_equal_to_r3": sci,
           "shared_counts_equal": {k: x == y for k, (x, y) in counts.items()}, "shared_counts": counts,
           "anchors": anchors, "counts_only_in_r4": sorted(set(a["counts"]) - set(r3["counts"])),
           "counts_only_in_r3": sorted(set(r3["counts"]) - set(a["counts"])),
           "keys_only_in_r4": sorted(set(a) - set(r3)), "keys_only_in_r3": sorted(set(r3) - set(a)),
           "differing_keys": sorted(k for k in set(a) | set(r3) if a.get(k) != r3.get(k)),
           "new_coverage": {"integrity": a["integrity"] | {k: len(v) for k, v in a["integrity"].items() if isinstance(v, list)},
                            "fixture_FX1": a["fixture_FX1"], "r3_integrity": r3.get("integrity"),
                            "r3_fixture_FX1": r3.get("fixture_FX1")}}
    rep["ok"] = (rep["r4_A_vs_B_identical"] and all(sci.values()) and all(rep["shared_counts_equal"].values())
                 and anchors == {"cells": 24, "candidate_decisions_checked": 3276,
                                 "transition_entries_owner_checked": 85504}
                 and set(rep["differing_keys"]) <= PROV | REVISED | {"counts"} and set(rep["counts_only_in_r4"]) <= NEW_COUNTS
                 and not rep["counts_only_in_r3"])
    json.dump(rep, open(out, "w"), indent=1, sort_keys=True)
    print("scientific keys equal:", all(sci.values()), "| shared counts equal:", all(rep["shared_counts_equal"].values()),
          "| anchors:", anchors, "| A==B:", rep["r4_A_vs_B_identical"], "| differing:", rep["differing_keys"])
    print("COMPARISON", "OK" if rep["ok"] else "NOT OK")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
