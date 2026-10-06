"""Build the cross-reference graph from the pinned corpus into `corpus/graph.duckdb`.

The OEIS `%Y` fields are the corpus's own edges: one row per (source, target) pair,
self-loops excluded. This is substrate, not an experiment — the same standing as the
Phase 0 corpus build. Every table carries provenance; the graph is rebuildable from the
pinned `oeisdata` SHA alone.

    python -m seqdecon.corpus.build_graph [--db PATH] [--graph PATH]
"""

from __future__ import annotations

import argparse
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb

_A_NUM = re.compile(r"A(\d{6})")
_BATCH = 50_000


def build(db_path: Path, graph_path: Path, quiet: bool = False) -> dict:
    t0 = time.time()
    con = duckdb.connect(str(db_path), read_only=True)
    meta = dict(con.execute("SELECT key, value FROM corpus_meta").fetchall())
    rows = con.execute("SELECT seq_id, content FROM fields WHERE code = 'Y'").fetchall()
    known = {r[0] for r in con.execute("SELECT seq_id FROM sequences").fetchall()}
    con.close()

    pairs: set[tuple[int, int]] = set()
    for seq_id, content in rows:
        for m in _A_NUM.finditer(content):
            dst = int(m.group(1))
            if dst != seq_id:
                pairs.add((seq_id, dst))

    dangling = sorted({d for (_s, d) in pairs if d not in known})

    graph_path.parent.mkdir(parents=True, exist_ok=True)
    if graph_path.exists():
        graph_path.unlink()
    g = duckdb.connect(str(graph_path))
    g.execute("CREATE TABLE nodes (seq_id INTEGER PRIMARY KEY)")
    g.execute("CREATE TABLE edges (src INTEGER, dst INTEGER)")
    g.execute("CREATE TABLE dangling (seq_id INTEGER PRIMARY KEY)")
    g.execute("CREATE TABLE graph_meta (key VARCHAR, value VARCHAR)")

    pairs_sorted = sorted(pairs)
    for i in range(0, len(pairs_sorted), _BATCH):
        chunk = pairs_sorted[i : i + _BATCH]
        g.executemany("INSERT INTO edges VALUES (?, ?)", chunk)
    g.execute("INSERT INTO nodes SELECT DISTINCT src FROM edges "
              "UNION SELECT DISTINCT dst FROM edges")
    g.executemany("INSERT INTO dangling VALUES (?)", [(d,) for d in dangling])
    for k, v in {
        "oeisdata_sha": meta.get("oeisdata_sha", "unknown"),
        "built_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "edges": str(len(pairs)),
        "dangling": str(len(dangling)),
        "builder": "seqdecon.corpus.build_graph",
    }.items():
        g.execute("INSERT INTO graph_meta VALUES (?, ?)", [k, v])
    n_nodes = g.execute("SELECT count(*) FROM nodes").fetchone()[0]
    n_edges = g.execute("SELECT count(*) FROM edges").fetchone()[0]
    g.close()

    if not quiet:
        print(f"graph: {n_edges:,} edges over {n_nodes:,} nodes, "
              f"{len(dangling):,} dangling references, {time.time() - t0:.1f}s")
    return {"edges": n_edges, "nodes": n_nodes, "dangling": len(dangling)}


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=root / "corpus" / "oeis.duckdb")
    ap.add_argument("--graph", type=Path, default=root / "corpus" / "graph.duckdb")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    build(args.db, args.graph, quiet=args.quiet)


if __name__ == "__main__":
    main()
