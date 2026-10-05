"""Prospective freeze for a non-legacy study (HID-search-v2), BENCHMARK.md section 4.

The freeze records the complete executable dependency CLOSURE (every non-test module
of the package, the schema-cover owner and its import, and the shared description-
length owner), verified by an import probe in a fresh interpreter that lists every
repository file actually loaded; the protocol packet and contract; resolved method
configurations; baseline parameters; the declared design; generator identities; the
analysis plan; resource policy; environment; a reserved-namespace exposure check; and
the prefreeze evidence files. Every recorded file is archived in a deterministic tar
inside the run directory. A git commit alone is not used (the tree is dirty).

``load_and_validate`` never downgrades a mismatch: a changed source, protocol file,
method configuration or design is a problem, and with a purpose the frozen scientific
environment is enforced as well.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from .study import ID_ROOT, REPO

PROTOCOL_FILES = (
    "index-deconvolution/PROTOCOL_hierarchy_search_v2.md",
    "index-deconvolution/KICKOFF_hierarchy_search_v2.md",
    "index-deconvolution/protocols/hierarchy_search_v2/SEARCH.md",
    "index-deconvolution/protocols/hierarchy_search_v2/BENCHMARK.md",
    "index-deconvolution/protocols/hierarchy_search_v2/ACCEPTANCE.md",
    "index-deconvolution/protocols/hierarchy_search_v2/study_contract.json",
    "index-deconvolution/protocols/hierarchy_search_v2/DELEGATION_MANIFEST.json",
    "index-deconvolution/protocols/hierarchy_search_v2/INITIAL_SOURCE_STATE.json",
    "index-deconvolution/protocols/hierarchy_v1/WIRE_FORMAT.md",
)
SHARED_OWNERS = ("index-deconvolution/src/deconvolution.py", "index-deconvolution/src/causalbool.py",
                 "src/description_lengths.py")
INFORMATIONAL_GLOBS = ("index-deconvolution/hierarchy/tests/*.py",
                       "index-deconvolution/hierarchy/*.md",
                       "index-deconvolution/notebooks/build_17.py",
                       "index-deconvolution/experiments/preserve_confirm_v1_r1_sources.py",
                       "index-deconvolution/experiments/audit_confirm_v1_r1_from_snapshot.sh",
                       "index-deconvolution/experiments/audit_search_v2_primary.py")
RESERVED_MARKERS = ("search_v2_confirmation", "search_v2_transfer", "search_v2_stress")

V3A_PACKET = "index-deconvolution/protocols/hierarchy_search_v3a/"
# Per-study freeze profile, selected by explicit study name (never by a name prefix):
# protocol files, extra executable closure outside the package, informational globs,
# reserved namespaces and the analysis plan's owner.
PROFILES = {
    "search-v2": {"protocol": PROTOCOL_FILES, "extra_closure": (),
                  "informational": INFORMATIONAL_GLOBS, "reserved": RESERVED_MARKERS,
                  "analysis_plan": ("report_v2", "ANALYSIS_PLAN_V2")},
    "search-v3a": {
        "protocol": ("index-deconvolution/PROTOCOL_hierarchy_search_v3a.md",
                     "index-deconvolution/KICKOFF_hierarchy_search_v3a.md",
                     *(V3A_PACKET + f for f in ("SEARCH.md", "BENCHMARK.md", "ACCEPTANCE.md",
                                                "DESIGN_REVIEW.md", "contract.json",
                                                "intended_cases.json", "DELEGATION_MANIFEST.json",
                                                "INITIAL_SOURCE_STATE.json",
                                                "INTEGRATION_CHECK.json", "PACKET_CHECKS.json",
                                                "check_packet.py")),
                     "index-deconvolution/protocols/hierarchy_v1/WIRE_FORMAT.md",
                     "index-deconvolution/protocols/hierarchy_search_v2/SEARCH.md",
                     "index-deconvolution/protocols/hierarchy_search_v2/BENCHMARK.md"),
        "extra_closure": ("index-deconvolution/experiments/search_v3a/__init__.py",
                          "index-deconvolution/experiments/search_v3a/audit.py",
                          "index-deconvolution/experiments/search_v3a/development.py",
                          "index-deconvolution/experiments/search_v3a/ledger.py",
                          "index-deconvolution/experiments/search_v3a/preserve.py",
                          "index-deconvolution/experiments/search_v3a/prospective.py",
                          "index-deconvolution/experiments/search_diagnosis/__init__.py",
                          "index-deconvolution/experiments/search_diagnosis/common.py"),
        "informational": ("index-deconvolution/hierarchy/tests/*.py",
                          "index-deconvolution/hierarchy/*.md"),
        "reserved": ("search_v3a_confirmation", "search_v3a_transfer", "search_v3a_stress",
                     "search_v3a_controls"),
        "analysis_plan": ("report_v3a", "ANALYSIS_PLAN_V3A")},
}


def profile(study) -> dict:
    """The freeze profile of the study's method registry (fixture studies included)."""
    from .study import V3A_REGISTRIES
    return PROFILES["search-v3a" if study.registry in V3A_REGISTRIES else "search-v2"]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def closure_files(study=None) -> list[str]:
    pkg = sorted(p.relative_to(REPO).as_posix()
                 for p in (ID_ROOT / "hierarchy").glob("*.py"))
    extra = list(profile(study)["extra_closure"]) if study is not None else []
    return pkg + list(SHARED_OWNERS) + extra


PROBE = r"""
import importlib, json, pkgutil, sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
import hierarchy
for m in pkgutil.iter_modules(hierarchy.__path__):
    if m.name != "tests":
        importlib.import_module("hierarchy." + m.name)
from hierarchy import candidates
candidates._cover_owner()
files = set()
for mod in list(sys.modules.values()):
    f = getattr(mod, "__file__", None)
    if f:
        p = Path(f).resolve()
        if repo in p.parents:
            files.add(p.relative_to(repo).as_posix())
print(json.dumps(sorted(files)))
"""


def import_probe(study=None) -> dict:
    env = dict(os.environ, PYTHONPATH=f"{ID_ROOT}{os.pathsep}{REPO / 'src'}")
    out = subprocess.run([sys.executable, "-c", PROBE, str(REPO)], cwd=REPO, env=env,
                         capture_output=True, text=True, check=True)
    allfiles = json.loads(out.stdout)
    third = [f for f in allfiles if f.startswith("venv/")]
    loaded = [f for f in allfiles if not f.startswith("venv/")]
    closure = set(closure_files(study))
    return {"loaded_repository_files": loaded,
            "third_party_files_loaded": len(third),
            "third_party_identity": "venv packages; versions recorded under environment",
            "outside_closure": sorted(set(loaded) - closure),
            "closure_not_loaded": sorted(closure - set(loaded))}


def informational_files(study=None) -> list[str]:
    out = set()
    for g in (profile(study)["informational"] if study is not None else INFORMATIONAL_GLOBS):
        out.update(p.relative_to(REPO).as_posix() for p in REPO.glob(g))
    return sorted(out)


def exposure_check(study, run_dir: Path) -> dict:
    """Before the freeze: no generated reserved strings, rows or manifests may exist."""
    hits = []
    root = study.result_root
    if root.exists():
        for p in root.rglob("*"):
            generated = (p.name.startswith("corpus_manifest") or p.name == "cases.jsonl"
                         or p.parent.name in ("rows", "logs", "archives"))
            if p.is_file() and generated and p.suffix in (".json", ".jsonl", ".log"):
                text = p.read_text(errors="replace")
                if any(m in text for m in profile(study)["reserved"]):
                    hits.append(str(p))
    present = [n for n in ("rows", "cases.jsonl", "corpus_manifest.jsonl")
               if (run_dir / n).exists()]
    return {"files_mentioning_reserved_namespaces": hits, "run_artifacts_present": present,
            "reserved_namespaces": list(profile(study)["reserved"]),
            "clean": not hits and not present,
            "scope": "every generated-data artefact (corpus manifests, cases.jsonl, rows, "
                     "logs) under the study result root; documentation that names the "
                     "namespaces is not exposure"}


def method_configs(study) -> dict:
    from . import benchmark as B
    return {m: {"kind": study.method(m).kind, "config": B.method_config(m, study),
                "sha256": B.method_config_sha(m, study)} for m in study.all_methods}


def design(study, run_id: str) -> dict:
    roles = study.run_roles(run_id)
    exp = {}
    for r in roles:
        spec = study.role(r)
        units = len(spec.families) * len(spec.base_lengths) * len(spec.replicates)
        exp[r] = {"units": units, "strings": 2 * units,
                  "rows": 2 * units * len(study.all_methods)}
    return {"roles": {r: study.role(r).as_dict() for r in roles}, "expected": exp,
            "expected_total_strings": sum(v["strings"] for v in exp.values()),
            "expected_total_rows": sum(v["rows"] for v in exp.values()),
            "methods": list(study.all_methods), "rows_per_case": len(study.all_methods),
            "paired_offsets": [0, 3],
            "case_design": "frozen Cartesian product role x family x base_length x replicate "
                           "x {base, ragged}; never inferred from rows"}


def dev_fingerprint(study) -> str:
    """Identity of the current code/configuration for unfrozen development rows."""
    blob = {"sources": {p: sha_file(REPO / p) for p in closure_files(study)},
            "methods": {m: v["sha256"] for m, v in method_configs(study).items()}}
    return "dev:" + hashlib.sha256(canonical(blob)).hexdigest()


def build(study, run_id: str, prefreeze_dir: Path | None) -> tuple[dict, bytes, str]:
    from . import benchmark as B
    from . import corpus, study_corpus
    import importlib
    prof = profile(study)
    plan = getattr(importlib.import_module(f".{prof['analysis_plan'][0]}", __package__),
                   prof["analysis_plan"][1])
    run_dir = study.run_dir(run_id)
    probe = import_probe(study)
    if probe["outside_closure"]:
        raise RuntimeError(f"import probe loaded files outside the closure: {probe['outside_closure']}")
    src = {p: sha_file(REPO / p) for p in closure_files(study)}
    proto = {p: sha_file(REPO / p) for p in prof["protocol"]}
    info = {p: sha_file(REPO / p) for p in informational_files(study)}
    prefreeze = {}
    if prefreeze_dir is not None and prefreeze_dir.exists():
        for p in sorted(prefreeze_dir.rglob("*")):
            if p.is_file():
                prefreeze[p.relative_to(REPO).as_posix()] = sha_file(p)
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True).stdout.strip()
    members = sorted(set(src) | set(proto) | set(info) | set(prefreeze))
    tar = _tar(members)
    fr = {
        "study": study.name, "run_id": run_id,
        "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_head_note": f"{git_head} (sources are uncommitted; content hashes identify them)",
        "source_sha256": src, "protocol_sha256": proto,
        "informational_sha256": info, "prefreeze_evidence_sha256": prefreeze,
        "import_probe": probe,
        "method_configs": method_configs(study),
        "baseline_parameters": {m: B.method_config(m, study) for m in study.baselines},
        "design": design(study, run_id),
        "generator": {"F01_F12": "corpus.generate_unit(rng_namespace, family, base_length, "
                                 "replicate), unchanged",
                      "stress": "study_corpus.s01/s02 (BENCHMARK.md section 3)",
                      "seed_formula": "sha256('hid-v1|{namespace}|{family}|{base_length}|"
                                      "{replicate}|{stream}')",
                      "corpus_sha256": sha_file(Path(corpus.__file__)),
                      "study_corpus_sha256": sha_file(Path(study_corpus.__file__))},
        "analysis_plan": plan,
        "resource_policy": dict(study.resources.as_dict(),
                                rss_method=B.RSS_METHOD,
                                worker="python -S -m hierarchy.benchmark --worker METHOD OUT "
                                       f"{study.registry} RSS_LIMIT"),
        "environment": B.environment(),
        "exposure_check": exposure_check(study, run_dir),
        "snapshot": {"path": "source_snapshot.tar", "sha256": hashlib.sha256(tar).hexdigest(),
                     "members": len(members)},
    }
    if not fr["exposure_check"]["clean"]:
        raise RuntimeError(f"reserved-data exposure check failed: {fr['exposure_check']}")
    return fr, tar, "\n".join(f"{sha_file(REPO / m)}  {m}" for m in members) + "\n"


def _tar(members) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for m in members:
            data = (REPO / m).read_bytes()
            ti = tarfile.TarInfo(m)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid = len(data), 0, 0o644, 0, 0
            tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def freeze_sha(fr: dict) -> str:
    return hashlib.sha256(canonical(fr)).hexdigest()


def write(study, run_id: str, prefreeze_dir: Path | None = None) -> dict:
    from .benchmark import atomic_write
    d = study.run_dir(run_id)
    if (d / "freeze.json").exists():
        raise FileExistsError(f"{d / 'freeze.json'} exists; a freeze is written once per run id")
    if (d / "rows").exists() or (d / "corpus_manifest.jsonl").exists() or \
            any(d.glob("corpus_manifest.*.jsonl")):
        raise RuntimeError("corpus or rows already exist for this run id; refusing to freeze after")
    fr, tar, manifest = build(study, run_id, prefreeze_dir)
    atomic_write(d / "source_snapshot.tar", tar)
    atomic_write(d / "source_snapshot.sha256", manifest.encode())
    atomic_write(d / "freeze.json", json.dumps(fr, indent=1, sort_keys=True).encode())
    atomic_write(d / "freeze.sha256", (freeze_sha(fr) + "\n").encode())
    return fr


def load_and_validate(study, run_id: str, purpose: str | None = None
                      ) -> tuple[dict, str, list[str]]:
    from . import benchmark as B
    d = study.run_dir(run_id)
    fr = json.loads((d / "freeze.json").read_text())
    sha = freeze_sha(fr)
    problems = []
    if (d / "freeze.sha256").read_text().strip() != sha:
        problems.append("freeze.json does not match freeze.sha256")
    if fr.get("study") != study.name or fr.get("run_id") != run_id:
        problems.append(f"freeze is for {fr.get('study')}:{fr.get('run_id')}, not {study.name}:{run_id}")
    for group, label in (("source_sha256", "source"), ("protocol_sha256", "protocol")):
        for p, h in fr.get(group, {}).items():
            path = REPO / p
            if not path.is_file():
                problems.append(f"{label} missing since freeze: {p}")
            elif sha_file(path) != h:
                problems.append(f"{label} changed since freeze: {p}")
    extra = sorted(set(closure_files(study)) - set(fr.get("source_sha256", {})))
    for p in extra:
        problems.append(f"source added to the closure since freeze: {p}")
    now = method_configs(study)
    for m, v in fr.get("method_configs", {}).items():
        if now.get(m, {}).get("sha256") != v["sha256"]:
            problems.append(f"method config changed: {m}")
    if sorted(now) != sorted(fr.get("method_configs", {})):
        problems.append("method registry differs from the freeze")
    if canonical(design(study, run_id)) != canonical(fr.get("design")):
        problems.append("declared design differs from the freeze")
    snap = d / "source_snapshot.tar"
    if not snap.is_file() or sha_file(snap) != fr.get("snapshot", {}).get("sha256"):
        problems.append("source snapshot missing or differs from the freeze")
    if purpose is not None:
        problems += B.check_environment(fr.get("environment", {}), purpose)
    return fr, sha, problems
