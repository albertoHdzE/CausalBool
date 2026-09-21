"""Exact integer-oracle recovery and positional packing."""


def _integer(value, name):
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return value


def _base(base):
    _integer(base, "base")
    if base <= 1:
        raise ValueError("base must exceed one")
    return base


def pack(values, base):
    base = _base(base)
    try:
        vals = list(values)
    except (TypeError, ValueError):
        raise ValueError("values must be an iterable") from None
    if not vals:
        raise ValueError("values must be nonempty")
    result = 0
    for i, digit in enumerate(vals):
        if type(digit) is not int or not 0 < digit < base:
            raise ValueError("digits must be positive integers below base")
        result += digit * base**i
    return result


def unpack(value, n, base):
    base = _base(base)
    _integer(value, "value")
    _integer(n, "n")
    if value < 0 or n <= 0:
        raise ValueError("value and n are out of range")
    out = [0] * n
    remaining = value
    for i in range(n):
        remaining, digit = divmod(remaining, base)
        if digit == 0:
            raise ValueError("packed value contains an invalid digit")
        out[i] = digit
    if remaining:
        raise ValueError("packed value does not fit n digits")
    return out


def recover(n, oracle, *, bound=None):
    _integer(n, "n")
    if n <= 0:
        raise ValueError("n must be positive")
    if bound is not None:
        _integer(bound, "bound")
        if bound <= 0:
            raise ValueError("bound must be positive")

    def ask(query):
        if len(query) != n or any(type(x) is not int for x in query):
            raise ValueError("invalid query")
        answer = oracle(query)
        if type(answer) is not int or answer <= 0:
            raise ValueError("oracle response must be a positive integer")
        return answer

    def decode(encoded, base):
        values = []
        remaining = encoded
        for _ in range(n):
            remaining, digit = divmod(remaining, base)
            if digit == 0:
                raise ValueError("oracle response contains an invalid digit")
            values.append(digit)
        if remaining:
            raise ValueError("oracle response does not fit n digits")
        return values

    if bound is None:
        first = ask([1] * n)
        if n == 1:
            values = [first]
        else:
            base = first + 1
            encoded = ask([base**i for i in range(n)])
            values = decode(encoded, base)
    else:
        base = bound + 1
        encoded = ask([base**i for i in range(n)])
        values = decode(encoded, base)
    if any(type(x) is not int or x <= 0 for x in values):
        raise ValueError("recovered invalid digit")
    if bound is not None and any(x > bound for x in values):
        raise ValueError("recovered value exceeds bound")
    if bound is None:
        # The first query is the sum; retain it as a consistency check.
        if sum(values) != first:
            raise ValueError("oracle responses are inconsistent")
    return values
