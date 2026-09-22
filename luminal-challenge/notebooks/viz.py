"""The single owner of every picture the Luminal notebooks draw.

Nothing here computes a compiler result. Every function takes objects that the
solution modules already produced -- bundles from ``direct_contract``, cubes and
fields from ``schema_index``, measured rows from the frozen evidence -- and
draws them. If a figure and a number ever disagree, the fault is in the caller,
not here.

This module exists because a function defined inside a notebook cell has no
importable home: it lives as quoted text in JSON and, once run, only in that
notebook's kernel. ``00-concepts.ipynb`` originally defined ``narrate``,
``show_timeline`` and ``show_lifetimes`` in cells 9, 14 and 20. Notebook 01
needs the same three renders, so they were moved here and both notebooks now
import them. Under the repository's single-owner rule this file is the only
place a notebook figure is defined; a second copy anywhere is a defect, and
``check_single_render_owner.py`` fails on one.

The palette is shared so that the same meaning carries the same colour across
every figure in both notebooks:

* ``FILL`` -- an occupied slot, a live value, a member of a set.
* ``EMPTY`` -- a legal but unused slot.
* ``EDGE`` -- the outline of an occupied region.
* ``EXCLUDED`` -- removed by a constraint: a blocked cycle, a taken address.
* ``CHOSEN`` -- the witness the method actually returned.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# A module must import cleanly regardless of who imports it, so the pinned
# reference goes on the path here rather than relying on a notebook cell having
# run first. This is path setup, not a second copy of any rule: every hardware
# fact below is still read from ``machine``.
ROOT = Path(__file__).resolve().parent.parent
for _entry in (str(ROOT / ".reference"), str(ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import machine  # noqa: E402  -- the frozen machine model, after the path is set

import schema_index as si  # noqa: E402


__all__ = [
    "ENGINES",
    "FILL",
    "EMPTY",
    "EDGE",
    "EXCLUDED",
    "CHOSEN",
    "narrate",
    "show_timeline",
    "show_lifetimes",
    "show_universe",
    "show_cover_blocks",
    "show_index_layout",
    "show_expression_tree",
    "show_search_economy",
    "show_program_results",
]


ENGINES = ["load", "scalar", "vector", "store", "flow"]

FILL = "#cfe3f3"
EMPTY = "#f2f4f7"
EDGE = "#5d8fb3"
EXCLUDED = "#f0d5d5"
CHOSEN = "#a8d5a2"


# --------------------------------------------------------------------------
# Renders shared with 00-concepts
# --------------------------------------------------------------------------


def narrate(program, facts, times, title) -> None:
    """Print a tick-by-tick account of one schedule."""
    span = max(times.values()) + 1          # the schedule is this many cycles long
    print(title)
    print(f"{'cycle':>5}  {'issued':30} {'becomes ready this cycle'}")
    for cycle in range(span):
        issued = [i for i, t in sorted(times.items()) if t == cycle]
        landing = [i for i, t in sorted(times.items())
                   if t + facts.latency[i] == cycle and facts.dest[i]]
        issue_text = ", ".join(
            f"op{i} {facts.opcode[i]}" for i in issued) or "-- nothing (stall) --"
        land_text = ", ".join(f"{facts.dest[i]}" for i in landing) or ""
        print(f"{cycle:>5}  {issue_text:30} {land_text}")
    print()


def show_timeline(bundles, title, figure_width=0.62) -> None:
    """One column per cycle, one row per engine. Blue means occupied."""
    n = len(bundles)
    fig, ax = plt.subplots(figsize=(max(4.0, figure_width * n + 1.6), 2.8))
    for row, engine in enumerate(ENGINES):
        for cycle, bundle in enumerate(bundles):
            ids = bundle.get(engine, [])
            ax.add_patch(Rectangle((cycle, row), 1, 1, linewidth=1,
                                   edgecolor="white",
                                   facecolor=FILL if ids else EMPTY))
            if ids:
                ax.text(cycle + 0.5, row + 0.5, ",".join(str(i) for i in ids),
                        ha="center", va="center", fontsize=9)
    ax.set_xlim(0, n)
    ax.set_ylim(0, len(ENGINES))
    ax.set_xticks([c + 0.5 for c in range(n)], [str(c) for c in range(n)])
    ax.set_yticks([r + 0.5 for r in range(len(ENGINES))],
                  [f"{e} x{machine.ENGINE_LIMITS[e]}" for e in ENGINES])
    ax.set_xlabel("cycle")
    ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()
    plt.show()


def show_lifetimes(facts, addresses, life, span, title) -> None:
    """One row per locker; each bar is a value occupying it while alive."""
    rows = max(addresses.values()) + 1
    fig, ax = plt.subplots(figsize=(max(4.0, 0.62 * span + 1.6), 0.6 * rows + 1.4))
    for name, base in addresses.items():
        start, end = life[name]
        ax.add_patch(Rectangle((start, base + 0.12), end - start + 1, 0.76,
                               facecolor=FILL, edgecolor=EDGE))
        ax.text(start + (end - start + 1) / 2, base + 0.5, name,
                ha="center", va="center", fontsize=8)
    ax.set_xlim(0, span)
    ax.set_ylim(0, rows)
    ax.set_xticks([c + 0.5 for c in range(span)], [str(c) for c in range(span)])
    ax.set_yticks([r + 0.5 for r in range(rows)], [f"word {r}" for r in range(rows)])
    ax.set_xlabel("cycle")
    ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()
    plt.show()


# --------------------------------------------------------------------------
# Renders of the index method itself
# --------------------------------------------------------------------------


def show_execution_trace(
    program: dict,
    compilation: dict,
    states: Sequence[object],
    title: str,
    scratch_words: Optional[int] = None,
) -> None:
    """The whole machine, cycle by cycle: what issued, the scratchpad, the buffers.

    One column per cycle. The top strip names the operations handed over. Below
    it is every scratch word the allocation uses, then every buffer word. A cell
    holds the number stored there at the *end* of that cycle, so reading a row
    left to right is the life of one word.

    Green marks a change made during that cycle -- a value committing to the
    scratchpad, or a store reaching a buffer. Everything else is carried over
    from the cycle before.

    ``states`` comes from ``trace.replay``, which checks itself against
    ``machine.run_compilation`` before returning, so what is drawn here has
    already been agreed with the validator.
    """

    if scratch_words is None:
        scratch_words = machine.scratch_footprint(program, compilation)
    span = len(states)

    buffer_slots: List[Tuple[str, int]] = []
    for name, length in program["buffers"].items():
        for offset in range(length):
            buffer_slots.append((name, offset))

    rows = 1 + scratch_words + len(buffer_slots)
    fig, ax = plt.subplots(figsize=(max(6.0, 0.86 * span + 3.0), 0.42 * rows + 1.8))

    def cell(column, row, text, face, weight="normal"):
        ax.add_patch(Rectangle((column, row), 1, 1, linewidth=1,
                               edgecolor="white", facecolor=face))
        if text:
            ax.text(column + 0.5, row + 0.5, text, ha="center", va="center",
                    fontsize=7, fontweight=weight)

    labels: List[str] = ["issued"]
    for word in range(scratch_words):
        labels.append(f"scratch {word}")
    for name, offset in buffer_slots:
        labels.append(f"{name}[{offset}]")

    for column, state in enumerate(states):
        ids = state.issued_ids
        cell(column, 0, ",".join(f"{i}" for i in ids) if ids else "·",
             FILL if ids else EMPTY, "bold")

        landed_here = {}
        for name, words in state.landed:
            base = compilation["scratch"][name]
            for k, word in enumerate(words):
                landed_here[base + k] = name

        for word in range(scratch_words):
            row = 1 + word
            value = state.scratch[word]
            if word in landed_here:
                cell(column, row, f"{landed_here[word]}\n{value}", CHOSEN, "bold")
            else:
                cell(column, row, str(value) if value else "",
                     FILL if value else EMPTY)

        written = {(b, o + k) for b, o, words in state.stored
                   for k in range(len(words))}
        for index, (name, offset) in enumerate(buffer_slots):
            row = 1 + scratch_words + index
            value = state.memory[name][offset]
            face = CHOSEN if (name, offset) in written else (
                "#e8eef4" if value else EMPTY)
            cell(column, row, str(value), face,
                 "bold" if (name, offset) in written else "normal")

    ax.axhline(1, color="#5d8fb3", linewidth=1.4)
    ax.axhline(1 + scratch_words, color="#5d8fb3", linewidth=1.4)

    ax.set_xlim(0, span)
    ax.set_ylim(0, rows)
    ax.set_xticks([c + 0.5 for c in range(span)], [str(c) for c in range(span)])
    ax.set_yticks([r + 0.5 for r in range(rows)], labels, fontsize=7)
    ax.set_xlabel("cycle")
    ax.set_title(title, fontsize=10)
    ax.invert_yaxis()
    fig.tight_layout()
    plt.show()


def show_inflight(
    facts,
    times: Dict[int, int],
    op_ids: Sequence[int],
    span: int,
    title: str,
) -> None:
    """A slot is used at the issue cycle only, not for the whole latency.

    One row per operation. The solid square is the cycle the operation is handed
    over, which is the only cycle it consumes a slot. The pale bar after it is
    the time it spends in flight, consuming nothing. The strip along the bottom
    counts slots actually used per cycle, so it can be read against the engine's
    limit.

    This exists because "the slot stays busy until the result lands" is the most
    natural wrong guess about the machine, and a timeline of issue cycles alone
    does not contradict it.
    """

    engines = {facts.engine[op_id] for op_id in op_ids}
    limit = min(machine.ENGINE_LIMITS[e] for e in engines)

    fig, (ax, bar) = plt.subplots(
        2, 1, figsize=(max(5.5, 0.78 * span + 2.4), 0.62 * len(op_ids) + 2.4),
        gridspec_kw={"height_ratios": [len(op_ids), 1.15]}, sharex=True,
    )

    used = {cycle: 0 for cycle in range(span)}
    for row, op_id in enumerate(op_ids):
        issue = times[op_id]
        latency = facts.latency[op_id]
        used[issue] = used.get(issue, 0) + 1
        for cycle in range(span):
            ax.add_patch(Rectangle((cycle, row), 1, 1, linewidth=1,
                                   edgecolor="white", facecolor=EMPTY))
        ax.add_patch(Rectangle((issue, row + 0.1), 1, 0.8,
                               facecolor=EDGE, edgecolor=EDGE))
        ax.text(issue + 0.5, row + 0.5, "issue", ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")
        if latency > 1:
            ax.add_patch(Rectangle((issue + 1, row + 0.26), latency - 1, 0.48,
                                   facecolor=FILL, edgecolor=EDGE,
                                   linestyle="--", linewidth=0.9))
            ax.text(issue + 1 + (latency - 1) / 2, row + 0.5, "in flight — no slot",
                    ha="center", va="center", fontsize=7)
        ax.add_patch(Rectangle((issue + latency, row + 0.1), 1, 0.8,
                               facecolor=CHOSEN, edgecolor="#2e6b2a"))
        ax.text(issue + latency + 0.5, row + 0.5, "lands", ha="center",
                va="center", fontsize=7)

    ax.set_xlim(0, span)
    ax.set_ylim(0, len(op_ids))
    ax.set_yticks([r + 0.5 for r in range(len(op_ids))],
                  [f"op{op_id} {facts.opcode[op_id]}" for op_id in op_ids])
    ax.set_title(title, fontsize=10)
    ax.invert_yaxis()

    for cycle in range(span):
        count = used.get(cycle, 0)
        bar.add_patch(Rectangle((cycle, 0), 1, 1, linewidth=1, edgecolor="white",
                                facecolor=FILL if count else EMPTY))
        bar.text(cycle + 0.5, 0.5, str(count), ha="center", va="center", fontsize=8,
                 fontweight="bold" if count else "normal")
    bar.set_xlim(0, span)
    bar.set_ylim(0, 1)
    bar.set_yticks([0.5], [f"slots used\n(limit {limit})"], fontsize=7)
    bar.set_xticks([c + 0.5 for c in range(span)], [str(c) for c in range(span)])
    bar.set_xlabel("cycle")

    fig.tight_layout()
    plt.show()


def show_memory_chain(program: dict, title: str) -> None:
    """The ordering edges between memory operations, direct and implied.

    Solid arrows are the edges ``machine.memory_predecessors`` actually reports.
    The dashed arrow is an ordering that holds as a consequence of following two
    solid ones, which no single row of the three-test table can show. A pair may
    be exempt from a direct edge and still be forced into an order this way.
    """

    memory = [op for op in program["operations"] if op["op"] in machine.MEMORY_OPS]
    index = {op["id"]: position for position, op in enumerate(memory)}

    direct = {op["id"]: list(machine.memory_predecessors(program, op["id"]))
              for op in memory}

    # Orderings that hold only by following two or more solid edges.
    implied = []
    for op in memory:
        reached = set()
        stack = list(direct[op["id"]])
        while stack:
            current = stack.pop()
            if current in reached:
                continue
            reached.add(current)
            stack.extend(direct.get(current, []))
        for earlier in sorted(reached - set(direct[op["id"]])):
            implied.append((earlier, op["id"]))

    fig, ax = plt.subplots(figsize=(1.9 * len(memory) + 2.0, 3.4))
    for op in memory:
        x = index[op["id"]]
        ax.add_patch(Rectangle((x - 0.42, -0.3), 0.84, 0.6,
                               facecolor=FILL if op["op"] in machine.LOAD_OPS
                               else EXCLUDED, edgecolor=EDGE))
        ax.text(x, 0.0, f"op{op['id']}\n{op['op']}\n{op['buffer']}[{op['offset']}]",
                ha="center", va="center", fontsize=8)

    # Anchored at the box centres rather than their edges: over one step the
    # gap between two boxes is too narrow for an arc to be visible at all.
    for later, earlier_list in direct.items():
        for earlier in earlier_list:
            ax.annotate("", xy=(index[later], 0.32), xytext=(index[earlier], 0.32),
                        arrowprops=dict(arrowstyle="-|>", color="#b4453c",
                                        linewidth=1.7, shrinkA=2, shrinkB=2,
                                        connectionstyle="arc3,rad=-0.55"))
    for earlier, later in implied:
        ax.annotate("", xy=(index[later], -0.32), xytext=(index[earlier], -0.32),
                    arrowprops=dict(arrowstyle="-|>", color="#6b7684",
                                    linewidth=1.4, linestyle="--",
                                    shrinkA=2, shrinkB=2,
                                    connectionstyle="arc3,rad=0.42"))

    ax.text(0.0, 1.02, "solid, above: a direct ordering the rule reports",
            transform=ax.transAxes, fontsize=8, color="#b4453c")
    ax.text(0.0, -0.16, "dashed, below: implied by following two solid arrows",
            transform=ax.transAxes, fontsize=8, color="#6b7684")

    ax.set_xlim(-0.8, len(memory) - 0.2)
    ax.set_ylim(-1.0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=10, pad=22)
    fig.tight_layout()
    plt.show()


def show_sharing_rule(
    life: Dict[str, Tuple[int, int]],
    pairs: Sequence[Tuple[str, str]],
    span: int,
    title: str,
) -> None:
    """Rule 4 drawn: which pairs of values may take turns in one locker.

    One panel per pair. Each value is a bar over the cycles it is live, from the
    cycle it is written to the cycle it is last read, both ends inclusive. A
    cycle where the two bars touch is marked, because touching is the whole
    rule: writes commit at the start of a cycle, before any read, so a newcomer
    writing on the reader's own cycle destroys the value first.

    Overlap is decided here by the same inclusive test the compiler uses, not by
    eye: ``start_a <= end_b and start_b <= end_a``.
    """

    fig, axes = plt.subplots(
        len(pairs), 1,
        figsize=(max(5.5, 0.72 * span + 2.2), 1.85 * len(pairs) + 0.6),
        squeeze=False,
    )
    for axis, (first, second) in zip(axes[:, 0], pairs):
        (start_a, end_a), (start_b, end_b) = life[first], life[second]
        clash = start_a <= end_b and start_b <= end_a
        contact = sorted(set(range(start_a, end_a + 1)) & set(range(start_b, end_b + 1)))

        for row, name in enumerate((first, second)):
            start, end = life[name]
            for cycle in range(span):
                axis.add_patch(Rectangle((cycle, row), 1, 1, linewidth=1,
                                         edgecolor="white", facecolor=EMPTY))
            colour = EXCLUDED if clash else FILL
            axis.add_patch(Rectangle((start, row + 0.08), end - start + 1, 0.84,
                                     facecolor=colour, edgecolor=EDGE, linewidth=1.3))
            axis.text(start + (end - start + 1) / 2, row + 0.5,
                      f"{name}  live {start}..{end}", ha="center", va="center",
                      fontsize=8)

        for cycle in contact:
            axis.add_patch(Rectangle((cycle, 0), 1, 2, linewidth=1.8,
                                     edgecolor="#b4453c", facecolor="none"))

        if clash:
            verdict = (f"MAY NOT SHARE  —  both live at cycle "
                       f"{', '.join(str(c) for c in contact)}")
            if start_b > start_a:
                # The newcomer's write lands on a cycle the incumbent still
                # needs: this is the "strictly after" half of the rule.
                note = (f"{second} would write at the start of cycle {start_b}, "
                        f"before {first} is read there")
            elif start_a > start_b:
                note = (f"{first} would write at the start of cycle {start_a}, "
                        f"before {second} is read there")
            else:
                # Neither is a newcomer; they simply coexist.
                note = (f"both hold a value throughout cycle "
                        f"{', '.join(str(c) for c in contact)} — one locker "
                        f"cannot hold two numbers")
        else:
            gap = max(start_a, start_b) - min(end_a, end_b)
            verdict = f"MAY SHARE  —  intervals never touch (gap of {gap} cycle)"
            note = (f"{second} writes at {start_b}, strictly after {first} "
                    f"is last read at {end_a}")

        axis.set_xlim(0, span)
        axis.set_ylim(0, 2)
        axis.set_xticks([c + 0.5 for c in range(span)], [str(c) for c in range(span)])
        axis.set_yticks([])
        axis.set_title(verdict, fontsize=9,
                       color="#b4453c" if clash else "#2e6b2a")
        axis.set_xlabel(note, fontsize=8)
        axis.invert_yaxis()

    fig.suptitle(title, y=1.0)
    fig.tight_layout()
    plt.show()


def show_memory_ordering(program: dict, title: str) -> None:
    """Rule 5 drawn: which pairs of memory operations are forced into an order.

    Every pair of memory operations is put through the three tests the frozen
    ``machine.memory_predecessors`` applies, and the verdict column is checked
    against that function rather than recomputed independently: a row is ordered
    exactly when the earlier operation appears in the later one's predecessor
    list.
    """

    memory = [op for op in program["operations"] if op["op"] in machine.MEMORY_OPS]
    rows: List[tuple] = []
    for index, earlier in enumerate(memory):
        for later in memory[index + 1:]:
            same = earlier["buffer"] == later["buffer"]
            overlap = same and machine._memory_ranges_overlap(earlier, later)
            both_loads = (earlier["op"] in machine.LOAD_OPS
                          and later["op"] in machine.LOAD_OPS)
            ordered = earlier["id"] in machine.memory_predecessors(
                program, later["id"])
            rows.append((earlier, later, same, overlap, both_loads, ordered))

    columns = ["same\nbuffer?", "ranges\noverlap?", "both\nloads?", "ORDERED?"]
    fig, ax = plt.subplots(figsize=(7.6, 0.56 * len(rows) + 1.9))

    for r, (earlier, later, same, overlap, both_loads, ordered) in enumerate(rows):
        label = (f"op{earlier['id']} {earlier['op']} {earlier['buffer']}"
                 f"[{earlier['offset']}]   →   "
                 f"op{later['id']} {later['op']} {later['buffer']}[{later['offset']}]")
        ax.text(-0.15, r + 0.5, label, ha="right", va="center", fontsize=8,
                family="monospace")
        for c, value in enumerate((same, overlap, both_loads, ordered)):
            # Shaded always means "yes" so the row reads left to right without
            # the eye having to relearn the code at the last column. The verdict
            # column is shaded in the constraint colour rather than the plain
            # one, because a "yes" there is a restriction on the schedule.
            if not value:
                face = EMPTY
            else:
                face = EXCLUDED if c == 3 else FILL
            ax.add_patch(Rectangle((c, r), 1, 1, linewidth=1,
                                   edgecolor="white", facecolor=face))
            ax.text(c + 0.5, r + 0.5, "yes" if value else "no", ha="center",
                    va="center", fontsize=8,
                    fontweight="bold" if c == 3 else "normal")

    for c, name in enumerate(columns):
        ax.text(c + 0.5, -0.18, name, ha="center", va="bottom", fontsize=8,
                fontweight="bold")

    ax.set_xlim(0, len(columns))
    ax.set_ylim(0, len(rows))
    ax.set_xticks([])
    ax.set_yticks([])
    # The column headers are drawn inside the axes above row zero, so the title
    # needs clearance for two lines of them or it lands on top.
    ax.set_title(title, fontsize=10, pad=40)
    ax.set_xlabel("ordered = same buffer AND ranges overlap AND not both loads;\n"
                  "an ordered pair must also sit in two different cycles",
                  fontsize=8)
    ax.invert_yaxis()
    fig.tight_layout()
    plt.show()


def show_universe(
    groups: Sequence[Tuple[str, Sequence[si.Cube]]],
    n: int,
    title: str,
    per_row: int = 16,
) -> None:
    """Every index of an ``n`` bit universe, with each group's members marked.

    One panel per group. A cell is the integer itself, shaded when some cube of
    that group contains it. Membership is asked of the cube algebra through
    ``si.cover_contains``; this function never decides what a cube denotes.
    """

    size = 1 << n
    rows = (size + per_row - 1) // per_row
    columns = min(size, per_row)
    fig, axes = plt.subplots(
        len(groups), 1,
        figsize=(0.52 * columns + 1.6, (0.52 * rows + 0.9) * len(groups)),
        squeeze=False,
    )
    for axis, (label, cover) in zip(axes[:, 0], groups):
        marked = 0
        for value in range(size):
            row, column = divmod(value, per_row)
            inside = si.cover_contains(cover, value)
            marked += inside
            axis.add_patch(Rectangle((column, row), 1, 1, linewidth=1,
                                     edgecolor="white",
                                     facecolor=FILL if inside else EMPTY))
            axis.text(column + 0.5, row + 0.5, str(value), ha="center",
                      va="center", fontsize=8,
                      color="#1b3a4b" if inside else "#9aa5b1")
        axis.set_xlim(0, columns)
        axis.set_ylim(0, rows)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_title(f"{label}  --  {marked} of {size} indices", fontsize=10)
        axis.invert_yaxis()
    fig.suptitle(title, y=1.0)
    fig.tight_layout()
    plt.show()


def show_cover_blocks(
    cover: Sequence[si.Cube],
    field: si.Field,
    lo: int,
    hi: int,
    title: str,
    excluded: Sequence[int] = (),
    chosen: Optional[int] = None,
) -> None:
    """An interval cover drawn as the aligned blocks it actually is.

    ``lo``/``hi`` bound the drawn axis. Each cube of the cover becomes one bar
    spanning the field values it admits, so a reader can see that a range of
    nine cycles is carried by a handful of blocks rather than nine singletons.
    """

    span = hi - lo + 1
    fig, ax = plt.subplots(figsize=(max(4.5, 0.46 * span + 1.8),
                                    0.42 * max(len(cover), 1) + 1.9))
    for value in range(lo, hi + 1):
        ax.add_patch(Rectangle((value, -0.9), 1, 0.7, linewidth=1,
                               edgecolor="white",
                               facecolor=EXCLUDED if value in excluded else EMPTY))
        ax.text(value + 0.5, -0.55, str(value), ha="center", va="center", fontsize=7)
    for index, cube in enumerate(cover):
        # A cube admits field value ``v`` when ``v`` agrees with every field
        # coordinate the cube has fixed. Coordinates outside the field are
        # irrelevant to the drawn axis and are not consulted.
        required = cube.anchor & field.mask
        fixed_in_field = cube.fixed_mask & field.mask
        values = [
            v for v in range(lo, hi + 1)
            if (field.encode(v) & fixed_in_field) == required
        ]
        if not values:
            continue
        start, end = min(values), max(values)
        ax.add_patch(Rectangle((start, index + 0.12), end - start + 1, 0.76,
                               facecolor=FILL, edgecolor=EDGE))
        ax.text(start + (end - start + 1) / 2, index + 0.5,
                f"{cube.label()}  ({len(values)})", ha="center", va="center",
                fontsize=7)
    if chosen is not None:
        ax.add_patch(Rectangle((chosen, -0.9), 1, 0.7, linewidth=1.6,
                               edgecolor="#2e6b2a", facecolor=CHOSEN))
        ax.text(chosen + 0.5, -0.55, str(chosen), ha="center", va="center",
                fontsize=7, fontweight="bold")
    ax.set_xlim(lo, hi + 1)
    ax.set_ylim(-1.0, max(len(cover), 1))
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlabel(f"value of field {field.name!r}")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_index_layout(fields: Sequence[si.Field], n: int, title: str) -> None:
    """The bit layout of one query's index, drawn as a labelled ruler.

    Coordinates are LSB-first, so bit 0 sits on the left exactly as
    ``Cube.label`` prints it.
    """

    fig, ax = plt.subplots(figsize=(max(5.0, 0.36 * n + 2.0), 1.9))
    palette = ["#cfe3f3", "#dfe8d5", "#f3e2cf", "#e3d5ef", "#d5eeee"]
    for index, field in enumerate(sorted(fields, key=lambda f: f.offset)):
        colour = palette[index % len(palette)]
        ax.add_patch(Rectangle((field.offset, 0.25), field.width, 0.6,
                               facecolor=colour, edgecolor=EDGE))
        ax.text(field.offset + field.width / 2, 0.55,
                f"{field.name}\n{field.width}b", ha="center", va="center", fontsize=8)
    for bit in range(n):
        ax.text(bit + 0.5, 0.08, str(bit), ha="center", va="center", fontsize=6,
                color="#6b7684")
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel(f"index coordinate (LSB-first), width {n} bits")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_expression_tree(expression, title: str, max_depth: int = 3) -> None:
    """The acceptance expression as an indented tree, with each leaf's cover size.

    Printed rather than plotted: the useful content is the shape and the
    alternative counts, and a text tree survives copying into a report. Node
    counts come from ``si.count_records`` so this cannot drift from the meter.
    """

    print(title)
    print(f"total expression records: {si.count_records(expression)}")

    def walk(node, depth, prefix):
        if depth > max_depth:
            print(f"{prefix}...")
            return
        if isinstance(node, si.Leaf):
            print(f"{prefix}Leaf  {len(node.cubes)} alternative(s)")
        elif isinstance(node, si.AllOf):
            print(f"{prefix}AllOf {len(node.children)} child(ren)  [every one must hold]")
            for child in node.children:
                walk(child, depth + 1, prefix + "    ")
        elif isinstance(node, si.AnyOf):
            print(f"{prefix}AnyOf {len(node.children)} child(ren)  [at least one]")
            for child in node.children:
                walk(child, depth + 1, prefix + "    ")

    walk(expression, 0, "  ")
    print()


def show_search_economy(
    labels: Sequence[str],
    visited: Sequence[int],
    total: Sequence[int],
    title: str,
) -> None:
    """Cubes actually visited against the size of the declared assignment space.

    Both bars are drawn on a logarithmic axis because the two quantities differ
    by orders of magnitude; the ratio is printed on each pair so the figure
    cannot be read without its denominator.
    """

    positions = range(len(labels))
    fig, ax = plt.subplots(figsize=(max(5.0, 1.5 * len(labels) + 2.0), 3.4))
    ax.bar([p - 0.2 for p in positions], total, width=0.4, color=EMPTY,
           edgecolor=EDGE, label="assignments in the declared domain")
    ax.bar([p + 0.2 for p in positions], visited, width=0.4, color=FILL,
           edgecolor=EDGE, label="cubes the search visited")
    for p, seen, whole in zip(positions, visited, total):
        if seen > 0 and whole > 0:
            ax.text(p, max(seen, whole) * 1.6, f"1 in {whole / seen:,.0f}",
                    ha="center", fontsize=8)
    ax.set_yscale("log")
    ax.set_xticks(list(positions), labels, fontsize=8)
    ax.set_ylabel("count (log scale)")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    plt.show()


def show_program_results(
    programs: Sequence[str],
    arms: Dict[str, Sequence[int]],
    title: str,
    ylabel: str = "cycles x scratch words (lower is better)",
) -> None:
    """One grouped bar per program, one bar per arm, on a common coordinate.

    Every arm is measured on the same programs with the same metric, which is
    the comparison this figure exists to make honest.
    """

    names = list(arms)
    width = 0.8 / len(names)
    positions = range(len(programs))
    fig, ax = plt.subplots(figsize=(max(6.0, 1.15 * len(programs) + 2.0), 3.8))
    shades = [EMPTY, "#dfe8d5", FILL]
    for index, name in enumerate(names):
        offset = (index - (len(names) - 1) / 2) * width
        ax.bar([p + offset for p in positions], arms[name], width=width,
               label=name, color=shades[index % len(shades)], edgecolor=EDGE)
    ax.set_yscale("log")
    ax.set_xticks(list(positions), programs, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    plt.show()
