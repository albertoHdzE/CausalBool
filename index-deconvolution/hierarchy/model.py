"""HID-v1 rule and DAG types: immutable, validated, no data generation.

Two representations of one object:

* ``Model`` -- the transmitted form: a tuple of rule records whose references
  point to strictly earlier records, root last (wire annex W3). This is what
  ``wire.serialize_model`` writes.
* ``Node`` -- the search form: hash-consed rule nodes that refer to child
  ``Node`` objects. Structurally identical nodes are the same object inside one
  ``NodeFactory``, so replacing a node replaces every occurrence of it (the
  joint change the protocol requires). ``to_model`` numbers a node graph in
  deterministic depth-first postorder; ``share=False`` writes one record per
  occurrence (the flat ablation forbids cross-child sharing).

The evaluator here (``Model.expand``/``NodeFactory.expand``) is the ENCODER's
evaluator. The independent decoder in decode.py does not use it.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import codes as C


class ModelError(ValueError):
    """A rule or model violates the W3 constraints."""


def _nat(name: str, v, minimum: int = 0) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ModelError(f"{name} must be an int (bool excluded), got {type(v).__name__}")
    if v < minimum or v > C.MAX_U:
        raise ModelError(f"{name}={v} outside [{minimum}, 2^63-1]")
    return v


def check_bits(bits) -> str:
    """Strict library bit-string check: ``str`` of 0/1 only, no stripping."""
    if type(bits) is not str:
        raise TypeError(f"bit string must be str, got {type(bits).__name__}")
    if bits.strip("01"):
        raise ValueError("bit string may contain only the characters '0' and '1'")
    return bits


# ---------------------------------------------------------------------------
# Transmitted rule records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Literal:
    bits: str

    def __post_init__(self):
        check_bits(self.bits)
        if not self.bits:
            raise ModelError("LITERAL must be nonempty")

    op = C.OP_LITERAL

    def refs(self) -> tuple[int, ...]:
        return ()


@dataclass(frozen=True)
class Concat:
    children: tuple[int, ...]

    def __post_init__(self):
        if len(self.children) < 2:
            raise ModelError("CONCAT arity must be >= 2")
        for c in self.children:
            _nat("child_id", c)

    op = C.OP_CONCAT

    def refs(self) -> tuple[int, ...]:
        return self.children


@dataclass(frozen=True)
class Repeat:
    child: int
    copies: int

    def __post_init__(self):
        _nat("child_id", self.child)
        _nat("copies", self.copies, 2)

    op = C.OP_REPEAT

    def refs(self) -> tuple[int, ...]:
        return (self.child,)


@dataclass(frozen=True)
class APUnion:
    length: int
    foreground: int
    aps: tuple[tuple[int, int, int], ...]

    def __post_init__(self):
        _nat("length", self.length, 1)
        if self.foreground not in (0, 1) or isinstance(self.foreground, bool):
            raise ModelError("foreground must be 0 or 1")
        prev = None
        for t in self.aps:
            start, step, count = t
            _nat("start", start)
            _nat("step", step, 1)
            _nat("count", count, 1)
            if count > self.length or start + (count - 1) * step >= self.length:
                raise ModelError(f"AP {t} leaves the domain of length {self.length}")
            if prev is not None and not prev < t:
                raise ModelError("AP entries must be strictly sorted, no duplicates")
            prev = t

    op = C.OP_AP_UNION

    def refs(self) -> tuple[int, ...]:
        return ()


@dataclass(frozen=True)
class SchemaUnion:
    length: int
    foreground: int
    pairs: tuple[tuple[int, int], ...]

    def __post_init__(self):
        _nat("length", self.length, 1)
        if self.foreground not in (0, 1) or isinstance(self.foreground, bool):
            raise ModelError("foreground must be 0 or 1")
        d = (self.length - 1).bit_length()
        prev = None
        for t in self.pairs:
            mask, value = t
            _nat("fixed_mask", mask)
            _nat("fixed_value", value)
            if mask >> d:
                raise ModelError(f"mask {mask} uses coordinates beyond d={d}")
            if value & ~mask:
                raise ModelError("fixed_value has bits outside fixed_mask")
            if value >= self.length:
                raise ModelError(f"schema {t} matches no address below {self.length}")
            if prev is not None and not prev < t:
                raise ModelError("schema pairs must be strictly sorted, no duplicates")
            prev = t

    op = C.OP_SCHEMA_UNION

    def refs(self) -> tuple[int, ...]:
        return ()


@dataclass(frozen=True)
class Patch:
    child: int
    positions: tuple[int, ...]

    def __post_init__(self):
        _nat("child_id", self.child)
        if not self.positions:
            raise ModelError("PATCH needs q_flip >= 1")
        prev = -1
        for p in self.positions:
            _nat("position", p)
            if p <= prev:
                raise ModelError("PATCH positions must be strictly increasing")
            prev = p

    op = C.OP_PATCH

    def refs(self) -> tuple[int, ...]:
        return (self.child,)


@dataclass(frozen=True)
class Xform:
    child: int
    flags: int
    rotation: int

    def __post_init__(self):
        _nat("child_id", self.child)
        _nat("flags", self.flags)
        _nat("right_rotation", self.rotation)
        if self.flags & ~3:
            raise ModelError("XFORM flags may use bits 0 and 1 only")
        if self.flags == 0 and self.rotation == 0:
            raise ModelError("XFORM flags=0, r=0 is an identity record")

    op = C.OP_XFORM

    def refs(self) -> tuple[int, ...]:
        return (self.child,)


Rule = Literal | Concat | Repeat | APUnion | SchemaUnion | Patch | Xform


# ---------------------------------------------------------------------------
# Semantics shared by both evaluators on the ENCODER side
# ---------------------------------------------------------------------------

def apply_xform(s: str, flags: int, rotation: int) -> str:
    """Complement, then reversal, then right circular rotation by ``rotation``."""
    if flags & C.XFORM_COMPLEMENT:
        s = s.translate(_COMPLEMENT)
    if flags & C.XFORM_REVERSE:
        s = s[::-1]
    if rotation:
        s = s[-rotation:] + s[:-rotation]
    return s


_COMPLEMENT = str.maketrans("01", "10")


def ap_string(length: int, fg: int, aps) -> str:
    out = bytearray(b"01"[1 - fg:2 - fg] * length)
    mark = 48 + fg
    for start, step, count in aps:
        out[start:start + (count - 1) * step + 1:step] = bytes([mark]) * count
    return out.decode("ascii")


def schema_string(length: int, fg: int, pairs) -> str:
    out = bytearray(b"01"[1 - fg:2 - fg] * length)
    mark = 48 + fg
    d = (length - 1).bit_length()
    full = (1 << d) - 1
    for mask, value in pairs:
        free = full & ~mask
        sub = free
        while True:                       # every filling of the free coordinates
            i = value | sub
            if i < length:
                out[i] = mark
            if sub == 0:
                break
            sub = (sub - 1) & free
    return out.decode("ascii")


def patch_string(s: str, positions) -> str:
    out = bytearray(s.encode("ascii"))
    for p in positions:
        out[p] ^= 1                       # '0' (48) <-> '1' (49)
    return out.decode("ascii")


# ---------------------------------------------------------------------------
# Model: the transmitted DAG
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Model:
    rules: tuple

    def __post_init__(self):
        if not self.rules:
            raise ModelError("a model needs q >= 1 rules")
        for i, r in enumerate(self.rules):
            if not isinstance(r, (Literal, Concat, Repeat, APUnion, SchemaUnion, Patch, Xform)):
                raise ModelError(f"rule {i} is not a rule record")
            for c in r.refs():
                if c >= i:
                    raise ModelError(f"rule {i} references {c}, not strictly earlier")
        lengths = self.lengths()
        for i, r in enumerate(self.rules):
            if isinstance(r, Patch) and r.positions[-1] >= lengths[r.child]:
                raise ModelError(f"PATCH {i} position beyond child length")
            if isinstance(r, Xform) and r.rotation >= lengths[r.child]:
                raise ModelError(f"XFORM {i} rotation >= child length")
        reach = [False] * len(self.rules)
        reach[-1] = True
        for i in range(len(self.rules) - 1, -1, -1):
            if reach[i]:
                for c in self.rules[i].refs():
                    reach[c] = True
        if not all(reach):
            raise ModelError(f"unreachable rules {[i for i, ok in enumerate(reach) if not ok]}")

    @property
    def root(self) -> int:
        return len(self.rules) - 1

    def lengths(self) -> list[int]:
        out: list[int] = []
        for r in self.rules:
            if isinstance(r, Literal):
                out.append(len(r.bits))
            elif isinstance(r, Concat):
                out.append(sum(out[c] for c in r.children))
            elif isinstance(r, Repeat):
                out.append(out[r.child] * r.copies)
            elif isinstance(r, (APUnion, SchemaUnion)):
                out.append(r.length)
            else:
                out.append(out[r.child])
        return out

    def depth(self) -> int:
        dep: list[int] = []
        for r in self.rules:
            dep.append(1 + max((dep[c] for c in r.refs()), default=0))
        return dep[-1]

    def expand(self) -> str:
        return self.expansions()[-1]

    def expansions(self) -> list[str]:
        """Expanded string of every rule, in id order (encoder-side evaluator)."""
        vals: list[str] = []
        for r in self.rules:
            if isinstance(r, Literal):
                vals.append(r.bits)
            elif isinstance(r, Concat):
                vals.append("".join(vals[c] for c in r.children))
            elif isinstance(r, Repeat):
                vals.append(vals[r.child] * r.copies)
            elif isinstance(r, APUnion):
                vals.append(ap_string(r.length, r.foreground, r.aps))
            elif isinstance(r, SchemaUnion):
                vals.append(schema_string(r.length, r.foreground, r.pairs))
            elif isinstance(r, Patch):
                vals.append(patch_string(vals[r.child], r.positions))
            else:
                vals.append(apply_xform(vals[r.child], r.flags, r.rotation))
        return vals


# ---------------------------------------------------------------------------
# Node: the search form (hash-consed)
# ---------------------------------------------------------------------------

class Node:
    """An interned rule node. Create only through ``NodeFactory``."""

    __slots__ = ("op", "args", "length", "uid", "depth", "children")

    def __repr__(self) -> str:
        return f"Node#{self.uid}({C.OP_NAMES[self.op]}, len={self.length})"


class NodeFactory:
    """Interns nodes so that structural identity is object identity.

    Interning is by STRUCTURE (opcode, fields, child identities), never by
    expanded output: two different descriptions of one substring stay distinct
    until their complete archives are compared.
    """

    def __init__(self) -> None:
        self._table: dict[tuple, Node] = {}
        self._exp: dict[int, str] = {}

    def __len__(self) -> int:
        return len(self._table)

    def _make(self, op: int, args: tuple, children: tuple, length: int) -> Node:
        key = (op,) + tuple(a.uid if isinstance(a, Node) else a for a in args)
        if op == C.OP_CONCAT:
            key = (op, tuple(c.uid for c in args[0]))
        node = self._table.get(key)
        if node is None:
            node = Node()
            node.op, node.args, node.length = op, args, length
            node.children = children
            node.depth = 1 + max((c.depth for c in children), default=0)
            node.uid = len(self._table)
            self._table[key] = node
        return node

    def literal(self, bits: str) -> Node:
        Literal(bits)
        return self._make(C.OP_LITERAL, (bits,), (), len(bits))

    def concat(self, children) -> Node:
        children = tuple(children)
        if len(children) == 1:
            return children[0]
        if len(children) < 2:
            raise ModelError("CONCAT arity must be >= 2")
        return self._make(C.OP_CONCAT, (children,), children,
                          sum(c.length for c in children))

    def repeat(self, child: Node, copies: int) -> Node:
        if copies == 1:
            return child
        Repeat(0, copies)
        return self._make(C.OP_REPEAT, (child, copies), (child,), child.length * copies)

    def ap_union(self, length: int, fg: int, aps) -> Node:
        aps = tuple(sorted(set(aps)))
        APUnion(length, fg, aps)
        return self._make(C.OP_AP_UNION, (length, fg, aps), (), length)

    def schema_union(self, length: int, fg: int, pairs) -> Node:
        pairs = tuple(sorted(set(pairs)))
        SchemaUnion(length, fg, pairs)
        return self._make(C.OP_SCHEMA_UNION, (length, fg, pairs), (), length)

    def patch(self, child: Node, positions) -> Node:
        positions = tuple(positions)
        if not positions:
            return child
        Patch(0, positions)
        if positions[-1] >= child.length:
            raise ModelError("PATCH position beyond child length")
        return self._make(C.OP_PATCH, (child, positions), (child,), child.length)

    def xform(self, child: Node, flags: int, rotation: int) -> Node:
        Xform(0, flags, rotation)
        if rotation >= child.length:
            raise ModelError("XFORM rotation >= child length")
        return self._make(C.OP_XFORM, (child, flags, rotation), (child,), child.length)

    # -- evaluation (encoder side) -------------------------------------------

    def expand(self, node: Node) -> str:
        memo = self._exp
        if node.uid in memo:
            return memo[node.uid]
        stack = [node]
        while stack:
            top = stack[-1]
            if top.uid in memo:
                stack.pop()
                continue
            pending = [c for c in top.children if c.uid not in memo]
            if pending:
                stack.extend(pending)
                continue
            stack.pop()
            op, a = top.op, top.args
            if op == C.OP_LITERAL:
                v = a[0]
            elif op == C.OP_CONCAT:
                v = "".join(memo[c.uid] for c in a[0])
            elif op == C.OP_REPEAT:
                v = memo[a[0].uid] * a[1]
            elif op == C.OP_AP_UNION:
                v = ap_string(*a)
            elif op == C.OP_SCHEMA_UNION:
                v = schema_string(*a)
            elif op == C.OP_PATCH:
                v = patch_string(memo[a[0].uid], a[1])
            else:
                v = apply_xform(memo[a[0].uid], a[1], a[2])
            memo[top.uid] = v
        return memo[node.uid]

    def rebuild(self, root: Node, mapping: dict[int, Node]) -> Node:
        """Return ``root`` with every node whose uid is in ``mapping`` replaced.

        All occurrences are replaced together, since an interned node is one
        object wherever it appears.
        """
        done: dict[int, Node] = {}
        stack = [root]
        while stack:
            top = stack[-1]
            if top.uid in done:
                stack.pop()
                continue
            if top.uid in mapping:
                done[top.uid] = mapping[top.uid]
                stack.pop()
                continue
            pending = [c for c in top.children if c.uid not in done]
            if pending:
                stack.extend(pending)
                continue
            stack.pop()
            op, a = top.op, top.args
            if not top.children:
                new = top
            elif op == C.OP_CONCAT:
                kids = [done[c.uid] for c in a[0]]
                new = top if all(k is c for k, c in zip(kids, a[0])) else self.concat(kids)
            elif op == C.OP_REPEAT:
                k = done[a[0].uid]
                new = top if k is a[0] else self.repeat(k, a[1])
            elif op == C.OP_PATCH:
                k = done[a[0].uid]
                new = top if k is a[0] else self.patch(k, a[1])
            else:
                k = done[a[0].uid]
                new = top if k is a[0] else self.xform(k, a[1], a[2])
            done[top.uid] = new
        return done[root.uid]


def nodes_postorder(root: Node, share: bool = True) -> list[Node]:
    """Depth-first postorder with ordered child traversal (iterative).

    With ``share=True`` each distinct node appears once (first visit); with
    ``share=False`` once per occurrence.
    """
    out: list[Node] = []
    seen: set[int] = set()
    stack: list[tuple[Node, int]] = [(root, 0)]
    while stack:
        node, i = stack.pop()
        if i == 0 and share and node.uid in seen:
            continue
        if i < len(node.children):
            stack.append((node, i + 1))
            stack.append((node.children[i], 0))
        else:
            if share:
                if node.uid in seen:
                    continue
                seen.add(node.uid)
            out.append(node)
    return out


def to_model(root: Node, share: bool = True) -> Model:
    """Number a node graph in deterministic postorder and return the Model."""
    order = nodes_postorder(root, share)
    rules = []
    if share:
        ids: dict[int, int] = {}
        for node in order:
            rules.append(_record(node, lambda c: ids[c.uid]))
            ids[node.uid] = len(rules) - 1
    else:
        # One record per occurrence. Each frame collects the ids of ITS OWN child
        # copies, so CONCAT(X, X) references two distinct records of X.
        stack: list[tuple[Node, list[int]]] = [(root, [])]
        while True:
            node, kid_ids = stack[-1]
            if len(kid_ids) < len(node.children):
                stack.append((node.children[len(kid_ids)], []))
                continue
            stack.pop()
            it = iter(kid_ids)
            rules.append(_record(node, lambda c: next(it)))
            if not stack:
                break
            stack[-1][1].append(len(rules) - 1)
    return Model(tuple(rules))


def _record(node: Node, idof) -> Rule:
    op, a = node.op, node.args
    if op == C.OP_LITERAL:
        return Literal(a[0])
    if op == C.OP_CONCAT:
        return Concat(tuple(idof(c) for c in a[0]))
    if op == C.OP_REPEAT:
        return Repeat(idof(a[0]), a[1])
    if op == C.OP_AP_UNION:
        return APUnion(*a)
    if op == C.OP_SCHEMA_UNION:
        return SchemaUnion(*a)
    if op == C.OP_PATCH:
        return Patch(idof(a[0]), a[1])
    return Xform(idof(a[0]), a[1], a[2])


def count_reachable(root: Node, share: bool = True) -> int:
    if share:
        return len(nodes_postorder(root, True))
    # Occurrence count of the tree expansion: occ(node) = 1 + sum occ(children).
    occ: dict[int, int] = {}
    for node in nodes_postorder(root, True):                 # children before parents
        occ[node.uid] = 1 + sum(occ[c.uid] for c in node.children)
    return occ[root.uid]
