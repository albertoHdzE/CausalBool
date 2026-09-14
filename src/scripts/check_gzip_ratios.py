"""gzip compression ratios for short binary strings.

AUDIT04 Phase 2. The whole body used to run at module level, so importing this
file executed every check and printed to stdout. It is kept because it records
what was checked -- gzip EXPANDS short strings, which is the observation behind
the project's refusal to read a compressed size as a complexity for small n --
but it now runs only when invoked.

Determinism: the 100-bit case drew from an UNSEEDED `random`, so the printed
ratio differed on every run and could not be reproduced. The seed is now pinned
and declared, per the project convention that stochastic toggles carry a
recorded seed.
"""
import gzip
import random

SEED = 2026


def check_gzip(s):
    """Print original vs gzip-compressed size for a binary string."""
    # Assume ASCII '0'/'1' encoding as that's standard for string compression tests
    data = s.encode('utf-8')
    original_size = len(data)
    compressed_size = len(gzip.compress(data))

    print(f"String: '{s}' (Len {original_size})")
    print(f"  Compressed Size: {compressed_size}")
    print(f"  Ratio (Comp/Orig): {compressed_size / original_size:.2f} ( >1.0 means expansion)")
    print(f"  Ratio (Orig/Comp): {original_size / compressed_size:.2f} ( <1.0 means expansion)")
    print("-" * 30)


def main() -> int:
    print("--- Biological Strings ---")
    check_gzip("00")          # Len 2
    check_gzip("0101")        # Len 4
    check_gzip("00001111")    # Len 8

    print("\n--- Random Strings ---")
    check_gzip("110100101110")   # Len 12
    check_gzip("1" * 50)         # Len 50 (Low entropy)

    rng = random.Random(SEED)
    r100 = "".join(str(rng.randint(0, 1)) for _ in range(100))
    check_gzip(r100)             # Len 100, seed pinned above
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
