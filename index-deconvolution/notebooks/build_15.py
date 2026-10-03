"""Builder for notebook 15 -- the shifted zero: where BDM sees structure and where it cannot.

Regenerates notebooks/15_shifted_zero_bdm_probe.ipynb. Standard library to build;
executing needs the CausalBool kernel (root venv with pybdm 0.1.0). CTM and BDM come
from the repository owner, src/description_lengths.py (ctm_1d, bdm_1d,
bdm_1d_partition) -- this notebook defines no complexity measure of its own. Archive
sizes come from the HID-v1 codec, index-deconvolution/hierarchy (encode_literal, infer).

Revision 2026-10-02 (HID-v1 stage H0): corrections from bitacora 33 section 3 are
applied here and regenerated, not edited into the executed notebook. Objects are
named A64, A72, A24, AX64, AXM64; every number the prose states is asserted by an
executed cell; the drop-policy scans are kept as labelled historical diagnostics
beside full-coverage scans. The comment block at the end of the setup cell (A64 and
A72 written as 8-bit rows) is the author's own edit, made in the executed notebook at
09:43 on 2026-10-02 and folded in here verbatim so builder and notebook agree.
"""
import os
from _nblib import md, code, write_notebook, BOOTSTRAP

HERE = os.path.dirname(os.path.abspath(__file__))

EXTRA = r'''
# The complexity measures live in ONE place: the repository's description-length owner.
_core = os.path.join(os.path.dirname(ROOT), "src")
for _p in (_core, ROOT):                       # ROOT first: a sibling repo ships a module "hierarchy"
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
sys.modules.pop("hierarchy", None)
import math, random, itertools, collections
from description_lengths import ctm_1d, bdm_1d, bdm_1d_partition, bdm_1d_trace
from hierarchy.wire import encode_literal
from hierarchy.infer import infer
from hierarchy.decode import decode_archive

def shannon_bits_per_symbol(s):
    """FOIL ONLY. Empirical Shannon entropy of the 0/1 frequencies -- not a complexity measure."""
    n = len(s); c = collections.Counter(s)
    return abs(-sum(v / n * math.log2(v / n) for v in c.values()))

def block_entropy(s, b):
    """FOIL ONLY. Shannon entropy (bits) of the distribution of aligned b-blocks."""
    blocks = [s[i:i + b] for i in range(0, len(s) - b + 1, b)]
    n = len(blocks); c = collections.Counter(blocks)
    return -sum(v / n * math.log2(v / n) for v in c.values())

def program_length(src, target):
    """Length (characters) of a Python expression that EVALUATES to target.
    Refuses a program that does not reproduce the string. Characters are not bits of a
    binary code: see section 3 for UTF-8 payload bits and actual archive bits."""
    out = eval(src, {"itertools": itertools})
    assert out == target, f"program does not reproduce the target: {src!r}"
    return len(src)

def show_bits(ax, strings, title, mark=None):
    """Render strings as rows of black (1) / white (0) cells -- the object itself."""
    M = np.array([[int(c) for c in s] for s in strings])
    ax.imshow(1 - M, cmap="gray", vmin=0, vmax=1, aspect="equal")
    ax.set_xticks(range(M.shape[1])); ax.set_yticks(range(M.shape[0]))
    ax.set_yticklabels(mark or strings, family="monospace", fontsize=8)
    ax.set_xticklabels(range(M.shape[1]), fontsize=7)
    ax.grid(False); ax.set_title(title)

def coverage(s, b, **kw):
    """Scored and dropped bits of one owner call, read from the partition it actually used."""
    d = bdm_1d_partition(s, block=b, **kw)
    return d["score"], d["covered_bits"], d["dropped_bits"]

ONES = "1" * 8
SHIFT = ["1" * i + "0" + "1" * (7 - i) for i in range(8)]   # zero at position i = 0..7
A64 = "".join(SHIFT)                                          # your string, 64 bits
A72 = ONES + A64                                              # with the all-ones anchor, 72 bits
print("A64 =", A64, len(A64), "bits")
print("A72 =", A72, len(A72), "bits")

# -----A64 -----
# 01111111
# 10111111
# 11011111
# 11101111
# 11110111
# 11111011
# 11111101
# 11111110

#-----A72--------
# 11111111
# 01111111
# 10111111
# 11011111
# 11101111
# 11110111
# 11111011
# 11111101
# 11111110
'''.strip()

cells = [
md(r"""
# 15 · The Shifted Zero: Where BDM Sees Structure, and Where It Cannot

> **Revised 2026-10-02 (HID-v1, stage H0).** The scientific review in bitacora 33 §3 found
> six problems in the first version: character counts were read as if they were bits; the
> name *A* meant two different strings; the drop-tail scans compared objects of different
> coverage; a finite slope was described as a law; a CTM spread was read against an
> invariance "slack" that has no numerical value; and one statement about P3 was false.
> They are corrected below, and each corrected statement is checked by an executed cell.
> The original drop-policy measurements are kept, labelled **historical diagnostic**.

**The question.** Take eight 8-bit strings, $a_i = 1^{i}\,0\,1^{7-i}$ for $i = 0..7$: one zero
sliding across a line of ones. Written separately, a program for each one grows a little
longer as the zero moves inward. That small variation is what BDM/CTM reports too, and it is
the finer granularity that BDM is credited with over Shannon entropy, which is flat for these
strings. But an observer who sees *the shift* writes **one** program, with an index, that
generates every case.

**Names used throughout.** Positions are zero-based from the left.

| name | definition | bits |
|---|---|---|
| A64 | $a_0 a_1 \dots a_7$ | 64 |
| A72 | `11111111` + A64 | 72 |
| A24 | `11111111` $a_0 a_1$ (the scratch "A" of bitacora 32) | 24 |
| AX64 | `11111111` $a_0 \dots a_6$: cases 1..8 of the scratch indexing (the first 64 bits of A72, **not** A64) | 64 |
| AXM64 | the same eight cases in the order (8,1,6,7,2,4,3,5) | 64 |

**What we probe.**

| § | experiment | what it isolates |
|---|---|---|
| 1 | render the object | what the string actually is, before any measure |
| 2 | each case separately: program length, CTM, Shannon | per-block granularity |
| 3 | one program for all cases, and what it costs in bits | characters versus bits versus archives |
| 4 | sum of the parts versus the whole, at every block size | BDM's partition and its coverage |
| 5 | more zeros, from `11111111` to `00000000` | a finite slope, and why it is not a law |
| 6 | the same blocks in random order | does order register? |
| 7 | rotation: last bit moved to the front | does a one-bit relabelling register? |
| 8 | patterns of patterns: A24, AX64, AXM64, P1–P3 | repetition at a higher level |
| 9 | the period and the schema are different objects | why "period 9" is not "compact sumandos" |

**A rule we follow throughout.** $K$ is uncomputable, so on the Kolmogorov side we only
ever show **explicit programs that run and reproduce the string**, each an upper bound in a
stated language. A Python expression is measured in characters; it becomes a bit count only
under a stated encoding (UTF-8 here) and framing. The decodable binary archives of §3 are
measured in bits of a specified format. CTM values are in bits under the $D(5)$
Turing-machine reference. These units are not interchangeable, so we never set one against
another as a gap.

**Shannon appears only as a foil**, because the claim under test is phrased against it.
Under this project's rules it is never a complexity measure.
"""),
code(BOOTSTRAP),
code(EXTRA),

md(r"""
## 1 · The object, before any measure

Below are the eight cases, then A64 $= a_0 + a_1 + \dots + a_7$ wrapped into rows of **8**
bits and rows of **9** bits. Look at the right-hand panel before reading any number.
"""),
code(r"""
fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
show_bits(ax[0], SHIFT, "the 8 cases $a_0..a_7$")
wrap = lambda s, w: [s[i:i + w].ljust(w, "1") for i in range(0, len(s), w)]
show_bits(ax[1], wrap(A64, 8), "A64 wrapped at width 8", mark=[f"row {r}" for r in range(8)])
w9 = wrap(A64, 9)
show_bits(ax[2], w9, "A64 wrapped at width 9 (last row padded)", mark=[f"row {r}" for r in range(len(w9))])
plt.tight_layout(); plt.show()
zeros = [i for i, c in enumerate(A64) if c == "0"]
print("zero positions in A64:", zeros)
print("gaps between zeros   :", np.diff(zeros).tolist())
assert zeros == list(range(0, 64, 9)) and A72 == ("1" * 8 + "0") * 8
"""),
md(r"""
**What the render shows.** At width 8 the zeros form a diagonal: the shift you designed.
At width 9 the diagonal collapses into **one vertical column**. The zeros sit at positions
$0, 9, 18, \dots, 63$, every gap is 9, and so

$$\mathrm{A64} = (0\,1^8)^7\,0 , \qquad \mathrm{A72} = 1^8 + \mathrm{A64} = (1^8\,0)^8 .$$

"Shift the zero one step per block" over blocks of 8 is, as a whole, a **period-9 string**.
At width 8 the shift is visible as a diagonal; at width 9 it disappears into plain
repetition. A partition of length 8 is the one choice that turns this repetition into eight
*different* blocks.
"""),

md(r"""
## 2 · Each case separately: program length, CTM, Shannon

First your nine one-off programs (`seq_11111111` …). We transcribe only the returned
expression, without `def` and docstring. Each one is checked by running it. Then CTM of each
8-bit string from the $D(5)$ table, and the Shannon foil.
"""),
code(r"""
USER_PROGS = {
    "11111111": 'f"{(1 << 8) - 1:08b}"',
    "01111111": 'f"{((1 << 8) - 1) >> 1:08b}"',
    "10111111": 'f"{(1 << 7) | (((1 << 8) - 1) >> 2):08b}"',
    "11011111": 'f"{(3 << 6) | (((1 << 8) - 1) >> 3):08b}"',
    "11101111": 'f"{(7 << 5) | (((1 << 8) - 1) >> 4):08b}"',
    "11110111": 'f"{(15 << 4) | (((1 << 8) - 1) >> 5):08b}"',
    "11111011": 'f"{(31 << 3) | (((1 << 8) - 1) >> 6):08b}"',
    "11111101": 'f"{(63 << 2) | (((1 << 8) - 1) >> 7):08b}"',
    "11111110": 'f"{((1 << 8) - 1) << 1 & 0xFF:08b}"',
}
cases = [ONES] + SHIFT
plen = [program_length(USER_PROGS[s], s) for s in cases]
ctm  = [ctm_1d(s) for s in cases]
H    = [shannon_bits_per_symbol(s) for s in cases]
print(f"{'string':>10} {'prog chars':>10} {'CTM bits':>9} {'Shannon b/sym':>13}")
for s, p, c, h in zip(cases, plen, ctm, H):
    print(f"{s:>10} {p:>10} {c:>9.3f} {h:>13.3f}")
"""),
code(r"""
x = np.arange(len(cases)); lab = ["1s"] + [f"z@{i}" for i in range(8)]
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
ax[0].plot(x, plen, "o-", color=INK); ax[0].set_title("your one-off programs (chars)")
ax[1].plot(x, ctm, "o-", color=HL);   ax[1].set_title("CTM (bits, D(5))")
ax[2].plot(x, H, "o-", color=OK);     ax[2].set_title("Shannon foil (bits/symbol)")
ax[2].set_ylim(-0.05, 1.05)
for a in ax: a.set_xticks(x); a.set_xticklabels(lab, rotation=45, fontsize=8)
plt.tight_layout(); plt.show()
spread = max(ctm[1:]) - min(ctm[1:])
print(f"CTM spread over the 8 shifted cases: {spread:.3f} bits (min {min(ctm[1:]):.3f}, max {max(ctm[1:]):.3f})")
print("CTM mirror-symmetric (a_i vs a_{7-i}):",
      all(abs(ctm_1d(SHIFT[i]) - ctm_1d(SHIFT[7 - i])) < 1e-12 for i in range(8)))
"""),
md(r"""
**Reading.** Your hand-drawn plot comes back, in CTM units: the all-ones string is the
cheapest, the zero at either end costs a little more, and the zero in the interior costs the
most, with a plateau there. Shannon is flat across all eight shifted cases, since each has
one zero and seven ones. So per block, CTM does show a granularity that Shannon lacks.

Two cautions keep the argument honest.

1. **The mirror symmetry is a property of the table, not a finding.** The $D(5)$ machine
   space is closed under reversal and complement, so $\mathrm{CTM}(a_i) =
   \mathrm{CTM}(a_{7-i})$ holds by construction. It is pinned as a test in the owner.
2. **The spread printed above is a table-dependent distinction, not an error bar.**
   *(Corrected.)* The first version said the spread lay "inside the invariance slack". The
   invariance theorem bounds the difference between two reference machines by a constant
   it does not evaluate, so it supplies **no numerical tolerance** against which this
   spread can be read, and the spread is not an estimated interval around true $K$. What
   the table shows is a distinction made by one reference machine, nothing more.
   Per-block granularity is in any case not where the argument bites; it bites where the
   blocks are *composed* (§3–§8).
"""),

md(r"""
## 2b · Word length and overlap: where do the hills come from?

**The hypothesis under test (author, 2026-10-02).** The hills and valleys of the CTM curve
above come from the way BDM walks the input: linearly, with overlapping windows. With no
overlap and a word of length 8, the curve should come close to Shannon, which is flat.

**Design.** Each case $a_i$ is scored again under every word length $b = 1..8$ and every step
$s = b, b-1, \dots, 1$; the **overlap** between consecutive windows is $b - s$. A setting is
used only if its windows cover all eight bits: sliding needs $(8-b) \bmod s = 0$; a
non-overlapping word that does not divide 8 is scored with the recursive remainder (the tail
becomes a shorter block, marked **r**). Settings that would leave bits unscored are shown
blank, not filled in.

**Common coordinate.** Shannon gives the same value to all eight cases, so "close to Shannon"
means a *flat profile*. Each profile is therefore read by its **spread** over the eight cases
and drawn **centred** on its own mean, so that bits of BDM and bits of Shannon never meet on
one axis. Shannon is the zero line.

**The inner workings.** `bdm_1d_trace`, added to the owner (`src/description_lengths.py`),
returns every window BDM scores, in the order pybdm produces them, with its CTM lookup,
whether it is a first sighting or a repeat, what it adds to the sum, and the running total.
It is built from pybdm's own `decompose` and `lookup`, and it refuses to return unless its
final running total equals `bdm_1d` to $10^{-9}$.
"""),
code(r"""
def print_trace(s, max_rows=None, **kw):
    # Print the walk: one line per scored window, drawn at its true offset in the input.
    t = bdm_1d_trace(s, **kw)
    step = t["block"] if t["shift"] is None else t["shift"]
    rows = t["rows"]
    print(f"input ({t['n']} bits) block={t['block']} step={step} overlap={t['block'] - step} "
          f"remainder={t['remainder']}: {len(rows)} windows, {t['covered_bits']} bits covered")
    print(f"{'step':>4} {'bits':>7}  {'window, drawn in place':<{t['n']}}  {'CTM':>7} {'seen':>4} {'adds':>7} {'running':>8}")
    print(f"{'':>4} {'':>7}  {s}")
    for r in rows[:max_rows]:
        lane = "." * r["start"] + r["block"] + "." * (t["n"] - r["start"] - r["length"])
        span = f"{r['start']}-{r['start'] + r['length'] - 1}"
        print(f"{r['step']:>4} {span:>7}  {lane}  {r['ctm']:>7.3f} {r['occurrence']:>4} "
              f"{r['added']:>7.3f} {r['running']:>8.3f}")
    if max_rows is not None and len(rows) > max_rows:
        print(f"     ... {len(rows) - max_rows} more windows; final running total {rows[-1]['running']:.3f}")
    return t

# Section 2 itself: an 8-bit case scored with an 8-bit word. How many windows are there?
a3 = SHIFT[3]
t_ns = print_trace(a3, block=8); print()
t_s1 = print_trace(a3, block=8, shift=1); print()
assert len(t_ns["rows"]) == len(t_s1["rows"]) == 1
assert t_ns["rows"][0]["ctm"] == ctm_1d(a3) == t_s1["rows"][0]["ctm"]
# A word shorter than the case: now there is a walk, and the windows overlap.
t_41 = print_trace(a3, block=4, shift=1)
"""),
md(r"""
**What the trace shows.** In section 2 each case is 8 bits and the word is 8 bits, so BDM
makes **one** window and reads **one** value from the $D(5)$ table: BDM$_8(a_i)$ is
CTM$(a_i)$, with or without a sliding step, because a window of 8 can only sit in one place
inside 8 bits. There is no walk and no overlap in section 2. The hills of that plot are
therefore not produced by the walk: they are the table's own values for the eight strings.

The last trace is the walk the hypothesis has in mind: word 4, step 1, so consecutive windows
share three bits. Every window that contains the zero is a different string (the zero sits
at a different offset), and every window that misses it is `1111`, scored once and then
charged only $\log_2$ increments. The grid below asks what this walk does to the profile.
"""),
code(r"""
def word_grid(strings, n=8):
    # Every (word b, step s) whose windows cover all n bits; the recursive remainder for a
    # non-overlapping word that does not divide n. Returns {(b, s): (kwargs, scores)}.
    out = {}
    for b in range(1, n + 1):
        for s in range(b, 0, -1):
            if (n - b) % s == 0:
                kw = dict(block=b) if s == b else dict(block=b, shift=s)
            elif s == b:
                kw = dict(block=b, remainder="recursive")
            else:
                continue
            out[b, s] = (kw, np.array([bdm_1d(x, **kw) for x in strings]))
    return out

G = word_grid(SHIFT)
spread = {k: float(np.ptp(v)) for k, (kw, v) in G.items()}
H_case = [8 * shannon_bits_per_symbol(s) for s in SHIFT]
print(f"Shannon total over the 8 cases: {H_case[0]:.3f} bits each, spread {np.ptp(H_case):.3f}")
print(f"settings scored: {len(G)} of {sum(range(1, 9))} (b, s) pairs; the rest would leave bits unscored")

M = np.full((8, 8), np.nan)
for (b, s), v in spread.items():
    M[b - 1, b - s] = v
fig, ax = plt.subplots(figsize=(8.5, 5.4))
im = ax.imshow(M, cmap="magma_r", origin="lower", aspect="auto")
for (b, s), v in spread.items():
    tag = "r" if G[b, s][0].get("remainder") == "recursive" else ""
    ax.text(b - s, b - 1, f"{v:.2f}{tag}", ha="center", va="center", fontsize=8,
            color="white" if v > 0.6 * np.nanmax(M) else "black")
ax.set(xticks=range(8), yticks=range(8), yticklabels=range(1, 9),
       xlabel="overlap between consecutive windows, b - s (bits)", ylabel="word length b (bits)",
       title="spread of BDM over the 8 shifted cases (bits); Shannon spread = 0\n"
             "blank = setting would leave bits unscored; r = recursive remainder")
ax.grid(False); plt.colorbar(im, ax=ax, label="max - min over a_0..a_7 (bits)")
plt.tight_layout(); plt.show()

assert all(np.allclose(G[8, s][1], [ctm_1d(x) for x in SHIFT]) for s in range(1, 9))
flat = sorted(k for k, v in spread.items() if v < 1e-9)
print("exactly flat (Shannon-like) settings (b, s):", flat)
print("largest spread:", max(spread, key=spread.get), f"{max(spread.values()):.2f} bits")
assert flat == [(1, 1), (2, 2)] and spread[4, 4] < 0.1 and spread[8, 8] < 1
assert max(spread.values()) > 20 * spread[8, 8]      # overlap hills dwarf the section-2 hills
assert abs(ctm_1d("01") - ctm_1d("10")) < 1e-12        # why word 2 cannot see the position
"""),
code(r"""
x = np.arange(8); lab = [f"z@{i}" for i in range(8)]
panels = [
    ("no overlap (s = b)", [(1, 1), (2, 2), (4, 4), (8, 8)]),
    ("word 4: overlap grows", [(4, 4), (4, 2), (4, 1)]),
    ("step 1: word grows", [(2, 1), (4, 1), (6, 1), (7, 1), (8, 1)]),
]
fig, ax = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
for j, (title, keys) in enumerate(panels):
    cols = plt.cm.viridis(np.linspace(0, .85, len(keys)))
    for (b, s), c in zip(keys, cols):
        v = G[b, s][1]
        lbl = f"b={b}, s={s} (overlap {b - s})" + (" = section 2" if b == 8 else "")
        ax[0, j].plot(x, v, "o-", color=c, label=lbl)
        ax[1, j].plot(x, v - v.mean(), "o-", color=c, label=lbl)
    ax[0, j].plot(x, H_case, "s--", color=OK, label="Shannon total, 8 H (bits)")
    ax[1, j].axhline(0, color=OK, lw=2, ls="--", label="Shannon, centred")
    ax[0, j].set(title=title, ylabel="bits"); ax[1, j].set(ylabel="bits minus own mean")
    ax[0, j].legend(fontsize=7)
for a in ax[1]: a.set_xticks(x); a.set_xticklabels(lab, fontsize=8)
fig.suptitle("top: raw values; bottom: each profile centred on its own mean (the common coordinate)")
plt.tight_layout(); plt.show()
"""),
md(r"""
**Reading the grid.**

* **Word 8 is section 2, whatever the overlap.** The whole top row has the spread of the CTM
  plot itself, because every step gives the same single window. Setting "no overlap and
  word 8" therefore reproduces the hills exactly; it does not flatten them. The asserted line
  above checks this for all eight steps.
* **Shannon-like flatness comes from short words, not from removing overlap.** With word 1
  or word 2 and no overlap the profile is exactly flat. At word 1 BDM sees only how many 0s
  and 1s there are, which is what Shannon sees. At word 2 the zero lands in `01` or `10`, and
  the $D(5)$ table gives those two strings the same value (reversal symmetry), so position is
  invisible again. Word 4 without overlap is almost flat for the same reason.
* **Overlap makes hills; it does not remove them.** Along most rows, moving right (more
  overlap) widens the spread (row 5 is the exception between overlaps 0 and 2), and with
  step 1 and a mid-sized word the spread is more than twenty times the CTM spread of
  section 2 (asserted). These hills have a different origin from the section-2
  hills; the next cell shows it.
"""),
code(r"""
# Mechanism: with step 1, how many windows contain the zero, and how many are all ones?
def anatomy(s, **kw):
    rows = bdm_1d_trace(s, **kw)["rows"]
    z = [r for r in rows if "0" in r["block"]]
    ones = [r for r in rows if "0" not in r["block"]]
    return len(rows), len(z), len({r["block"] for r in z}), len(ones), rows[-1]["running"]

for b in (4, 6):
    print(f"word {b}, step 1")
    print(f"{'case':>5} {'windows':>7} {'with zero':>9} {'distinct':>8} {'all ones':>8} {'BDM':>7}")
    for i, s in enumerate(SHIFT):
        w, nz, dz, no, v = anatomy(s, block=b, shift=1)
        assert dz == nz            # every window holding the zero is a different string
        print(f"{'z@' + str(i):>5} {w:>7} {nz:>9} {dz:>8} {no:>8} {v:>7.2f}")
    print()

# Render the walk: each window as a bar at its true position, coloured by first sighting / repeat.
fig, ax = plt.subplots(2, 3, figsize=(15, 5.6))
for row, i in enumerate((0, 3)):
    for col, kw in enumerate((dict(block=4), dict(block=4, shift=2), dict(block=4, shift=1))):
        a = ax[row, col]; s = SHIFT[i]; t = bdm_1d_trace(s, **kw)
        for j, ch in enumerate(s):
            a.add_patch(plt.Rectangle((j, 0), 1, 1, color="black" if ch == "1" else "white", ec="0.5"))
        for r in t["rows"]:
            y = -1.2 - 1.1 * r["step"]
            first = r["occurrence"] == 1
            a.add_patch(plt.Rectangle((r["start"], y), r["length"], .9, alpha=.85,
                                      color=HL if "0" in r["block"] else INK, fill=first,
                                      hatch=None if first else "//", lw=1.5))
            a.text(r["start"] + r["length"] + .15, y + .45,
                   f"{r['block']}  +{r['added']:.2f}", va="center", fontsize=7, family="monospace")
        a.set(xlim=(0, 13), ylim=(-1.4 - 1.1 * len(t["rows"]), 1.2), yticks=[],
              title=f"a_{i}, word 4, step {kw.get('shift', 4)}: BDM = {t['rows'][-1]['running']:.2f}")
        a.set_xticks(range(9)); a.grid(False)
fig.suptitle("the input (top row of cells) and every window BDM scores; red = holds the zero, "
             "filled = first sighting (adds CTM), hatched = repeat (adds a log2 increment)", fontsize=10)
plt.tight_layout(); plt.show()
"""),
md(r"""
**Mechanism of the overlap hills.** With step 1, a zero at the edge of the case is inside
one window only; a zero in the interior is inside up to $b$ windows, and each of those
windows is a *different* string, because the zero sits at a different offset in each. Every
new string pays its full CTM. The windows that miss the zero are all `1…1` and, after the
first, pay only a $\log_2$ increment. So the sliding profile is, to first order, the number
of windows that hold the zero, a tent that rises from the edges, multiplied by the CTM of
one window (about 8 bits for word 4, printed in the trace above). It is a count of **how many times the walk re-reads the same zero
in a new frame**, not a finer judgement of complexity.

The section-2 hills are a different object: one lookup per case, and the shape is that of the
$D(5)$ table, smaller (under one bit of spread) and mirror-symmetric by construction.
"""),
code(r"""
# The walk through a full input: A64 (eight cases joined) under several settings.
print("A64, word 8, no overlap: the walk lands exactly on your eight cases")
print_trace(A64, block=8); print()
print("A64, word 8, step 4 (overlap 4): windows straddle two cases")
print_trace(A64, block=8, shift=4); print()
print("A72, word 9, no overlap: one string, read eight times")
print_trace(A72, block=9); print()
print("A64, word 8, step 1 (overlap 7): every offset; all windows printed")
t_a64_1 = print_trace(A64, block=8, shift=1)
"""),
md(r"""
**What the walks show.** Word 8 without overlap lands exactly on your eight cases, so
BDM$_8$(A64) is the sum of the eight section-2 values. With step 4 each window straddles two
cases, and from window 9 onwards every string has been seen before: each repeat adds 1 bit
($\log_2 2$), not its CTM. With step 1 the walk visits all 57 offsets but finds only **nine**
distinct strings, because A64 has period 9 (section 1): the walk itself exposes the period,
and after the first nine windows the running total only creeps up by $\log_2$ increments.
A72 under word 9 is the extreme: one string, read eight times.
"""),
code(r"""
_t = bdm_1d_trace(A64, block=8, shift=1)["rows"]
assert len(_t) == 57 and len({r["block"] for r in _t}) == 9
assert all(r["occurrence"] > 1 for r in _t[9:])
# Running BDM along the walk: x = last bit read so far, y = BDM of everything read.
settings = [("A64", A64, dict(block=8)), ("A64", A64, dict(block=8, shift=4)),
            ("A64", A64, dict(block=8, shift=1)), ("A64", A64, dict(block=4)),
            ("A64", A64, dict(block=4, shift=1)), ("A72", A72, dict(block=9))]
fig, ax = plt.subplots(1, 2, figsize=(15, 4.6))
cols = plt.cm.tab10(np.arange(len(settings)))
for (name, s, kw), c in zip(settings, cols):
    rows = bdm_1d_trace(s, **kw)["rows"]
    end = np.array([r["start"] + r["length"] for r in rows])
    run = np.array([r["running"] for r in rows])
    new = np.array([r["occurrence"] == 1 for r in rows])
    lbl = f"{name}, b={kw['block']}, s={kw.get('shift', kw['block'])}: {len(rows)} windows, {new.sum()} distinct"
    for a in ax:
        a.plot(end, run, "-", color=c, lw=1.2, label=lbl)
        a.plot(end[new], run[new], "o", color=c, ms=4)
        a.plot(end[~new], run[~new], "o", mfc="white", color=c, ms=4)
ax[0].set(xlabel="last bit read", ylabel="running BDM (bits)", title="full scale")
ax[1].set(xlabel="last bit read", ylabel="running BDM (bits)", yscale="log",
          title="log scale: jumps = new string (adds its CTM), flat steps = repeats (log2 increments)")
ax[0].legend(fontsize=7); plt.tight_layout(); plt.show()
"""),
code(r"""
# Beyond the shifted family: all 256 eight-bit words. How closely does each setting
# rank words the way Shannon does? Spearman is rank-based, so the units never meet.
from scipy.stats import spearmanr
WORDS = [format(w, "08b") for w in range(256)]
H_words = np.array([8 * shannon_bits_per_symbol(w) for w in WORDS])
GW = word_grid(WORDS)
rho = {k: spearmanr(v, H_words).correlation for k, (kw, v) in GW.items()}
R = np.full((8, 8), np.nan)
for (b, s), r in rho.items():
    R[b - 1, b - s] = r
fig = plt.figure(figsize=(15, 5))
a0 = fig.add_subplot(1, 4, (1, 2))
im = a0.imshow(R, cmap="viridis", origin="lower", aspect="auto", vmin=min(rho.values()), vmax=1)
for (b, s), r in rho.items():
    a0.text(b - s, b - 1, f"{r:.2f}", ha="center", va="center", fontsize=8,
            color="black" if r > .6 else "white")
a0.set(xticks=range(8), yticks=range(8), yticklabels=range(1, 9), xlabel="overlap b - s",
       ylabel="word length b", title="Spearman(BDM, Shannon) over all 256 eight-bit words")
a0.grid(False); plt.colorbar(im, ax=a0)
for a, (b, s) in zip((fig.add_subplot(1, 4, 3), fig.add_subplot(1, 4, 4)), ((1, 1), (8, 8))):
    a.scatter(H_words, GW[b, s][1], s=12, color=INK, alpha=.6)
    a.set(xlabel="Shannon total 8 H (bits)", ylabel="BDM (bits)",
          title=f"b={b}, s={s}: rho = {rho[b, s]:.2f}")
plt.tight_layout(); plt.show()
print(f"word 1 (rho = {rho[1, 1]:.3f}) to word 8 (rho = {rho[8, 8]:.3f}); "
      f"minimum over the grid {min(rho.values()):.3f} at {min(rho, key=rho.get)}")
others = [r for k, r in rho.items() if k != (1, 1)]
print(f"every other setting: rho between {min(others):.2f} and {max(others):.2f}")
# Word 1 sees only the counts: words with the same number of ones get the same BDM.
v1 = GW[1, 1][1]
assert all(np.ptp([v1[j] for j, w in enumerate(WORDS) if w.count("1") == c]) < 1e-12 for c in range(9))
assert abs(rho[1, 1] - 1) < 1e-12 and max(others) < 0.7
"""),
md(r"""
**Verdict on the hypothesis.**

* *"No overlap, word 8, gives Shannon."* **Not supported.** For an 8-bit case that setting is
  the section-2 computation itself: one window, one table lookup, the same hills. The trace
  and the top row of the grid show it.
* *"The hills come from the linear walk and its overlaps."* **Not for section 2**, where
  there is no walk. **Yes for a different set of hills**: once the word is shorter than the
  input and windows overlap, BDM re-reads the zero in several frames and charges full CTM for
  each, which builds a large tent-shaped profile. That is an artefact of the partition, and
  it is larger than anything the table itself distinguishes.
* *What does approach Shannon.* **Word 1, and only word 1.** At word 1 BDM is a function of
  the 0/1 counts alone, which is the information Shannon uses, and over all 256 eight-bit
  words it ranks them exactly as Shannon does (asserted). Word 2 is flat on the shifted family
  only through a symmetry of the table (`01` and `10` have equal CTM); over all 256 words its
  ranking is far from Shannon's. Every setting other than word 1 has a rank correlation with
  Shannon well below one (printed range), with no monotone trend in word length or overlap.
  So the word length is the knob that moves BDM from a frequency count (word 1) to a table
  lookup of the whole string (word 8); overlap mainly multiplies how often the same local
  feature is paid for.

These are statements about pybdm's $D(5)$ table and partitions on 8-bit inputs, not about
$K$. Nothing here bears on the argument of §3–§8, which concerns composition of blocks.
"""),

md(r"""
## 3 · One program for every case — and what it costs in bits

Your indexed generator (`shift_zero_concat`) makes any case from an index. Below are four
Python expressions for **A64**, each checked by running it, measured three ways:

* **characters** of the expression (one language, Python source);
* **UTF-8 payload bits** of those characters, before any framing — what the text would
  occupy as a stored file;
* for comparison, the **actual decodable archives** of the HID-v1 format
  (`index-deconvolution/hierarchy`): the packed literal archive of A64, and the archive the
  bounded HID search finds for it. Archive bits include the 4-byte magic, codec byte, length
  fields and padding.
"""),
code(r"""
PROGS_A64 = {
    "literal (print the string)":  repr(A64),
    "your eight one-offs, joined":  " + ".join(USER_PROGS[s] for s in SHIFT),
    "indexed shift (your idea)":   "''.join('1'*i+'0'+'1'*(7-i) for i in range(8))",
    "period 9 (the render's idea)": "('0'+'1'*8)*7+'0'",
}
print(f"{'expression for A64':<30} {'chars':>5} {'UTF-8 bits':>10}")
for name, src in PROGS_A64.items():
    n = program_length(src, A64)
    print(f"{name:<30} {n:>5} {8 * len(src.encode('utf-8')):>10}   {src[:48]}{'...' if len(src) > 48 else ''}")
lit = encode_literal(A64)
hid = infer(A64)
assert decode_archive(hid.archive) == A64
print()
print(f"A64 itself                          : {len(A64)} bits")
print(f"packed literal archive (raw mode)   : {8 * len(lit)} bits  (64 data bits + 56 bits of envelope)")
print(f"HID-v1 search result                : {hid.archive_bits} bits, mode={hid.mode}")
p9 = "('0'+'1'*8)*7+'0'"
assert program_length(p9, A64) == 17 and 8 * len(p9.encode("utf-8")) == 136
p72 = "('1'*8+'0')*8"
print(f"\nA72 is generated by {p72!r}: {program_length(p72, A72)} characters "
      f"({8 * len(p72.encode('utf-8'))} UTF-8 bits); the 17-character expression outputs A64, not A72.")
"""),
md(r"""
**Reading (corrected).** The ranking of the four expressions is meaningful *within Python
source*: the joined one-offs inherit every case's private cost, the indexed generator
replaces eight programs with one, and the period-9 expression is shortest because it does
not shift anything, it repeats.

What the first version implied, and what does **not** follow: the 17-character period
expression occupies **136 UTF-8 payload bits** before any framing. That is shorter than the
*textual Python literal* of A64, but longer than the 64 bits of A64 itself. Characters of a
general-purpose language are not a compressed binary code, so these counts are not
bit-valued bounds on $K$ to be set against BDM bits.

A specified binary format changes the question. The HID-v1 archive above includes its whole
envelope; at 64 bits the envelope dominates and the search returns the literal mode, which is
the expected behaviour of a fixed format on a tiny input, not a failure. Whether such a
format is economical on *unseen* sequences is the subject of notebook 16 and its frozen
benchmark, not of this probe.

The generator is constant-sized only over this finite range of single-digit parameters. For
growing inputs the honest statement is $K(f(n,k)) \le K(n,k) + c_f$: the parameters, counts
and lengths must themselves be encoded.
"""),

md(r"""
## 4 · The sum of the parts against the whole, at every block size

BDM cuts the string into blocks, looks each distinct block up in the CTM table, and adds
$\log_2(\text{multiplicity})$ for repeats:
$\mathrm{BDM}(s) = \sum_{\text{distinct } b} \big[\mathrm{CTM}(b) + \log_2 n_b\big]$.

* With blocks of 8 aligned to your cases, every block of A64 is distinct, so
  $\mathrm{BDM}_8(\mathrm{A64}) = \sum_i \mathrm{CTM}(a_i)$ **exactly**.
* The informative experiment is to change the block length. The first version did this with
  pybdm's tail-dropping partition. **That scan is kept below as a historical diagnostic,
  with its coverage printed**, because a dropped tail changes the object being scored. Beside
  it are two full-coverage scans in which every bit is scored: the aligned **recursive**
  boundary (the remainder is scored as a shorter block) and **sliding** blocks with step 1.
"""),
code(r"""
sum_parts = sum(ctm_1d(s) for s in SHIFT)
print(f"sum of CTM(a_i), i=0..7        = {sum_parts:.3f} bits")
print(f"BDM_8(A64) (aligned, whole)    = {bdm_1d(A64, block=8):.3f} bits   <- identical, by definition")
_r = random.Random(72)
R72 = "".join(_r.choice("01") for _ in range(72))   # control: a random 72-bit string, seed pinned
print("control R72 =", R72)
rows = []
for b in range(1, 13):
    for name, s in (("A64", A64), ("A72", A72), ("R72", R72)):
        drop, cov, dropped = coverage(s, b, remainder="drop")
        rec = bdm_1d(s, block=b, remainder="recursive")
        slide = bdm_1d(s, block=b, shift=1)
        rows.append(dict(name=name, b=b, drop=drop, covered=cov, dropped=dropped, recursive=rec, sliding=slide))
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
for a, key, title in zip(ax, ("drop", "recursive", "sliding"),
                         ("HISTORICAL: tail dropped (coverage varies)", "full coverage: aligned recursive",
                          "full coverage: sliding, step 1")):
    for name, col in (("A64", INK), ("A72", HL), ("R72", "0.6")):
        bs = [r["b"] for r in rows if r["name"] == name and r["b"] >= 2]
        a.plot(bs, [r[key] for r in rows if r["name"] == name and r["b"] >= 2], "o-", color=col, label=name)
    a.axvline(9, color=OK, ls="--", lw=1); a.set(title=title, xlabel="block length", ylabel="BDM (bits)")
    a.legend(fontsize=8)
plt.tight_layout(); plt.show()
ctl = {(r["b"]): r for r in rows if r["name"] == "R72"}
print(f"{'b':>3} | {'A72 drop':>8} {'scored':>6} {'dropped':>7} {'/R72':>5} | {'A72 recursive':>13} {'/R72':>5} | {'A72 sliding':>11} {'/R72':>5}")
for r in rows:
    if r["name"] == "A72" and r["b"] >= 2:
        c = ctl[r["b"]]
        print(f"{r['b']:>3} | {r['drop']:>8.2f} {r['covered']:>6} {r['dropped']:>7} {r['drop'] / c['drop']:>5.2f} | "
              f"{r['recursive']:>13.2f} {r['recursive'] / c['recursive']:>5.2f} | {r['sliding']:>11.2f} {r['sliding'] / c['sliding']:>5.2f}")
a72 = {r["b"]: r for r in rows if r["name"] == "A72"}
argmin_2_12 = min(range(2, 13), key=lambda b: a72[b]["drop"])
argmin_1_12 = min(range(1, 13), key=lambda b: a72[b]["drop"])
print(f"\nraw minimum of BDM_b(A72) over b = 2..12 selects b = {argmin_2_12} (score {a72[argmin_2_12]['drop']:.3f}); "
      f"over 1..12 it selects b = {argmin_1_12} (score {a72[argmin_1_12]['drop']:.3f})")
print("A72 coverage at b = 3, 9, 1:", [a72[b]["dropped"] for b in (3, 9, 1)], "bits dropped")
assert argmin_2_12 == 3 and argmin_1_12 == 1 and all(a72[b]["dropped"] == 0 for b in (1, 3, 9))
"""),
md(r"""
**Reading (corrected).** One string gets many values, and the spread is large: block 8 and
block 9 differ by about a factor of seven on A72 in the historical scan. At block 9 one block
is repeated eight times; at block 12, $\mathrm{lcm}(9,12)=36$, so every block occurs twice;
at block 8, $\mathrm{lcm}(9,8)=72$ and no block repeats, so A72 — which the 14-character
expression `('1'*8+'0')*8` generates — scores close to the random control. *(The first
version attributed this to the 17-character program; that program outputs A64, not A72.)*

**A raw minimum over block length does not find the period.** The printed scan shows it: over
$b = 2..12$ the minimum is at $b = 3$, not 9, and allowing $b = 1$ selects 1. All three
partitions cover every bit of A72, so this is not a tail artefact. Changing $b$ changes the
dictionary and how much ordering information is omitted, so the raw minimum does not compare
complete descriptions. Selecting a model needs complete code lengths; using BDM as a
discriminator needs calibration against matched controls with the whole selection rerun on
every control (notebook 16 does this).

**What BDM credits, stated precisely (narrowed).** The first version said repetition is "the
one regularity BDM rewards". That is too broad: CTM scores local structure inside each block
(§2). The defensible criticism is narrower: aligned BDM aggregates blocks as a **multiset**,
so relationships and order *between* blocks are not represented, and identical repetition is
credited only where the partition creates it. Known alternatives — overlapping (sliding)
blocks and recursive boundaries, shown in the right two panels — change the numbers; they
are discussed by the original BDM paper (Zenil et al., *Entropy* 20:605, 2018), so this probe
illustrates that discussion rather than discovering it.
"""),

md(r"""
## 5 · More zeros: from `11111111` to `00000000`

Two ways to generalise "one zero, shifted":

* **sliding run**: a run of $k$ zeros sliding through 8 positions, $1^{i}0^{k}1^{8-k-i}$,
  giving $9-k$ cases;
* **every placement**: all 8-bit strings with exactly $k$ zeros, giving $\binom{8}{k}$
  cases, concatenated in lexicographic order.
"""),
code(r"""
def fam_run(k):  return ["1" * i + "0" * k + "1" * (8 - k - i) for i in range(9 - k)] if k else [ONES]
def fam_comb(k): return ["".join("0" if j in c else "1" for j in range(8)) for c in itertools.combinations(range(8), k)]
GEN = {
    "run":  "''.join('1'*i+'0'*{k}+'1'*(8-{k}-i) for i in range(9-{k}))" ,
    "comb": "''.join(''.join('0'if j in c else'1'for j in range(8))for c in itertools.combinations(range(8),{k}))",
}
res = {}
for fam_name, fam in (("run", fam_run), ("comb", fam_comb)):
    for k in range(9):
        blocks = fam(k); s = "".join(blocks)
        gen = GEN[fam_name].format(k=k) if (fam_name == "comb" or k) else repr(ONES)
        res[fam_name, k] = dict(n=len(blocks), bits=len(s), bdm8=bdm_1d(s, block=8),
                                mean_ctm=np.mean([ctm_1d(b) for b in blocks]),
                                gen=program_length(gen, s), lit=program_length(repr(s), s))
print(f"{'fam':>4} {'k':>2} {'cases':>5} {'bits':>5} {'BDM_8':>8} {'mean CTM':>8} {'gen chars':>9} {'literal':>7}")
for (f, k), r in res.items():
    print(f"{f:>4} {k:>2} {r['n']:>5} {r['bits']:>5} {r['bdm8']:>8.1f} {r['mean_ctm']:>8.2f} {r['gen']:>9} {r['lit']:>7}")
"""),
code(r"""
fig, ax = plt.subplots(1, 3, figsize=(14, 4))
for f, col in (("run", INK), ("comb", HL)):
    ks = range(9)
    ax[0].plot(ks, [res[f, k]["bdm8"] for k in ks], "o-", color=col, label=f)
    ax[1].plot(ks, [res[f, k]["gen"] for k in ks], "o-", color=col, label=f"{f}: one generator")
    ax[1].plot(ks, [res[f, k]["lit"] for k in ks], "s:", color=col, alpha=.5, label=f"{f}: literal")
    ax[2].plot([res[f, k]["n"] for k in ks], [res[f, k]["bdm8"] for k in ks], "o", color=col, label=f)
ax[0].set(title="BDM_8 of the concatenation", xlabel="k zeros", ylabel="bits")
ax[1].set(title="program length (chars)", xlabel="k zeros", yscale="log")
ax[2].set(title="BDM_8 against number of cases (18 constructed points)", xlabel="cases concatenated", ylabel="bits")
for a in ax: a.legend(fontsize=8)
plt.tight_layout(); plt.show()
n = np.array([res[f, k]["n"] for f in ("run", "comb") for k in range(9)])
v = np.array([res[f, k]["bdm8"] for f in ("run", "comb") for k in range(9)])
slope = np.polyfit(n, v, 1)[0]
print(f"least-squares slope over these 18 constructed points: {slope:.2f} bits per added case")
print("comb family symmetric in k <-> 8-k:",
      all(abs(res['comb', k]['bdm8'] - res['comb', 8 - k]['bdm8']) < 1e-9 for k in range(9)))
C8 = sum(ctm_1d(format(w, "08b")) for w in range(256))
for m in (10, 100, 10**4, 10**6):
    print(f"bound on BDM_8 for m = {m:>7} complete blocks: C_8 + 256*log2(m) = {C8 + 256 * math.log2(m):10.1f} bits "
          f"(a literal of the same string has {8 * m} bits)")
"""),
md(r"""
**Reading (corrected).**

* **On these constructed families, BDM_8 tracks the number of distinct cases.** Each new
  distinct 8-bit block adds its CTM. The printed slope summarises 18 constructed points with
  distinct blocks; they are not 18 independent observations of a scaling law, and there are
  only 256 distinct 8-bit words.
* **The finite slope is not an asymptotic law.** For a fixed block size $b$ and a finite CTM
  table, with $m$ complete blocks, $\mathrm{BDM}_b(x) \le C_b + 2^b \log_2 m$, where $C_b$
  is the sum of the table's CTM values: each multiplicity is at most $m$ and there are at
  most $2^b$ distinct words. Fixed-$b$ BDM therefore grows at most **logarithmically** in
  length, on fair random strings too. The last printed lines evaluate this bound; the first
  version's "BDM is linear in the number of cases" holds only in the finite constructed
  range.
* **The generator is constant only over a finite parameter range.** The $k=0$ sliding case
  is a different (literal) program, and for growing inputs the parameters themselves must be
  encoded, as in §3.
* For small families the literal is shorter than the generator: listing five cases or
  fewer is cheaper than describing the rule. That is the expected crossover.
* **Symmetry, and where it holds.** The *every placement* family is exactly symmetric in
  $k \leftrightarrow 8-k$ by complement invariance of the table. The *sliding run* family is
  not: its complement partner is a run of *ones* sliding through zeros.
"""),

md(r"""
## 6 · The same blocks in random order

Shuffle the nine cases of A72 and concatenate them. On the Kolmogorov side an arbitrary order
must be *specified*: a multiset of $m$ blocks with counts $n_j$ has $m!/\prod_j n_j!$
orderings, and an arbitrary one can be sent as a rank in that class — at most
$\lceil\log_2 9!\rceil$ bits for nine distinct cases — while a simple order may cost much
less. We draw 2000 shuffles (seed pinned) and score each at blocks 8, 9 and 12. Block 8 and 9
tile A72 exactly, so nothing is dropped there; at block 12 the historical drop policy is
used and its coverage printed.
"""),
code(r"""
rng = random.Random(15)
blocks9 = [ONES] + SHIFT
ordered = "".join(blocks9)
assert ordered == A72
shuffles = []
for _ in range(2000):
    p = blocks9[:]; rng.shuffle(p); shuffles.append("".join(p))
fig, ax = plt.subplots(1, 3, figsize=(14, 3.6))
for a, b in zip(ax, (8, 9, 12)):
    vals = np.array([bdm_1d(s, block=b, remainder="drop") for s in shuffles])
    o, cov, dropped = coverage(ordered, b, remainder="drop")
    a.hist(vals, bins=40 if np.ptp(vals) > 1e-6 else 1, color=INK, alpha=.7); a.axvline(o, color=HL, lw=2, label=f"ordered {o:.1f}")
    a.set(title=f"block {b}: 2000 shuffles ({dropped} bits dropped)", xlabel="BDM (bits)"); a.legend(fontsize=8)
    print(f"block {b:>2}: ordered {o:7.2f} | shuffles min {vals.min():7.2f} median {np.median(vals):7.2f} "
          f"max {vals.max():7.2f} | share of shuffles <= ordered {np.mean(vals <= o + 1e-9):.4f} | dropped {dropped}")
plt.tight_layout(); plt.show()
print(f"log2(9!) = {math.log2(math.factorial(9)):.2f} bits")
print(f"block-entropy foil, block 8: ordered {block_entropy(ordered, 8):.3f}, every shuffle {block_entropy(shuffles[0], 8):.3f}")
"""),
md(r"""
**Reading.**

* **Block 8 (aligned to the cases): order does not register at all.** All 2000 shuffles get
  *exactly* the ordered value. Aligned BDM is a function of the multiset of blocks, and in
  this respect it is the same as the block-entropy foil.
* **Blocks 9 and 12: the ordered string is among the lowest.** Once the partition cuts
  *across* the cases, the ordered string's repetition becomes repeated blocks; shuffling
  breaks it and BDM rises. This is the correct direction, but it is bought by the choice of
  block length, as in §4.

The order information reaches aligned BDM only through **coincidences between the partition
and the generator**.
"""),

md(r"""
## 7 · Rotation: move the last bit to the front

A *specified* one-position rotation changes $K$ by at most a fixed program constant. An
**arbitrary** rotation must also transmit its amount: at most $\lceil\log_2 n\rceil + O(1)$
bits when $n$ is available from the decoded object, and the implementation constant cannot
simply be dropped. We do your experiment on A64 and A72, sweep every rotation amount, and
repeat it for one shuffled string as a control.
"""),
code(r"""
rot = lambda s, r: s[-r:] + s[:-r] if r else s
for name, s in (("A64", A64), ("A72", A72)):
    r1 = rot(s, 1)
    print(f"{name}: rotated by 1 -> blocks of 8: {[r1[i:i+8] for i in range(0, len(r1), 8)]}")
    print(f"      BDM_8 before {bdm_1d(s, block=8):.3f}   after {bdm_1d(r1, block=8):.3f}")
shuf = shuffles[0]
fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
for a, b in zip(ax, (8, 12)):
    for name, s, col in (("A72 ordered", A72, HL), ("A64", A64, INK), ("A72 shuffled", shuf, BAD)):
        vals = [bdm_1d(rot(s, r), block=b, remainder="drop") for r in range(len(s))]
        a.plot(vals, color=col, label=f"{name}: range {min(vals):.1f}-{max(vals):.1f}")
        print(f"BDM_{b:<2} {name:<13} over {len(s)} rotations: min {min(vals):7.2f} max {max(vals):7.2f} "
              f"spread {max(vals) - min(vals):6.2f} bits (dropped tail: {len(s) % b} bits)")
    a.set(title=f"BDM_{b} under every rotation", xlabel="rotation amount r", ylabel="bits")
    a.legend(fontsize=8)
plt.tight_layout(); plt.show()
print("an arbitrary rotation index for n = 64 costs at most ceil(log2 64) =", math.ceil(math.log2(64)), "bits + O(1)")
"""),
md(r"""
**Reading.**

* **A72: every rotation leaves BDM_8 unchanged.** This is not robustness: a rotation of a
  period-9 string is again period-9, and its 8-blocks are the same multiset.
* **A64: rotation by one is not invisible, but it is small at block 8**, and much larger at
  block 12, where 64 is not a multiple of 12 and the historical scan drops a tail.
* **The shuffled control** spreads widely at block 8: without the period, every shift of the
  seams lands on new blocks.

For $K$, the rotated strings differ from the original by a rotation index, at most
$\lceil\log_2 n\rceil$ bits plus a constant.
"""),

md(r"""
## 8 · Patterns of patterns: A24, AX64, AXM64, P1, P2, P3

These are the page-19 constructions, previously only in a scratch appendix of bitacora 32
(where "A" meant A24, a different object from A64). Cases follow `shift_zero_concat`: case 1
is all ones and case $j+1$ has its zero at position $j$. P1 = A24·A24, P2 = A24·AX64·AXM64,
P3 = AXM64·AXM64·AXM64. For each block length the table prints the full length, the bits
scored and dropped by the **historical drop policy**, the block count and distinct blocks,
the repeated blocks, and the full-coverage recursive score.
"""),
code(r"""
CASES = [ONES] + SHIFT
cat = lambda idx: "".join(CASES[j - 1] for j in idx)
A24, AX64, AXM64 = cat([1, 2, 3]), cat(range(1, 9)), cat([8, 1, 6, 7, 2, 4, 3, 5])
assert AX64 == A72[:64] and AX64 != A64
PATTERNS = {"A24": A24, "AX64": AX64, "AXM64": AXM64, "P1": A24 * 2, "P2": A24 + AX64 + AXM64, "P3": AXM64 * 3}
pp = {}
print(f"{'object':<6} {'len':>4} {'b':>3} {'drop BDM':>9} {'scored':>6} {'dropped':>7} {'blocks':>6} {'distinct':>8} "
      f"{'recursive BDM':>13}  repeated blocks (multiplicity)")
for name, s in PATTERNS.items():
    for b in (8, 9, 12):
        drop, cov, dropped = coverage(s, b, remainder="drop")
        blocks = [s[i:i + b] for i in range(0, cov, b)]
        cnt = collections.Counter(blocks)
        rep = {k: v for k, v in sorted(cnt.items()) if v > 1}
        rec = bdm_1d(s, block=b, remainder="recursive")
        pp[name, b] = dict(drop=drop, cov=cov, dropped=dropped, blocks=len(blocks), distinct=len(cnt), rec=rec)
        print(f"{name:<6} {len(s):>4} {b:>3} {drop:>9.1f} {cov:>6} {dropped:>7} {len(blocks):>6} {len(cnt):>8} {rec:>13.1f}  "
              + (", ".join(f"{k}x{v}" for k, v in rep.items()) or "-"))
assert pp["P3", 12]["blocks"] == 16 and pp["P3", 12]["distinct"] == 15
assert pp["A24", 9]["dropped"] == 6 and pp["AX64", 12]["dropped"] == 4 and pp["AXM64", 12]["dropped"] == 4
assert pp["P2", 12]["dropped"] == 8 and pp["P3", 12]["dropped"] == 0
assert abs(pp["AX64", 8]["drop"] - pp["AXM64", 8]["drop"]) < 1e-9
for name in ("AX64", "AXM64"):
    r = infer(PATTERNS[name]); assert decode_archive(r.archive) == PATTERNS[name]
    print(f"HID-v1 archive for {name}: {r.archive_bits} bits (literal archive {r.literal_bits} bits), "
          f"archive bytes differ: order is transmitted")
"""),
md(r"""
**Reading (corrected).**

* **Coverage differs between rows of the historical scan.** A24 at block 9 scores 18 of 24
  bits (25 % dropped); AX64 and AXM64 at block 12 score 60 of 64; P2 at block 12 scores 144
  of 152; P3 at block 12 scores all 192. The first version's P3/AXM ratio at block 12 therefore
  mixed a partition effect with different coverage. The recursive column scores every bit.
* **P3 at block 12 has 16 blocks and 15 distinct ones; one block occurs twice.** The first
  version's statement that no block repeats was false. $\mathrm{lcm}(64, 12) = 192$ explains
  when the alignment recurs, not the absence of accidental repeated contents.
* **BDM_8 cannot tell AX64 from AXM64** (equal scores, asserted above). A decodable archive
  must transmit the order; the two HID archives differ.
* At block 8, P3's three repeats of each block are credited as $\log_2 3$ per distinct block;
  a description that names "three copies of AXM64" pays for the repetition once. This is the
  level argument, now on an executed cell.
"""),

md(r"""
## 9 · The period and the schema are different objects

The zeros of A64 sit at addresses $0, 9, 18, \dots, 63$, which in six-bit binary read
`000000, 001001, …, 111111` — the form `abcabc`. Sumandos are the fillings of a schema's
**own don't-care coordinates** (GLOSSARY §1d). Every ordinary wildcard cube with more than one
point contains two addresses at Hamming distance one. The cell checks that no two zero
addresses are Hamming neighbours, so a cube cover of this zero support **in the original six
coordinates needs eight singleton cubes** — no stars at all, despite the simple period.
"""),
code(r"""
zs = [i for i, c in enumerate(A64) if c == "0"]
print("zero addresses (6-bit):", [f"{z:06b}" for z in zs])
edges = [(x, y) for x in zs for y in zs if x < y and bin(x ^ y).count("1") == 1]
print("Hamming-one pairs among them:", edges)
assert not edges
"""),
md(r"""
**Reading.** "Recover period 9" is therefore not automatically "recover compact sumandos".
This does not make the string incompressible: its complementary support, an arithmetic
progression of step 9, relations between coordinates, or a transformation may all be
economical — but each has to be defined and **charged** in a decodable code. Notebook 16
builds such a code (HID-v1), with arithmetic progressions and schemata as separate,
explicitly transmitted rule types, and tests it on held-out sequences.

## What the probe supports, and what it does not

**Supported, by the cells above:**

1. Per case, CTM makes distinctions Shannon does not (§2); the spread is a property of one
   reference table, not an error interval.
2. BDM's value for a fixed string depends strongly on the block length and the boundary
   policy (§4); its low values occur where the partition matches the period, and a raw
   minimum over block length does not identify the period.
3. Aligned BDM aggregates blocks as a multiset: relationships and order between blocks are
   not represented (§6, §8).
4. Characters of a Python expression are not bits of a binary code (§3).

**Not supported. Do not claim these:**

* "BDM is no better than Shannon", "BDM rewards only repetition", or "BDM is wrong about
  $K$".
* A linear growth law for fixed-$b$ BDM (§5 gives the logarithmic bound).
* Any absolute comparison of CTM bits with program characters.
* That letting the data pick $b$ by raw minimum would find the generator (§4).

The next experiment is not another BDM example: it is a specified, decodable code whose
inference is frozen before it meets new sequences — notebook 16.
"""),
]

write_notebook(cells, os.path.join(HERE, "15_shifted_zero_bdm_probe.ipynb"))
