"""Write the closure's patches (active owner -> report-r2 source) and informational prose diffs.

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
SRC = CLOSURE / "report-r2" / "source"
ACTIVE = ID / "experiments" / "search_diagnosis"
RUN = ID / "results" / "hierarchy_search_diagnosis" / "search-diagnosis-v1-r1"


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
    (out / "R3_reporting_pipeline.patch").write_text(r3)
    (out / "R1R2_build_18_report_r2.patch").write_text(
        udiff(ID / "notebooks" / "build_18.py", SRC / "build_18.py", rel(ID / "notebooks" / "build_18.py")))
    prose = ""
    pairs = [(RUN / n, CLOSURE / "corrected" / m) for n, m in (
        ("REPORT.md", "REPORT.md"), ("DECISION.md", "DECISION.md"),
        ("NEXT_PROTOCOL_DRAFT.md", "NEXT_PROTOCOL_DRAFT.md"), ("HANDOFF.md", "HANDOFF_a1.md"))]
    pairs.append((ID / "bitacora" / "42_hierarchy_search_diagnosis.md",
                   CLOSURE / "corrected" / "bitacora_42_hierarchy_search_diagnosis.md"))
    for old, new in pairs:
        prose += udiff(old, new, rel(old), rel(new))
    (out / "R1R2_prose_corrections.informational.diff").write_text(prose)
    print({p.name: len(p.read_text().splitlines()) for p in sorted(out.iterdir())})
    return 0


if __name__ == "__main__":
    sys.exit(main())
