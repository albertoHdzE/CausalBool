"""task-compaction-v1 final audit closure -- evidence audit revision r4.

A separately identified wrapper around the hash-pinned finalization audit_r3.py. It replaces
exactly two r3 entry points and nothing scientific:

  R1  check_fixture  -> check_fixture_r4: FX1 is bound to its declaration (fixture_id, outputs,
      transitions); every required field is validated for type, shape, range and nullability,
      and every rejected branch appends a field-specific INVALID issue. An absent file is
      INCOMPLETE. The intended fixture and the completed certificate checks are counted
      separately. On valid data the frozen certificate (validity and minimality) still runs.
  R2  check_seal     -> check_seal_r4: the intended seal set (60 paths) and its hash values come
      from the ORIGINAL seal.json, whose SHA-256 is pinned here and must also equal the entry in
      the separately pinned original output_manifest.json (every one of the 60 values is also
      cross-checked against that manifest). The candidate seal is audited against that
      authority; it is never the source of intended coverage, and data bytes are compared with
      the authority's values, never with the candidate's.

Everything else -- the parsing layer, schemas, the expected-value authority expected_r3.py, the
frozen certificate/witness/table primitives, freeze and source-resolution checks -- is r3's,
imported by path after SHA-256 verification. r3's module object is used in-process with these
two functions (and its report finisher, to stamp the r4 identity) rebound; no file is changed.

Bypass mode (--bypass-integrity) bypasses only changed DATA bytes. It never bypasses a missing
seal file or entry, seal schema, the authority's identity, its exact path set, or a candidate
hash that contradicts the authority.

Usage: python audit_r4.py <production dir> <audit out dir> [--bypass-integrity] [--inputs-root DIR]
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
BASE = os.path.join(REPO, "index-deconvolution", "results", "causal_task_compaction_v1")
ORIG_RUN = os.path.join(BASE, "task-compaction-v1-r1")
FIN = os.path.join(BASE, "finalization", "task-compaction-v1-finalization-r1")
PINNED_R4 = {
    "audit_r3.py": (os.path.join(FIN, "src", "audit_r3.py"),
                    "d7b15a1379bb069a4be1f31436158e16e733a853724c322366f127bac6c216f3"),
    "expected_r3.py": (os.path.join(FIN, "src", "expected_r3.py"),
                       "91698c3130bf35234122a0f80a2e345b28a935a183f25c38cc392c6dfe63a33c"),
    "original output_manifest.json": (os.path.join(ORIG_RUN, "output_manifest.json"),
                                      "d6aff053fae966c3b5c50ae83e590bfc674af39a5db664a532850b2a77150c4f"),
    "original seal.json": (os.path.join(ORIG_RUN, "production", "seal.json"),
                           "c97e8031d1902b53d4c274d7103eb16c3049ffc9e9b2f0f1f3237b909d4cc330"),
}
# Declared fixture (delegation task-compaction-v1-final-audit-closure/PROTOCOL.md, R1).
FX1_DECL = {"fixture_id": "FX1_identity", "outputs": [0, 0, 1, 1], "transitions": [[0, 1, 2, 3]]}
SEAL_FIELDS = frozenset({"files", "sha256"})
HEX64 = re.compile(r"[0-9a-f]{64}")


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


for _name, (_p, _h) in PINNED_R4.items():
    if sha(_p) != _h:
        raise SystemExit(f"pinned identity mismatch: {_name}")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R3 = _load("audit_r3_finalization", PINNED_R4["audit_r3.py"][0])   # verifies r2, frozen audit, freeze
if sha(os.path.join(R3.HERE, "expected_r3.py")) != PINNED_R4["expected_r3.py"][1]:
    raise SystemExit("pinned identity mismatch: expected_r3.py as loaded by audit_r3")
R2, A = R3.R2, R3.A
is_int, int_vec = R2.is_int, R2.int_vec


def _authority():
    """The 60 intended seal paths and hashes, from the pinned original seal, cross-checked."""
    with open(PINNED_R4["original output_manifest.json"][0]) as fh:
        om = json.load(fh)["sha256"]
    with open(PINNED_R4["original seal.json"][0]) as fh:
        seal = json.load(fh)
    if om["production/seal.json"]["sha256"] != PINNED_R4["original seal.json"][1]:
        raise SystemExit("seal authority: original output manifest disagrees with the pinned seal hash")
    m = seal["sha256"]
    if not (set(seal) == SEAL_FIELDS and seal["files"] == len(m) == 60):
        raise SystemExit("seal authority: original seal is not the declared 60-entry seal")
    if any(om.get(f"production/{k}", {}).get("sha256") != v for k, v in m.items()):
        raise SystemExit("seal authority: a seal value disagrees with the original output manifest")
    return dict(m)


AUTH = _authority()
AUTHORITY_LOG = {"source": "task-compaction-v1-r1/production/seal.json",
                 "sha256": PINNED_R4["original seal.json"][1],
                 "confirmed_by": "task-compaction-v1-r1/output_manifest.json entry production/seal.json "
                                 "and its 60 production/<path> entries",
                 "confirmed_by_sha256": PINNED_R4["original output_manifest.json"][1],
                 "intended_entries": len(AUTH)}


# ---------------------------------------------------------------------- R2: seal against the authority
def check_seal_r4(prod, L, bypass, report):
    intended = len(AUTH)
    integ = {"authority": AUTHORITY_LOG["source"], "intended_entries": intended, "candidate_seal": "missing",
             "candidate_entries_present": 0, "candidate_entries_agreeing": 0, "candidate_entries_missing": [],
             "candidate_entries_rejected": [], "data_absent": [], "hashes_compared": 0, "hash_mismatch": [],
             "hash_mismatch_bypassed": False}
    report["integrity"] = integ
    L.intended["seal_entries_agreeing"] = intended
    L.intended["sealed_files_checked"] = intended
    st, seal = R2.load_json(os.path.join(prod, "seal.json"), L, "seal")   # missing -> INCOMPLETE
    cand = {}
    if st == "ok":
        integ["candidate_seal"] = "present"
        if not isinstance(seal, dict):
            L.bad_field("seal", "seal", "object required")
        else:
            for k in sorted(SEAL_FIELDS - set(seal)):
                L.bad_field("seal", k, "missing required field")
            for k in sorted(set(seal) - SEAL_FIELDS):
                L.bad_field("seal", k, "undeclared field")
            if "files" in seal and not (is_int(seal["files"]) and seal["files"] == intended):
                L.bad_field("seal", "files", f"non-boolean int equal to the authority's {intended} required")
            m = seal.get("sha256")
            if "sha256" in seal and not isinstance(m, dict):
                L.bad_field("seal", "sha256", "object required")
            elif isinstance(m, dict):
                cand = m
    elif st == "invalid":
        integ["candidate_seal"] = "malformed"
    for k in sorted(cand):
        v = cand[k]
        if k not in AUTH:
            reason = "undeclared path: outside the authority's exact set"
        elif not (type(v) is str and HEX64.fullmatch(v)):
            reason = "malformed hash: 64 lowercase hex characters required"
        elif v != AUTH[k]:
            reason = "contradicts the pinned authority"
        else:
            integ["candidate_entries_agreeing"] += 1
            continue
        L.bad_field("seal", f"sha256[{k}]", reason)
        integ["candidate_entries_rejected"].append(k)
    integ["candidate_entries_present"] = sum(k in AUTH for k in cand)
    for k in sorted(set(AUTH) - set(cand)):
        integ["candidate_entries_missing"].append(k)
        L.absent("seal", f"seal entry {k}")
    for k, v in sorted(AUTH.items()):                     # data bytes against the AUTHORITY
        p = os.path.join(prod, k)
        if not os.path.isfile(p):
            integ["data_absent"].append(k)
            L.absent("seal", f"sealed artifact {k}")
            continue
        integ["hashes_compared"] += 1
        if sha(p) != v:
            integ["hash_mismatch"].append(k)
            if not bypass:
                L.bad("seal", f"sealed artifact {k}: present bytes differ from the pinned seal authority")
    integ["hash_mismatch_bypassed"] = bool(bypass and integ["hash_mismatch"])
    L.tick("seal_entries_agreeing", integ["candidate_entries_agreeing"])
    L.tick("sealed_files_checked", integ["hashes_compared"])


# ---------------------------------------------------------------------- R1: the declared fixture
def check_fixture_r4(prod, L, report):
    rec = {"fixture_id_declared": FX1_DECL["fixture_id"], "intended": 1, "file_available": False,
           "schema_valid": False, "certificate_checks_intended": 2, "certificate_checks_completed": 0,
           "validity": None, "minimality": None, "issues": []}
    report["fixture_FX1"] = rec
    L.intended["fixtures_checked"] = 1
    L.intended["fixture_certificate_checks"] = 2
    n0 = len(L.invalid)
    st, fx = R2.load_json(os.path.join(prod, "fixtures", "FX1_identity.json"), L, "FX1")
    if st != "ok":
        rec["not_checked"] = f"fixture file {st}"
        rec["issues"] = L.invalid[n0:]
        return
    rec["file_available"] = True
    if not isinstance(fx, dict):
        L.bad_field("FX1", "fixture", "object required")
        rec["issues"] = L.invalid[n0:]
        return
    ok = R3.inventory(L, "FX1", fx, R3.FX_FIELDS, "fixture")

    def need(k, cond, why):
        nonlocal ok
        if k in fx and not cond:
            L.bad_field("FX1", f"fixture.{k}", why)
            ok = False
        return k in fx and cond
    for k, v in FX1_DECL.items():                        # identity and model, type-exactly
        if k in fx:
            ok &= R3.strict(L, "FX1", fx[k], v, f"fixture.{k}")
    N, n_tables = len(FX1_DECL["outputs"]), len(FX1_DECL["transitions"])
    g = fx.get
    st_ok = need("stages", isinstance(g("stages"), list) and len(g("stages")) >= 2
                 and all(int_vec(s, N, 0, N) for s in g("stages")), f"list of >= 2 int vectors of length {N} in [0, {N}) required")
    al_ok = need("alpha", int_vec(g("alpha"), N, 0, N), f"int vector of length {N} in [0, {N}) required")
    if need("K", is_int(g("K")) and g("K") >= 1, "non-boolean int >= 1 required") and al_ok:
        ok &= R3.strict(L, "FX1", g("K"), max(g("alpha")) + 1, "fixture.K")
    need("decoder", int_vec(g("decoder"), None, 0), "int vector required")
    need("representatives", int_vec(g("representatives"), None, 0, N), f"int vector in [0, {N}) required")
    need("macro", isinstance(g("macro"), list) and len(g("macro")) == n_tables
         and all(int_vec(t, None, 0) for t in g("macro")), f"list of {n_tables} int vectors required")
    need("strict_rounds", is_int(g("strict_rounds")) and g("strict_rounds") >= 0, "non-boolean int >= 0 required")
    if "coarsening" in fx:
        co = g("coarsening")
        if co is None:
            L.bad_field("FX1", "fixture.coarsening", "null where a value is required")
            ok = False
        elif st_ok:
            s = g("stages")
            need("coarsening", isinstance(co, list) and len(co) == len(s) - 1 and all(
                int_vec(co[d], max(s[d + 1]) + 1, 0, max(s[d]) + 1) for d in range(len(co))),
                "one map per stage step, stage d+1 classes -> stage d classes, required")
        else:
            need("coarsening", isinstance(co, list) and all(int_vec(r, None, 0) for r in co), "list of int maps required")
    if ok:
        why = R2.schema_certificate(fx, N, n_tables)   # the inherited guard, kept as a second line
        if why:
            L.bad_field("FX1", "fixture", f"schema: {why}")
            ok = False
    rec["schema_valid"] = ok
    if not ok:
        rec["not_checked"] = "certificate: fixture record invalid"
        rec["issues"] = L.invalid[n0:]
        return
    L.tick("fixtures_checked")
    fxL = A.Ledger()
    r = A.certificate(fx, fx["transitions"], fxL, "FX1")
    rec.update(validity=r["validity"], minimality=r["minimality"], certificate_checks_completed=2)
    L.tick("fixture_certificate_checks", 2)
    L.invalid += fxL.invalid
    rec["issues"] = L.invalid[n0:]


# ---------------------------------------------------------------------- identity and wiring
_finish_r3 = R3.finish


def finish_r4(L, report, out):
    report["audit_revision"] = "r4"
    report["source_identity"]["audit_r4.py"] = sha(os.path.abspath(__file__))
    report["source_identity"].update({k: v[1] for k, v in PINNED_R4.items()})
    report["seal_authority"] = AUTHORITY_LOG
    report["fixture_declaration"] = FX1_DECL
    return _finish_r3(L, report, out)


class _R2View:
    """r2's namespace as r3 sees it, with check_seal replaced by the authority-based check."""
    check_seal = staticmethod(check_seal_r4)

    def __getattr__(self, name):
        return getattr(R2, name)


R3.R2 = _R2View()
R3.check_fixture = check_fixture_r4
R3.finish = finish_r4
main = R3.main

if __name__ == "__main__":
    sys.exit(main(*R3._args(sys.argv[1:])))
