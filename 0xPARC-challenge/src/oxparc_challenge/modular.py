"""Small-prime verification of the four-variable cubic identity."""


def _poly_add(left, right):
    out = dict(left)
    for monomial, coefficient in right.items():
        out[monomial] = out.get(monomial, 0) + coefficient
        if not out[monomial]:
            del out[monomial]
    return out


def _poly_mul(left, right):
    out = {}
    for lm, lc in left.items():
        for rm, rc in right.items():
            monomial = tuple(a + b for a, b in zip(lm, rm))
            out[monomial] = out.get(monomial, 0) + lc * rc
    return {m: c for m, c in out.items() if c}


def _var(index):
    monomial = [0, 0, 0]
    monomial[index] = 1
    return {tuple(monomial): 1}


def cubic_identity_coefficients():
    a, b, c = (_var(i) for i in range(3))
    d = {m: -coefficient for m, coefficient in _poly_add(_poly_add(a, b), c).items()}
    cubes = _poly_add(_poly_add(_poly_mul(_poly_mul(a, a), a), _poly_mul(_poly_mul(b, b), b)),
                      _poly_add(_poly_mul(_poly_mul(c, c), c), _poly_mul(_poly_mul(d, d), d)))
    ab = _poly_add(a, b)
    ac = _poly_add(a, c)
    bc = _poly_add(b, c)
    identity = _poly_add(cubes, {m: 3 * coefficient for m, coefficient in
                                 _poly_mul(_poly_mul(ab, ac), bc).items()})
    return identity


def solutions(p):
    if type(p) is not int or p <= 1 or p > 31:
        raise ValueError("p must be an integer in [2, 31]")
    if any(p % q == 0 for q in range(2, int(p**0.5) + 1)):
        raise ValueError("p must be prime")
    result = []
    for a in range(p):
        for b in range(p):
            for c in range(p):
                d = (-a - b - c) % p
                if ((a*a + b*b + c*c + d*d) % p == 0 and
                        (a**3 + b**3 + c**3 + d**3) % p == 0):
                    result.append((a, b, c, d))
    return result
