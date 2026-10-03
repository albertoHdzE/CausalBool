"""HID-v1 benchmark execution: freeze, isolated workers, watchdog, resumable rows.

Each encoding runs in its own ``python -S`` worker process (no site-packages, so
no sibling-repository .pth injection), receives only the bit string on stdin and
the method name, and writes its archive atomically. The parent enforces the
wall-clock watchdog, reads the child's own peak RSS from ``os.wait4`` and runs
at most two workers at once. The worker also watches its own peak RSS and exits
with a distinct code above the limit, because macOS does not enforce RLIMIT_AS.

Rows for one case are written together, atomically, to rows/<case_id>.json and
only then counted as done; ``--resume`` skips a case whose stored rows carry the
same freeze hash and input hash and whose archives are intact. Timeouts, RSS
breaches, errors and budget exhaustion are rows with explicit status.

Every function takes an explicit ``study`` (``study.LEGACY`` by default, which is the
frozen HID-v1 behaviour): its method registry, roles and resource policy. Workers
resolve their method from the named registry and dispatch on its declared kind.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import codes as C
from .baselines import BASELINE_METHODS, METHOD_CODEC, encode_baseline, select_best
from .decode import decode_archive
from .infer import ABLATIONS, RESTRICTED_ORACLE, infer

PKG = Path(__file__).resolve().parent
ID_ROOT = PKG.parent                      # index-deconvolution/
REPO = ID_ROOT.parent
RESULTS = ID_ROOT / "results" / "hierarchy_v1"

HID_METHODS = tuple(f"hid_{k}" for k in ABLATIONS)
ENCODE_METHODS = HID_METHODS + BASELINE_METHODS
ALL_METHODS = ENCODE_METHODS + ("baseline_best",)

WALL_LIMIT_S = 30.0
RSS_LIMIT_BYTES = 1 << 30
MAX_WORKERS = 2
TOTAL_BUDGET_S = 6 * 3600
RSS_EXIT = 86
RSS_METHOD = ("os.wait4 ru_maxrss of the worker process (bytes on darwin); worker "
              "self-terminates with exit 86 when its ru_maxrss exceeds 1 GiB")

FROZEN_SOURCES = (
    "index-deconvolution/hierarchy/__init__.py", "index-deconvolution/hierarchy/codes.py",
    "index-deconvolution/hierarchy/model.py", "index-deconvolution/hierarchy/wire.py",
    "index-deconvolution/hierarchy/decode.py", "index-deconvolution/hierarchy/candidates.py",
    "index-deconvolution/hierarchy/infer.py", "index-deconvolution/hierarchy/baselines.py",
    "index-deconvolution/hierarchy/corpus.py", "index-deconvolution/hierarchy/benchmark.py",
    "index-deconvolution/hierarchy/diagnostics.py", "index-deconvolution/hierarchy/report.py",
    "index-deconvolution/hierarchy/ledger.py", "index-deconvolution/hierarchy/validation.py",
    "index-deconvolution/hierarchy/cli.py",
    "index-deconvolution/src/deconvolution.py", "index-deconvolution/src/causalbool.py",
    "src/description_lengths.py",
)
PROTOCOL_FILES = (
    "index-deconvolution/PROTOCOL_hierarchical_index_generalization.md",
    "index-deconvolution/protocols/hierarchy_v1/WIRE_FORMAT.md",
    "index-deconvolution/protocols/hierarchy_v1/BENCHMARK.md",
    "index-deconvolution/protocols/hierarchy_v1/ACCEPTANCE.md",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def run_dir(run_id: str) -> Path:
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_." for c in run_id):
        raise ValueError(f"run id {run_id!r} must be lowercase [a-z0-9-_.]")
    if run_id.startswith("dev"):
        return RESULTS / "development" / run_id
    return RESULTS / run_id


def _study(study):
    if study is None:
        from .study import LEGACY
        return LEGACY
    return study


def _is_legacy(study) -> bool:
    return study is None or study.registry == "hid-v1"


def method_config(method: str, study=None) -> dict:
    if _is_legacy(study):
        if method.startswith("hid_"):
            cfg = ABLATIONS[method[4:]]
            return {"kind": "hid", "search_config": cfg.__dict__ | {}}
    else:
        spec = study.method(method)
        if spec.kind == "hid_v2":
            return {"kind": "hid_v2", "search_config": spec.config.as_dict()}
        if spec.kind == "portfolio":
            return {"kind": "portfolio", "constituents": list(study.baselines)}
    return {"kind": "baseline", "method": method,
            "codec_id": METHOD_CODEC.get(method), "zlib_level": C.ZLIB_LEVEL,
            "lzma_preset": C.LZMA_PRESET, "lzma_check": "CHECK_CRC64",
            "pair_max_rules": C.PAIR_MAX_RULES}


def method_config_sha(method: str, study=None) -> str:
    if _is_legacy(study):
        if method.startswith("hid_"):
            return ABLATIONS[method[4:]].sha256()
    elif study.method(method).kind == "hid_v2":
        return study.method(method).config.sha256()
    if method == "baseline_best":
        return sha256_bytes(canonical([method_config(m) for m in BASELINE_METHODS]))
    return sha256_bytes(canonical(method_config(method)))


# ---------------------------------------------------------------------------
# Environment and freeze
# ---------------------------------------------------------------------------

def environment() -> dict:
    import lzma
    import zlib
    env = {"python": sys.version, "python_implementation": platform.python_implementation(),
           "platform": platform.platform(), "machine": platform.machine(),
           "zlib_version": zlib.ZLIB_VERSION, "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
           "lzma_liblzma": getattr(lzma, "__version__", None) or _liblzma_version(),
           "cpu_count": os.cpu_count()}
    try:
        env["cpu"] = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                    capture_output=True, text=True).stdout.strip()
        env["ram_bytes"] = int(subprocess.run(["sysctl", "-n", "hw.memsize"],
                                              capture_output=True, text=True).stdout.strip())
    except (OSError, ValueError):
        env["cpu"], env["ram_bytes"] = None, None
    for mod in ("numpy", "matplotlib", "pybdm", "pytest"):
        try:
            m = __import__(mod)
            env[f"{mod}_version"] = getattr(m, "__version__", "unknown")
        except ImportError:
            env[f"{mod}_version"] = None
    return env


# Fields whose change can change a stored number, per purpose. Everything else in
# ``environment()`` (hardware, OS build, plotting and test libraries) is informational.
# Workers run ``python -S``: archive bytes depend on the interpreter and the two
# compression libraries only; the bootstrap depends on numpy; BDM on numpy and pybdm.
ENVIRONMENT_REQUIRED = {
    "benchmark": ("python", "python_implementation", "zlib_version", "zlib_runtime_version",
                  "lzma_liblzma"),
    "diagnostics": ("python", "python_implementation", "numpy_version", "pybdm_version"),
    "report": ("python", "python_implementation", "numpy_version"),
}
ENVIRONMENT_INFORMATIONAL = ("platform", "machine", "cpu", "cpu_count", "ram_bytes",
                             "matplotlib_version", "pytest_version")


def check_environment(frozen_env: dict, purpose: str, current: dict | None = None) -> list[str]:
    """Mismatches between the frozen and the current scientific environment.

    A field the freeze does not record, or records as null, is a mismatch: a missing
    fingerprint must never match silently."""
    cur = environment() if current is None else current
    problems = []
    for k in ENVIRONMENT_REQUIRED[purpose]:
        want, got = frozen_env.get(k), cur.get(k)
        if want is None:
            problems.append(f"environment[{k}]: the freeze records no value, so {purpose} "
                            "cannot be validated; re-freeze under a new run id")
        elif got is None:
            problems.append(f"environment[{k}]: frozen {want!r}, but the current interpreter "
                            f"provides none; run {purpose} with the frozen environment")
        elif want != got:
            problems.append(f"environment[{k}]: frozen {want!r}, current {got!r}; run "
                            f"{purpose} with the frozen interpreter/libraries or re-freeze "
                            "under a new run id")
    return problems


def environment_comparison(frozen_env: dict, current: dict | None = None) -> dict:
    """Informational field-by-field comparison (used by offline verification)."""
    cur = environment() if current is None else current
    keys = sorted(set(frozen_env) | set(cur))
    return {k: {"frozen": frozen_env.get(k), "current": cur.get(k),
                "equal": frozen_env.get(k) == cur.get(k),
                "required_for": [p for p, ks in ENVIRONMENT_REQUIRED.items() if k in ks]}
            for k in keys}


def _liblzma_version() -> str:
    import lzma
    probe = lzma.compress(b"", format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6)
    return f"probe-sha256:{sha256_bytes(probe)}"


def source_hashes() -> dict:
    return {p: sha256_file(REPO / p) for p in FROZEN_SOURCES}


def protocol_hashes() -> dict:
    return {p: sha256_file(REPO / p) for p in PROTOCOL_FILES}


def build_freeze(run_id: str) -> dict:
    from . import corpus
    from .report import ANALYSIS_PLAN
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True).stdout.strip()
    return {
        "run_id": run_id, "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_head_note": f"{git_head} (inputs are uncommitted; content hashes identify them)",
        "protocol_sha256": protocol_hashes(), "source_sha256": source_hashes(),
        "documentation_sha256_informational": {
            "index-deconvolution/hierarchy/SEARCH_SPEC.md":
                sha256_file(REPO / "index-deconvolution/hierarchy/SEARCH_SPEC.md")},
        "search_configs": {k: v.__dict__ | {"sha256": v.sha256()} for k, v in ABLATIONS.items()},
        "restricted_oracle_config": RESTRICTED_ORACLE.__dict__ | {"sha256": RESTRICTED_ORACLE.sha256()},
        "baseline_parameters": {m: method_config(m) for m in BASELINE_METHODS},
        "methods": list(ALL_METHODS),
        "environment": environment(),
        "generator": {"splits": {k: {kk: list(vv) for kk, vv in v.items()}
                                 for k, v in corpus.SPLITS.items()},
                      "held_out": list(corpus.HELD_OUT), "streams": list(corpus.STREAMS),
                      "seed_formula": "sha256('hid-v1|split|family|base_length|replicate|stream')"},
        "expected_counts": {s: {"scored_strings": v["scored_strings"],
                                "method_rows": v["scored_strings"] * len(ALL_METHODS)}
                            for s, v in corpus.expected_counts().items()},
        "resource_policy": {"wall_limit_s": WALL_LIMIT_S, "rss_limit_bytes": RSS_LIMIT_BYTES,
                            "max_workers": MAX_WORKERS, "total_budget_s": TOTAL_BUDGET_S,
                            "rss_method": RSS_METHOD,
                            "worker": "python -S -m hierarchy.benchmark --worker METHOD"},
        "analysis_plan": ANALYSIS_PLAN,
    }


def freeze_sha(freeze: dict) -> str:
    return sha256_bytes(canonical(freeze))


def write_freeze(run_id: str) -> dict:
    d = run_dir(run_id)
    path = d / "freeze.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; a freeze is written once per run id")
    if (d / "rows").exists() or (d / "corpus_manifest.jsonl").exists():
        raise RuntimeError("corpus or rows already exist for this run id; refusing to freeze after")
    fr = build_freeze(run_id)
    atomic_write(path, json.dumps(fr, indent=1, sort_keys=True).encode())
    atomic_write(d / "freeze.sha256", (freeze_sha(fr) + "\n").encode())
    return fr


def load_and_validate_freeze(run_id: str, purpose: str | None = None, study=None
                             ) -> tuple[dict, str, list[str]]:
    """Return (freeze, its sha, list of mismatches against the current tree).

    With ``purpose`` ("benchmark", "diagnostics", "report") the frozen scientific
    environment for that purpose is enforced as well."""
    if not _is_legacy(study):
        from . import freeze_v2
        return freeze_v2.load_and_validate(study, run_id, purpose)
    d = run_dir(run_id)
    fr = json.loads((d / "freeze.json").read_text())
    sha = freeze_sha(fr)
    stored = (d / "freeze.sha256").read_text().strip()
    problems = []
    if stored != sha:
        problems.append("freeze.json does not match freeze.sha256")
    for p, h in fr["source_sha256"].items():
        if sha256_file(REPO / p) != h:
            problems.append(f"source changed since freeze: {p}")
    for p, h in fr["protocol_sha256"].items():
        if sha256_file(REPO / p) != h:
            problems.append(f"protocol changed since freeze: {p}")
    for k, v in fr["search_configs"].items():
        if ABLATIONS[k].sha256() != v["sha256"]:
            problems.append(f"search config changed: {k}")
    if purpose is not None:
        problems += check_environment(fr.get("environment", {}), purpose)
    return fr, sha, problems


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _rss_watch(limit: int) -> None:
    import resource
    while True:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform != "darwin":
            rss *= 1024
        if rss > limit:
            os._exit(RSS_EXIT)
        time.sleep(0.02)


def worker_main(method: str, out_path: str, registry: str = "hid-v1",
                rss_limit: int = RSS_LIMIT_BYTES) -> int:
    threading.Thread(target=_rss_watch, args=(rss_limit,), daemon=True).start()
    bits = sys.stdin.read()
    t0 = time.perf_counter_ns()
    info: dict = {}
    kind = "hid_v1" if registry == "hid-v1" and method.startswith("hid_") else None
    if registry != "hid-v1":
        from .study import method_registry
        spec = next(m for m in method_registry(registry) if m.name == method)
        kind = spec.kind
    if kind == "hid_v2":
        from .search_v2 import infer_v2
        res = infer_v2(bits, spec.config)
        archive = res.archive
        tele = res.telemetry
        info = {"mode": "literal" if archive[4] == C.CODEC_LITERAL else "hid",
                "rule_count": None, "dag_depth": None,
                "candidate_count": sum((tele["stages"][s].get("serialized") or 0)
                                       for s in tele["stages"]),
                "deterministic_work": tele["stages"].get("L", {}).get("work_units"),
                "stop_reason": "completed", "counters": tele,
                "best_source": res.selected_stage, "trace": list(res.trace)}
        if archive[4] == C.CODEC_HID:
            from .ledger import archive_ledger
            model = archive_ledger(archive)["model"]
            info["rule_count"], info["dag_depth"] = len(model.rules), model.depth()
    elif kind == "hid_v1":
        res = infer(bits, ABLATIONS[method[4:]])
        archive = res.archive
        info = {"mode": res.mode, "rule_count": res.rule_count, "dag_depth": res.dag_depth,
                "candidate_count": res.candidate_counts.get("serialized_unique"),
                "deterministic_work": res.work.get("work_units"),
                "stop_reason": res.stop_reason, "counters": res.candidate_counts,
                "best_source": res.best_source, "trace": list(res.trace)}
    else:
        archive = encode_baseline(bits, method)
    t1 = time.perf_counter_ns()
    atomic_write(Path(out_path), archive)
    info["encode_wall_ns"] = t1 - t0
    sys.stdout.write(json.dumps(info))
    return 0


# ---------------------------------------------------------------------------
# Parent: case execution
# ---------------------------------------------------------------------------

def store_archive(d: Path, archive: bytes) -> tuple[str, str]:
    h = sha256_bytes(archive)
    rel = f"archives/{h[:2]}/{h}.isd"
    p = d / rel
    if not p.exists():
        atomic_write(p, archive)
    elif p.read_bytes() != archive:
        raise RuntimeError(f"content-addressed archive {rel} is corrupted")
    return rel, h


class _Job:
    def __init__(self, case, method: str, d: Path, registry: str = "hid-v1",
                 rss_limit: int | None = None) -> None:
        self.case, self.method, self.d = case, method, d
        self.registry = registry
        self.rss_limit = RSS_LIMIT_BYTES if rss_limit is None else rss_limit
        self.tmp = d / "tmp" / f"{case.case_id}.{method}.{os.getpid()}.out"
        self.tmp.parent.mkdir(parents=True, exist_ok=True)
        self.err = d / "tmp" / f"{case.case_id}.{method}.{os.getpid()}.err"
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0",
               "PYTHONPATH": f"{ID_ROOT}{os.pathsep}{REPO / 'src'}"}
        self.t0 = time.perf_counter_ns()
        self.errfh = open(self.err, "wb")
        self.proc = subprocess.Popen(
            self.worker_argv(method), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.errfh, env=env, cwd=str(ID_ROOT))
        self.out = b""
        self._reader = threading.Thread(target=self._feed, daemon=True)
        self._reader.start()
        self.done = None

    def worker_argv(self, method: str) -> list[str]:
        argv = [sys.executable, "-S", "-m", "hierarchy.benchmark", "--worker", method,
                str(self.tmp)]
        if self.registry != "hid-v1" or self.rss_limit != RSS_LIMIT_BYTES:
            argv += [self.registry, str(self.rss_limit)]
        return argv

    def _feed(self) -> None:
        try:
            self.proc.stdin.write(self.case.bits.encode("ascii"))
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        self.out = self.proc.stdout.read()

    def poll(self, wall_limit: float) -> bool:
        pid, status, ru = os.wait4(self.proc.pid, os.WNOHANG)
        elapsed = (time.perf_counter_ns() - self.t0) / 1e9
        if pid == 0:
            if elapsed > wall_limit:
                self.proc.kill()
                pid, status, ru = os.wait4(self.proc.pid, 0)
                self.proc.returncode = -9
                self._finish(status, ru, timed_out=True)
                return True
            return False
        self.proc.returncode = os.waitstatus_to_exitcode(status)
        self._finish(status, ru, timed_out=False)
        return True

    def _finish(self, status, ru, timed_out: bool) -> None:
        self._reader.join(timeout=5)
        self.errfh.close()
        rss = ru.ru_maxrss if sys.platform == "darwin" else ru.ru_maxrss * 1024
        self.done = {"timed_out": timed_out, "exit": self.proc.returncode,
                     "worker_wall_ns": time.perf_counter_ns() - self.t0,
                     "peak_rss_bytes": int(rss), "stdout": self.out}


def _row_base(case, method, run_id, fsha, study=None) -> dict:
    row = _row_fields(case, method, run_id, fsha, study)
    if not _is_legacy(study):
        role = study.role(case.split)
        row.update({"study": study.name, "role": role.name,
                    "rng_namespace": role.rng_namespace, "evidence_role": role.evidence_role,
                    "method_kind": study.method(method).kind})
    return row


def _row_fields(case, method, run_id, fsha, study) -> dict:
    return {"run_id": run_id, "freeze_sha256": fsha, "split": case.split, "family": case.family,
            "base_length": case.base_length, "replicate": case.replicate,
            "ragged": case.ragged, "case_id": case.case_id, "input_sha256": case.input_sha256,
            "n_bits": len(case.bits), "method": method,
            "config_sha256": method_config_sha(method, study), "status": None,
            "archive_path": None, "archive_sha256": None, "archive_bits": None,
            "raw_bits": len(case.bits), "raw_archive_bits": None, "decode_ok": None,
            "selected_codec_id": None, "selected_method": None, "rule_count": None,
            "dag_depth": None, "candidate_count": None, "deterministic_work": None,
            "stop_reason": None, "encode_wall_ns": None, "worker_wall_ns": None,
            "peak_rss_bytes": None, "rss_method": RSS_METHOD, "exception_type": None,
            "exception_message": None, "stderr_log": None, "search_counters": None,
            "best_source": None, "trace": None}


def _job_row(job: _Job, run_id: str, fsha: str, raw_bits: int, study=None,
             wall_limit: float | None = None) -> tuple[dict, bytes | None]:
    case, method, d = job.case, job.method, job.d
    row = _row_base(case, method, run_id, fsha, study)
    row["raw_archive_bits"] = raw_bits
    res = job.done
    row["worker_wall_ns"] = res["worker_wall_ns"]
    row["peak_rss_bytes"] = res["peak_rss_bytes"]
    hid = method.startswith("hid_") if _is_legacy(study) else study.method(method).is_hid
    wall_limit = WALL_LIMIT_S if wall_limit is None else wall_limit
    errtext = job.err.read_bytes().decode("utf-8", "replace") if job.err.exists() else ""
    archive = None
    if res["timed_out"] or res["exit"] == RSS_EXIT:
        kind = "timeout" if res["timed_out"] else "rss_limit"
        row["status"] = f"{kind}_raw" if hid else f"censored_{kind}"
        row["exception_type"] = kind
        row["exception_message"] = (f"worker exceeded {wall_limit} s" if res["timed_out"]
                                    else f"worker exceeded {job.rss_limit} bytes RSS")
        from .wire import encode_literal
        archive = encode_literal(case.bits)          # operational fallback, labelled
    elif res["exit"] != 0:
        row["status"] = "error"
        lines = [ln for ln in errtext.strip().splitlines() if ln.strip()]
        last = lines[-1] if lines else f"exit {res['exit']}"
        row["exception_type"] = last.split(":")[0][:200]
        row["exception_message"] = last[:2000]
    else:
        try:
            archive = job.tmp.read_bytes()
            info = json.loads(res["stdout"].decode() or "{}")
        except (OSError, ValueError) as exc:
            row["status"] = "error"
            row["exception_type"] = type(exc).__name__
            row["exception_message"] = str(exc)
            archive = None
        else:
            row["status"] = "ok"
            row["encode_wall_ns"] = info.get("encode_wall_ns")
            for k in ("rule_count", "dag_depth", "candidate_count", "deterministic_work",
                      "stop_reason", "best_source", "trace"):
                row[k] = info.get(k)
            row["search_counters"] = info.get("counters")
    if errtext.strip() and row["status"] == "error":
        log = d / "logs" / "stderr" / f"{case.case_id}.{method}.log"
        atomic_write(log, errtext.encode())
        row["stderr_log"] = str(log.relative_to(d))
    if archive is not None:
        try:
            ok = decode_archive(archive) == case.bits
        except Exception as exc:                     # noqa: BLE001 -- recorded, not hidden
            ok = False
            row["exception_type"] = type(exc).__name__
            row["exception_message"] = f"decoder: {exc}"
        row["decode_ok"] = ok
        if not ok:
            row["status"] = "error"
            row["exception_type"] = row["exception_type"] or "wrong_decode"
        rel, h = store_archive(d, archive)
        row["archive_path"], row["archive_sha256"] = rel, h
        row["archive_bits"] = 8 * len(archive)
        row["selected_codec_id"] = archive[4]
    for p in (job.tmp, job.err):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    return row, archive


def portfolio_row(case, rows: dict, archives: dict, run_id: str, fsha: str,
                  raw_bits: int, study=None) -> dict:
    row = _row_base(case, "baseline_best", run_id, fsha, study)
    row["raw_archive_bits"] = raw_bits
    cons = [rows[m] for m in BASELINE_METHODS]
    ok = all(r["status"] == "ok" for r in cons)
    avail = {m: archives[m] for m in BASELINE_METHODS
             if rows[m]["status"] == "ok" and archives.get(m) is not None}
    walls = [r["encode_wall_ns"] for r in cons if r["encode_wall_ns"] is not None]
    workers = [r["worker_wall_ns"] for r in cons if r["worker_wall_ns"] is not None]
    row["encode_wall_ns"] = sum(walls) if ok else None
    row["worker_wall_ns"] = sum(workers)
    row["peak_rss_bytes"] = max((r["peak_rss_bytes"] or 0) for r in cons)
    row["rss_method"] = "max over the nine constituent workers"
    if not avail:
        row["status"] = "error"
        row["exception_type"] = "no_constituent"
        return row
    if ok:
        best = select_best(avail)
    else:
        best = min(avail, key=lambda m: (len(avail[m]), avail[m][4], avail[m]))
    a = avail[best]
    row["status"] = "ok" if ok else "incomplete_constituents"
    row["selected_method"] = best
    row["selected_codec_id"] = a[4]
    row["archive_path"] = rows[best]["archive_path"]
    row["archive_sha256"] = rows[best]["archive_sha256"]
    row["archive_bits"] = 8 * len(a)
    row["decode_ok"] = decode_archive(a) == case.bits
    if not row["decode_ok"]:
        row["status"] = "error"
    return row


def not_run_rows(case, run_id: str, fsha: str, reason: str, study=None) -> list[dict]:
    out = []
    for m in (ALL_METHODS if _is_legacy(study) else study.all_methods):
        r = _row_base(case, m, run_id, fsha, study)
        r["status"] = "not_run"
        r["exception_message"] = reason
        out.append(r)
    return out


def case_rows_path(d: Path, case) -> Path:
    return d / "rows" / f"{case.case_id}.json"


def case_is_complete(d: Path, case, fsha: str, study=None) -> bool:
    p = case_rows_path(d, case)
    if not p.exists():
        return False
    try:
        rows = json.loads(p.read_text())
    except ValueError:
        return False
    methods = ALL_METHODS if _is_legacy(study) else study.all_methods
    if len(rows) != len(methods) or {r["method"] for r in rows} != set(methods):
        return False
    for r in rows:
        if r["freeze_sha256"] != fsha or r["input_sha256"] != case.input_sha256 or \
                (not _is_legacy(study) and r["config_sha256"] != method_config_sha(r["method"], study)):
            raise RuntimeError(f"stored rows for {case.case_id} carry a different freeze or "
                               "input hash; this run id is invalid for resume")
        if r["status"] == "not_run":
            return False
        if r["archive_path"]:
            a = d / r["archive_path"]
            if not a.exists() or sha256_file(a) != r["archive_sha256"]:
                return False
    return True


class Budget:
    def __init__(self, d: Path, total_s: float) -> None:
        self.path = d / "budget.json"
        self.total = total_s
        self.used = json.loads(self.path.read_text())["used_s"] if self.path.exists() else 0.0
        self.t0 = time.monotonic()

    def elapsed(self) -> float:
        return self.used + time.monotonic() - self.t0

    def save(self) -> None:
        atomic_write(self.path, json.dumps({"used_s": self.elapsed(),
                                            "total_s": self.total}).encode())
        self.used, self.t0 = self.elapsed(), time.monotonic()

    def expired(self) -> bool:
        return self.elapsed() > self.total


def run_cases(cases, d: Path, run_id: str, fsha: str, resume: bool, log,
              budget: Budget | None = None, stop_after: int | None = None, study=None,
              job_class=None) -> dict:
    """Run every case; at most ``max_workers`` encodings concurrently (MAX_WORKERS for
    the legacy study, the study's resource policy otherwise). ``job_class`` lets a test
    supply a controlled worker; production uses ``_Job``."""
    from .wire import encode_literal
    legacy = _is_legacy(study)
    encode_methods = ENCODE_METHODS if legacy else study.encode_methods
    all_methods = ALL_METHODS if legacy else study.all_methods
    max_workers = MAX_WORKERS if legacy else study.resources.max_workers
    wall_limit = WALL_LIMIT_S if legacy else study.resources.wall_limit_s
    registry = "hid-v1" if legacy else study.registry
    rss_limit = RSS_LIMIT_BYTES if legacy else study.resources.rss_limit_bytes
    job_class = job_class or _Job
    stats = {"done": 0, "skipped": 0, "not_run": 0}
    pending_cases = []
    for c in cases:
        if resume and case_is_complete(d, c, fsha, study):
            stats["skipped"] += 1
        else:
            if case_rows_path(d, c).exists() and not resume:
                raise RuntimeError(f"rows exist for {c.case_id}; use --resume")
            pending_cases.append(c)
    queue = [(c, m) for c in pending_cases for m in encode_methods]
    per_case: dict[str, dict] = {c.case_id: {} for c in pending_cases}
    arcs: dict[str, dict] = {c.case_id: {} for c in pending_cases}
    by_id = {c.case_id: c for c in pending_cases}
    running: list[_Job] = []
    finished_cases = 0
    stop = False
    while queue or running:
        if budget is not None and budget.expired():
            stop = True
        while not stop and queue and len(running) < max_workers:
            c, m = queue.pop(0)
            running.append(job_class(c, m, d) if legacy else
                           job_class(c, m, d, registry=registry, rss_limit=rss_limit))
        if not running:
            break
        time.sleep(0.005)
        for job in list(running):
            if job.poll(wall_limit):
                running.remove(job)
                raw_bits = 8 * len(encode_literal(job.case.bits))
                row, archive = _job_row(job, run_id, fsha, raw_bits, study, wall_limit)
                per_case[job.case.case_id][job.method] = row
                arcs[job.case.case_id][job.method] = archive
                cid = job.case.case_id
                if len(per_case[cid]) == len(encode_methods):
                    case = by_id[cid]
                    rows = per_case.pop(cid)
                    rows["baseline_best"] = portfolio_row(case, rows, arcs.pop(cid), run_id,
                                                          fsha, raw_bits, study)
                    out = [rows[m] for m in all_methods]
                    atomic_write(case_rows_path(d, case),
                                 json.dumps(out, sort_keys=True).encode())
                    stats["done"] += 1
                    finished_cases += 1
                    bad = [r["method"] for r in out if r["status"] != "ok"]
                    log(f"{cid} done ({stats['done']}/{len(pending_cases)})"
                        + (f" non-ok: {bad}" if bad else ""))
                    if budget is not None:
                        budget.save()
                    if stop_after is not None and finished_cases >= stop_after:
                        stop = True        # deliberate interruption: unfinished cases unwritten
    if budget is not None and budget.expired():
        for cid in per_case:               # every unfinished case becomes explicit not_run rows
            rows = not_run_rows(by_id[cid], run_id, fsha, "total wall-clock budget expired", study)
            atomic_write(case_rows_path(d, by_id[cid]), json.dumps(rows, sort_keys=True).encode())
            stats["not_run"] += 1
    return stats


def collect_rows(d: Path, cases) -> list[dict]:
    rows = []
    for c in cases:
        p = case_rows_path(d, c)
        if p.exists():
            rows.extend(json.loads(p.read_text()))
    rows.sort(key=lambda r: (r["case_id"], r["method"]))
    return rows


def write_cases_jsonl(d: Path, split_rows: dict[str, list[dict]], order=None) -> None:
    lines = []
    for split in (order or ("development", "confirmation", "transfer")):
        for r in split_rows.get(split, []):
            lines.append(json.dumps(r, sort_keys=True))
    atomic_write(d / "cases.jsonl", ("\n".join(lines) + "\n").encode() if lines else b"")


def benchmark(run_id: str, split: str, resume: bool, log=print,
              stop_after: int | None = None, require_freeze: bool = True, study=None,
              budget=None, fsha: str | None = None, job_class=None) -> dict:
    """Benchmark one declared split (role) of ``study``. A non-legacy study passes its
    own ``budget`` (cumulative category clock) and, for unfrozen development runs, the
    development fingerprint as ``fsha``."""
    from . import corpus
    legacy = _is_legacy(study)
    d = run_dir(run_id) if legacy else study.run_dir(run_id)
    if require_freeze:
        fr, fsha, problems = load_and_validate_freeze(run_id, purpose="benchmark", study=study)
        if problems:
            raise RuntimeError("freeze validation failed: " + "; ".join(problems))
    elif fsha is None:
        fsha = "development-unfrozen"
    if legacy:
        cases, manifest = corpus.split_cases(split)
    else:
        if split not in study.run_roles(run_id):
            raise RuntimeError(f"run {run_id} does not declare role {split}")
        cases, manifest = study.role_cases(split, d)
    man_path = d / f"corpus_manifest.{split}.jsonl"
    text = "\n".join(json.dumps(m, sort_keys=True) for m in manifest) + "\n"
    if man_path.exists() and man_path.read_text() != text:
        raise RuntimeError(f"regenerated {split} corpus differs from the stored manifest")
    atomic_write(man_path, text.encode())
    if budget is None:
        budget = Budget(d, TOTAL_BUDGET_S)
    (d / "logs").mkdir(parents=True, exist_ok=True)
    logf = open(d / "logs" / f"benchmark_{split}.log", "a")

    def _log(msg):
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
        logf.write(line + "\n")
        logf.flush()
        log(line)

    _log(f"start split={split} cases={len(cases)} resume={resume} freeze={fsha}")
    stats = run_cases(cases, d, run_id, fsha, resume, _log, budget, stop_after, study,
                      job_class)
    _log(f"end split={split} stats={stats} budget_used_s={budget.elapsed():.0f}")
    logf.close()
    _merge_outputs(d, study, run_id)
    return stats


def _merge_outputs(d: Path, study=None, run_id: str | None = None) -> None:
    from . import corpus
    split_rows = {}
    manifests = []
    legacy = _is_legacy(study)
    order = ("development", "confirmation", "transfer") if legacy else \
        tuple(study.run_roles(run_id))
    for split in order:
        mp = d / f"corpus_manifest.{split}.jsonl"
        if mp.exists():
            if legacy:
                cases, _ = corpus.split_cases(split)
            else:
                cases = [_CaseRef(cid) for cid in _manifest_case_ids(mp)]
            split_rows[split] = collect_rows(d, cases)
            manifests.append(mp.read_text())
    write_cases_jsonl(d, split_rows, order)
    atomic_write(d / "corpus_manifest.jsonl", "".join(manifests).encode())


class _CaseRef:
    """A case id only (merging needs no bits; prospective inputs are not regenerated)."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id


def _manifest_case_ids(mp: Path) -> list[str]:
    out = []
    for line in mp.read_text().splitlines():
        if line.strip():
            m = json.loads(line)
            out += m["case_ids"] if "case_ids" in m else [m["case_id"]]
    return out


# ---------------------------------------------------------------------------
# Tiny-oracle comparison (development evidence, not a benchmark split)
# ---------------------------------------------------------------------------

def run_oracle(out_path: Path) -> dict:
    from .tests import oracle
    res = {"language": "trees of <= 3 nodes: L(w), R(L(w),c), R(R(L(w),c1),c2), "
                       "C(L(a),L(b)); no sharing, AP, schema, transform or patch",
           "restricted_search_config": RESTRICTED_ORACLE.__dict__,
           "restricted_search_exhausts_language": False,
           "exhaustion_note": ("the restricted search proposes L, R(L) at the exact "
                               "primitive period, and every C(L,L) split; it never "
                               "proposes R(R(L)) or R of a non-primitive root, so it "
                               "does not enumerate the language; gaps below measure it"),
           "tables": {}}
    for name, table in (("n_le_8_all_targets", oracle.oracle_n8()),
                        ("generated_le_64_leaves_1_4", oracle.oracle_generated64())):
        rows = []
        for s, row in table.items():
            r = infer(s, RESTRICTED_ORACLE)
            full = infer(s, ABLATIONS["full"])
            rows.append(dict(row, target=s, n=len(s),
                             restricted_bits=r.archive_bits, restricted_mode=r.mode,
                             full_bits=full.archive_bits, full_mode=full.mode,
                             gap_restricted_vs_raw_inclusive=r.archive_bits - row["raw_inclusive_bits"],
                             full_minus_raw_inclusive=full.archive_bits - row["raw_inclusive_bits"]))
        gaps = [x["gap_restricted_vs_raw_inclusive"] for x in rows]
        res["tables"][name] = {
            "targets": len(rows),
            "represented_targets": sum(1 for x in rows if x["grammar_only_bits"] is not None),
            "grammar_beats_raw": sum(1 for x in rows if x["raw_inclusive_mode"] == "hid"),
            "restricted_gap_bits": {"zero": sum(1 for g in gaps if g == 0),
                                    "positive": sum(1 for g in gaps if g > 0),
                                    "negative": sum(1 for g in gaps if g < 0),
                                    "max": max(gaps)},
            "full_beats_oracle": sum(1 for x in rows if x["full_minus_raw_inclusive"] < 0),
            "examples": [x for x in rows if x["target"] in ("1" * 64, "0" * 8, "01" * 32, "1")],
            "rows": rows}
    atomic_write(out_path, json.dumps(res, indent=1).encode())
    return res


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        sys.exit(worker_main(sys.argv[2], sys.argv[3]))
    if len(sys.argv) == 6 and sys.argv[1] == "--worker":
        sys.exit(worker_main(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])))
    sys.exit("usage: python -S -m hierarchy.benchmark --worker METHOD OUT_PATH [REGISTRY RSS]")


class CategoryBudget:
    """Durable cumulative wall-clock allowance per execution category of a study.

    Every increment is appended to ``<result_root>/execution_ledger.jsonl``, so elapsed
    time survives interruptions, resumes and repeated jobs; nothing ever resets it."""

    def __init__(self, study, category: str, job: str, run_id: str) -> None:
        self.path = study.result_root / "execution_ledger.jsonl"
        self.category, self.job, self.run_id = category, job, run_id
        self.total = study.resources.allowance(category)
        if self.total is None:
            raise ValueError(f"study {study.name} declares no allowance for {category}")
        self.used = self.category_used(study, category)
        self.t0 = self.last = time.monotonic()

    @staticmethod
    def category_used(study, category: str | None = None) -> float:
        p = study.result_root / "execution_ledger.jsonl"
        if not p.exists():
            return 0.0
        tot = 0.0
        for line in p.read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                if category is None or e["category"] == category:
                    tot += e["seconds"]
        return tot

    def elapsed(self) -> float:
        return self.used + time.monotonic() - self.t0

    def save(self) -> None:
        now = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as fh:
            fh.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                 "category": self.category, "job": self.job,
                                 "run_id": self.run_id, "seconds": now - self.last}) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.last = now

    def expired(self) -> bool:
        return self.elapsed() > self.total
