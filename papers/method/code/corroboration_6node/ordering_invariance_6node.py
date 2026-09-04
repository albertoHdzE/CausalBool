from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

CM06 = [
    [1, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0],
    [1, 0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 0],
    [1, 0, 1, 0, 1, 0],
]

DYN06 = ["OR", "NOT", "OR", "IMPLIES", "AND", "XOR"]


def phi(j: int, n: int) -> int:
    bits = f"{j - 1:0{n}b}"
    return int(bits[::-1], 2) + 1


def phi_set(values: list[int], n: int) -> list[int]:
    return sorted(phi(v, n) for v in values)


def lsb_inputs(n: int) -> list[tuple[int, ...]]:
    return [tuple(int(b) for b in f"{x:0{n}b}"[::-1]) for x in range(2**n)]


def msb_inputs(n: int) -> list[tuple[int, ...]]:
    return [tuple(int(b) for b in f"{x:0{n}b}") for x in range(2**n)]


def network_update(state: tuple[int, ...]) -> tuple[int, ...]:
    x1, x2, x3, x4, _, _ = state
    y1 = x1
    y2 = 1 - x2
    y3 = x3
    y4 = int((1 - x1) or x4)
    y5 = int(x2 and x4)
    y6 = (x1 + x3 + y5) % 2
    return (y1, y2, y3, y4, y5, y6)


def output_indices_with_one(outputs: list[tuple[int, ...]], node: int) -> list[int]:
    return [i for i, row in enumerate(outputs, start=1) if row[node - 1] == 1]


def wl_list(values: list[int]) -> str:
    return "{" + ", ".join(str(v) for v in values) + "}"


def write_text(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    and_lsb = [11, 12, 15, 16, 27, 28, 31, 32, 43, 44, 47, 48, 59, 60, 63, 64]
    xor_lsb = [
        2, 4, 5, 7, 10, 11, 13, 16, 18, 20, 21, 23, 26, 27, 29, 32,
        34, 36, 37, 39, 42, 43, 45, 48, 50, 52, 53, 55, 58, 59, 61, 64,
    ]

    # AUDIT03. `lsb_inputs` was defined here and NEVER CALLED: the LSB one-sets
    # above were hard-coded literals, so only the MSB side of the invariance
    # claim was ever recomputed. The check still had teeth -- a wrong literal
    # would fail it -- but it asserted half of what it could compute.
    #
    # Both sides are now derived from the same update rule under the two
    # orderings, and the published literals are verified against the computed
    # LSB one-sets rather than trusted. The orphan is gone because it is used.
    outputs_lsb = [network_update(state) for state in lsb_inputs(6)]
    and_lsb_computed = output_indices_with_one(outputs_lsb, 5)
    xor_lsb_computed = output_indices_with_one(outputs_lsb, 6)
    if and_lsb_computed != and_lsb or xor_lsb_computed != xor_lsb:
        raise SystemExit(
            "ordering_invariance_6node.py: the published LSB one-sets do not "
            f"match the computed ones.\n  AND published {and_lsb}\n"
            f"  AND computed  {and_lsb_computed}\n  XOR published {xor_lsb}\n"
            f"  XOR computed  {xor_lsb_computed}")

    outputs_msb = [network_update(state) for state in msb_inputs(6)]
    and_phi = phi_set(and_lsb, 6)
    xor_phi = phi_set(xor_lsb, 6)
    and_msb = output_indices_with_one(outputs_msb, 5)
    xor_msb = output_indices_with_one(outputs_msb, 6)

    verified_and = and_phi == and_msb
    verified_xor = xor_phi == xor_msb
    verified_phi_involution = all(phi(phi(j, 6), 6) == j for j in range(1, 65))

    if not (verified_and and verified_xor and verified_phi_involution):
        raise SystemExit("Verification failed for ordering_invariance_6node.py")

    session_lines = [
        "In := phi06[j_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, 6]], 2]",
        f"In := andLSB06 = {wl_list(and_lsb)}",
        f"In := andPhi06 = Sort[phi06 /@ andLSB06]",
        f"In := andMSB06 = {wl_list(and_msb)}",
        "",
        "(* Transported AND one-set under MSB ordering *)",
        f"Out = {wl_list(and_phi)}",
        "",
        "(* Direct MSB exhaustive baseline for node 5 *)",
        f"Out = {wl_list(and_msb)}",
        "",
        "(* Exact invariance check for AND *)",
        f"Out = {verified_and}",
        "",
        f"In := xorLSB06 = {wl_list(xor_lsb)}",
        f"In := xorPhi06 = Sort[phi06 /@ xorLSB06]",
        f"In := xorMSB06 = {wl_list(xor_msb)}",
        "",
        "(* Transported XOR one-set under MSB ordering *)",
        f"Out = {wl_list(xor_phi)}",
        "",
        "(* Direct MSB exhaustive baseline for node 6 *)",
        f"Out = {wl_list(xor_msb)}",
        "",
        "(* Exact invariance check for XOR *)",
        f"Out = {verified_xor}",
        "",
        "(* Involution check: phi(phi(j)) = j for all j in U *)",
        f"Out = {verified_phi_involution}",
    ]

    summary_rows = [
        f"Node 5 (AND) & {len(and_lsb)} & \\texttt{{{str(verified_and)}}} & \\texttt{{{str(verified_phi_involution)}}} \\\\",
        f"Node 6 (XOR) & {len(xor_lsb)} & \\texttt{{{str(verified_xor)}}} & \\texttt{{{str(verified_phi_involution)}}} \\\\",
    ]

    summary = {
        "PhiInvolutionVerified": verified_phi_involution,
        "AND": {
            "LSBSet": and_lsb,
            "TransportedSet": and_phi,
            "MSBBaseline": and_msb,
            "Verified": verified_and,
        },
        "XOR": {
            "LSBSet": xor_lsb,
            "TransportedSet": xor_phi,
            "MSBBaseline": xor_msb,
            "Verified": verified_xor,
        },
    }

    write_text(BASE_DIR / "ordering_invariance_session.txt", session_lines)
    write_text(BASE_DIR / "ordering_invariance_summary_rows.tex", summary_rows)
    (BASE_DIR / "ordering_invariance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
