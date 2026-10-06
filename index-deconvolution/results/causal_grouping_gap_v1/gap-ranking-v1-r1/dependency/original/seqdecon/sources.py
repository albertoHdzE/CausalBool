"""The controlled trio: finance, cellular automata, biological Boolean networks.

The last two are **positive controls**. Their generating program is known, short and
deterministic, so if the pipeline finds no compressible structure *there* the pipeline
is broken and a finance negative is uninterpretable rather than informative.

Finance data and the `.bnet` models are read from the sibling `CausalBool` tree; nothing
is imported from it, only data files are read. Every loader records a content hash so a
result can be traced to the exact bytes it was computed from.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CAUSALBOOL = Path(
    os.environ.get("CAUSALBOOL_ROOT", Path.home() / "Documents/projects/CausalBool")
)
FINANCE_DIR = CAUSALBOOL / "index-deconvolution" / "finance" / "data_long"
BNET_DIR = CAUSALBOOL / "data" / "bio" / "raw"

#: Declared in advance. Class-2 (90, 150), class-3 (30, 45) and class-4 (110, 54)
#: elementary rules, so the arm spans structured, chaotic and complex behaviour rather
#: than being cherry-picked to succeed.
CA_RULES = (30, 45, 54, 90, 110, 150)
CA_WIDTH = 101
CA_STEPS = 4000
BNET_STEPS = 4000


@dataclass(frozen=True)
class Series:
    """One source series, with the provenance needed to reproduce it."""

    name: str
    arm: str  # "finance" | "ca" | "bio"
    values: list  # list[float] for finance, list[int] for the binary arms
    provenance: str


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------


def load_yahoo_close(path: Path) -> list[float]:
    """Closing prices in date order from a Yahoo chart JSON. Nulls dropped."""
    d = json.loads(path.read_text())
    r = d["chart"]["result"][0]
    out: dict[str, float] = {}
    for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
        if c is None:
            continue
        day = datetime.fromtimestamp(t, tz=UTC).strftime("%Y-%m-%d")
        out[day] = float(c)
    return [out[d_] for d_ in sorted(out)]


def load_finance(directory: Path = FINANCE_DIR) -> list[Series]:
    if not directory.is_dir():
        raise FileNotFoundError(f"finance data not found at {directory}")
    out = []
    for p in sorted(directory.glob("*.json")):
        vals = load_yahoo_close(p)
        out.append(
            Series(p.stem, "finance", vals,
                   f"{p.name}@{_sha(p.read_bytes())} n={len(vals)}")
        )
    return out


# ---------------------------------------------------------------------------
# Cellular automata
# ---------------------------------------------------------------------------


def evolve_eca(rule: int, initial: list[int], steps: int) -> list[list[int]]:
    """Space-time diagram of an elementary CA, periodic boundaries."""
    w = len(initial)
    rows = [list(initial)]
    for _ in range(steps - 1):
        cur = rows[-1]
        rows.append(
            [(rule >> ((cur[(i - 1) % w] << 2) | (cur[i] << 1) | cur[(i + 1) % w])) & 1
             for i in range(w)]
        )
    return rows


def load_ca(
    rules: tuple[int, ...] = CA_RULES,
    width: int = CA_WIDTH,
    steps: int = CA_STEPS,
    seed: int = 0,
) -> list[Series]:
    """Busiest-cell time series of each declared rule, under two initial conditions.

    Both initial conditions are declared: ``single`` (one 1 at the centre — the classic
    structured case) and ``random`` (seeded, the generic case). The probe is the cell
    that flips most, tie-broken to the lowest index — the same rule the biological arm
    uses, so the two binary arms are not probed differently.

    The centre cell is *not* used as the probe: under rules 90 and 150 a single-1
    initial condition leaves it frozen at 0, which would have handed the arm two empty
    targets for a reason that has nothing to do with the premise under test.
    """
    single = [0] * width
    single[width // 2] = 1
    rng = random.Random(seed)
    randomic = [rng.randint(0, 1) for _ in range(width)]

    out = []
    for ic_name, initial in (("single", single), ("random", randomic)):
        for rule in rules:
            rows = evolve_eca(rule, initial, steps)
            flips = [
                sum(rows[t][i] != rows[t - 1][i] for t in range(1, len(rows)))
                for i in range(width)
            ]
            best = max(range(width), key=lambda i: (flips[i], -i))
            out.append(
                Series(
                    f"rule{rule}_{ic_name}", "ca", [row[best] for row in rows],
                    f"eca rule={rule} width={width} steps={steps} ic={ic_name} "
                    f"seed={seed} cell={best} flips={flips[best]}",
                )
            )
    return out


# ---------------------------------------------------------------------------
# Biological Boolean networks
# ---------------------------------------------------------------------------

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_RESERVED = {"and", "or", "not", "True", "False"}


def parse_bnet(path: Path) -> tuple[list[str], list]:
    """Parse a PyBoolNet `.bnet` file into node names and compiled update functions.

    Format is one node per line, ``name, expression``, with ``!`` ``&`` ``|`` over node
    names. Constants ``0``/``1`` appear as bare literals.
    """
    names: list[str] = []
    exprs: list[str] = []
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line or "," not in line:
            continue
        name, expr = line.split(",", 1)
        name, expr = name.strip(), expr.strip()
        if not name or name.lower() == "targets":
            continue
        names.append(name)
        exprs.append(expr)

    index = {n: i for i, n in enumerate(names)}
    funcs = []
    for expr in exprs:
        py = expr.replace("!", " not ").replace("&", " and ").replace("|", " or ")
        py = _IDENT.sub(
            lambda m: (f"s[{index[m.group()]}]" if m.group() in index
                       else m.group() if m.group() in _RESERVED else "0"),
            py,
        )
        # `!X` expands to " not X"; a leading space is an IndentationError in eval mode
        funcs.append(compile(py.strip(), "<bnet>", "eval"))
    return names, funcs


def evolve_bnet(funcs: list, initial: list[int], steps: int) -> list[list[int]]:
    """Synchronous trajectory of a Boolean network."""
    rows = [list(initial)]
    for _ in range(steps - 1):
        s = rows[-1]
        rows.append([int(bool(eval(f, {"s": s}))) for f in funcs])
    return rows


def load_bio(
    directory: Path = BNET_DIR, steps: int = BNET_STEPS, seed: int = 0
) -> list[Series]:
    """Per network, the trajectory of the node that flips most, from a seeded random IC.

    Boolean networks fall onto an attractor quickly and most nodes freeze; the busiest
    node is the one that carries an occurrence set at all. Tie-break is the lowest node
    index, so the choice is deterministic. Networks whose busiest node never flips are
    returned with an empty series and filtered downstream, counted rather than silently
    dropped.
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"bnet models not found at {directory}")
    out = []
    for p in sorted(directory.glob("*.bnet")):
        try:
            names, funcs = parse_bnet(p)
        except Exception as exc:  # a malformed model is recorded, not hidden
            out.append(Series(p.stem, "bio", [], f"{p.name} PARSE-FAILED: {exc}"))
            continue
        if not funcs:
            out.append(Series(p.stem, "bio", [], f"{p.name} no nodes"))
            continue
        rng = random.Random(seed)
        initial = [rng.randint(0, 1) for _ in names]
        try:
            rows = evolve_bnet(funcs, initial, steps)
        except Exception as exc:
            out.append(Series(p.stem, "bio", [], f"{p.name} EVAL-FAILED: {exc}"))
            continue
        flips = [
            sum(rows[t][i] != rows[t - 1][i] for t in range(1, len(rows)))
            for i in range(len(names))
        ]
        best = max(range(len(names)), key=lambda i: (flips[i], -i))
        out.append(
            Series(
                p.stem, "bio", [row[best] for row in rows],
                f"{p.name}@{_sha(p.read_bytes())} node={names[best]} "
                f"flips={flips[best]} nodes={len(names)} steps={steps} seed={seed}",
            )
        )
    return out
