"""Replay a compilation cycle by cycle, keeping every intermediate state.

``machine.run_compilation`` executes a schedule and returns only the final
buffers. To watch the scratchpad and the buffers change tick by tick, the same
walk has to be performed while recording what each cycle did.

Why this is not simply a call into the owner
--------------------------------------------
``machine.py`` is the owner of execution and it is **frozen** -- the challenge
brief forbids modifying it -- so it cannot be enriched with a hook, and it
exposes no per-cycle entry point. Prefix replay is not available either, because
``run_compilation`` calls ``check_compilation`` first and a truncated schedule is
rejected as incomplete.

What is duplicated here is therefore the *bookkeeping loop* and nothing else.
Every opcode's meaning still comes from the owner: ``machine._evaluate``
computes each result, ``machine.OP_SPECS`` supplies latencies and argument
kinds, and ``machine.STORE_OPS``, ``machine.VLEN`` and ``machine.SCRATCH_WORDS``
are imported rather than restated. No arithmetic is reimplemented.

The guard against drift is parity, checked on every single call: ``replay``
finishes by running ``machine.run_compilation`` on the same inputs and raising
if the two disagree on any buffer. A trace that has diverged from the validator
cannot be drawn, so a figure built from it cannot teach something the validator
would reject.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
for _entry in (str(ROOT / ".reference"), str(ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import machine  # noqa: E402  -- the frozen owner of execution semantics

import common  # noqa: E402  -- the owner of the greedy list scheduler


__all__ = ["CycleState", "TraceMismatch", "replay",
           "QueueEntry", "ListStep", "replay_list_schedule"]


class TraceMismatch(AssertionError):
    """The replay disagreed with ``machine.run_compilation``."""


@dataclass
class CycleState:
    """Everything one cycle did, and the state it left behind."""

    cycle: int
    issued: Dict[str, List[int]] = field(default_factory=dict)
    landed: List[Tuple[str, List[int]]] = field(default_factory=list)
    stored: List[Tuple[str, int, List[int]]] = field(default_factory=list)
    scratch: List[int] = field(default_factory=list)
    memory: Dict[str, List[int]] = field(default_factory=dict)

    @property
    def issued_ids(self) -> List[int]:
        return sorted(op_id for ids in self.issued.values() for op_id in ids)


def replay(program: dict, compilation: dict, case: dict) -> List[CycleState]:
    """Execute the schedule, recording the state left by every cycle.

    Mirrors ``machine.run_compilation`` step for step: pending writes commit at
    the start of a cycle, operands are read after that, and stores to main
    memory are collected and applied at the end of the cycle.
    """

    machine.check_compilation(program, compilation)
    machine.validate_case(program, case)

    memory = {name: [machine.u32(word) for word in words]
              for name, words in case.items()}
    scratch = [0] * machine.SCRATCH_WORDS
    allocations = compilation["scratch"]
    operations = program["operations"]
    pending: Dict[int, List[Tuple[str, int, List[int]]]] = {}

    states: List[CycleState] = []

    for cycle, bundle in enumerate(compilation["bundles"]):
        state = CycleState(cycle=cycle,
                           issued={engine: list(ids) for engine, ids in bundle.items()})

        # Writes commit at the beginning of a cycle, before any operand is read.
        for name, base, words in pending.pop(cycle, []):
            scratch[base : base + len(words)] = words
            state.landed.append((name, list(words)))

        memory_writes: List[Tuple[str, int, List[int]]] = []
        for op_ids in bundle.values():
            for op_id in op_ids:
                operation = operations[op_id]
                opcode = operation["op"]
                arg_values = []
                for name, kind in zip(operation.get("args", []),
                                      machine.OP_SPECS[opcode]["args"]):
                    base = allocations[name]
                    width = machine.VLEN if kind == "vector" else 1
                    words = scratch[base : base + width]
                    arg_values.append(words if kind == "vector" else words[0])

                if opcode in machine.STORE_OPS:
                    words = (arg_values[0] if opcode == "vstore"
                             else [arg_values[0]])
                    memory_writes.append(
                        (operation["buffer"], operation["offset"], list(words)))
                    continue

                result = machine._evaluate(opcode, arg_values, operation, memory)
                words = result if isinstance(result, list) else [result]
                ready = cycle + machine.OP_SPECS[opcode]["latency"]
                pending.setdefault(ready, []).append(
                    (operation["dest"], allocations[operation["dest"]], list(words)))

        for buffer, offset, words in memory_writes:
            memory[buffer][offset : offset + len(words)] = words
            state.stored.append((buffer, offset, list(words)))

        state.scratch = list(scratch)
        state.memory = {name: list(words) for name, words in memory.items()}
        states.append(state)

    # Parity with the owner, on every call. A diverged trace is never returned.
    official = machine.run_compilation(program, compilation, case)
    if states:
        replayed = states[-1].memory
    else:
        replayed = {name: list(words) for name, words in memory.items()}
    if replayed != official:
        raise TraceMismatch(
            "replay disagrees with machine.run_compilation: "
            f"replay={replayed} official={official}"
        )
    return states


# --------------------------------------------------------------------------
# The greedy list scheduler, decision by decision
# --------------------------------------------------------------------------
#
# ``common.classical_compile`` owns the greedy baseline, and its bytes are
# pinned by SHA-256 in ``compare_direct.py`` because the comparison evidence was
# measured against them. It therefore cannot be enriched with a hook either. As
# with ``replay`` above, only the bookkeeping loop is repeated here, so that the
# ready queue of every cycle can be kept; the dependency graph comes from
# ``common.dependencies`` and the slot limits from ``machine.ENGINE_LIMITS``.
# The guard is the same: the finished schedule must equal the one the owner
# returns, or nothing is returned at all.


@dataclass
class QueueEntry:
    """One operation in a cycle's ready queue, and what the rule did with it."""

    op_id: int
    opcode: str
    engine: str
    priority: int      # longest latency-weighted path from this op to the end
    fanout: int        # number of direct consumers, the first tie-break
    placed: bool       # False means its engine's slots were already full


@dataclass
class ListStep:
    """One cycle of the greedy scheduler."""

    cycle: int
    queue: List[QueueEntry]          # ready operations, in priority order
    waiting: List[int]               # pending operations whose inputs are not ready
    used: Dict[str, int]             # slots taken per engine after this cycle


def replay_list_schedule(program: dict) -> Tuple[List[ListStep], dict]:
    """Run the critical-path list scheduler, keeping every cycle's ready queue.

    Returns the steps and the compilation ``common.classical_compile`` produced.
    Raises ``TraceMismatch`` if the replayed issue cycles differ from the
    owner's, which includes the case where the owner fell back to the serial
    schedule.
    """

    ops = program["operations"]
    preds = common.dependencies(program)
    successors: List[List[Tuple[int, int]]] = [[] for _ in ops]
    for i, ps in enumerate(preds):
        for p, lag in ps.items():
            successors[p].append((i, lag))
    heights = [0] * len(ops)
    for i in reversed(range(len(ops))):
        heights[i] = max((lag + heights[j] for j, lag in successors[i]), default=0)

    times: Dict[int, int] = {}
    pending, cycle = set(range(len(ops))), 0
    steps: List[ListStep] = []
    while pending:
        ready = [i for i in pending if all(p in times and times[p] + lag <= cycle
                                          for p, lag in preds[i].items())]
        used = dict.fromkeys(machine.ENGINE_LIMITS, 0)
        queue: List[QueueEntry] = []
        for i in sorted(ready, key=lambda i: (-heights[i], -len(successors[i]), i)):
            engine = machine.OP_SPECS[ops[i]["op"]]["engine"]
            placed = used[engine] < machine.ENGINE_LIMITS[engine]
            if placed:
                times[i] = cycle
                pending.remove(i)
                used[engine] += 1
            queue.append(QueueEntry(i, ops[i]["op"], engine, heights[i],
                                    len(successors[i]), placed))
        steps.append(ListStep(cycle, queue,
                              sorted(pending - set(ready)),
                              {e: n for e, n in used.items() if n}))
        cycle += 1

    compiled = common.classical_compile(program)
    if common.issue_times(compiled) != times:
        raise TraceMismatch(
            "replay disagrees with common.classical_compile: "
            f"replay={times} official={common.issue_times(compiled)}"
        )
    return steps, compiled
