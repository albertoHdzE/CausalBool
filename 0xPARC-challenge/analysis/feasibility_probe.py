"""Bounded feasibility probes, not a complete challenge solver or ZK backend.

Run from any directory: python /path/to/feasibility_probe.py
Uses the existing CausalBool gate evaluator and private symbolic manager as
read-only experimental dependencies. Emits evidence JSON to stdout.
"""
from functools import lru_cache
from itertools import product
from pathlib import Path
import json
import hashlib
import random
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "index-deconvolution/src"))
sys.path.insert(0, str(ROOT / "doppel-challenge/src"))
from causalbool import apply_gate
from doppel_challenge.repertoire_program import (
    _Manager, ProgramLimits, ResourceLimitError,
)

P = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def dot_product_probe():
    rng = random.Random(20260914)
    cases = 0
    for n in range(1, 17):
        for _ in range(20):
            values = [rng.randrange(1, 1 << 80) for _ in range(n)]
            base = sum(values) + 1  # First query: all coefficients equal one.
            answer = sum(v * base**i for i, v in enumerate(values))
            recovered = []
            for _ in values:
                answer, digit = divmod(answer, base)
                recovered.append(digit)
            assert recovered == values and answer == 0
            cases += 1
    return {"exact_integer_round_trips": cases, "queries": 2}


def majority_probe():
    records = []
    for n in (3, 5, 7, 9):
        gates = []
        unique = {}

        @lru_cache(None)
        def compile_weights(weights):
            total = sum(weights)
            for i, weight in enumerate(weights):
                if 2 * weight > total:
                    return i
            a, b, c = [i for i, w in enumerate(weights) if w][:3]
            refs = []
            # Cyclic identifications: b=a, c=b, a=c.
            for keep, remove in ((a, b), (b, c), (c, a)):
                child = list(weights)
                child[keep] += child[remove]
                child[remove] = 0
                refs.append(compile_weights(tuple(child)))
            for ref in refs:
                if refs.count(ref) >= 2:
                    return ref
            key = tuple(sorted(refs))
            if key not in unique:
                unique[key] = n + len(gates)
                gates.append(key)
            return unique[key]

        root = compile_weights((1,) * n)
        for bits in product((0, 1), repeat=n):
            wires = list(bits)
            for operands in gates:
                wires.append(apply_gate("MAJORITY", [wires[i] for i in operands]))
            assert wires[root] == int(sum(bits) > n // 2)
        records.append({"inputs": n, "assignments": 1 << n,
                        "constructed_gates_before_reachability_pruning": len(gates),
                        "recursive_subproblems": compile_weights.cache_info().currsize})
    bits = [1, 1, 0, 1, 1, 0, 0, 0, 0]
    naive = apply_gate("MAJORITY", [apply_gate("MAJORITY", bits[i:i+3])
                                    for i in (0, 3, 6)])
    assert naive == 1 and sum(bits) == 4
    return {"exhaustive_checks": records,
            "naive_tree_counterexample": {"bits": bits, "tree": naive, "correct": 0},
            "full_2025_circuit_materialized": False}


def symbolic_limit_probe():
    small = []
    for n in (5, 31, 101):
        k = n // 2 + 1
        manager = _Manager(n, ProgramLimits())
        root = manager.threshold(list(range(n)), k)
        predicted = sum(min(k, r) for r in range(1, n + 1))
        assert len(manager.nodes) == predicted
        seen, stack = set(), [root]
        while stack:
            ref = stack.pop()
            if ref < 2 or ref in seen:
                continue
            seen.add(ref)
            stack.extend(manager.nodes[ref - 2][1:])
        assert len(seen) == k * (n - k + 1)
        small.append({"inputs": n, "allocated": len(manager.nodes), "reachable": len(seen)})
    manager = _Manager(2025, ProgramLimits())
    try:
        manager.threshold(list(range(2025)), 1013)
    except ResourceLimitError:
        assert len(manager.nodes) == 1_000_000
    else:
        raise AssertionError("Expected current default allocation limit to be exceeded")
    return {"small_checks": small, "2025_default_limit_observed": len(manager.nodes),
            "2025_unrestricted_allocation_count_derived": sum(min(1013, r) for r in range(1, 2026)),
            "2025_reachable_count_derived": 1013**2,
            "note": "Tests threshold construction, not a 2025-input MAJ3 circuit."}


def modular_probe():
    records = []
    for p in (3, 5, 7, 11, 13, 19):
        solutions = []
        for a, b, c in product(range(p), repeat=3):
            d = (-a-b-c) % p
            if (a*a + b*b + c*c + d*d) % p == 0 and (
                    a**3 + b**3 + c**3 + d**3) % p == 0:
                solutions.append((a, b, c, d))
        if p % 4 == 3 and p != 3:
            assert solutions == [(0, 0, 0, 0)]
        else:
            assert len(solutions) > 1
        records.append({"prime": p, "solutions": len(solutions)})
    p = (1 << 127) - 1
    assert p % 4 == 3 and pow(p-1, (p-1)//2, p) == p-1
    return {"small_prime_enumeration": records, "target_prime_mod_4": p % 4,
            "target_legendre_minus_one": -1,
            "note": "Full-size no-solution result is algebraic, not exhaustive enumeration."}


def limb_check(a, b, n, *, bits=64, limbs=64, corrupt_carry=False):
    base = 1 << bits
    if not (2 <= a < base**limbs and 2 <= b < base**limbs and 0 <= n < base**limbs):
        return False
    av = [(a >> (bits*i)) & (base-1) for i in range(limbs)]
    bv = [(b >> (bits*i)) & (base-1) for i in range(limbs)]
    nv = [(n >> (bits*i)) & (base-1) for i in range(limbs)] + [0]*limbs
    # Actual R1CS must bind these partial products with separate constraints.
    partial = [[x*y for y in bv] for x in av]
    carry = [0]
    sums = []
    for k in range(2*limbs):
        total = sum(partial[i][k-i] for i in range(limbs) if 0 <= k-i < limbs)
        sums.append(total)
        carry.append((total + carry[-1]) // base)
    if corrupt_carry:
        carry[1] += 1
    carry_limit = 1 << (bits + (limbs-1).bit_length())
    assert limbs * (base-1)**2 + carry_limit < P
    assert (base-1) + base * carry_limit < P
    return (carry[0] == carry[-1] == 0
            and all(0 <= c < carry_limit for c in carry)
            and all((sums[k] + carry[k] - nv[k] - base*carry[k+1]) % P == 0
                    for k in range(2*limbs)))


def constraint_probe():
    rng = random.Random(814)
    range_checks = 0
    for x in (0, 1, 1 << 63, (1 << 64)-1, 1 << 64, P-1):
        bits = [(x >> i) & 1 for i in range(64)]
        accepted = (all(b*(b-1) % P == 0 for b in bits)
                    and (x-sum(b*(1 << i) for i, b in enumerate(bits))) % P == 0)
        assert accepted == (x < 1 << 64)
        range_checks += 1
    assert 2*(2-1) % P != 0  # A nonbinary witness must be constrained out.
    inverse_checks = 0
    for r in (0, 1, 2, 3, P-1, P+1):
        if (r-1) % P:
            s = pow((r-1) % P, -1, P)
            assert ((r-1)*s) % P == 1
            inverse_checks += 1
        else:
            assert ((r-1)*12345) % P == 0
    toy_checks = 0
    for a, b in product(range(2, 16), repeat=2):
        for n in range(16):
            assert limb_check(a, b, n, bits=2, limbs=2) == (a*b == n)
            toy_checks += 1
    cases = []
    for width in (32, 128, 1024, 2048):
        for _ in range(5):
            a, b = rng.randrange(2, 1 << width), rng.randrange(2, 1 << width)
            assert limb_check(a, b, a*b)
            assert not limb_check(a, b, a*b + 1)
            assert not limb_check(a, b, a*b, corrupt_carry=True)
            cases.append(width)
    # Demonstrates the danger of enforcing only one field multiplication.
    a, b, n = 2, (P+15)//2, 15
    assert (a*b-n) % P == 0 and a*b != n
    assert not limb_check(a, b, n)
    return {"range_boundary_checks": range_checks,
            "inverse_witness_checks": inverse_checks, "toy_exhaustive_checks": toy_checks,
            "large_integer_cases": len(cases), "max_factor_bits_tested": max(cases),
            "changed_output_and_carry_rejected": True, "modular_alias_rejected": True,
            "circom_compilation_performed": False,
            "note": "Checks proposed arithmetic equations; not a compiled R1CS soundness test."}


def dft_bsgs(vector, baby):
    n = len(vector)
    assert n % baby == 0
    indices = np.arange(n)
    rotations = [np.roll(vector, -i) for i in range(baby)]
    out = np.zeros(n, dtype=complex)
    for offset in range(0, n, baby):
        inner = np.zeros(n, dtype=complex)
        for i in range(baby):
            k = offset + i
            exponents = (indices * ((indices+k) % n)) % n
            diagonal = np.exp(-2j*np.pi*exponents/n)
            inner += np.roll(diagonal, offset) * rotations[i]
        out += np.roll(inner, -offset)
    return out


def fft_probe():
    rng = np.random.default_rng(913)
    records = []
    for n, baby in ((4, 2), (16, 4), (32, 4), (64, 8), (128, 8)):
        largest_error = 0.0
        # Basis vectors establish every matrix column numerically at small sizes.
        cases = [np.eye(n, dtype=complex)[:, i] for i in range(n)]
        cases += [rng.normal(size=n) + 1j*rng.normal(size=n)]
        for x in cases:
            expected, actual = np.fft.fft(x), dft_bsgs(x, baby)
            err = float(np.max(np.abs(expected-actual)))
            largest_error = max(largest_error, err)
            assert err < 1e-10
        records.append({"slots": n, "tested_vectors": len(cases), "max_abs_error": largest_error})
    costs = []
    for n, baby in ((32768, 128), (65536, 256)):
        rotations = baby-1 + n//baby-1
        additions, multiplications = n-1, n
        microseconds = 4*additions + 5600*multiplications + 6100*rotations
        costs.append({"slots": n, "multiplications": multiplications, "additions": additions,
                      "rotations": rotations, "multiplicative_depth": 1,
                      "serial_cost_seconds": microseconds/1e6})
    return {"plaintext_checks": records, "dense_baseline_cost_estimates": costs,
            "ciphertext_benchmark_performed": False,
            "assumptions": "Known diagonal-vector multiplication allowed; costs charged as stated; serial execution."}


if __name__ == "__main__":
    result = {"dot_product": dot_product_probe(), "majority": majority_probe(),
              "symbolic_limits": symbolic_limit_probe(), "modular_equations": modular_probe(),
              "constraints": constraint_probe(), "fourier": fft_probe()}
    result["environment"] = {"python": sys.version.split()[0], "numpy": np.__version__}
    result["source_sha256"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("0xPARC-challenge/analysis/feasibility_probe.py",
                     "index-deconvolution/src/causalbool.py",
                     "doppel-challenge/src/doppel_challenge/repertoire_program.py")
    }
    print(json.dumps(result, indent=2))
