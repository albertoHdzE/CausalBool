"""Write the follow-up closure's REPLACEMENT patches (active owner -> report-r3 source).

Patches use repository-relative a/ b/ paths for ``git apply`` from the repository root;
they are delivered for review and NOT applied. Reads only; writes this closure's patches/.
"""
import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLOSURE = HERE.parent
ID = CLOSURE.parents[3]
REPO = ID.parent
SRC = CLOSURE / "report-r3" / "source"
ACTIVE = ID / "experiments" / "search_diagnosis"


def udiff(old: Path | None, new: Path, path: str, newpath: str | None = None) -> str:
    a = old.read_text().splitlines(keepends=True) if old and old.exists() else []
    b = new.read_text().splitlines(keepends=True)
    if a == b:
        return ""
    head = "" if a else f"diff --git a/{path} b/{path}\nnew file mode 100644\n"
    return head + "".join(difflib.unified_diff(a, b, "/dev/null" if not a else f"a/{path}",
                                               f"b/{newpath or path}"))


def main() -> int:
    out = CLOSURE / "patches"
    rel = lambda p: str(p.relative_to(REPO))   # noqa: E731
    r3 = ""
    for f in sorted((SRC / "search_diagnosis").rglob("*.py")):
        act = ACTIVE / f.relative_to(SRC / "search_diagnosis")
        r3 += udiff(act if act.exists() else None, f, rel(act))
    (out / "R3_R3a_R3b_reporting_pipeline.patch").write_text(r3)
    (out / "R1R2_build_18_report_r3.patch").write_text(
        udiff(ID / "notebooks" / "build_18.py", SRC / "build_18.py", rel(ID / "notebooks" / "build_18.py")))
    print({p.name: len(p.read_text().splitlines()) for p in sorted(out.iterdir())})
    return 0


if __name__ == "__main__":
    sys.exit(main())
