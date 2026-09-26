
import json, os, sys
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_MODULES = {"efficiency_ranker", "schema_index"}
EVENTS = {"code": 0, "ranker_input": [], "refused_opens": [], "refused_imports": []}
DECLARED = os.environ.get("EFFICIENCY_RANKER_INPUT", "")
BASES = tuple(os.path.realpath(p) for p in {sys.base_prefix, sys.prefix, sys.exec_prefix})


class Deny:
    def find_spec(self, name, path=None, target=None):
        top = name.split(".")[0]
        if top in sys.stdlib_module_names or top in ALLOWED_MODULES:
            return None
        EVENTS["refused_imports"].append(name)
        raise ImportError(f"guard: import of {name!r} refused")


def classify(path):
    real = os.path.realpath(path)
    if DECLARED and real == os.path.realpath(DECLARED):
        return "ranker_input"
    if real.startswith(BASES):
        return "code"
    if real.startswith(os.path.join(WORKSPACE, "")) and (
            real.endswith((".py", ".pyc")) or os.path.basename(os.path.dirname(real))
            == "__pycache__" or os.path.isdir(real)):
        return "code"
    return None


def hook(event, args):
    if event != "open" or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    path = os.fsdecode(args[0])
    kind = classify(path)
    if kind == "ranker_input":
        EVENTS["ranker_input"].append(path)
    elif kind == "code":
        EVENTS["code"] += 1
    else:
        EVENTS["refused_opens"].append(path)
        raise PermissionError(f"guard: open of {path!r} refused")


sys.meta_path.insert(0, Deny())
sys.path[:] = [WORKSPACE] + [p for p in sys.path if os.path.realpath(p).startswith(BASES)]
sys.addaudithook(hook)

mode = sys.argv[1]
result = {"mode": mode}
try:
    if mode == "replay":
        import efficiency_ranker
        result["replay"] = efficiency_ranker.replay(json.loads(sys.argv[2]))
    elif mode == "control_import":
        import research.structural_oracle  # noqa: F401  (must be refused)
        result["violation"] = "import succeeded"
    elif mode == "control_open":
        with open(sys.argv[2], "rb") as handle:  # must be refused
            handle.read(1)
        result["violation"] = "open succeeded"
    result["status"] = "OK"
except BaseException as exc:
    result["status"] = "REFUSED" if isinstance(exc, (ImportError, PermissionError)) else "ERROR"
    result["error"] = f"{type(exc).__name__}: {exc}"
result["events"] = EVENTS
result["loaded_modules"] = sorted(sys.modules)
sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
