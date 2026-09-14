"""Canonical codecs for distribution and mechanism description lengths.

The distribution codec is a reversible, self-delimiting rational codec.  It is
not silently called the native CausalBool ``Locations/Sumandos`` mechanism
encoding; that encoding is exposed separately for explicit ablation studies.
"""
from __future__ import annotations

import json
import hashlib
from typing import Any


def _gamma_encode(x: int) -> str:
    if x < 1:
        raise ValueError("gamma code requires x >= 1")
    bits = bin(x)[2:]
    return "0" * (len(bits) - 1) + bits


def _gamma_decode(bits: str, i: int) -> tuple[int, int]:
    start = i
    while i < len(bits) and bits[i] == "0":
        i += 1
    zeros = i - start
    end = i + zeros + 1
    if end > len(bits):
        raise ValueError("truncated gamma code")
    return int(bits[i:end], 2), end


def _state_bits(state: int, n: int) -> str:
    return "".join("1" if state >> i & 1 else "0" for i in range(n))


def _validate_rep(rep: dict[str, Any]) -> tuple[int, list[int], list[int], int]:
    n = int(rep["cols"])
    support = list(rep.get("support", []))
    counts = list(rep.get("counts", []))
    denominator = int(rep.get("probability_denominator", 1))
    if n < 0 or denominator < 1 or len(support) != len(counts):
        raise ValueError("malformed repertoire")
    if support != sorted(set(support)):
        raise ValueError("support must be sorted and unique")
    if any(not isinstance(s, int) or s < 0 or s >= 1 << n for s in support):
        raise ValueError("support state out of range")
    if any(not isinstance(c, int) or c <= 0 for c in counts):
        raise ValueError("counts must be positive integers")
    if sum(counts) != denominator:
        raise ValueError("counts must sum to probability_denominator")
    return n, support, counts, denominator


def encode_repertoire(rep: dict[str, Any], include_schema: bool = True) -> dict[str, Any]:
    """Encode one exact rational distribution and return lengths and payloads."""
    n, support, counts, denominator = _validate_rep(rep)
    # Decimal stream: n, support cardinality, then fixed-width LSB-first states.
    decimal = _gamma_encode(n + 1) + _gamma_encode(len(support) + 1)
    decimal += "".join(_state_bits(s, n) for s in support)
    # Summandos stream: n, cardinality, shared denominator, then numerators.
    summandos = (_gamma_encode(n + 1) + _gamma_encode(len(support) + 1)
                 + _gamma_encode(denominator))
    summandos += "".join(_gamma_encode(c) for c in counts)
    schema_length = None
    if include_schema and "matrix" in rep:
        from .adapters import schema_normal_form_length
        schema_length = float(sum(schema_normal_form_length([row[k] for row in rep["matrix"]], n)
                                  for k in range(n)))
    json_payload = json.dumps(
        {"N": n, "support": support, "counts": counts,
         "probability_denominator": denominator},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return {"decimal_bits": len(decimal), "summandos_bits": len(summandos),
            "L_CB_bits": len(decimal) + len(summandos), "decimal_str": decimal,
            "summandos_str": summandos, "schema_length": schema_length,
            "codec": "canonical_distribution_v2", "codec_metadata_bits": 0,
            "encoding_sensitivity": {
                "canonical_distribution_bits": len(decimal) + len(summandos),
                "json_distribution_bits": 8 * len(json_payload),
                "support_only_bits": len(_gamma_encode(len(support) + 1)) + n * len(support),
            }}


def decode_repertoire(decimal_str: str, summandos_str: str, n: int) -> dict[str, Any]:
    """Decode the exact distribution codec and verify all framing metadata."""
    encoded_n, i = _gamma_decode(decimal_str, 0)
    count, i = _gamma_decode(decimal_str, i)
    if encoded_n != n + 1 or i + (count - 1) * n != len(decimal_str):
        raise ValueError("invalid decimal stream framing")
    support = []
    for _ in range(count - 1):
        bits = decimal_str[i:i + n]
        support.append(int(bits[::-1], 2) if bits else 0)
        i += n
    encoded_n2, j = _gamma_decode(summandos_str, 0)
    count2, j = _gamma_decode(summandos_str, j)
    denominator, j = _gamma_decode(summandos_str, j)
    if encoded_n2 != n + 1 or count2 != count:
        raise ValueError("decimal/summandos framing mismatch")
    counts = []
    for _ in range(count - 1):
        value, j = _gamma_decode(summandos_str, j)
        counts.append(value)
    if j != len(summandos_str) or support != sorted(set(support)) or sum(counts) != denominator:
        raise ValueError("invalid distribution payload")
    return {"rows": 1 << n, "cols": n, "matrix_lsb_first": True,
            "support": support, "counts": counts, "probability_denominator": denominator,
            "probs": [c / denominator for c in counts], "observable": "distribution"}


def _lcm(a: int, b: int) -> int:
    x, y = a, b
    while y:
        x, y = y, x % y
    return a * b // x


def _encode_pair(rep_a: dict[str, Any], rep_b: dict[str, Any]) -> tuple[str, str]:
    na, sa, ca, da = _validate_rep(rep_a)
    nb, sb, cb, db = _validate_rep(rep_b)
    if na != nb:
        raise ValueError("pair requires equal N")
    denominator = _lcm(da, db)
    amap = {s: c * denominator // da for s, c in zip(sa, ca)}
    bmap = {s: c * denominator // db for s, c in zip(sb, cb)}
    states = sorted(set(amap) | set(bmap))
    # Canonical joint payload: sorted states, both count vectors, shared header.
    decimal = _gamma_encode(na + 1) + _gamma_encode(len(states) + 1)
    decimal += "".join(_state_bits(s, na) for s in states)
    summandos = _gamma_encode(na + 1) + _gamma_encode(len(states) + 1) + _gamma_encode(denominator)
    summandos += "".join(_gamma_encode(amap.get(s, 0) + 1) + _gamma_encode(bmap.get(s, 0) + 1) for s in states)
    return decimal, summandos


def native_mechanism_encoding(A: list[list[int]], gates: list[str], params: list[dict] | None = None) -> str:
    """Canonical payload for the mechanism, separate from distribution coding."""
    payload = {"A": A, "gates": gates, "params": params or [{} for _ in gates],
               "orientation": "A[target][source]"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "".join(f"{byte:08b}" for byte in raw)


def simple_baseline_lengths(rep: dict[str, Any]) -> dict[str, int]:
    """Lengths for support-only and explicit state/count baselines."""
    n, support, counts, _ = _validate_rep(rep)
    return {"support_only_bits": len(_gamma_encode(len(support) + 1)) + n * len(support),
            "explicit_distribution_bits": len(encode_repertoire(rep, include_schema=False)["decimal_str"])
            + sum(len(_gamma_encode(c)) for c in counts)}


def ncd(rep_a: dict[str, Any], rep_b: dict[str, Any]) -> dict[str, Any]:
    """Symmetric NCD from a canonical joint distribution codec."""
    a, b = encode_repertoire(rep_a, include_schema=False), encode_repertoire(rep_b, include_schema=False)
    decimal, summandos = _encode_pair(rep_a, rep_b)
    concat = len(decimal) + len(summandos)
    la, lb = a["L_CB_bits"], b["L_CB_bits"]
    denominator = max(la, lb)
    return {"L_CB_A": la, "L_CB_0": lb, "L_CB_concat": concat,
            "NCD": (concat - min(la, lb)) / denominator if denominator else 0.0,
            "self_distance_overhead_bits": concat - la if rep_a == rep_b else None,
            "pair_codec": "canonical_symmetric_union_v2"}


# ---------------------------------------------------------------------------
# Complete one-step behaviour codec
# ---------------------------------------------------------------------------

FULL_BEHAVIOUR_CODEC = "canonical_decimal_sumandos_v1"


class MaterializationRequired(RuntimeError):
    """Raised when an arbitrary additive pair has no algebraic cardinality."""


def _as_nonnegative_ints(values: Any, field: str) -> list[int]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    result = [int(value) for value in values]
    if any(value < 0 for value in result):
        raise ValueError(f"{field} must contain non-negative integers")
    if result != sorted(set(result)):
        raise ValueError(f"{field} must be sorted and unique")
    return result


def _pattern_integer(pattern: Any, n: int) -> int:
    if isinstance(pattern, int):
        value = pattern
    else:
        if not isinstance(pattern, (list, tuple)) or len(pattern) != n:
            raise ValueError("output pattern must be an N-bit list")
        if any(bit not in (0, 1) for bit in pattern):
            raise ValueError("output pattern bits must be 0 or 1")
        value = sum(int(bit) << index for index, bit in enumerate(pattern))
    if value < 0 or value >= 1 << n:
        raise ValueError("output pattern is outside the N-bit alphabet")
    return value


def _pattern_bits(value: int, n: int) -> list[int]:
    return [(value >> index) & 1 for index in range(n)]


def unfold_decimal_sumandos(
    decimal_repertoire: list[int] | tuple[int, ...],
    sumandos: list[int] | tuple[int, ...],
    network_size: int | None = None,
) -> list[int]:
    """Decode an exact zero-based ``DecimalRepertoire + Sumandos`` pair.

    The mathematical rule is ``{decimal + sumando}``.  The result is a
    canonical sorted set: duplicate sums are removed because exhaustive
    positions are a set of input locations, not a multiset.  If ``network_size``
    is supplied, every position is checked against ``0 ... 2**N-1``.

    This function is deliberately explicit and should be used for small
    explanatory examples or validation.  Large experiments should use
    :func:`decimal_sumandos_cardinality` and the recorded counts instead of
    materialising the Cartesian sum.
    """
    decimals = _as_nonnegative_ints(decimal_repertoire, "DecimalRepertoire")
    offsets = _as_nonnegative_ints(sumandos, "Sumandos")
    if not decimals or not offsets:
        return []
    positions = sorted({decimal + offset for decimal in decimals for offset in offsets})
    if network_size is not None:
        if network_size < 0:
            raise ValueError("network_size must be non-negative")
        limit = 1 << network_size
        if any(position >= limit for position in positions):
            raise ValueError("unfolded position is outside the exhaustive state space")
    return positions


def _subset_sum_offsets(mask: int) -> list[int]:
    bits = [1 << index for index in range(mask.bit_length()) if mask & (1 << index)]
    offsets = [0]
    for bit in bits:
        offsets += [offset + bit for offset in list(offsets)]
    return sorted(offsets)


def _closed_subcube_mask(positions: set[int]) -> int:
    """Return bit directions under which ``positions`` is closed."""
    if not positions:
        return 0
    mask = 0
    for bit_index in range(max(positions).bit_length()):
        bit = 1 << bit_index
        if all((position ^ bit) in positions for position in positions):
            mask |= bit
    return mask


def canonical_decimal_sumandos_pair(
    positions: list[int] | tuple[int, ...],
    network_size: int,
    *,
    max_explicit_sumandos_bits: int = 20,
) -> tuple[list[int], list[int], bool]:
    """Choose a deterministic additive pair for an exact position set.

    The canonical factorisation uses every bit direction for which the set is
    closed under XOR.  In the resulting pair, anchors have those bits clear,
    so ordinary addition and XOR agree and the translates are disjoint.  If
    the inferred offset family is too large to list, the safe canonical
    fallback is ``positions + {0}``; this keeps the representation exact and
    avoids silently expanding a large set.
    """
    if network_size < 0:
        raise ValueError("network_size must be non-negative")
    state_limit = 1 << network_size
    values = sorted(set(int(position) for position in positions))
    if any(position < 0 or position >= state_limit for position in values):
        raise ValueError("position is outside the exhaustive state space")
    if not values:
        return [], [], True
    mask = _closed_subcube_mask(set(values))
    n_offsets = 1 << mask.bit_count()
    if n_offsets > (1 << max_explicit_sumandos_bits):
        return values, [0], True
    offsets = _subset_sum_offsets(mask)
    anchors = sorted(position for position in values if not (position & mask))
    unfolded = sorted({anchor + offset for anchor in anchors for offset in offsets})
    if unfolded != values:
        return values, [0], True
    return anchors, offsets, len(anchors) * len(offsets) == len(values)


def decimal_sumandos_cardinality(
    decimal_repertoire: list[int] | tuple[int, ...],
    sumandos: list[int] | tuple[int, ...],
    *,
    disjoint: bool = False,
) -> int:
    """Return an exact pair cardinality without unfolding when justified.

    A certified disjoint pair has cardinality ``|D|*|S|``.  The singleton
    offset case is also algebraically safe.  An arbitrary pair can contain
    collisions (for example ``{1,2,3,4}+{2,3}``), so this function refuses to
    guess and asks the caller to use the explicit decoder for such a case.
    """
    decimals = _as_nonnegative_ints(decimal_repertoire, "DecimalRepertoire")
    offsets = _as_nonnegative_ints(sumandos, "Sumandos")
    if not decimals or not offsets:
        return 0
    if len(offsets) == 1 or disjoint:
        return len(decimals) * len(offsets) if disjoint else len(set(decimals[i] + offsets[0] for i in range(len(decimals))))
    raise MaterializationRequired(
        "pair collisions are not ruled out; use unfold_decimal_sumandos for an exact count"
    )


def one_step_statistics_from_encoding(encoding: dict[str, Any]) -> dict[str, Any]:
    """Derive exact counts and probabilities from additive pairs only.

    This is the large-network statistics path: it never calls the unfolding
    decoder.  Each row must either carry an exact owner-provided count or be a
    certified disjoint pair, in which case ``|D|*|S|`` is exact.
    """
    n, _, rows = _normalise_full_behaviour(encoding)
    counts = []
    patterns = []
    for row in rows:
        provided_count = row.get("occurrence_count")
        if row["pair_is_disjoint"]:
            count = decimal_sumandos_cardinality(
                row["DecimalRepertoire"], row["Sumandos"], disjoint=True
            )
            if provided_count is not None and int(provided_count) != count:
                raise ValueError("owner count disagrees with algebraic pair cardinality")
        elif provided_count is not None:
            # An owner may supply an exact symbolic count for a pair whose
            # translates are not certified disjoint.  Do not unfold it here.
            count = int(provided_count)
        else:
            count = decimal_sumandos_cardinality(
                row["DecimalRepertoire"], row["Sumandos"], disjoint=False
            )
        counts.append(int(count))
        patterns.append(row["output_pattern"])
    denominator = 1 << n
    total = sum(counts)
    return {
        "counts": counts,
        "patterns": patterns,
        "total_occurrences": total,
        "expected_occurrences": denominator,
        "counts_sum_exact": total == denominator,
        "probabilities": [
            {"numerator": count, "denominator": denominator} for count in counts
        ],
        "support_size": sum(count > 0 for count in counts),
        "positions_materialized": False,
    }


def _varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint requires a non-negative integer")
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def _normalise_full_behaviour(encoding: dict[str, Any]) -> tuple[int, int, list[dict[str, Any]]]:
    n = int(encoding["network_size"])
    division_size = int(encoding.get("division_size", 2))
    if n < 0 or division_size < 1:
        raise ValueError("invalid network-size framing")
    rows = encoding.get("representations", encoding.get("output_repertoire", []))
    if not isinstance(rows, list):
        raise ValueError("representations must be a list")
    normalised: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("representation row must be an object")
        pattern_value = _pattern_integer(row.get("output_pattern", row.get("pattern")), n)
        decimals = _as_nonnegative_ints(
            row.get("DecimalRepertoire", row.get("decimal_repertoire", [])),
            "DecimalRepertoire",
        )
        offsets = _as_nonnegative_ints(
            row.get("Sumandos", row.get("sumandos", [])), "Sumandos"
        )
        count = row.get("occurrence_count")
        if count is None:
            count = decimal_sumandos_cardinality(
                decimals, offsets, disjoint=bool(row.get("pair_is_disjoint", False))
            )
        count = int(count)
        if count < 0:
            raise ValueError("occurrence_count must be non-negative")
        normalised.append({
            "pattern_value": pattern_value,
            "output_pattern": _pattern_bits(pattern_value, n),
            "DecimalRepertoire": decimals,
            "Sumandos": offsets,
            "occurrence_count": count,
            "pair_is_disjoint": bool(row.get("pair_is_disjoint", False)),
        })
    normalised.sort(key=lambda row: row["pattern_value"])
    if len({row["pattern_value"] for row in normalised}) != len(normalised):
        raise ValueError("output patterns must be unique")
    return n, division_size, normalised


def canonical_serialize_full_behaviour(encoding: dict[str, Any]) -> bytes:
    """Serialize the exact complete one-step representation canonically."""
    n, division_size, rows = _normalise_full_behaviour(encoding)
    output_bytes = (n + 7) // 8
    payload = bytearray(b"CBFB")
    payload.append(1)  # codec version
    payload += _varint(n)
    payload += _varint(division_size)
    payload += _varint(len(rows))
    for row in rows:
        pattern_value = row["pattern_value"]
        payload += int(pattern_value).to_bytes(output_bytes, "little") if output_bytes else b""
        decimals = row["DecimalRepertoire"]
        offsets = row["Sumandos"]
        payload += _varint(len(decimals))
        for value in decimals:
            payload += _varint(value)
        payload += _varint(len(offsets))
        for value in offsets:
            payload += _varint(value)
    return bytes(payload)


def flat_index_content_bitstring(encoding: dict[str, Any]) -> str:
    """Return only the flat DecimalRepertoire/Sumandos value stream.

    Output patterns are traversed in canonical decimal order, so pattern
    identifiers are not emitted.  Each DecimalRepertoire value is followed by
    each Sumandos value for that row, using a fixed-width LSB-first N-bit
    representation.  Row cardinalities, headers, delimiters, and other wire
    framing are intentionally excluded from this semantic content score.

    The result is deliberately *not* a standalone decoder stream: its row and
    list boundaries come from the fixed external convention.  The complete
    self-delimiting representation remains ``canonical_serialize_full_behaviour``.
    """
    n, _, rows = _normalise_full_behaviour(encoding)
    width = max(1, n)
    limit = 1 << n
    bits: list[str] = []
    for row in rows:
        for field in ("DecimalRepertoire", "Sumandos"):
            for value in row[field]:
                if value >= limit:
                    raise ValueError(f"{field} value is outside the N-bit state alphabet")
                bits.append(format(value, f"0{width}b")[::-1])
    return "".join(bits)


def flat_index_content_metadata(encoding: dict[str, Any]) -> dict[str, Any]:
    """Return semantic flat-stream length and identity metadata."""
    bits = flat_index_content_bitstring(encoding)
    padding_bits = (-len(bits)) % 8
    return {
        "flat_index_content_codec": "flat_decimal_sumandos_values_v1",
        "flat_index_content_bit_length": len(bits),
        "flat_index_content_padding_bits_for_bytes": padding_bits,
        "flat_index_content_sha256": hashlib.sha256(bits.encode("ascii")).hexdigest(),
        "flat_index_content_is_standalone_stream": False,
    }


def _normalise_whole_repertoire(encoding: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    n = int(encoding["network_size"])
    rows = encoding.get("column_representations", [])
    if n < 0 or not isinstance(rows, list) or len(rows) != n:
        raise ValueError("whole repertoire must contain one row per output column")
    normalised = []
    for expected_node, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("column representation must be an object")
        node = int(row.get("node", expected_node))
        if node != expected_node:
            raise ValueError("column representations must be in node order")
        normalised.append({
            "node": node,
            "DecimalRepertoire": _as_nonnegative_ints(
                row.get("DecimalRepertoire", []), "DecimalRepertoire"
            ),
            "Sumandos": _as_nonnegative_ints(
                row.get("Sumandos", []), "Sumandos"
            ),
        })
    return n, normalised


def flat_whole_repertoire_content_bitstring(encoding: dict[str, Any]) -> str:
    """Return the semantic D/S stream for the whole output repertoire.

    The input repertoire and output-column order are implicit.  The stream
    contains only the fixed-width values in one DecimalRepertoire/Sumandos pair
    per output column; it does not enumerate or identify full output patterns.
    """
    n, rows = _normalise_whole_repertoire(encoding)
    width = max(1, n)
    limit = 1 << n
    bits: list[str] = []
    for row in rows:
        for field in ("DecimalRepertoire", "Sumandos"):
            for value in row[field]:
                if value >= limit:
                    raise ValueError(f"{field} value is outside the N-bit state alphabet")
                bits.append(format(value, f"0{width}b")[::-1])
    return "".join(bits)


def canonical_serialize_whole_repertoire(encoding: dict[str, Any]) -> bytes:
    """Serialize the ordered whole-repertoire column pairs for audit use."""
    n, rows = _normalise_whole_repertoire(encoding)
    payload = bytearray(b"CBWR")
    payload.append(1)
    payload += _varint(n)
    payload += _varint(len(rows))
    for row in rows:
        decimals = row["DecimalRepertoire"]
        offsets = row["Sumandos"]
        payload += _varint(len(decimals))
        for value in decimals:
            payload += _varint(value)
        payload += _varint(len(offsets))
        for value in offsets:
            payload += _varint(value)
    return bytes(payload)


def whole_repertoire_encoding_metadata(encoding: dict[str, Any]) -> dict[str, Any]:
    bits = flat_whole_repertoire_content_bitstring(encoding)
    payload = canonical_serialize_whole_repertoire(encoding)
    return {
        "whole_repertoire_codec": "canonical_column_decimal_sumandos_v1",
        "flat_index_content_codec": "flat_column_decimal_sumandos_values_v1",
        "flat_index_content_bit_length": len(bits),
        "flat_index_content_padding_bits_for_bytes": (-len(bits)) % 8,
        "flat_index_content_sha256": hashlib.sha256(bits.encode("ascii")).hexdigest(),
        "canonical_serialization_sha256": hashlib.sha256(payload).hexdigest(),
        "encoded_bit_length": len(payload) * 8,
        "data_bit_length": len(payload) * 8,
        "total_declared_program_length_bits": None,
        "serialization_bytes": len(payload),
        "flat_index_content_is_standalone_stream": False,
    }


def full_behaviour_encoding_metadata(encoding: dict[str, Any]) -> dict[str, Any]:
    """Return stable length and digest metadata for the full-behaviour codec."""
    payload = canonical_serialize_full_behaviour(encoding)
    digest = hashlib.sha256(payload).hexdigest()
    data_bits = len(payload) * 8
    return {
        "codec": FULL_BEHAVIOUR_CODEC,
        "encoded_bit_length": data_bits,
        "data_bit_length": data_bits,
        "fixed_decoder_overhead_bits": None,
        "total_declared_program_length_bits": None,
        "canonical_serialization_sha256": digest,
        "serialization_bytes": len(payload),
        **flat_index_content_metadata(encoding),
    }


def bdm_full_behaviour(
    encoding: dict[str, Any], *, input_mode: str = "wire"
) -> dict[str, Any]:
    """Run optional BDM on the declared wire or semantic content input.

    ``input_mode='flat_index'`` is the Section 12 comparison: BDM receives the
    same semantic DecimalRepertoire/Sumandos value stream used by the legacy
    per-output-pattern flat index-content length.  ``input_mode='whole_index'``
    applies the same comparison to the whole ordered output-repertoire owner,
    one pair per output column.  ``input_mode='wire'`` preserves the original
    audit behavior over the complete canonical serialization.
    """
    if input_mode == "flat_index":
        bits = flat_index_content_bitstring(encoding)
        source_codec = "flat_decimal_sumandos_values_v1"
        semantic_bit_length = len(bits)
    elif input_mode == "whole_index":
        bits = flat_whole_repertoire_content_bitstring(encoding)
        source_codec = "flat_column_decimal_sumandos_values_v1"
        semantic_bit_length = len(bits)
    elif input_mode == "wire":
        payload = canonical_serialize_full_behaviour(encoding)
        bits = "".join(f"{byte:08b}" for byte in payload)
        source_codec = FULL_BEHAVIOUR_CODEC
        semantic_bit_length = len(bits)
    else:
        raise ValueError("input_mode must be 'flat_index', 'whole_index', or 'wire'")
    width = max(4, int(len(bits) ** 0.5))
    rows = (len(bits) + width - 1) // width
    padded = bits.ljust(rows * width, "0")
    provenance = {
        "implementation": "pybdm",
        "version": "0.1.0",
        "dimensionality": 2,
        "input_shape": [rows, width],
        "padding_policy": "right_zero_pad_to_declared_rectangle",
        "input_mode": input_mode,
        "source_codec": source_codec,
        "semantic_bit_length": semantic_bit_length,
        "padded_bit_length": len(padded),
    }
    try:
        import numpy as np
        from .adapters import bdm_2d
        matrix = np.asarray([[int(bit) for bit in padded[i:i + width]]
                             for i in range(0, len(padded), width)], dtype=int)
        value = bdm_2d(matrix, below_floor="raise")
    except ImportError as exc:
        return {"status": "failed_missing_dependency", "value": None,
                "failure": str(exc), "provenance": provenance}
    except Exception as exc:  # pybdm errors are part of the explicit comparison record
        return {"status": "failed_bdm_execution", "value": None,
                "failure": str(exc), "provenance": provenance}
    return {"status": "completed", "value": value, "failure": None,
            "provenance": provenance}
