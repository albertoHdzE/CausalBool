"""Small, explicit quadratic gadgets for the arithmetic challenge.

The builders below use the frozen serialized constraint representation.  The
corresponding witness helpers validate their integer inputs before converting
them to canonical field representatives.
"""

from . import FIELD_PRIME
from .constraints import ConstraintSystem, LinearExpression, QuadraticConstraint


_P = FIELD_PRIME
_B64 = 1 << 64


def _l(constant=0, **terms):
    return LinearExpression(constant=constant, terms=terms)


def _row(a, b, c, label):
    return QuadraticConstraint(a, b, c, label)


def _integer(value, name):
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value


def _range_rows(signal, bits):
    rows = []
    for index, bit in enumerate(bits):
        rows.append(_row(_l(**{bit: 1}), _l(constant=-1, **{bit: 1}), _l(), f"{signal}_bit_{index}"))
    rows.append(
        _row(
            _l(constant=1),
            _l(**{signal: 1}),
            _l(**{bit: 1 << index for index, bit in enumerate(bits)}),
            f"{signal}_pack",
        )
    )
    return rows


def _bits(value, prefix):
    return {f"{prefix}_b{index}": (value >> index) & 1 for index in range(64)}


def _inverse(value):
    return pow(value % _P, _P - 2, _P)


def build_range():
    """Build a 64-bit private ``x`` with canonical binary decomposition."""
    bits = [f"x_b{index}" for index in range(64)]
    return ConstraintSystem(
        private_inputs=["x"],
        auxiliary_signals=bits,
        constraints=_range_rows("x", bits),
    )


def witness_range(x):
    x = _integer(x, "x")
    if not 0 <= x < _B64:
        raise ValueError("x must be a 64-bit nonnegative integer")
    return {"x": x, **_bits(x, "x")}


def build_exclude_one():
    """Build the field equation ``(r - 1) * s = 1``."""
    return ConstraintSystem(
        private_inputs=["r"],
        auxiliary_signals=["s"],
        constraints=[
            _row(_l(constant=-1, r=1), _l(s=1), _l(constant=1), "exclude_one")
        ],
    )


def witness_exclude_one(r):
    r = _integer(r, "r")
    if not 0 <= r < _P or r == 1:
        raise ValueError("r must be canonical and different from one")
    return {"r": r, "s": _inverse(r - 1)}


def build_factor64():
    """Build the range-checked 64-bit factorization system."""
    n_bits = [f"n_b{index}" for index in range(64)]
    u_bits = [f"u_b{index}" for index in range(64)]
    v_bits = [f"v_b{index}" for index in range(64)]
    auxiliary = n_bits + u_bits + v_bits + ["u_inv", "v_inv", "u_one_inv", "v_one_inv"]
    rows = []
    rows.extend(_range_rows("n", n_bits))
    rows.extend(_range_rows("u", u_bits))
    rows.extend(_range_rows("v", v_bits))
    rows.append(_row(_l(u=1), _l(v=1), _l(n=1), "factor_product"))
    # The sums of bits 1..63 exclude zero, while the separate inverse rows
    # exclude one.  Together they enforce 2 <= u,v without integer assertions.
    for signal, bits, inverse, one_inverse in (
        ("u", u_bits, "u_inv", "u_one_inv"),
        ("v", v_bits, "v_inv", "v_one_inv"),
    ):
        nonzero = {bit: 1 for bit in bits[1:]}
        rows.append(_row(_l(**nonzero), _l(**{inverse: 1}), _l(constant=1), f"nontrivial_{signal}"))
        rows.append(
            _row(
                _l(constant=-1, **{signal: 1}),
                _l(**{one_inverse: 1}),
                _l(constant=1),
                f"nontrivial_{signal}_one",
            )
        )
    return ConstraintSystem(
        public_inputs=["n"],
        private_inputs=["u", "v"],
        auxiliary_signals=auxiliary,
        constraints=rows,
    )


def witness_factor64(n, u, v):
    n = _integer(n, "n")
    u = _integer(u, "u")
    v = _integer(v, "v")
    if not (0 <= n < _B64 and 2 <= u < _B64 and 2 <= v < _B64):
        raise ValueError("n, u, and v must satisfy the 64-bit factorization bounds")
    if u * v != n:
        raise ValueError("u*v must equal n")
    result = {"n": n, "u": u, "v": v}
    result.update(_bits(n, "n"))
    result.update(_bits(u, "u"))
    result.update(_bits(v, "v"))
    result["u_inv"] = _inverse(sum((u >> index) & 1 for index in range(1, 64)))
    result["v_inv"] = _inverse(sum((v >> index) & 1 for index in range(1, 64)))
    result["u_one_inv"] = _inverse(u - 1)
    result["v_one_inv"] = _inverse(v - 1)
    return result


def build_factor4096():
    base = 1 << 64
    n_limbs = [f"n_{index}" for index in range(64)]
    u_limbs = [f"u_{index}" for index in range(64)]
    v_limbs = [f"v_{index}" for index in range(64)]
    limb_bits = []
    for prefix in ("n", "u", "v"):
        for index in range(64):
            limb_bits.extend(f"{prefix}_{index}_b{bit}" for bit in range(64))
    partials = [f"q_{i}_{j}" for i in range(64) for j in range(64)]
    carries = [f"carry_{index}" for index in range(129)]
    carry_bits = [f"carry_{index}_b{bit}" for index in range(1, 128) for bit in range(70)]
    auxiliary = limb_bits + partials + carries + carry_bits + ["u_inv", "v_inv"]

    rows = []
    for prefix, limbs in (("n", n_limbs), ("u", u_limbs), ("v", v_limbs)):
        for index, limb in enumerate(limbs):
            bits = [f"{limb}_b{bit}" for bit in range(64)]
            rows.extend(_range_rows(limb, bits))

    for i in range(64):
        for j in range(64):
            rows.append(_row(_l(**{f"u_{i}": 1}), _l(**{f"v_{j}": 1}), _l(**{f"q_{i}_{j}": 1}), f"partial_{i}_{j}"))

    # Column k states the ordinary base-2^64 multiplication recurrence.
    for k in range(128):
        left = {f"q_{i}_{k-i}": 1 for i in range(max(0, k - 63), min(63, k) + 1)}
        left[f"carry_{k}"] = 1
        right = {f"carry_{k + 1}": base}
        if k < 64:
            right[f"n_{k}"] = 1
        rows.append(_row(_l(constant=1), _l(**left), _l(**right), f"column_{k}"))

    rows.extend([
        _row(_l(carry_0=1), _l(constant=1), _l(), "endpoint_0"),
        _row(_l(carry_128=1), _l(constant=1), _l(), "endpoint_128"),
    ])
    for index in range(1, 128):
        bits = [f"carry_{index}_b{bit}" for bit in range(70)]
        rows.extend(_range_rows(f"carry_{index}", bits))
    for prefix, limbs, inverse in (("u", u_limbs, "u_inv"), ("v", v_limbs, "v_inv")):
        higher_bits = {
            f"{limb}_b{bit}": 1
            for limb in limbs
            for bit in range(64)
            if not (limb == limbs[0] and bit == 0)
        }
        rows.append(_row(_l(**higher_bits), _l(**{inverse: 1}), _l(constant=1), f"nontrivial_{prefix}"))

    return ConstraintSystem(
        public_inputs=n_limbs,
        private_inputs=u_limbs + v_limbs,
        auxiliary_signals=auxiliary,
        constraints=rows,
    )


def witness_factor4096(n, u, v):
    n = _integer(n, "n")
    u = _integer(u, "u")
    v = _integer(v, "v")
    limit = 1 << 4096
    if not (0 <= n < limit and 2 <= u < limit and 2 <= v < limit):
        raise ValueError("n, u, and v must be 4096-bit nonnegative integers")
    if u * v != n or n >= limit:
        raise ValueError("u*v must equal n and fit in 4096 bits")

    def limbs(value):
        return [(value >> (64 * index)) & ((1 << 64) - 1) for index in range(64)]

    ns, us, vs = limbs(n), limbs(u), limbs(v)
    result = {}
    for prefix, values in (("n", ns), ("u", us), ("v", vs)):
        for index, value in enumerate(values):
            result[f"{prefix}_{index}"] = value
            for bit in range(64):
                result[f"{prefix}_{index}_b{bit}"] = (value >> bit) & 1

    for i, u_limb in enumerate(us):
        for j, v_limb in enumerate(vs):
            result[f"q_{i}_{j}"] = u_limb * v_limb

    base = 1 << 64
    carries = [0] * 129
    for k in range(128):
        total = carries[k]
        total += sum(us[i] * vs[k - i] for i in range(max(0, k - 63), min(63, k) + 1))
        expected = ns[k] if k < 64 else 0
        if total % base != expected:
            raise ValueError("factor limbs do not match n")
        carries[k + 1] = total // base
    if carries[128] != 0:
        raise ValueError("factor product overflows 4096 bits")
    for index, carry in enumerate(carries):
        result[f"carry_{index}"] = carry
        if 1 <= index <= 127:
            for bit in range(70):
                result[f"carry_{index}_b{bit}"] = (carry >> bit) & 1

    higher_u = sum((u >> bit) & 1 for bit in range(1, 4096))
    higher_v = sum((v >> bit) & 1 for bit in range(1, 4096))
    result["u_inv"] = _inverse(higher_u)
    result["v_inv"] = _inverse(higher_v)
    return result
