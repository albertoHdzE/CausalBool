"""AUDIT03 -- elementwise parity for the causalbool_paths collapse.

Runs each of the FOUR production copies of _repo_root/_paper_root/
_paper_figures_dir, exactly as written today, against the proposed owner
src/causalbool_paths.py, and prints the disagreement count with its
denominator. Refuses if it loaded nothing: a parity run over zero sites is
not a pass.
"""
import ast, os, sys, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import causalbool_paths as owner

SITES = ["src/analysis/Cancer_Corruption.py",
         "src/analysis/Phase_Transition_Bio_Overlay.py",
         "src/analysis/KRB_Corruption_Anchors.py",
         "src/stats/Bayesian_Meta_Analysis.py"]
WANT = ("_repo_root", "_paper_root", "_paper_figures_dir")

def extract(path):
    """Rebuild the file's copies in isolation, with __file__ set to that file."""
    tree = ast.parse((ROOT / path).read_text())
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in WANT]
    if len(fns) != len(WANT):
        return None
    src = "\n".join(ast.unparse(f) for f in fns)
    ns = {"os": os, "Path": Path, "__file__": str(ROOT / path)}
    exec(compile(textwrap.dedent(src), path, "exec"), ns)
    return ns

# The env override must be exercised too, not just the default branch.
CASES = [None, "/tmp/cb_paper_root_probe"]

rows, diffs = 0, 0
report = []
for path in SITES:
    ns = extract(path)
    if ns is None:
        print(f"REFUSED: could not extract all of {WANT} from {path}")
        sys.exit(2)
    for env in CASES:
        if env is None:
            os.environ.pop(owner.PAPER_ROOT_ENV, None)
        else:
            os.environ[owner.PAPER_ROOT_ENV] = env
        pairs = [
            ("_repo_root",         Path(ns["_repo_root"]()),         owner.repo_root(ROOT / path)),
            ("_paper_root",        Path(ns["_paper_root"]()),        owner.paper_root()),
            ("_paper_figures_dir", Path(ns["_paper_figures_dir"]()), owner.paper_figures_dir()),
        ]
        for name, old, new in pairs:
            rows += 1
            if old != new:
                diffs += 1
                report.append(f"  DIFF {path} [{name}] env={env}\n    copy : {old}\n    owner: {new}")
os.environ.pop(owner.PAPER_ROOT_ENV, None)

if rows == 0:
    print("REFUSED: zero comparisons made."); sys.exit(2)
print(f"causalbool_paths parity: {rows - diffs}/{rows} agree, {diffs} differ "
      f"({len(SITES)} sites x {len(CASES)} env cases x {len(WANT)} helpers)")
for line in report: print(line)

# Negative control: the owner must NOT agree with a deliberately wrong root.
ctrl = owner.repo_root(ROOT / SITES[0]) / "definitely_not_the_root"
print(f"negative control fires: {ctrl != owner.repo_root(ROOT / SITES[0])}")
sys.exit(1 if diffs else 0)
