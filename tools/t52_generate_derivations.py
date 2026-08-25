#!/usr/bin/env python3
"""AUDIT01/T5.2 (D-6 CLOSED by author: ALL TWELVE families) - generate the ten
missing per-family derivation documents, embedding the EXECUTED mechanical
witnesses from papers/method/derivations/verification/<FAMILY>.json.

Existing docs already cover the band framework (01), AND (02_cb_and),
OR (02_cb_or) and the worked exam; this generator adds the remaining families
so the set as a whole covers all twelve, per the author's directive.
Deterministic; re-runnable."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VER = ROOT / "papers/method/derivations/verification"
OUT = ROOT / "papers/method/derivations"

# number -> word for doc filenames
IDX = {"XOR": "03", "NAND": "04", "NOR": "05", "XNOR": "06", "NOT": "07",
       "IMPLIES": "08", "NIMPLIES": "09", "MAJORITY": "10", "KOFN": "11",
       "CANALISING": "12"}

DEFS = {
    "XOR": (
        r"\paragraph{Definition.} $g(x)=x_1\oplus\cdots\oplus x_d$ on the connected inputs $I_c$ (odd parity).",
        r"\paragraph{Closed form.} $J=\{r:\ \sum_{i\in I_c} x_i(r)\equiv 1 \pmod 2\}$, i.e.\ the union over odd subsets $S\subseteq I_c$ of $\bigl(\bigcap_{i\in S}B_i\bigr)\cap\bigl(\bigcap_{i\in I_c\setminus S}\overline{B}_i\bigr)$.",
        r"Parity is invariant under $\varphi$-transport because bit-reversal permutes rows and commutes with coordinate projection.",
    ),
    "NAND": (
        r"\paragraph{Definition.} $g(x)=1-\bigwedge_{i\in I_c}x_i$.",
        r"\paragraph{Closed form.} $J=\mathcal{U}\setminus\bigcap_{i\in I_c}B_i$: the complement of the AND one-set (De Morgan dual via set complement).",
        r"$\varphi$ commutes with complementation: transporting then complementing equals complementing then transporting.",
    ),
    "NOR": (
        r"\paragraph{Definition.} $g(x)=1$ iff all connected inputs are $0$.",
        r"\paragraph{Closed form.} $J=\bigcap_{i\in I_c}\overline{B}_i$: the intersection of zero-bands (complement of the OR one-set).",
        r"Zero-bands transport under $\varphi$ exactly as one-bands ($\varphi B_i^{\sigma}=B_{\varphi(i)}^{\sigma}$).",
    ),
    "XNOR": (
        r"\paragraph{Definition.} $g(x)=1-\mathrm{XOR}(x)$ (even parity).",
        r"\paragraph{Closed form.} $J=\{r:\ \sum_{i\in I_c}x_i(r)\equiv 0\pmod 2\}$, union over even $S\subseteq I_c$ (the empty subset included) of the corresponding band intersections.",
        r"Even-parity unions transport under $\varphi$ by the same row-permutation argument as XOR.",
    ),
    "NOT": (
        r"\paragraph{Definition.} $g(x)=1-x_{a}$ with $a=$\texttt{i} (network-absolute coordinate; default $\min I_c$).",
        r"\paragraph{Closed form.} $J=\overline{B}_{a}$. The parameter convention is absolute coordinates (ORDERING.md \S4b).",
        r"$\varphi\,\overline{B}_{a}=\overline{B}_{\varphi(a)}$ within the arity-$n$ space.",
    ),
    "IMPLIES": (
        r"\paragraph{Definition.} $g(x)=\neg x_{a}\vee x_{b}$, $\langle a,b\rangle=$\texttt{pair} (absolute coordinates; default first two of $I_c$).",
        r"\paragraph{Closed form.} $J=\mathcal{U}\setminus\bigl(B_{a}\cap\overline{B}_{b}\bigr)$: implication fails exactly on $(1,0)$.",
        r"The failure pattern transports as $\varphi(B_a\cap\overline{B}_b)=B_{\varphi(a)}\cap\overline{B}_{\varphi(b)}$.",
    ),
    "NIMPLIES": (
        r"\paragraph{Definition.} $g(x)=x_{a}\wedge\neg x_{b}$.",
        r"\paragraph{Closed form.} $J=B_{a}\cap\overline{B}_{b}$ (the failure pattern of implication itself).",
        r"Same transport identity as IMPLIES without the outer complement.",
    ),
    "MAJORITY": (
        r"\paragraph{Definition.} $g(x)=1$ iff $|\{i\in I_c:x_i=1\}|\ge t$, threshold $t=\lfloor d/2\rfloor+1$ (\texttt{tiePolicy}``\texttt{strict}'', ties$\to$0; D-3). At or above'' policy uses $t=\lceil d/2\rceil$.",
        r"\paragraph{Closed form.} $J=\bigcup_{S\subseteq I_c,\,|S|\ge t}\Bigl(\bigcap_{i\in S}B_i\cap\bigcap_{i\in I_c\setminus S}\overline{B}_i\Bigr)$: the union of Hamming layers at or above the threshold.",
        r"Hamming weight is preserved by $\varphi$, so layer unions are transport-invariant.",
    ),
    "KOFN": (
        r"\paragraph{Definition.} $g(x)=1$ iff $|\{i:x_i=1\}|\ge k$ (\texttt{strict}: $>k$); DEV-T4.7-1 pinned all four sites to one semantics.",
        r"\paragraph{Closed form.} $J=\bigcup_{S\subseteq I_c,\,|S|\ge k}\bigl(\bigcap_{i\in S}B_i\cap\bigcap_{i\in I_c\setminus S}\overline{B}_i\bigr)$ (strict variant uses $|S|>k$).",
        r"As with MAJORITY, $\varphi$ preserves layer structure.",
    ),
    "CANALISING": (
        r"\paragraph{Definition.} If $x_{c}=v$ (canalising coordinate $c=$\texttt{canalisingIndex}, Ic-relative per T4.1/F36) the output is the fixed \texttt{canalisedOutput} $o$; otherwise it falls back to OR over the remaining connected inputs.",
        r"\paragraph{Closed form.} For $o=1$: $J=B_{c}^{v}\cup\bigl(\overline{B}_{c}^{v}\cap R\bigr)$ where $B^{v}_c$ is the value-$v$ band of $c$ and $R$ is the OR one-set over $I_c\setminus\{c\}$ lifted through its own band expression; for $o=0$: $J=\overline{B}^{v}_{c}\cap R$. The closed-form engine realises this by selecting accepting assignments over the $I_c$-tuple and joining free coordinates.",
        r"Transport requires care: $\varphi$ flips coordinate positions, so the canalising coordinate must be re-expressed after transport --- this is why blind $\Phi$-transport was rejected for CANALISING in \texttt{IndexSet} (T1.2) and why F36 fixed the branch explicitly (T4.1).",
    ),
}


def witness_rows(family: str) -> tuple[int, int, str]:
    data = json.loads((VER / f"{family}.json").read_text())
    cases = data["cases"]
    n_cases = len(cases)
    fails = sum(0 if c.get("equal") else 1 for c in cases)
    arities = sorted({c["n"] for c in cases})
    return n_cases, fails, ", ".join(map(str, arities))


def main() -> int:
    summary = json.loads((VER / "witnesses_summary.json").read_text())
    index_lines = [
        "# Derivation documents — gate-family closed forms",
        "",
        "Per-family derivations mandated by AUDIT01/T5.2 (D-6 CLOSED 2026-08-25:",
        "**all twelve families**, author directive). Each document states the",
        "family definition, the closed-form one-set, its band decomposition and",
        "Φ-transport reading, and embeds the EXECUTED mechanical witness",
        "(arity 2..6, elementwise equality vs the exhaustive LUT — never",
        "cardinality alone). Witness JSONs: `verification/`.",
        "Regenerate witnesses: `WolframKernel -script tools/t52_family_witnesses.wl`.",
        "",
        "| Doc | Family | Cases (arity ≤ 6) | Failures |",
        "|---|---|---|---|",
        "| 01_causalBool_inputs | band framework | — | — |",
        "| 02_cb_and / 02_cb_or | AND, OR | see files | — |",
    ]
    for family, (num) in IDX.items():
        n_cases, fails, arities = witness_rows(family)
        assert fails == 0, f"{family}: {fails} failing witness cases"
        defn, form, transport = DEFS[family]
        template = """% AUDIT01/T5.2 - generated derivation document (D-6: all twelve families)
% Witness source: verification/@FAM@.json (executed @EXEC@)
\\documentclass{article}
\\usepackage{amsmath,amssymb}
\\title{Gate family @FAM@: closed-form one-set derivation}
\\date{2026-08-25}
\\begin{document}
\\maketitle

@DEF@

@FORM@

\\paragraph{Ordering transport.} @TRANS@
Canonical internal representation is LSB-first (weights $w(i)=2^{i-1}$);
transport to MSB row order exclusively via the involution $\\varphi$
(\\texttt{GOVERNANCE/ORDERING.md} \\S2).

\\paragraph{Mechanical witness (arity up to 6).} Executed elementwise equality
against the exhaustive truth-table repertoire:
\\begin{center}
\\begin{tabular}{lc}
\\hline
Witness property & Value \\\\ \\hline
Parameterisations swept & per \\texttt{tools/t52_family_witnesses.wl} grid \\\\
Arities covered & @ARITIES@ \\\\
Total cases & @NCASES@ \\\\
Elementwise failures & \\textbf{@FAILS@} \\\\
Maximum symmetric-difference size & 0 \\\\ \\hline
\\end{tabular}
\\end{center}

\\paragraph{Reproduce.} \\texttt{WolframKernel -script tools/t52_family_witnesses.wl}
(regenerates every family's \\texttt{verification/*.json}; exits non-zero on any failure).

\\end{document}
"""
        tex = (template
               .replace("@FAM@", family)
               .replace("@EXEC@", summary["executedAt"])
               .replace("@DEF@", defn)
               .replace("@FORM@", form)
               .replace("@TRANS@", transport)
               .replace("@ARITIES@", arities)
               .replace("@NCASES@", str(n_cases))
               .replace("@FAILS@", str(fails)))
        path = OUT / f"{num}_cb_{family.lower()}.tex"
        path.write_text(tex)
        print("written:", path.name)
        index_lines.append(
            f"| {path.name} | {family} | {n_cases} (arities {arities}) | {fails} |")
    (OUT / "README.md").write_text("\n".join(index_lines) + "\n")
    print("written: README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
