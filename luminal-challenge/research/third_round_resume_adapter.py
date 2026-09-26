"""R_adapter: the minimal real C1 adapter operations, timed on the frozen M0 workloads.

``ADAPTER_SPEC.json`` (resume run) fixes what is timed. Per row (one fresh
process, one frozen workload): an UNTIMED shared-kernel pass produces the BS1
state of every event (BS1 class bodies unchanged); then ONE cold timed pass
performs, per event and through one bound adapter method, the operations C1 adds
to R0's expander: reading the parent node's state reference and its domains,
constructing the ``efficiency_search._Node`` that holds the new state reference,
pushing it on the query frontier, and releasing nodes when their parent's
expansion ends (streaming, no last-use knowledge) and at query end.

No search is run and BS1 is not altered. Full ``_Node`` construction is timed
although R0 builds the same nodes: an upper bound on the additional work.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

from research import efficiency_search as es
from research import optimization_common as oc
from research import third_round_common as tc
from research import third_round_kernel as tk
from research import third_round_resume_common as rc
from research import third_round_workload as tw

STAGE = rc.ADAPTER_STAGE


def collect_states(prepared: dict) -> List[object]:
    """Untimed: the BS1 output of every event (the same calls as ``replay_shared``)."""

    stats = es.PropagationStats()
    props: Dict[int, tk.SharedPropagation] = {}
    out: List[object] = []
    for event in prepared["events"]:
        kind, ev, index = event[0], event[1], event[2]
        prop = props.get(index)
        if prop is None:
            prop = props[index] = tk.SharedPropagation(prepared["domains"][index], stats)
        if kind == "T":
            parent, d_in, op, value = event[3:]
            result = prop.time_root(d_in) if parent is None else prop.time_child(
                out[parent], op, value)
        elif kind == "P":
            d_ev, a_ev, best = event[3:]
            result = prop.prune_state(out[d_ev], None if a_ev is None else out[a_ev].A, best)
        elif kind == "L":
            result = prop.address_pairs(event[3])
        else:
            parent, pairs_ev, a_in, name, value = event[3:]
            result = prop.address_root(a_in, out[pairs_ev]) if parent is None else \
                prop.address_child(out[parent], name, value)
        out.append(result)
    return out


class Adapter:
    """The C1 call-site indirection: one bound method per event kind."""

    __slots__ = ("nodes", "frontier", "expanding", "reads")

    def __init__(self) -> None:
        self.nodes: Dict[int, Dict[int, object]] = {}    # per query: event -> node
        self.frontier: Dict[int, list] = {}
        self.expanding: Dict[int, int] = {}
        self.reads = 0

    def _expand(self, index: int, parent: int) -> object:
        nodes = self.nodes[index]
        current = self.expanding.get(index)
        if current != parent:
            if current is not None:
                nodes.pop(current, None)              # the parent's expansion ended
            self.expanding[index] = parent
        return nodes[parent]

    def time_root(self, index: int, ev: int, S) -> None:
        nodes = self.nodes.setdefault(index, {})
        self.frontier.setdefault(index, [])
        if S is None:
            return
        node = es._Node(None, S, None, None, "time", 0, None, (), 0, 0)
        nodes[ev] = node
        self.frontier[index].append(node)

    def time_child(self, index: int, ev: int, parent: int, op: int, S2) -> None:
        pnode = self._expand(index, parent)
        state = pnode.D
        self.reads += len(state.D[op])               # allowed = set(node.D.D[op])
        if S2 is None:
            return
        node = es._Node(None, S2, None, None, "time", pnode.position + 1, None, pnode.ranks,
                        pnode.disc, 0)
        self.nodes[index][ev] = node
        self.frontier[index].append(node)

    def prune(self, index: int, S, AS) -> None:
        state = S                                    # prune_state(node.D, AS.A, best)
        if AS is not None:
            self.reads += len(AS.A)
        self.reads += len(state.D)

    def address_root(self, index: int, ev: int, S, AS, pairs) -> None:
        self.nodes.setdefault(index, {})
        self.frontier.setdefault(index, [])
        if AS is None:
            return
        self.reads += len(AS.A)
        node = es._Node(None, S, AS, pairs, "address", 0, (), (), 0, 0)
        self.nodes[index][ev] = node
        self.frontier[index].append(node)

    def address_child(self, index: int, ev: int, parent: int, name: str, AS2) -> None:
        pnode = self._expand(index, parent)
        self.reads += len(pnode.A.A[name])            # allowed = set(node.A.A[name])
        if AS2 is None:
            return
        self.reads += len(AS2.A)
        node = es._Node(None, pnode.D, AS2, pnode.pairs, "address", pnode.position + 1,
                        pnode.order, pnode.ranks, pnode.disc, 0)
        self.nodes[index][ev] = node
        self.frontier[index].append(node)

    def dispose(self) -> None:
        for index in list(self.nodes):               # epoch / query disposal
            self.nodes[index].clear()
            self.frontier[index].clear()
        self.nodes.clear()
        self.frontier.clear()


def timed_adapter(prepared: dict, states: List[object]) -> float:
    events = prepared["events"]
    last_d: Dict[int, object] = {}
    started = time.perf_counter()
    adapter = Adapter()
    for event in events:
        kind, ev, index = event[0], event[1], event[2]
        if kind == "T":
            if event[3] is None:
                adapter.time_root(index, ev, states[ev])
            else:
                adapter.time_child(index, ev, event[3], event[5], states[ev])
            last_d[index] = states[ev]
        elif kind == "P":
            d_ev, a_ev = event[3], event[4]
            adapter.prune(index, states[d_ev], None if a_ev is None else states[a_ev])
        elif kind == "A":
            if event[3] is None:
                adapter.address_root(index, ev, last_d.get(index), states[ev],
                                     states[event[4]])
            else:
                adapter.address_child(index, ev, event[3], event[6], states[ev])
    adapter.dispose()
    del adapter
    return time.perf_counter() - started


def worker(spec: dict) -> dict:
    raw = gzip.decompress(Path(spec["workload_path"]).read_bytes())
    if oc.sha256_bytes(raw) != spec["workload_sha256"]:
        raise RuntimeError("workload differs from the frozen manifest")
    prepared = tw.prepare(json.loads(raw))
    states = collect_states(prepared)
    seconds = timed_adapter(prepared, states)
    return {"family": tc.family_of(spec["seed"]), "adapter_seconds": seconds,
            "events": len(prepared["events"])}


def specs() -> list:
    manifest = json.loads((rc.PARENT_RUN / "WORKLOAD_MANIFEST.json").read_text())
    out = []
    for seed_text, item in sorted(manifest["workloads"].items()):
        for rep in range(3):
            out.append({"stage_id": STAGE, "program_sha256": item["program_sha256"],
                        "seed": int(seed_text), "repetition": rep, "arm_id": "adapter",
                        "mode_key": "adapter", "workload_path": item["path"],
                        "workload_sha256": item["sha256"]})
    return rc.ordered(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec")
    parser.add_argument("--run")
    args = parser.parse_args(argv)
    if args.spec:
        sys.stdout.write(json.dumps(worker(json.loads(args.spec)), sort_keys=True) + "\n")
        return 0
    plan = specs()
    if len(plan) != rc.ADAPTER_ROWS:
        raise RuntimeError(f"{len(plan)} specs, expected {rc.ADAPTER_ROWS}")
    report = rc.run_stage(Path(args.run), STAGE, plan, "research.third_round_resume_adapter")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
