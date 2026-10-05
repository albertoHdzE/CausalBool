"""bnet.py

Parser for PyBoolNet ``.bnet`` files into the CausalBool :class:`Network` form.

A ``.bnet`` file lists one node per line as ``name, expression`` where the
expression uses ``!`` (not), ``&`` (and), ``|`` (or) over node names, in
disjunctive normal form for gene-regulatory models.  Each node is parsed into
its referenced inputs (functional connectivity) and its Boolean function is
evaluated exhaustively into a look-up table over those inputs, giving the exact
network in our formalism without any assumption about gate type.

Node order follows the file; indices are 0-based.  The look-up table of each
node is built LSB-first over its connected inputs in ascending index order,
matching :mod:`causalbool`.
"""

from __future__ import annotations

import re

from causalbool import Network

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _to_python(expr: str) -> str:
    return expr.replace("!", " not ").replace("&", " and ").replace("|", " or ")


def parse_bnet(path: str) -> tuple[Network, list[str]]:
    """Parse a ``.bnet`` file, returning the network and the node-name list."""
    names: list[str] = []
    exprs: list[str] = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "," not in line:
                continue
            left, right = line.split(",", 1)
            left = left.strip()
            right = right.strip()
            if left.lower() == "targets" and right.lower() == "factors":
                continue  # header
            names.append(left)
            exprs.append(right)

    index = {name: i for i, name in enumerate(names)}
    n = len(names)

    C = [[0] * n for _ in range(n)]
    gates: list[str] = ["FALSE"] * n
    params: list[dict] = [dict() for _ in range(n)]

    for k, expr in enumerate(exprs):
        referenced = sorted(
            {index[t] for t in _IDENT.findall(expr) if t in index}
        )
        py = _to_python(expr)

        m = len(referenced)
        table = []
        for y in range(2 ** m):
            ns = {}
            for j, var in enumerate(referenced):
                ns[names[var]] = bool((y >> j) & 1)
            val = eval(py, {"__builtins__": {}}, ns)  # noqa: S307 - controlled input
            table.append(int(bool(val)))

        for var in referenced:
            C[k][var] = 1
        if m == 0:
            gates[k] = "TRUE" if table[0] == 1 else "FALSE"
        else:
            gates[k] = "LUT"
            params[k] = {"table": table}

    return Network(n=n, C=C, gates=gates, params=params), names


def network_to_bnet(net: Network, names: list[str]) -> str:
    """Write ``net`` as ``.bnet`` text, the inverse of :func:`parse_bnet`.

    Each node's function is tabulated over its connected inputs and written as
    the compact DNF of :func:`deconvolution.minimal_dnf`, so any gate the
    forward method accepts (named families and LUT alike) is expressible.  The
    header ``targets, factors`` makes the file readable by BoolNet's
    ``loadNetwork`` as well as by PyBoolNet.  Constants are written ``0``/``1``.
    """
    from causalbool import truth_table
    from deconvolution import minimal_dnf

    lines = ["targets, factors"]
    for k in range(net.n):
        ic = net.connected_inputs(k)
        g = net.gates[k]
        if g in ("TRUE", "FALSE"):
            reduced = [1 if g == "TRUE" else 0]
        elif g == "LUT":
            reduced = list(net.params[k]["table"])
        else:
            reduced = truth_table(g, len(ic), net.params[k])
        if not any(reduced):
            expr = "0"
        elif all(reduced):
            expr = "1"
        else:
            terms = []
            for clause in minimal_dnf(reduced):
                lits = ([names[ic[j]] for j in clause["activators"]]
                        + ["!" + names[ic[j]] for j in clause["inhibitors"]])
                terms.append(" & ".join(lits))
            expr = " | ".join(f"({t})" if len(terms) > 1 and "&" in t else t
                              for t in terms)
        lines.append(f"{names[k]}, {expr}")
    return "\n".join(lines) + "\n"
