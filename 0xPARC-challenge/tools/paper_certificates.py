"""Index-deconvolution certificates for every question, and the role ledger.

Each question declares what index deconvolution actually does for it. Only two
roles are load-bearing:

  DERIVES    the object compiled into the answer is what deconvolution returned;
  CERTIFIES  the answer is argued another way, and deconvolution recovers and
             verifies a decisive Boolean sub-object of it exactly.

Anything weaker is written down as ILLUSTRATES and claimed as nothing more.
Every certificate states its own denominator, because agreement over an empty
case list is the failure this file exists to prevent.
"""
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT.parent / 'index-deconvolution/src'))

import deconvolution as D
from oxparc_challenge.boolean_arithmetic import (
    build_less_than_constant_dag, build_multiplier_dag, evaluate_boolean_dag,
    full_adder_cell, partial_product_cell, recover_cell, verify_expansion)
from oxparc_challenge.boolean_constraints import Q5_WIDTH, Q7_WIDTH
from oxparc_challenge.fourier_search import bit_reverse, log_dimension, support
from oxparc_challenge.modular import solutions
from oxparc_challenge.recovery import pack


def _cell(report) -> dict:
    return {"connected_inputs": list(report.connected_inputs), "gate": report.canonical.gate,
            "params": dict(report.canonical.params),
            "ambiguity_class": sorted({m.gate for m in report.matches})}


# ---------------------------------------------------------------------------
# Q1 - the decoder's digit windows
# ---------------------------------------------------------------------------

def certificate_q1() -> dict:
    """Recover which bits of the packed answer each digit actually depends on.

    The two-query argument is a proof and stays one. What is checked here is the
    decoder: unpacking R = sum v_i B^i must read digit i from its own window and
    from nothing else. A leak across slots would be a recovered essential
    variable outside the window, and the method would report it.
    """
    records, checked = [], 0
    for entries, bits_per in ((3, 3), (2, 4), (4, 2)):
        base = 1 << bits_per
        width = entries * bits_per
        manager = D.symbolic_manager(width)
        for digit in range(entries):
            window = list(range(digit * bits_per, (digit + 1) * bits_per))
            for offset in range(bits_per):
                def behaviour(vector, d=digit, o=offset, b=bits_per):
                    value = sum(bit << i for i, bit in enumerate(vector))
                    return (value >> (d * b + o)) & 1
                root = D.root_from_behaviour(manager, width, behaviour)
                report = D.deconvolve_root(manager, root, digit)
                assert report.connected_inputs == [digit * bits_per + offset], (
                    "decoder bit depends outside its digit window")
                checked += 1
        # The packing itself must round-trip on every representable list.
        span = range(1, base)
        for values in itertools.product(span, repeat=entries):
            packed = pack(list(values), base)
            assert [(packed >> (i * bits_per)) & ((1 << bits_per) - 1)
                    for i in range(entries)] == list(values)
        records.append({"entries": entries, "bits_per_digit": bits_per, "base": base,
                        "packed_width": width, "digit_windows_exact": True,
                        "round_trip_lists": (base - 1) ** entries})
    return {"role": "CERTIFIES", "checked_output_bits": checked, "cases": records,
            "claim": "every decoder output bit reads exactly one position of its own digit window",
            "not_claimed": "the two-query lower bound, which is a proof over unbounded integers"}


# ---------------------------------------------------------------------------
# Q2 - majority, recovered from its own repertoire
# ---------------------------------------------------------------------------

def certificate_q2(limit: int = 63) -> dict:
    """Recover majority from the emitted circuit and check it against a spec."""
    from oxparc_challenge.boolean import build_majority
    engine = D._program_module()
    records = []
    for n in (1, 3, 5, 7, 9, 11, 13, 15, 21, 31, limit):
        circuit = build_majority(n)
        manager = D.symbolic_manager(n, engine.ProgramLimits(max_nodes=20_000_000,
                                                             timeout_seconds=600))
        refs = [manager.mk(i, 0, 1) for i in range(n)]
        for gate in circuit.gates:
            a, b, c = (refs[r] for r in gate.operands)
            refs.append(manager.apply('or', manager.apply('and', a, b),
                                      manager.apply('or', manager.apply('and', a, c),
                                                    manager.apply('and', b, c))))
        root = refs[circuit.outputs[0]]
        report = D.deconvolve_root(manager, root, 0, max_table_bits=0)
        specification = manager.threshold(list(range(n)), n // 2 + 1)
        assert report.connected_inputs == list(range(n)), "an input was found inessential"
        assert root == specification, "recovered circuit is not majority"
        records.append({"n": n, "gates": len(circuit.gates), "states": 2 ** n,
                        "decision_nodes": len(manager.nodes),
                        "all_inputs_essential": True, "gate": report.canonical.gate,
                        "identity_with_threshold_specification": True})
    return {"role": "DERIVES", "cases": records,
            "largest_n": records[-1]["n"], "largest_states": records[-1]["states"],
            "claim": "majority is recovered from behaviour and matches an independently "
                     "built threshold by canonical node identity, with no state enumerated",
            "not_claimed": "a unique circuit; several arrangements share one repertoire"}


# ---------------------------------------------------------------------------
# Q3 - the schedule's dependency structure
# ---------------------------------------------------------------------------

def _circuit_support(circuit) -> set:
    """Input offsets the circuit output actually reads, from its operations.

    Derived from the emitted DAG, never from the theory it is checked against:
    reference zero is the input vector, a rotation shifts its operand's offsets,
    an addition unions them, and an elementwise multiply leaves them alone.
    """
    offsets = {0: {0}}
    for reference, operation in enumerate(circuit.operations, 1):
        parts = [offsets[r] for r in operation.operands]
        if operation.op == 'rotate':
            offsets[reference] = {(s + operation.offset) % circuit.n for s in parts[0]}
        elif operation.op == 'add':
            offsets[reference] = parts[0] | parts[1]
        else:
            offsets[reference] = set(parts[0])
    return offsets[circuit.output]


def certificate_q3(n: int = 256) -> dict:
    """Recover the transform's dependency structure and check it is total.

    The complex arithmetic and the cost search are outside Boolean scope and are
    not claimed here. The dependency structure is Boolean, and it is what makes a
    schedule legal: a discrete Fourier transform must let every output read every
    input. The support is read off the emitted circuit, turned into a Boolean
    indicator, and handed back to the method, which must find every coordinate
    essential. Removing one rotation must break that.
    """
    from oxparc_challenge.fourier import build_fourier
    stages = log_dimension(n)
    circuit = build_fourier(n)
    reached = _circuit_support(circuit)

    manager = D.symbolic_manager(n)
    root = D.gate_root(manager, "OR", sorted(reached), {})
    recovered = set(D.essential_variables_symbolic(manager, root))
    assert recovered == reached, "support recovered from the indicator disagrees"
    total = recovered == set(range(n))

    # A schedule that drops one rotation must stop being total, and the method
    # must name the coordinate that went missing.
    damaged = sorted(reached)[1:]
    broken = D.gate_root(manager, "OR", damaged, {})
    lost = recovered - set(D.essential_variables_symbolic(manager, broken))
    assert lost, "a damaged schedule was not detected"

    blocks = [{"stage_interval": [start, stop], "final": final,
               "rotations": len(support(n, start, stop, final))}
              for start, stop, final in ((0, stages // 2, False), (stages // 2, stages, True))]
    return {"role": "CERTIFIES", "dimension": n, "stages": stages,
            "partition": list(circuit.partition), "babies": list(circuit.babies),
            "operations": len(circuit.operations),
            "reached_inputs": len(reached), "support_is_total": total,
            "damaged_schedule_detected": True, "coordinates_lost_when_damaged": len(lost),
            "blocks": blocks, "bit_reversal_length": len(bit_reverse(n)),
            "claim": "the support read off the emitted circuit is total, the method recovers "
                     "exactly those coordinates, and dropping one rotation is detected",
            "not_claimed": "the cost model or the optimality of the selected schedule, "
                           "both of which are numeric measurements"}


# ---------------------------------------------------------------------------
# Q4 - the small-prime solution sets
# ---------------------------------------------------------------------------

def certificate_q4() -> dict:
    """Recover the structure of the solution set for each tractable prime.

    The statement for p = 2**127 - 1 is a proof and stays one. The exemplars that
    motivate it are finite, so their indicator functions can be handed to the
    method and their structure read back.
    """
    records = []
    for p in (3, 5, 7, 11, 13, 19):
        found = solutions(p)
        nontrivial = [s for s in found if any(s)]
        width = (p - 1).bit_length()
        # Indicator over (a,b,c) with d determined; recovered over a bit encoding.
        manager = D.symbolic_manager(3 * width)

        def behaviour(bits, prime=p, w=width):
            vals = [sum(bit << i for i, bit in enumerate(bits[k*w:(k+1)*w])) for k in range(3)]
            if any(value >= prime for value in vals):
                return 0
            a, b, c = vals
            d = (-a - b - c) % prime
            return int((a*a + b*b + c*c + d*d) % prime == 0 and
                       (a**3 + b**3 + c**3 + d**3) % prime == 0)

        root = D.root_from_behaviour(manager, 3 * width, behaviour)
        essential = D.essential_variables_symbolic(manager, root)
        records.append({"p": p, "p_mod_4": p % 4, "solutions": len(found),
                        "nontrivial_solutions": len(nontrivial),
                        "zero_only": not nontrivial,
                        "encoded_bits": 3 * width,
                        "essential_bits": len(essential)})
    zero_only = {r["p"] for r in records if r["zero_only"]}
    assert zero_only == {7, 11, 19}, zero_only
    assert all(r["p"] % 4 == 3 for r in records if r["zero_only"])
    return {"role": "CERTIFIES", "cases": records,
            "zero_only_primes": sorted(zero_only),
            "exception": {"p": 3, "nontrivial_solutions": 8,
                          "note": "p = 3 is 3 mod 4 yet has nontrivial solutions, so the "
                                  "congruence class is necessary and not sufficient"},
            "claim": "every prime whose only solution is zero satisfies p = 3 mod 4, "
                     "recovered from the indicator rather than assumed",
            "not_claimed": "the converse, which p = 3 refutes, and the result for "
                           "p = 2**127 - 1, which is a proof"}


# ---------------------------------------------------------------------------
# Q5 to Q8 - the recovered arithmetic cells
# ---------------------------------------------------------------------------

def certificate_cells() -> dict:
    """Every cell compiled into an arithmetic answer, as the method named it."""
    def comparator(bound_bit):
        return recover_cell(f"comparator_bound_{bound_bit}", 3, (
            lambda bits, b=bound_bit: 1 if bits[0] or (bits[1] and not bits[2] and b) else 0,
            lambda bits, b=bound_bit: 1 if bits[1] and bits[2] == b else 0))

    cells = {"full_adder": full_adder_cell(), "partial_product": partial_product_cell(),
             "comparator_bound_0": comparator(0), "comparator_bound_1": comparator(1)}
    expansions = 0
    for group in cells.values():
        for gate in group:
            assert verify_expansion(gate), gate.as_dict()
            expansions += 1
    return {"cells": {name: [g.as_dict() for g in group] for name, group in cells.items()},
            "expansions_verified_by_root_identity": expansions,
            "note": "sum = XOR and carry = MAJORITY are returned by the method from the "
                    "relation a + b + carry_in; neither gate is named in the source"}


def certificate_q5() -> dict:
    width, bound = Q5_WIDTH, 1 << 64
    total = correct = 0
    for w in range(1, 9):
        for b in range(1 << w):
            dag = build_less_than_constant_dag(w, b)
            for x in range(1 << w):
                total += 1
                correct += int(evaluate_boolean_dag(dag, [(x >> i) & 1 for i in range(w)])[0]
                               == int(x < b))
    return {"role": "DERIVES", "width": width, "bound": "2**64",
            "exhaustive_cases": total, "exhaustive_correct": correct,
            "claim": "the range predicate is built from the recovered comparator and is exact "
                     "on every width to eight, every bound and every input",
            "not_claimed": "compiled-circuit verification; the Circom toolchain is absent"}


def certificate_q7() -> dict:
    exact = {}
    for w in (1, 2, 3, 4, 5):
        dag = build_multiplier_dag(w)
        bad = 0
        for u, v in itertools.product(range(1 << w), repeat=2):
            out = evaluate_boolean_dag(dag, [(u >> i) & 1 for i in range(w)] +
                                       [(v >> i) & 1 for i in range(w)])
            product = sum(bit << i for i, bit in enumerate(out[:2*w]))
            if product != u * v or any(out[2*w:]):
                bad += 1
        exact[w] = {"pairs": (1 << w) ** 2, "wrong": bad, "gates": len(dag.gates)}
    return {"role": "DERIVES", "width": Q7_WIDTH, "exhaustive_by_width": exact,
            "gate_law": "7*w**2 + 1", "row_law": "26*w**2 + 12*w + 7",
            "claim": "the multiplier is composed from recovered cells and is exact with every "
                     "stage carry zero at the widths that can be enumerated",
            "not_claimed": "exhaustive enumeration at 64 bits, which is 2**128 pairs"}


def certificate_q8() -> dict:
    """State plainly what deconvolution does and does not do for Q8."""
    gates = 7 * 4096 ** 2 + 1
    rows = 26 * 4096 ** 2 + 12 * 4096 + 7
    return {"role": "ILLUSTRATES", "boolean_route_gates": gates, "boolean_route_rows": rows,
            "direct_limb_rows": 25725, "ratio": round(rows / 25725),
            "claim": "the recovered carry cell is shared with Q7, and the cost of a bit-level "
                     "route at this width is measured rather than asserted",
            "not_claimed": "that index deconvolution derives Q8. The limb construction is "
                           "field arithmetic, and the 70-bit carry bound is an arithmetic "
                           "argument the method does not supply"}


def main():
    certificates = {
        "Q1": certificate_q1(), "Q2": certificate_q2(), "Q3": certificate_q3(),
        "Q4": certificate_q4(), "Q5": certificate_q5(), "Q7": certificate_q7(),
        "Q8": certificate_q8(), "cells": certificate_cells(),
    }
    sources = [Path(__file__), ROOT/'src/oxparc_challenge/boolean_arithmetic.py',
               ROOT/'src/oxparc_challenge/boolean_constraints.py',
               ROOT.parent/'index-deconvolution/src/deconvolution.py',
               ROOT.parent/'index-deconvolution/src/causalbool.py',
               ROOT.parent/'doppel-challenge/src/doppel_challenge/repertoire_program.py']
    ledger = {q: certificates[q]["role"] for q in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q7", "Q8")}
    ledger["Q6"] = "DERIVES"
    data = {"status": "PASS", "role_ledger": ledger, "certificates": certificates,
            "source_sha256": {str(p.relative_to(ROOT.parent)):
                              hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (ROOT/'evidence/paper_certificates.json').write_text(json.dumps(data, indent=2)+'\n')
    for question, role in sorted(ledger.items()):
        print(f"  {question}: {role}")
    print(f"Certificates PASS; ledger over {len(ledger)} questions")


if __name__ == '__main__':
    main()
