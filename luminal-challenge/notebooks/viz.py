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
* ``DEAD`` -- a code whose legal prefix has no legal continuation (notebook 02).
"""

from __future__ import annotations

import math
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
    "show_list_schedule",
    "show_cube_anatomy",
    "show_universe",
    "show_cover_blocks",
    "show_index_layout",
    "show_expression_tree",
    "show_search_economy",
    "show_program_results",
    "show_code_statuses",
    "show_decode_steps",
    "show_decision_icicle",
    "show_stacked_outcomes",
    "show_objective_plane",
    "show_effects",
    "show_domain_filtering",
    "show_window_catalog",
    "show_index_scores",
    "show_bars",
]


ENGINES = ["load", "scalar", "vector", "store", "flow"]

FILL = "#cfe3f3"
EMPTY = "#f2f4f7"
EDGE = "#5d8fb3"
EXCLUDED = "#f0d5d5"
CHOSEN = "#a8d5a2"
# Added for notebooks 02 and 03. A dead end is not the same failure as an
# invalid code, so it gets its own neutral grey rather than a second red.
DEAD = "#aeb3ba"


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


def show_list_schedule(steps: Sequence[object], title: str) -> None:
    """The greedy list scheduler, one row per cycle, read like a queue at a till.

    Each row is the ready queue of that cycle -- every operation whose inputs
    have landed -- sorted left to right by the rule's priority. The rule walks
    the row once: green cards got a slot and issue this cycle; red cards found
    their engine already full and go back into next cycle's queue. The note at
    the right counts the operations still waiting for data, which is why a
    row can be empty.

    ``steps`` comes from ``trace.replay_list_schedule``, which checks itself
    against ``common.classical_compile`` before returning.
    """

    width = max(len(step.queue) for step in steps)
    rows = len(steps)
    fig, ax = plt.subplots(figsize=(2.0 * width + 4.2, 0.72 * rows + 1.6))

    for row, step in enumerate(steps):
        if not step.queue:
            ax.text(width / 2, row + 0.5,
                    "queue empty — nothing ready, results still in flight",
                    ha="center", va="center", fontsize=8, style="italic",
                    color="#7a7f87")
        for col, entry in enumerate(step.queue):
            face, edge = (CHOSEN, "#2e6b2a") if entry.placed else (EXCLUDED, "#b35d5d")
            ax.add_patch(Rectangle((col + 0.05, row + 0.08), 0.9, 0.84,
                                   facecolor=face, edgecolor=edge))
            ax.text(col + 0.5, row + 0.36, f"op{entry.op_id} {entry.opcode}",
                    ha="center", va="center", fontsize=8, fontweight="bold")
            ax.text(col + 0.5, row + 0.68,
                    f"prio {entry.priority} · feeds {entry.fanout}",
                    ha="center", va="center", fontsize=7)
            if not entry.placed:
                ax.text(col + 0.5, row + 0.18, f"{entry.engine} full",
                        ha="center", va="center", fontsize=6, color="#8a2f2f")
        slots = ", ".join(f"{e} {n}/{machine.ENGINE_LIMITS[e]}"
                          for e, n in step.used.items())
        note = f"slots: {slots}" if slots else "slots: none used"
        if step.waiting:
            note += f"\nwaiting for data: {len(step.waiting)} ops"
        ax.text(width + 0.15, row + 0.5, note, ha="left", va="center", fontsize=7)

    ax.set_xlim(0, width + 2.2)
    ax.set_ylim(0, rows)
    ax.set_xticks([c + 0.5 for c in range(width)], [f"#{c + 1}" for c in range(width)])
    ax.xaxis.set_ticks_position("top")
    ax.set_xlabel("position in the ready queue (highest priority first)")
    ax.xaxis.set_label_position("top")
    ax.set_yticks([r + 0.5 for r in range(rows)], [f"cycle {s.cycle}" for s in steps])
    for side in ("right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(title, fontsize=10, pad=28)
    ax.invert_yaxis()
    fig.tight_layout()
    plt.show()


# --------------------------------------------------------------------------
# Renders of the index method itself
# --------------------------------------------------------------------------


def show_violations(panels: Sequence[dict], span: int, title: str) -> None:
    """The three ways a compilation is rejected, each drawn as its collision.

    One panel per violation, all on the same cycle axis so they can be compared.
    Red is always the thing that breaks the rule; green is the moment that would
    have made it legal.

    Each panel is an explicit descriptor rather than something inferred, because
    the point is to draw one specific illegal arrangement, not to search for
    illegality:

    * ``latency``  -- keys ``value, issued, lands, reader, reads_at``
    * ``capacity`` -- keys ``cycle, engine, ops, limit``
    * ``sharing``  -- keys ``word, first, second`` where each is ``(name, lo, hi)``

    Every panel also carries ``message``, which is the validator's own words.
    """

    fig, axes = plt.subplots(
        len(panels), 1, figsize=(max(6.0, 0.78 * span + 2.6), 2.5 * len(panels)),
        squeeze=False,
    )

    for axis, panel in zip(axes[:, 0], panels):
        kind = panel["kind"]

        if kind == "latency":
            rows = [panel["value"], panel["reader"]]
            for row in range(2):
                for cycle in range(span):
                    axis.add_patch(Rectangle((cycle, row), 1, 1, linewidth=1,
                                             edgecolor="white", facecolor=EMPTY))
            issued, lands = panel["issued"], panel["lands"]
            axis.add_patch(Rectangle((issued, 0.1), 1, 0.8, facecolor=EDGE,
                                     edgecolor=EDGE))
            axis.text(issued + 0.5, 0.5, "issue", ha="center", va="center",
                      fontsize=7, color="white", fontweight="bold")
            if lands > issued + 1:
                axis.add_patch(Rectangle((issued + 1, 0.3), lands - issued - 1, 0.4,
                                         facecolor=FILL, edgecolor=EDGE,
                                         linestyle="--", linewidth=0.9))
                axis.text((issued + 1 + lands) / 2, 0.5, "in flight — does not exist yet",
                          ha="center", va="center", fontsize=7)
            axis.add_patch(Rectangle((lands, 0.1), 1, 0.8, facecolor=CHOSEN,
                                     edgecolor="#2e6b2a"))
            axis.text(lands + 0.5, 0.5, "exists", ha="center", va="center", fontsize=7)

            reads = panel["reads_at"]
            axis.add_patch(Rectangle((reads, 1.1), 1, 0.8, facecolor=EXCLUDED,
                                     edgecolor="#b4453c", linewidth=1.8))
            axis.text(reads + 0.5, 1.5, "reads it", ha="center", va="center",
                      fontsize=7, fontweight="bold")
            # The axis is inverted, so a smaller y sits higher: the arrow and its
            # label go in the gap between the two rows, not across the red box.
            axis.annotate("", xy=(lands + 0.5, 1.04), xytext=(reads + 0.5, 1.04),
                          arrowprops=dict(arrowstyle="-|>", color="#b4453c",
                                          linewidth=1.5, linestyle=":"))
            axis.text((reads + lands) / 2 + 0.5, 0.97,
                      f"{lands - reads} cycle too early", ha="center",
                      va="bottom", fontsize=7.5, color="#b4453c",
                      fontweight="bold")
            axis.set_ylim(0, 2)
            axis.set_yticks([0.5, 1.5], rows, fontsize=8)

        elif kind == "capacity":
            ops, limit, cycle = panel["ops"], panel["limit"], panel["cycle"]
            for slot in range(len(ops)):
                for column in range(span):
                    axis.add_patch(Rectangle((column, slot), 1, 1, linewidth=1,
                                             edgecolor="white", facecolor=EMPTY))
            for slot, op_id in enumerate(ops):
                over = slot >= limit
                axis.add_patch(Rectangle((cycle, slot + 0.1), 1, 0.8,
                                         facecolor=EXCLUDED if over else FILL,
                                         edgecolor="#b4453c" if over else EDGE,
                                         linewidth=1.8 if over else 1.0))
                axis.text(cycle + 0.5, slot + 0.5, f"op{op_id}", ha="center",
                          va="center", fontsize=7,
                          fontweight="bold" if over else "normal")
            axis.axhline(limit, color="#b4453c", linestyle="--", linewidth=1.4)
            axis.text(span - 0.1, limit, f"  {panel['engine']} limit = {limit}",
                      ha="right", va="bottom", fontsize=7, color="#b4453c")
            axis.set_ylim(0, len(ops))
            axis.set_yticks([s + 0.5 for s in range(len(ops))],
                            [f"slot {s}" if s < limit else "overflow"
                             for s in range(len(ops))], fontsize=8)

        elif kind == "sharing":
            (first, lo1, hi1), (second, lo2, hi2) = panel["first"], panel["second"]
            for column in range(span):
                axis.add_patch(Rectangle((column, 0), 1, 1, linewidth=1,
                                         edgecolor="white", facecolor=EMPTY))
            # Inverted axis: the first-named value is given the smaller y so it
            # is drawn on top, matching the order it is described in.
            axis.add_patch(Rectangle((lo1, 0.1), hi1 - lo1 + 1, 0.35,
                                     facecolor=EXCLUDED, edgecolor=EDGE))
            axis.text(lo1 + (hi1 - lo1 + 1) / 2, 0.28, f"{first}  {lo1}..{hi1}",
                      ha="center", va="center", fontsize=7)
            axis.add_patch(Rectangle((lo2, 0.55), hi2 - lo2 + 1, 0.35,
                                     facecolor=EXCLUDED, edgecolor=EDGE))
            axis.text(lo2 + (hi2 - lo2 + 1) / 2, 0.72, f"{second}  {lo2}..{hi2}",
                      ha="center", va="center", fontsize=7)
            for cycle in sorted(set(range(lo1, hi1 + 1)) & set(range(lo2, hi2 + 1))):
                axis.add_patch(Rectangle((cycle, 0), 1, 1, linewidth=2.0,
                                         edgecolor="#b4453c", facecolor="none"))
            axis.set_ylim(0, 1)
            axis.set_yticks([0.5], [f"scratch word {panel['word']}"], fontsize=8)

        axis.set_xlim(0, span)
        axis.set_xticks([c + 0.5 for c in range(span)], [str(c) for c in range(span)])
        axis.set_title(panel["message"], fontsize=8.5, color="#b4453c")
        axis.invert_yaxis()

    axes[-1, 0].set_xlabel("cycle")
    fig.suptitle(title, y=1.0)
    fig.tight_layout()
    plt.show()


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


def show_cube_anatomy(cube: si.Cube, title: str, max_members: int = 16) -> None:
    """Take one cube's printed label apart, coordinate by coordinate.

    The upper panel stacks the label string over the two integers it is printed
    from, one column per coordinate, LSB-first so that x0 sits on the left
    exactly as ``Cube.label`` writes it. The lower panel adds each sumando to
    the anchor and recovers a member.

    Every value drawn is asked of the cube: ``label`` supplies the marks,
    ``members`` supplies the set, and each sumando is read back as
    ``member - anchor``. This function decides nothing about what a cube
    denotes; it only lays out what ``schema_index`` already said.
    """

    marks = cube.label().split(":")[1]
    free_positions = [i for i, mark in enumerate(marks) if mark == "*"]
    members = list(cube.members())[:max_members]
    sumandos = [member - cube.anchor for member in members]

    gutter = 3.0
    columns = max(cube.n, 1)
    rows = len(members) + 1
    fig, (top, bottom) = plt.subplots(
        2, 1,
        figsize=(max(6.0, 0.86 * columns + gutter + 1.0), 2.5 + 0.34 * rows),
        gridspec_kw={"height_ratios": [5, max(rows, 3)]},
    )

    # ---- upper panel: the label over the integers it is printed from -------
    legend = [
        ("coordinate", [f"x{i}" for i in range(cube.n)], None),
        ("weight  2**i", [str(1 << i) for i in range(cube.n)], None),
        ("anchor bits", [str((cube.anchor >> i) & 1) for i in range(cube.n)],
         lambda i: FILL if (cube.anchor >> i) & 1 else EMPTY),
        ("free mask bits", [str((cube.free_mask >> i) & 1) for i in range(cube.n)],
         lambda i: CHOSEN if (cube.free_mask >> i) & 1 else EMPTY),
        ("printed label", list(marks),
         lambda i: CHOSEN if marks[i] == "*" else FILL if marks[i] == "1" else EMPTY),
    ]
    for row, (name, cells, colour) in enumerate(legend):
        top.text(-0.2, row + 0.5, name, ha="right", va="center", fontsize=8.5)
        for i, text in enumerate(cells):
            if colour is not None:
                top.add_patch(Rectangle((i, row + 0.08), 1, 0.84, linewidth=1,
                                        edgecolor="white", facecolor=colour(i)))
            top.text(i + 0.5, row + 0.5, text, ha="center", va="center",
                     fontsize=11 if name == "printed label" else 9,
                     family="monospace" if name == "printed label" else None,
                     fontweight="bold" if name == "printed label" else "normal")
    top.set_xlim(-gutter, columns)
    top.set_ylim(0, len(legend))
    top.set_xticks([])
    top.set_yticks([])
    top.invert_yaxis()
    top.set_title(f"{title}\n{cube.label()}   "
                  f"anchor={cube.anchor}  free_mask={cube.free_mask}  "
                  f"size={cube.size}", fontsize=10)

    # ---- lower panel: anchor + sumando = member ----------------------------
    width = 1 + len(free_positions) + 2
    headers = ["anchor"] + [f"x{p}  (+{1 << p})" for p in free_positions] + ["=", "member"]
    for column, text in enumerate(headers):
        bottom.text(column + 0.5, 0.5, text, ha="center", va="center", fontsize=8.5)
    for row, (member, sumando) in enumerate(zip(members, sumandos), start=1):
        bottom.add_patch(Rectangle((0, row + 0.08), 1, 0.84, linewidth=1,
                                   edgecolor="white", facecolor=FILL))
        bottom.text(0.5, row + 0.5, str(cube.anchor), ha="center", va="center",
                    fontsize=9)
        for column, position in enumerate(free_positions, start=1):
            on = (sumando >> position) & 1
            bottom.add_patch(Rectangle((column, row + 0.08), 1, 0.84, linewidth=1,
                                       edgecolor="white",
                                       facecolor=CHOSEN if on else EMPTY))
            bottom.text(column + 0.5, row + 0.5,
                        f"+{1 << position}" if on else "+0",
                        ha="center", va="center", fontsize=9,
                        color="#1b3a4b" if on else "#9aa5b1")
        bottom.text(width - 1.5, row + 0.5, "=", ha="center", va="center", fontsize=9)
        bottom.add_patch(Rectangle((width - 1, row + 0.08), 1, 0.84, linewidth=1,
                                   edgecolor=EDGE, facecolor=FILL))
        bottom.text(width - 0.5, row + 0.5, str(member), ha="center", va="center",
                    fontsize=9, fontweight="bold")
    bottom.set_xlim(-gutter, width)
    bottom.set_ylim(0, rows)
    bottom.set_xticks([])
    bottom.set_yticks([])
    bottom.invert_yaxis()
    bottom.text(-0.2, 0.5, "the sumandos", ha="right", va="center", fontsize=8.5)
    shown = len(members)
    bottom.set_xlabel(
        f"every subset of the {len(free_positions)} free weights, added to the "
        f"anchor: {shown} of {cube.size} members drawn", fontsize=8)

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


# --------------------------------------------------------------------------
# Renders for 02-structural-encoding and 03-objective-index-search
# --------------------------------------------------------------------------


_STATUS_COLOUR = {
    "COMPLETE": FILL,
    "INVALID_CODE": EXCLUDED,
    "DEAD_END": DEAD,
    "INTERRUPTED": "#fff2c6",
}


def show_code_statuses(
    panels: Sequence[Tuple[str, Sequence[str]]],
    title: str,
    per_row: int = 32,
    marked: Iterable[int] = (),
) -> None:
    """Every code of a bit universe, coloured by what the decoder returned.

    ``panels`` holds one ``(label, statuses)`` pair per codec, where
    ``statuses[z]`` is the status the decoder returned for code ``z``. Nothing
    here decodes; the caller passes the decoder's own answers. ``marked`` codes
    are drawn in the chosen colour, for example the elite members.
    """

    marked = set(marked)
    size = max(len(statuses) for _, statuses in panels)
    rows = (size + per_row - 1) // per_row
    columns = min(size, per_row)
    fig, axes = plt.subplots(
        len(panels), 1,
        figsize=(0.36 * columns + 1.8, (0.36 * rows + 1.0) * len(panels)),
        squeeze=False,
    )
    for axis, (label, statuses) in zip(axes[:, 0], panels):
        counts: Dict[str, int] = {}
        for code, status in enumerate(statuses):
            counts[status] = counts.get(status, 0) + 1
            row, column = divmod(code, per_row)
            colour = CHOSEN if (status == "COMPLETE" and code in marked) \
                else _STATUS_COLOUR.get(status, EMPTY)
            axis.add_patch(Rectangle((column, row), 1, 1, linewidth=0.8,
                                     edgecolor="white", facecolor=colour))
            if status == "COMPLETE":
                axis.text(column + 0.5, row + 0.5, str(code), ha="center",
                          va="center", fontsize=6.5, color="#1b3a4b")
        axis.set_xlim(0, columns)
        axis.set_ylim(0, rows)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.invert_yaxis()
        summary = ", ".join(f"{name} {counts[name]}" for name in
                            ("COMPLETE", "INVALID_CODE", "DEAD_END", "INTERRUPTED")
                            if name in counts)
        axis.set_title(f"{label}  --  {summary}  (of {len(statuses)} codes)", fontsize=10)
    handles = [Rectangle((0, 0), 1, 1, facecolor=_STATUS_COLOUR[name], edgecolor=EDGE)
               for name in ("COMPLETE", "INVALID_CODE", "DEAD_END")]
    names = ["COMPLETE (a legal compilation)", "INVALID_CODE (rank past the legal list)",
             "DEAD_END (no legal option left)"]
    if marked:
        handles.append(Rectangle((0, 0), 1, 1, facecolor=CHOSEN, edgecolor=EDGE))
        names.append("COMPLETE and marked")
    fig.legend(handles, names, loc="lower center", ncol=len(names), fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(title, y=1.0)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    plt.show()


def show_decode_steps(steps: Sequence[dict], title: str) -> None:
    """One row per decision of a decode: declared values, legal ones, the pick.

    Each step is a dict with ``label``, ``declared`` (the declared domain, in
    ascending order), ``options`` (the ordered legal option list the codec built
    at that prefix), ``bits`` (the field's bits as printed, LSB-first), ``rank``
    and ``chosen``. Declared values that are not legal are drawn as excluded;
    each legal value carries its rank in the option list above it.
    """

    width = max(len(step["declared"]) for step in steps)
    fig, ax = plt.subplots(figsize=(0.62 * width + 7.2, 0.95 * len(steps) + 1.1))
    for row, step in enumerate(steps):
        y = len(steps) - 1 - row
        ax.text(-0.3, y + 0.4, step["label"], ha="right", va="center", fontsize=10,
                fontweight="bold")
        options = list(step["options"])
        for column, value in enumerate(step["declared"]):
            legal = value in options
            colour = EMPTY if legal else EXCLUDED
            edge = EDGE
            if step.get("chosen") == value:
                colour, edge = CHOSEN, "#2e6b2a"
            ax.add_patch(Rectangle((column, y), 0.9, 0.8, facecolor=colour,
                                   edgecolor=edge, linewidth=1.4 if colour == CHOSEN else 0.8))
            ax.text(column + 0.45, y + 0.4, str(value), ha="center", va="center", fontsize=9)
            if legal:
                ax.text(column + 0.45, y + 0.92, f"r{options.index(value)}", ha="center",
                        va="bottom", fontsize=6.5, color="#4a6b82")
        listing = "[" + ", ".join(str(v) for v in options) + "]"
        if step.get("chosen") is None:
            verdict = step.get("verdict", "stops here")
        else:
            verdict = f"rank {step['rank']}  ->  {step['chosen']}"
        ax.text(width + 0.4, y + 0.4,
                f"O(s) = {listing}     bits {step['bits']}  ->  {verdict}",
                ha="left", va="center", fontsize=9, family="monospace")
    ax.set_xlim(-2.2, width + 9.5)
    ax.set_ylim(-0.3, len(steps) + 0.1)
    ax.axis("off")
    ax.set_title(title, fontsize=10)
    handles = [Rectangle((0, 0), 1, 1, facecolor=c, edgecolor=EDGE)
               for c in (EMPTY, EXCLUDED, CHOSEN)]
    ax.legend(handles, ["declared and legal now (rN = its rank)",
                        "declared but illegal at this prefix", "the value the bits select"],
              loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=3, fontsize=8,
              frameon=False)
    fig.tight_layout()
    plt.show()


def show_decision_icicle(
    paths: Sequence[Tuple[Tuple[str, ...], int]],
    title: str,
    depth_labels: Sequence[str],
    notes: Optional[Dict[Tuple[str, ...], str]] = None,
    excluded: Iterable[Tuple[str, ...]] = (),
    best: Optional[int] = None,
) -> None:
    """The legal decision tree drawn as an icicle: one band per decision.

    ``paths`` is one ``(choices, product)`` pair per complete legal decode, in
    the order the codec enumerates them. A prefix becomes one rectangle spanning
    the leaves beneath it, so the width of a node is the number of complete
    compilations it still contains. ``notes`` adds a text under a prefix (a
    bound, for example); ``excluded`` prefixes are shaded as removed; leaves
    whose product equals ``best`` are drawn in the chosen colour.
    """

    notes = notes or {}
    excluded = set(excluded)
    depth = max(len(choices) for choices, _ in paths)
    leaves = len(paths)
    fig, ax = plt.subplots(figsize=(max(7.0, 0.34 * leaves + 2.4), 1.05 * (depth + 1) + 0.8))
    for level in range(depth):
        start = 0
        while start < leaves:
            prefix = paths[start][0][: level + 1]
            end = start
            while end < leaves and paths[end][0][: level + 1] == prefix:
                end += 1
            colour = EXCLUDED if prefix in excluded else EMPTY
            ax.add_patch(Rectangle((start, depth - level), end - start, 0.9,
                                   facecolor=colour, edgecolor=EDGE, linewidth=0.8))
            text = prefix[-1]
            if prefix in notes:
                text += "\n" + notes[prefix]
            ax.text(start + (end - start) / 2, depth - level + 0.45, text, ha="center",
                    va="center", fontsize=7 if end - start > 1 else 6)
            start = end
    for index, (_, product) in enumerate(paths):
        colour = CHOSEN if best is not None and product == best else FILL
        ax.add_patch(Rectangle((index, 0), 1, 0.9, facecolor=colour, edgecolor=EDGE,
                               linewidth=0.8))
        ax.text(index + 0.5, 0.45, str(product), ha="center", va="center", fontsize=7,
                rotation=90 if leaves > 24 else 0)
    for level, label in enumerate(depth_labels[:depth]):
        ax.text(-0.4, depth - level + 0.45, label, ha="right", va="center", fontsize=8)
    ax.text(-0.4, 0.45, "J = C x S", ha="right", va="center", fontsize=8)
    ax.set_xlim(-3.0, leaves)
    ax.set_ylim(0, depth + 1)
    ax.axis("off")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_stacked_outcomes(
    labels: Sequence[str],
    stacks: Dict[str, Sequence[float]],
    title: str,
    xlabel: str = "count",
    colours: Optional[Dict[str, str]] = None,
    totals: bool = True,
) -> None:
    """Horizontal stacked bars: what every attempt of every row turned into.

    ``stacks`` maps an outcome name to one value per label. The total is printed
    at the end of each bar so no bar can be read without its denominator.
    """

    palette = ["#cfe3f3", "#f0d5d5", "#d6d9de", "#a8d5a2", "#f3e2cf", "#e3d5ef",
               "#fff2c6", "#d5eeee"]
    colours = colours or {}
    fig, ax = plt.subplots(figsize=(8.6, 0.46 * len(labels) + 1.5))
    left = [0.0] * len(labels)
    for index, (name, values) in enumerate(stacks.items()):
        colour = colours.get(name, _STATUS_COLOUR.get(name, palette[index % len(palette)]))
        ax.barh(range(len(labels)), values, left=left, color=colour, edgecolor=EDGE,
                linewidth=0.6, label=name)
        left = [a + b for a, b in zip(left, values)]
    if totals:
        for row, total in enumerate(left):
            ax.text(total, row, f"  {total:,.0f}" if total >= 10 else f"  {total:g}",
                    va="center", fontsize=8)
    ax.set_yticks(range(len(labels)), labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.set_xlim(0, max(left) * 1.12 if max(left) > 0 else 1)
    handles, names = ax.get_legend_handles_labels()
    fig.legend(handles, names, fontsize=8, loc="lower center", ncol=min(5, len(stacks)),
               frameon=False)
    fig.tight_layout(rect=(0, 0.42 / (0.46 * len(labels) + 1.5), 1, 1))
    plt.show()


def show_objective_plane(
    incumbent: Tuple[int, int],
    title: str,
    targets: Sequence[Tuple[int, int]] = (),
    points: Sequence[Tuple[str, Tuple[int, int]]] = (),
    caps: Optional[dict] = None,
    c_range: Tuple[int, int] = (1, 20),
    s_range: Tuple[int, int] = (1, 20),
) -> None:
    """The (cycles, scratch) plane an improvement has to land in.

    Every integer point with ``C*S <= J0 - 1`` is a strict improvement; they are
    drawn as small dots under the curve ``C*S = J0``. Each target rectangle is
    the set of points the old controller could ask for: ``C <= Ct`` and
    ``S <= St``. ``caps`` (keys ``LC``, ``LS``, ``Ccap``, ``Scap``) draws the box
    the integer-cap lemma keeps. The caller supplies every number.
    """

    c0, s0 = incumbent
    j0 = c0 * s0
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    lo_c, hi_c = c_range
    lo_s, hi_s = s_range
    improving = [(c, s) for c in range(lo_c, hi_c + 1) for s in range(lo_s, hi_s + 1)
                 if c * s <= j0 - 1]
    if caps is not None:
        ax.add_patch(Rectangle((caps["LC"] - 0.5, caps["LS"] - 0.5),
                               caps["Ccap"] - caps["LC"] + 1, caps["Scap"] - caps["LS"] + 1,
                               facecolor="#eef6ea", edgecolor="#2e6b2a", linestyle="--",
                               linewidth=1.2, label="kept by the integer caps"))
    for index, (tc, ts) in enumerate(targets):
        ax.add_patch(Rectangle((lo_c - 0.5, lo_s - 0.5), tc - lo_c + 1, ts - lo_s + 1,
                               facecolor="none", edgecolor=EDGE, linewidth=1.2,
                               label="old target rectangles" if index == 0 else None))
        ax.text(tc + 0.5, ts + 0.4, f"({tc},{ts})", fontsize=7, color=EDGE)
    xs = [c for c, _ in improving]
    ys = [s for _, s in improving]
    ax.scatter(xs, ys, s=6, color="#9aa5b1", label=f"every strict improvement, C*S <= {j0 - 1}")
    curve_c = [c / 10 for c in range(lo_c * 10, hi_c * 10 + 1)]
    ax.plot(curve_c, [j0 / c for c in curve_c], color="#b24a4a", linewidth=1.0,
            label=f"C*S = {j0} (the incumbent's product)")
    ax.scatter([c0], [s0], s=70, marker="s", color="#1b3a4b", zorder=5,
               label=f"incumbent ({c0}, {s0})")
    for label, (c, s) in points:
        ax.scatter([c], [s], s=80, marker="*", color="#2e6b2a", zorder=6)
        ax.annotate(f"{label} ({c},{s})  J={c * s}", (c, s), textcoords="offset points",
                    xytext=(6, 6), fontsize=8, color="#2e6b2a")
    ax.set_xlim(lo_c - 0.5, hi_c + 0.5)
    ax.set_ylim(lo_s - 0.5, hi_s + 0.5)
    ax.set_xlabel("C, cycles")
    ax.set_ylabel("S, scratch words")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=7.5, loc="upper right")
    fig.tight_layout()
    plt.show()


def show_effects(
    rows: Sequence[Tuple[str, float, float, float]],
    title: str,
    xlabel: str = "mean paired log(J_control / J_candidate)   (> 0: candidate has lower J)",
) -> None:
    """A forest plot of paired log-ratio effects, each with its own interval.

    Rows are ``(label, estimate, low, high)`` read from the frozen evidence. The
    zero line is drawn because an interval touching it is not a result. Each
    row also prints its estimate as a percentage change in geometric J.
    """

    fig, ax = plt.subplots(figsize=(8.8, 0.5 * len(rows) + 1.4))
    for index, (label, estimate, low, high) in enumerate(rows):
        clear = low > 0 or high < 0
        colour = "#2e6b2a" if clear else "#6b7684"
        ax.plot([low, high], [index, index], color=colour, linewidth=2.2)
        ax.scatter([estimate], [index], color=colour, s=36, zorder=3)
        percent = (1 - math.exp(-estimate)) * 100
        ax.text(max(high, 0) + 0.004, index,
                f"{estimate:+.4f} [{low:+.4f}, {high:+.4f}]  ~{percent:+.1f}% J",
                va="center", fontsize=7.5)
    ax.axvline(0, color="#b24a4a", linewidth=1.0)
    ax.set_yticks(range(len(rows)), [row[0] for row in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=8.5)
    ax.set_title(title, fontsize=10)
    span_low = min(min(row[2] for row in rows), 0)
    span_high = max(max(row[3] for row in rows), 0)
    ax.set_xlim(span_low - 0.01, span_high + (span_high - span_low) * 0.9 + 0.02)
    fig.tight_layout()
    plt.show()


def show_domain_filtering(
    rows: Sequence[Tuple[str, Sequence[int], Sequence[int], Dict[int, str]]],
    title: str,
) -> None:
    """Each variable's domain before and after propagation, value by value.

    A row is ``(label, declared, kept, reasons)``: ``reasons`` maps a removed
    value to the short rule tag that removed it, read from the propagator's own
    certificates. Nothing here decides what is removed.

    A row may carry a fifth element, the value the method finally chose from
    what was kept (a query's minimum member); it is drawn in the chosen colour.
    """

    width = max(len(row[1]) for row in rows)
    fig, ax = plt.subplots(figsize=(0.55 * width + 3.4, 0.62 * len(rows) + 1.3))
    for row, (label, declared, kept, reasons, *rest) in enumerate(rows):
        chosen = rest[0] if rest else None
        y = len(rows) - 1 - row
        ax.text(-0.3, y + 0.4, label, ha="right", va="center", fontsize=9)
        for column, value in enumerate(declared):
            alive = value in kept
            face = (CHOSEN if value == chosen else FILL) if alive else EXCLUDED
            ax.add_patch(Rectangle((column, y), 0.9, 0.8, facecolor=face,
                                   edgecolor=EDGE, linewidth=0.7))
            ax.text(column + 0.45, y + 0.5, str(value), ha="center", va="center", fontsize=8)
            if not alive and value in reasons:
                ax.text(column + 0.45, y + 0.14, reasons[value], ha="center", va="center",
                        fontsize=5.5, color="#8a2f2f")
    ax.set_xlim(-2.4, width + 0.2)
    ax.set_ylim(-0.3, len(rows))
    ax.axis("off")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_window_catalog(
    entries: Sequence[Tuple[str, Sequence[int]]],
    operations: int,
    title: str,
) -> None:
    """Which operations each query releases: one row per query, one column per op.

    Rows are ``(label, window)`` in the order the controller would ask them.
    A filled cell is an operation whose issue time (and result address) the query
    may change; every blank cell stays exactly where the incumbent put it.
    """

    palette = ["#cfe3f3", "#dfe8d5", "#f3e2cf", "#e3d5ef", "#d5eeee"]
    tags: Dict[str, str] = {}
    fig, ax = plt.subplots(figsize=(0.36 * operations + 4.2, 0.3 * len(entries) + 1.3))
    for row, (label, window) in enumerate(entries):
        tag = label.split(" ")[0]
        colour = tags.setdefault(tag, palette[len(tags) % len(palette)])
        for op in range(operations):
            inside = op in window
            ax.add_patch(Rectangle((op, row), 1, 1, linewidth=0.5, edgecolor="white",
                                   facecolor=colour if inside else EMPTY))
            if inside:
                ax.add_patch(Rectangle((op, row), 1, 1, linewidth=0.5, edgecolor=EDGE,
                                       facecolor="none"))
        ax.text(-0.3, row + 0.5, label, ha="right", va="center", fontsize=7)
    for op in range(operations):
        ax.text(op + 0.5, -0.4, str(op), ha="center", va="center", fontsize=6.5,
                color="#6b7684")
    ax.set_xlim(-9.0, operations)
    ax.set_ylim(len(entries), -1)
    ax.axis("off")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_index_scores(
    bits: int,
    scores: Dict[int, float],
    title: str,
    outlined: Optional[Dict[str, Iterable[int]]] = None,
    per_row: int = 32,
) -> None:
    """Every code of a bit universe shaded by a score in [0, 1], with outlined sets.

    ``scores`` gives the score of each code (codes absent are drawn blank; an
    empty mapping draws membership outlines only, without a colour bar).
    ``outlined`` maps a legend label to a set of codes drawn with a coloured
    outline -- the training elites, say, or the unseen test objects.
    """

    outline_colours = ["#2e6b2a", "#b24a4a", "#1b3a4b", "#b27a1b"]
    outlined = {label: set(codes) for label, codes in (outlined or {}).items()}
    size = 1 << bits
    rows = (size + per_row - 1) // per_row
    columns = min(size, per_row)
    cmap = plt.get_cmap("Blues")
    fig, ax = plt.subplots(figsize=(0.34 * columns + 2.4, 0.34 * rows + 1.6))
    for code in range(size):
        row, column = divmod(code, per_row)
        score = scores.get(code)
        colour = EMPTY if score is None else cmap(0.12 + 0.8 * score)
        ax.add_patch(Rectangle((column, row), 1, 1, linewidth=0.5, edgecolor="white",
                               facecolor=colour))
        for index, (label, codes) in enumerate(outlined.items()):
            if code in codes:
                inset = 0.08 + 0.1 * index
                ax.add_patch(Rectangle((column + inset, row + inset), 1 - 2 * inset,
                                       1 - 2 * inset, linewidth=1.3, facecolor="none",
                                       edgecolor=outline_colours[index % 4]))
    handles = [Rectangle((0, 0), 1, 1, facecolor="none", edgecolor=outline_colours[i % 4],
                         linewidth=1.3) for i in range(len(outlined))]
    if handles:
        ax.legend(handles, list(outlined), fontsize=7.5, loc="lower center",
                  bbox_to_anchor=(0.5, -0.12 - 0.5 / max(rows, 1)), ncol=len(handles),
                  frameon=False)
    if scores:
        mappable = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
        fig.colorbar(mappable, ax=ax, fraction=0.025, pad=0.02, label="predicted score")
    for code in range(size):
        row, column = divmod(code, per_row)
        ax.text(column + 0.5, row + 0.5, str(code), ha="center", va="center", fontsize=4.5,
                color="#6b7684")
    ax.set_xlim(0, columns)
    ax.set_ylim(0, rows)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_bars(
    labels: Sequence[str],
    values: Sequence[float],
    title: str,
    ylabel: str,
    reference: Optional[Tuple[str, float]] = None,
    fmt: str = "{:.3g}",
    log: bool = False,
) -> None:
    """Plain bars with the value printed on each, and an optional reference line."""

    fig, ax = plt.subplots(figsize=(max(5.0, 1.1 * len(labels) + 2.2), 3.4))
    ax.bar(range(len(labels)), values, color=FILL, edgecolor=EDGE)
    for index, value in enumerate(values):
        ax.text(index, value, fmt.format(value), ha="center", va="bottom", fontsize=8)
    if reference is not None:
        ax.axhline(reference[1], color="#b24a4a", linewidth=1.0, linestyle="--")
        ax.text(len(labels) - 0.5, reference[1], reference[0], ha="right", va="bottom",
                fontsize=8, color="#b24a4a")
    if log:
        ax.set_yscale("log")
    ax.set_xticks(range(len(labels)), labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_ratio_intervals(
    rows: Sequence[Tuple[str, float, float, float, Optional[float]]],
    title: str,
    xlabel: str = "ratio candidate / control   (< 1: candidate is lower)",
) -> None:
    """Ratios with their intervals, each against its own registered gate.

    A row is ``(label, point, low, high, gate)``, read from frozen evidence. The
    line at 1 is "no difference"; the dashed mark on a row is the ceiling its
    upper bound had to stay under, so a reader sees the margin, not a verdict.
    """

    fig, ax = plt.subplots(figsize=(7.4, 0.75 * len(rows) + 1.5))
    for index, (label, point, low, high, gate) in enumerate(rows):
        ax.plot([low, high], [index, index], color=EDGE, linewidth=2.2)
        ax.plot([point], [index], "o", color=EDGE)
        ax.text(high, index + 0.18, f"  {point:.3f} [{low:.3f}, {high:.3f}]", fontsize=8,
                va="bottom")
        if gate is not None:
            ax.plot([gate, gate], [index - 0.3, index + 0.3], color="#b24a4a",
                    linestyle="--", linewidth=1.2)
            ax.text(gate, index - 0.32, f"gate {gate:g}", color="#b24a4a", fontsize=7,
                    ha="center", va="top")
    ax.axvline(1.0, color=DEAD, linewidth=1.0)
    ax.set_yticks(range(len(rows)), [row[0] for row in rows], fontsize=8)
    ax.set_ylim(-0.8, len(rows) - 0.3)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()


def show_ratio_scatter(
    points: Sequence[Tuple[float, float, str]],
    title: str,
    xlabel: str,
    ylabel: str = "ratio candidate / control",
    reference: Optional[Tuple[str, float]] = None,
) -> None:
    """One dot per unit (``x``, ``ratio``, group), log x, with the line at 1.

    Groups are coloured in order of first appearance. ``reference`` adds a named
    horizontal line (for example the pooled estimate). The caller computes every
    value; this function only places them.
    """

    palette = ["#5d8fb3", "#b24a4a", "#6aa36f", "#c49a3a", "#8a6bb5", "#7a7f87"]
    groups: List[str] = []
    for _, _, group in points:
        if group not in groups:
            groups.append(group)
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for index, group in enumerate(groups):
        xs = [x for x, _, g in points if g == group]
        ys = [y for _, y, g in points if g == group]
        ax.scatter(xs, ys, s=16, alpha=0.75, color=palette[index % len(palette)], label=group)
    ax.axhline(1.0, color=DEAD, linewidth=1.0)
    if reference is not None:
        ax.axhline(reference[1], color="#b24a4a", linestyle="--", linewidth=1.0)
        ax.text(max(x for x, _, _ in points), reference[1],
                f"{reference[0]} ", color="#b24a4a", fontsize=8, ha="right", va="bottom")
    ax.set_xscale("log")
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.legend(fontsize=8, frameon=False, ncol=min(len(groups), 5))
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    plt.show()
