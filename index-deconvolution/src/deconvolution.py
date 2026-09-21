"""deconvolution.py

Index-set deconvolution for synchronous Boolean networks.

Given only the output repertoire of a network (a ``2**n x n`` binary matrix)
this module recovers, per node, the exact pair ``(I_c, f)`` where ``I_c`` is the
set of connected inputs and ``f`` is the Boolean function on those inputs, and
then names ``f`` with the canonical CausalBool gate family.

Method (see ``bitacora/01_deconvolution_method_design.md`` for the full
derivation).  The forward CausalBool transform factorises over nodes: output
column ``k`` is a function of the connected inputs only, so deconvolution
factorises into independent per-column problems, each solved exactly by:

(This sentence used to add "with the disconnected nodes contributing only the
free offset dimension, whose decimal encoding is the sumandos".  Removed: it
defines the sumandos by the disconnected coordinates, which GLOSSARY sec.1d
forbids -- see the ruling quoted at Step 1 below.  The factorisation over
connected inputs is true and is what this module does; the claim about what the
sumandos ARE is the part that was wrong.)

  1. Essential-variable detection by single-bit perturbation.  Bit ``i`` is a
     connected input of node ``k`` iff flipping bit ``i`` of some input changes
     column ``k``.  Perturbing a disconnected node never changes the output;
     perturbing a connected node can.  This is the exact, deterministic analogue
     of the perturbation step in Zenil's algorithmic-information deconvolution.

  2. Gate identification.  Restrict the column to its essential variables to
     obtain a reduced truth table, then match it against every canonical gate
     signature (searching KOFN and CANALISING parameters).  Because the forward
     method is an exact index-set formula, this inversion is exact and the
     reconstructed network reproduces the repertoire byte for byte.

Node/bit indices are 0-based, matching :mod:`causalbool`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from causalbool import Network, apply_gate, truth_table, repertoire


# ---------------------------------------------------------------------------
# Step 1 - essential-variable detection (connected vs free coordinates)
#
# THREE terminology rulings apply here, and this comment has stated each of them
# only after contradicting it.
#
# GLOSSARY sec.1e, AUTHOR RULING 2026-09-07 -- *PIVOT* IS A FINANCE TERM.  It
# names a specific kind of set there, and it names NOTHING in this method.  This
# comment block itself said "the complement of the PIVOT COORDINATES", which is
# how the word kept its foothold: sec.1c withdrew the pairing and left the word.
# The method's six objects are CONNECTED INPUTS, ESSENTIAL VARIABLES, DECIMAL
# ANCHOR, DECIMAL FAMILY, FREE COORDINATES and SUMANDOS.  One of those six is
# always the word wanted; the seventh does not exist.
#
# GLOSSARY sec.1c -- the complement of the CONNECTED INPUTS is the FREE
# COORDINATES, *not* the sumandos, which are the free coordinates' ENCODING and
# stand parallel to the decimal anchor.  Setting a set opposite an encoding also
# wrongly suggests a lossy split: this factorisation is EXACT, Dec(L,S) = {l+s}
# rebuilds the repertoire, so there is no residual here.  pivot/residual is the
# lossy pair and belongs to causal reachability, not to this method.
#
# GLOSSARY sec.1d, AUTHOR RULING 2026-09-03 -- SUMANDOS ARE NOT "THE
# DISCONNECTED COORDINATES", and this file previously said they were, twice.
#
#   Definition.  The sumandos of a schema are the fillings of ITS OWN DON'T-CARE
#   POSITIONS, wherever those positions fall.  Omega is the offset family they
#   generate.
#
# The disconnected coordinates are free in every schema and are the special case
# always present -- but the special case may be ILLUSTRATED, never DEFINED AS the
# general object.  RULE 110 is the standing counterexample: three inputs, ALL
# THREE CONNECTED.  Under the narrow reading its free coordinates are empty, so
# Omega = {0}, there is no compression and L must list all five minterms.  Under
# the correct reading it is three schemata -- 01*, 10*, *10 -- and every one of
# their don't-cares sits ON A CONNECTED INPUT.  The narrow reading cannot express
# the right one.
#
# This is quantitative, not terminological.  The narrow reading sees compression
# only from disconnected coordinates, so it cannot tell an OR from an XOR of the
# same in-degree -- both are "one gate with n-d free coordinates".  The general
# reading separates them exactly: an OR of in-degree 10 covers 1023 minterms with
# 10 schemata, an XOR of in-degree 10 covers 512 minterms and needs 512, because
# none of its minterms merge.  A measure blind to that is not measuring the
# object, and reading the method this way makes it look trivial when it is not.
#
# Settled and re-adopted FIVE times as of 2026-09-07.  The cause is always the
# same: a reader meets a helper that computes Complement[Range[n], connected] and
# promotes that implementation detail into the definition.  Guarded now by
# tests/analysis/test_sumandos_definition.py.
# ---------------------------------------------------------------------------

def essential_variables(column: list[int], n: int) -> list[int]:
    """Return the ascending list of bit positions on which ``column`` depends.

    Bit ``i`` is essential iff there exists an input ``x`` with
    ``column[x] != column[x ^ (1 << i)]``.  These are exactly the CONNECTED
    INPUTS, and they are what this method calls the node's ESSENTIAL VARIABLES.
    The remaining bits are the FREE COORDINATES.

    Neither set is "the pivot coordinates" (GLOSSARY sec.1e, author ruling
    2026-09-07): *pivot* is a finance term and names nothing here.  This
    docstring used to say it did.

    THE FREE COORDINATES ARE NOT "THE SUMANDOS" (GLOSSARY sec.1d, author ruling
    2026-09-03).  This docstring used to end "their subset sums are the
    sumandos", which defines the general object by its special case.  The
    sumandos of a schema are the fillings of that schema's own don't-care
    positions, wherever those positions fall -- INCLUDING don't-cares on
    connected inputs, which is where all of Rule 110's live.  The disconnected
    coordinates are free in every schema and so are always among them; that is
    an illustration of the definition, not the definition.
    """
    if len(column) != 2 ** n:
        raise ValueError("column length must be 2**n")
    essential = []
    for i in range(n):
        # Create a number with only the i-th bit set (1 shifted left by i positions)
        # Example: if i=2 (0-based, 3rd bit), 1 << 2 = 4 (binary 100)
        # This lets us check if flipping just that one bit changes the output
        bit = 1 << i
        sensitive = False
        for x in range(2 ** n):
            if x & bit:
                continue  # visit each unordered pair once (x has bit i = 0)
            if column[x] != column[x | bit]:
                sensitive = True
                break
        if sensitive:
            essential.append(i)
    return essential


def reduce_column(column: list[int], n: int, essential: list[int]) -> list[int]:
    """Project ``column`` onto its essential variables.

    Returns a length ``2**m`` reduced truth table (``m = len(essential)``),
    enumerated LSB-first over the essential variables in ascending order.
    Raises ``AssertionError`` if the column is not in fact constant across the
    non-essential dimension, which would indicate the essential set is wrong.
    """
    m = len(essential)
    reduced: list[int] = [-1] * (2 ** m)
    for x in range(2 ** n):
        y = 0
        for j, e in enumerate(essential):
            if x & (1 << e):
                y |= (1 << j)
        val = column[x]
        if reduced[y] == -1:
            reduced[y] = val
        else:
            assert reduced[y] == val, (
                "non-essential variable affects output; essential set is wrong"
            )
    assert all(v != -1 for v in reduced)
    return reduced


# ---------------------------------------------------------------------------
# Step 2 - gate identification against the canonical family
# ---------------------------------------------------------------------------

# Canonical priority: simplest / most specific named gates first.  Any match
# reproduces the reduced truth table exactly, so this ordering only selects the
# representative reported as canonical; the full match list records ambiguity.
_CANONICAL_PRIORITY = (
    "AND", "OR", "NAND", "NOR", "XOR", "XNOR",
    "NOT", "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "REGULATORY", "CANALISING",
    "REGULATORY_DNF",
)


def minimal_dnf(reduced: list[int]) -> list[dict]:
    """Cover the on-set of a reduced truth table by regulatory clauses.

    Uses Quine-McCluskey to find the prime implicants and a greedy set cover to
    choose a compact subset.  Each returned clause is a dict with ``activators``
    (variables required to be 1) and ``inhibitors`` (required to be 0); variables
    in neither are don't-care.  The union of the clauses' cosets equals the
    on-set exactly.
    """
    m = (len(reduced)).bit_length() - 1
    minterms = [y for y, v in enumerate(reduced) if v == 1]
    if not minterms:
        return []

    full_mask = (1 << m) - 1
    terms = {(y, full_mask) for y in minterms}  # (fixed bits, fixed mask)
    primes: set[tuple[int, int]] = set()
    while terms:
        merged: set[tuple[int, int]] = set()
        used: set[tuple[int, int]] = set()
        tlist = list(terms)
        for i in range(len(tlist)):
            for j in range(i + 1, len(tlist)):
                b1, mask1 = tlist[i]
                b2, mask2 = tlist[j]
                if mask1 != mask2:
                    continue
                diff = b1 ^ b2
                if diff and (diff & (diff - 1)) == 0 and (diff & mask1):
                    newmask = mask1 & ~diff
                    merged.add((b1 & newmask, newmask))
                    used.add(tlist[i])
                    used.add(tlist[j])
        for t in terms:
            if t not in used:
                primes.add(t)
        terms = merged

    def covers(prime: tuple[int, int], mt: int) -> bool:
        b, mask = prime
        return (mt & mask) == b

    prime_list = list(primes)
    uncovered = set(minterms)
    chosen: list[tuple[int, int]] = []
    while uncovered:
        best = max(prime_list,
                   key=lambda p: sum(1 for mt in uncovered if covers(p, mt)))
        chosen.append(best)
        uncovered = {mt for mt in uncovered if not covers(best, mt)}

    clauses = []
    for b, mask in chosen:
        activators = [j for j in range(m) if (mask >> j) & 1 and (b >> j) & 1]
        inhibitors = [j for j in range(m) if (mask >> j) & 1 and not ((b >> j) & 1)]
        clauses.append({"activators": activators, "inhibitors": inhibitors})
    return clauses


@dataclass
class GateMatch:
    gate: str
    params: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"gate": self.gate, "params": dict(self.params)}


def _candidate_gates(m: int) -> list[GateMatch]:
    """Enumerate all (gate, params) candidates for arity ``m``."""
    cands: list[GateMatch] = []
    if m == 0:
        return cands  # constant handled separately
    for g in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY"):
        cands.append(GateMatch(g))
    if m == 1:
        cands.append(GateMatch("NOT"))
    if m == 2:
        cands.append(GateMatch("IMPLIES"))
        cands.append(GateMatch("NIMPLIES"))
    for k in range(1, m + 1):
        cands.append(GateMatch("KOFN", {"k": k}))
    for ci in range(m):
        for cv in (0, 1):
            for co in (0, 1):
                cands.append(GateMatch(
                    "CANALISING",
                    {"canalisingIndex": ci, "canalisingValue": cv,
                     "canalisedOutput": co},
                ))
    return cands


def identify_gate(reduced: list[int]) -> tuple[list[GateMatch], GateMatch]:
    """Match a reduced truth table against the canonical gate family.

    Returns ``(matches, canonical)`` where ``matches`` is every candidate whose
    truth table equals ``reduced`` (the ambiguity/equivalence class) and
    ``canonical`` is the highest-priority representative.  Handles the constant
    (arity 0) case with the pseudo-gates ``TRUE`` / ``FALSE``.
    """
    m = (len(reduced)).bit_length() - 1  # log2 of length
    if 2 ** m != len(reduced):
        raise ValueError("reduced table length must be a power of two")

    if m == 0:
        g = "TRUE" if reduced[0] == 1 else "FALSE"
        match = GateMatch(g)
        return [match], match

    matches = [c for c in _candidate_gates(m)
               if truth_table(c.gate, m, c.params) == reduced]

    # Regulatory (activator/inhibitor) clause: the reduced truth table has a
    # single 1, whose position encodes which inputs are activators (bit 1) and
    # which are inhibitors (bit 0).  This names the mixed AND-NOT functions that
    # pervade gene-regulatory logic and have no other canonical name.
    if sum(reduced) == 1:
        ystar = reduced.index(1)
        activators = [j for j in range(m) if (ystar >> j) & 1]
        matches.append(GateMatch("REGULATORY", {"activators": activators, "arity": m}))

    # Regulatory disjunctive normal form: any regulatory function as a compact
    # union of activator/inhibitor clauses (a union of anchor-shifted cosets).
    # Named only when it genuinely compresses the on-set and the arity is small
    # enough for the cover to be meaningful; otherwise the look-up table stands.
    if 1 < sum(reduced) < len(reduced) and m <= 12:
        clauses = minimal_dnf(reduced)
        params = {"clauses": clauses, "arity": m}
        if truth_table("REGULATORY_DNF", m, params) == reduced and len(clauses) < sum(reduced):
            matches.append(GateMatch("REGULATORY_DNF", params))

    if not matches:
        # No canonical gate reproduces this function.  Report as a raw truth
        # table so the caller can still reconstruct via an explicit LUT.
        lut = GateMatch("LUT", {"table": list(reduced)})
        return [lut], lut

    def priority(mm: GateMatch) -> tuple[int, int]:
        base = _CANONICAL_PRIORITY.index(mm.gate)
        # Prefer smaller k for KOFN, lower index for canalising: stable choice.
        secondary = mm.params.get("k", 0) + mm.params.get("canalisingIndex", 0)
        return (base, secondary)

    canonical = min(matches, key=priority)
    return matches, canonical


# ---------------------------------------------------------------------------
# Per-node and full-network deconvolution
# ---------------------------------------------------------------------------

@dataclass
class NodeReconstruction:
    node: int
    connected_inputs: list[int]
    # ``None`` only on the symbolic path, where an in-degree above the caller's
    # tabulation bound makes 2**m rows the thing we are avoiding.  The
    # exhaustive path always fills it.
    reduced_truth_table: list[int] | None
    matches: list[GateMatch]
    canonical: GateMatch

    def as_dict(self) -> dict:
        return {
            "node": self.node,
            "connected_inputs": list(self.connected_inputs),
            "arity": len(self.connected_inputs),
            "reduced_truth_table": (None if self.reduced_truth_table is None
                                    else list(self.reduced_truth_table)),
            "num_matches": len(self.matches),
            "matches": [m.as_dict() for m in self.matches],
            "canonical": self.canonical.as_dict(),
        }


def deconvolve_column(column: list[int], n: int, node: int) -> NodeReconstruction:
    """Deconvolve a single output column into ``(I_c, gate)``."""
    ic = essential_variables(column, n)
    reduced = reduce_column(column, n, ic)
    matches, canonical = identify_gate(reduced)
    return NodeReconstruction(node, ic, reduced, matches, canonical)


def deconvolve(rep: list[list[int]]) -> tuple[Network, list[NodeReconstruction]]:
    """Deconvolve a full ``2**n x n`` repertoire into a :class:`Network`.

    Returns the reconstructed network and the per-node reconstruction reports.
    The reconstructed network is built so that its canonical gate is applied to
    its connected inputs in ascending order, matching the forward method.
    """
    R = len(rep)
    n = len(rep[0])
    if 2 ** n != R:
        raise ValueError("repertoire must have 2**n rows and n columns")

    reports: list[NodeReconstruction] = []
    C = [[0] * n for _ in range(n)]
    gates: list[str] = ["FALSE"] * n
    params: list[dict] = [dict() for _ in range(n)]

    for k in range(n):
        column = [rep[x][k] for x in range(R)]
        rec = deconvolve_column(column, n, k)
        reports.append(rec)
        for i in rec.connected_inputs:
            C[k][i] = 1
        gates[k] = rec.canonical.gate
        params[k] = dict(rec.canonical.params)

    net = Network(n=n, C=C, gates=gates, params=params)
    return net, reports


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _apply_reconstructed_column(rec: NodeReconstruction, n: int) -> list[int]:
    """Recompute a node column from its reconstruction (supports LUT gates)."""
    ic = rec.connected_inputs
    g = rec.canonical
    col = []
    for x in range(2 ** n):
        sub = [(x >> i) & 1 for i in ic]
        if g.gate == "TRUE":
            col.append(1)
        elif g.gate == "FALSE":
            col.append(0)
        elif g.gate == "LUT":
            y = 0
            for j in range(len(ic)):
                if sub[j]:
                    y |= (1 << j)
            col.append(g.params["table"][y])
        else:
            col.append(apply_gate(g.gate, sub, g.params))
    return col


def verify_forward(original: list[list[int]], net: Network) -> dict:
    """Provably non-circular verification: rebuild the whole repertoire through
    the forward model from the recovered network ``(C, gates, params)`` and
    compare it to the original.

    This shares nothing with the deconvolution's internal bookkeeping: it takes
    the recovered network object and runs the same forward transform used to
    generate any network's behaviour.  It is the honest test that the recovered
    structure reproduces the data, as opposed to replaying a stored column.
    """
    rebuilt = repertoire(net)
    exact = rebuilt == original
    mismatched = [k for k in range(len(original[0]))
                  if [row[k] for row in rebuilt] != [row[k] for row in original]]
    return {"exact": exact, "mismatched_nodes": mismatched,
            "n_nodes": len(original[0]), "repertoire_rows": len(original)}


# ---------------------------------------------------------------------------
# Symbolic backend - the same three steps without enumerating 2**n states
#
# The exhaustive path above is the definition and stays the reference.  This
# path computes the identical objects on an ordered decision diagram whose
# unique table is canonical, so node identity IS functional identity over every
# one of the 2**n inputs.  Nothing is sampled and nothing is approximated; the
# saving is that the repertoire is never materialised.
#
# Step 1 becomes a cofactor comparison: bit i is essential for root f iff
# f|(i=0) and f|(i=1) are different nodes.  Step 2 becomes root identity
# against each candidate gate built symbolically.  Verification becomes root
# identity between the recompiled network and the original.
#
# Engine ownership.  The diagram engine is
# ``doppel-challenge/src/doppel_challenge/repertoire_program.py`` and the twelve
# canonical families are built by its ``_Manager.gate``; this module never
# re-implements them.  The five Python-only extension families of
# ``causalbool.apply_gate`` (TRUE, FALSE, LUT, REGULATORY, REGULATORY_DNF) have
# no counterpart there, so their symbolic form is built here, beside the
# semantics they mirror.
# ---------------------------------------------------------------------------

_EXTENSION_GATES = ("TRUE", "FALSE", "LUT", "REGULATORY", "REGULATORY_DNF")


def _program_module():
    """Load the exact repertoire-program engine that owns the diagram."""
    import importlib.util
    import sys
    from pathlib import Path

    name = "_causalbool_repertoire_program"
    module = sys.modules.get(name)
    if module is None:
        path = (Path(__file__).resolve().parents[2]
                / "doppel-challenge/src/doppel_challenge/repertoire_program.py")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load the repertoire-program engine: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def symbolic_manager(n: int, limits=None):
    """Return a fresh diagram manager over ``n`` coordinates.

    Roots are only comparable within one manager, so every object that will be
    compared must be built through the same instance.
    """
    engine = _program_module()
    return engine._Manager(n, limits or engine.ProgramLimits())


def _literal(manager, coordinate: int, value: int) -> int:
    """Root of the single-coordinate test ``coordinate == value``."""
    return manager.mk(coordinate, 0, 1) if value else manager.mk(coordinate, 1, 0)


def gate_root(manager, gate: str, coordinates: list[int], params: dict | None = None) -> int:
    """Build the root of one named gate acting on ``coordinates``.

    The twelve canonical families are delegated to the engine that owns them.
    Only the extension families are constructed here.  Parameter indices are
    positions within ``coordinates``, matching :func:`causalbool.apply_gate`.
    """
    p = dict(params or {})
    if gate == "TRUE":
        return 1
    if gate == "FALSE":
        return 0
    if gate == "LUT":
        # Shannon expansion of the stored table over the connected inputs.
        table = p["table"]
        root = 0
        for y, bit in enumerate(table):
            if not bit:
                continue
            term = 1
            for j, c in enumerate(coordinates):
                term = manager.apply("and", term, _literal(manager, c, (y >> j) & 1))
            root = manager.apply("or", root, term)
        return root
    if gate == "REGULATORY":
        activators = set(p["activators"])
        root = 1
        for j, c in enumerate(coordinates):
            root = manager.apply("and", root,
                                 _literal(manager, c, 1 if j in activators else 0))
        return root
    if gate == "REGULATORY_DNF":
        root = 0
        for clause in p["clauses"]:
            term = 1
            for j in clause["activators"]:
                term = manager.apply("and", term, _literal(manager, coordinates[j], 1))
            for j in clause["inhibitors"]:
                term = manager.apply("and", term, _literal(manager, coordinates[j], 0))
            root = manager.apply("or", root, term)
        return root
    return manager.gate(gate, list(coordinates), p)


def root_from_behaviour(manager, n: int, behaviour) -> int:
    """Root of the function ``behaviour(bits) -> 0/1`` observed over ``n`` bits.

    This is the ingestion step and it is 2**n by definition: a complete finite
    repertoire is exactly what the method consumes.  It is for small cells.
    Everything downstream of it -- essential variables, gate naming, forward
    verification, composition -- is then non-exhaustive, which is where the
    saving lies.
    """
    root = 0
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)]
        if not behaviour(bits):
            continue
        term = 1
        for i, bit in enumerate(bits):
            term = manager.apply("and", term, _literal(manager, i, bit))
        root = manager.apply("or", root, term)
    return root


def essential_variables_symbolic(manager, root: int, n: int | None = None) -> list[int]:
    """Ascending coordinates on which ``root`` depends, by cofactor identity.

    Exactly :func:`essential_variables`, at the cost of one diagram pass per
    coordinate instead of 2**n evaluations.
    """
    width = manager.n if n is None else n
    return [i for i in range(width)
            if manager.restrict(root, i, 0) != manager.restrict(root, i, 1)]


def evaluate_root(manager, root: int, values: dict[int, int]) -> int:
    """Evaluate one root under a coordinate assignment by walking the diagram."""
    node = root
    while node >= 2:
        coordinate, low, high = manager.nodes[node-2]
        node = high if values.get(coordinate, 0) else low
    return node


def reduced_table_symbolic(manager, root: int, coordinates: list[int]) -> list[int]:
    """Reduced truth table of ``root`` over its connected inputs.

    Materialising this costs 2**m, so callers must bound ``m``.  It is needed
    only to name the DNF-style extension families; the canonical twelve are
    identified by root identity and never build it.
    """
    m = len(coordinates)
    return [evaluate_root(manager, root,
                          {c: (y >> j) & 1 for j, c in enumerate(coordinates)})
            for y in range(1 << m)]


def identify_gate_symbolic(manager, root: int, coordinates: list[int],
                           max_table_bits: int = 16) -> tuple[list[GateMatch], GateMatch]:
    """Name ``root`` within the canonical family by root identity.

    Returns ``(matches, canonical)`` exactly as :func:`identify_gate` does.  The
    regulatory clause families need the reduced table, so they are only offered
    when ``len(coordinates) <= max_table_bits``; above that bound a function
    with no canonical name is reported as ``LUT`` carrying its diagram size,
    because there the diagram itself is the shortest description we hold.
    """
    m = len(coordinates)
    if m == 0:
        match = GateMatch("TRUE" if root == 1 else "FALSE")
        return [match], match

    matches = [c for c in _candidate_gates(m)
               if gate_root(manager, c.gate, coordinates, c.params) == root]

    if m <= max_table_bits:
        reduced = reduced_table_symbolic(manager, root, coordinates)
        if sum(reduced) == 1:
            ystar = reduced.index(1)
            matches.append(GateMatch("REGULATORY",
                                     {"activators": [j for j in range(m) if (ystar >> j) & 1],
                                      "arity": m}))
        if 1 < sum(reduced) < len(reduced) and m <= 12:
            clauses = minimal_dnf(reduced)
            params = {"clauses": clauses, "arity": m}
            if (len(clauses) < sum(reduced)
                    and gate_root(manager, "REGULATORY_DNF", coordinates, params) == root):
                matches.append(GateMatch("REGULATORY_DNF", params))
        if not matches:
            lut = GateMatch("LUT", {"table": reduced})
            return [lut], lut
    elif not matches:
        # Too wide to tabulate: report the diagram as the description itself.
        lut = GateMatch("LUT", {"program_nodes": len(manager.nodes), "arity": m})
        return [lut], lut

    def priority(mm: GateMatch) -> tuple[int, int]:
        base = _CANONICAL_PRIORITY.index(mm.gate)
        secondary = mm.params.get("k", 0) + mm.params.get("canalisingIndex", 0)
        return (base, secondary)

    canonical = min(matches, key=priority)
    return matches, canonical


def deconvolve_root(manager, root: int, node: int = 0,
                    max_table_bits: int = 16) -> NodeReconstruction:
    """Deconvolve one symbolic output into ``(I_c, gate)`` without enumeration."""
    ic = essential_variables_symbolic(manager, root)
    matches, canonical = identify_gate_symbolic(manager, root, ic, max_table_bits)
    reduced = (reduced_table_symbolic(manager, root, ic)
               if len(ic) <= max_table_bits else None)
    return NodeReconstruction(node, ic, reduced, matches, canonical)


def network_roots(manager, net: Network) -> list[int]:
    """Symbolic forward method: one root per node of ``net``.

    The twelve canonical families route to the engine's own builder, so this is
    the same forward transform the engine applies in
    ``compile_repertoire_program``; it additionally admits the extension
    families a deconvolution may recover.
    """
    return [gate_root(manager, net.gates[k], net.connected_inputs(k), net.params[k])
            for k in range(net.n)]


def verify_forward_symbolic(manager, original_roots: list[int], net: Network) -> dict:
    """Rebuild ``net`` through the forward method and compare roots.

    Canonical node identity settles agreement on every one of the 2**n inputs
    at once.  ``original_roots`` must have been built in the same manager.
    """
    rebuilt = network_roots(manager, net)
    mismatched = [k for k in range(len(original_roots)) if rebuilt[k] != original_roots[k]]
    return {"exact": not mismatched, "mismatched_nodes": mismatched,
            "n_nodes": len(original_roots), "comparison": "canonical decision-node identity",
            "states_covered": 1 << manager.n, "states_enumerated": 0,
            "allocated_nodes": len(manager.nodes)}


def verify(original: list[list[int]], reports: list[NodeReconstruction]) -> dict:
    """Check that the reconstruction reproduces the original repertoire exactly.

    Reconstruction is done from the per-node reports.  Note the scope honestly:
    for a node named LUT the stored truth table is replayed, so reproduction is
    exact by construction; the non-trivial content is the recovered functional
    connectivity (which drives the reduction) and the named-gate identification.
    For a fully independent check that shares no bookkeeping with the
    deconvolution, use :func:`verify_forward` on the recovered network.
    """
    R = len(original)
    n = len(original[0])
    exact = True
    mismatched_nodes = []
    for k in range(n):
        col_orig = [original[x][k] for x in range(R)]
        col_rec = _apply_reconstructed_column(reports[k], n)
        if col_orig != col_rec:
            exact = False
            mismatched_nodes.append(k)
    return {
        "exact": exact,
        "mismatched_nodes": mismatched_nodes,
        "n_nodes": n,
        "repertoire_rows": R,
    }
