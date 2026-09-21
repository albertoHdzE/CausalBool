"""Independent evaluators for serialized quadratic constraint rows.

This module deliberately operates on the serialized representations.  It does
not construct (or import) the constraint and gadget objects used to produce
those representations, so it can serve as an independent check of them.
"""

import re

from . import FIELD_PRIME


_DECIMAL = re.compile(r"^[+-]?\d+$")
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _mapping(value, what):
    if not isinstance(value, dict):
        raise ValueError(f"{what} must be an object")
    return value


def _decimal(value, what):
    """Parse a serialized decimal integer, rejecting implicit coercions."""
    if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise ValueError(f"{what} must be a decimal string")
    try:
        return int(value, 10)
    except ValueError as exc:  # defensive: fullmatch above should suffice
        raise ValueError(f"{what} must be a decimal string") from exc


def _canonical(value, what):
    if type(value) is not int or not 0 <= value < FIELD_PRIME:
        raise ValueError(f"{what} must be a canonical field integer")
    return value


def _require_prime(value):
    if _decimal(value, "prime") != FIELD_PRIME:
        raise ValueError("challenge constraint field required")


def _signal_names(system):
    names = []
    for field in ("public_inputs", "private_inputs", "auxiliary_signals"):
        values = system.get(field)
        if not isinstance(values, list):
            raise ValueError(f"{field} must be a list")
        for name in values:
            if not isinstance(name, str) or not _NAME.fullmatch(name):
                raise ValueError("invalid signal name")
            names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("duplicate signal name")
    return set(names)


def _linear(expression, witness, names, what):
    expression = _mapping(expression, what)
    if set(expression) != {"constant", "terms"}:
        raise ValueError(f"malformed {what}")
    constant = _decimal(expression["constant"], f"{what}.constant")
    terms = _mapping(expression["terms"], f"{what}.terms")
    total = constant
    for name, coefficient in terms.items():
        if not isinstance(name, str) or name not in names:
            raise ValueError("unknown signal")
        total += _decimal(coefficient, f"{what}.terms[{name!r}]") * witness[name]
    return total % FIELD_PRIME


def check_rows(system_dict, witness_dict):
    """Return labels of failing serialized quadratic rows.

    Both inputs are required to contain the exact serialized schema emitted by
    ``ConstraintSystem.to_dict`` and a complete canonical witness.
    """
    system = _mapping(system_dict, "system")
    if system.get("version") != "oxparc-r1cs-v1":
        raise ValueError("unsupported constraint system version")
    _require_prime(system.get("prime"))
    names = _signal_names(system)
    witness = _mapping(witness_dict, "witness")
    if set(witness) != names:
        raise ValueError("witness must contain exactly the declared signals")
    for name, value in witness.items():
        _canonical(value, f"witness[{name!r}]")

    rows = system.get("constraints")
    if not isinstance(rows, list):
        raise ValueError("constraints must be a list")
    failures = []
    for row_number, row in enumerate(rows):
        row = _mapping(row, f"constraints[{row_number}]")
        if set(row) != {"A", "B", "C", "label"}:
            raise ValueError(f"malformed constraints[{row_number}]")
        if not isinstance(row["label"], str):
            raise ValueError("constraint label must be a string")
        a = _linear(row["A"], witness, names, f"constraints[{row_number}].A")
        b = _linear(row["B"], witness, names, f"constraints[{row_number}].B")
        c = _linear(row["C"], witness, names, f"constraints[{row_number}].C")
        if (a * b - c) % FIELD_PRIME:
            failures.append(row["label"])
    return failures


def _compiled_linear(terms, witness, nvars, what):
    terms = _mapping(terms, what)
    total = 0
    for index, coefficient in terms.items():
        if not isinstance(index, str) or not re.fullmatch(r"(?:0|[1-9]\d*)", index):
            raise ValueError(f"{what} has an invalid witness index")
        position = int(index, 10)
        if position >= nvars:
            raise ValueError(f"{what} has an out-of-range witness index")
        total += _decimal(coefficient, f"{what}[{index!r}]") * witness[position]
    return total % FIELD_PRIME


def check_compiled_rows(exported_r1cs_dict, witness_list):
    """Return indices of failing rows in a serialized snarkjs R1CS export."""
    exported = _mapping(exported_r1cs_dict, "exported R1CS")
    _require_prime(exported.get("prime"))
    nvars = exported.get("nVars")
    if type(nvars) is not int or nvars <= 0:
        raise ValueError("nVars must be a positive integer")
    if not isinstance(witness_list, list) or len(witness_list) != nvars:
        raise ValueError("witness length must equal nVars")
    for position, value in enumerate(witness_list):
        _canonical(value, f"witness[{position}]")
    if witness_list[0] != 1:
        raise ValueError("compiled witness[0] must be one")

    rows = exported.get("constraints")
    if not isinstance(rows, list):
        raise ValueError("constraints must be a list")
    failures = []
    for row_number, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(f"constraints[{row_number}] must contain [A, B, C]")
        a = _compiled_linear(row[0], witness_list, nvars, f"constraints[{row_number}].A")
        b = _compiled_linear(row[1], witness_list, nvars, f"constraints[{row_number}].B")
        c = _compiled_linear(row[2], witness_list, nvars, f"constraints[{row_number}].C")
        if (a * b - c) % FIELD_PRIME:
            failures.append(row_number)
    return failures
