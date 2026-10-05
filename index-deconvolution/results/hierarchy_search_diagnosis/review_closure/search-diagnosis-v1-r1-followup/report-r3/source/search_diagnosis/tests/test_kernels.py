"""Hand-derived fixtures for the D4 translations, the B configurations and D3 pricing."""
from __future__ import annotations

from dataclasses import fields

import pytest

from hierarchy import codes as C
from hierarchy.baselines import encode_baseline
from hierarchy.decode import decode_archive
from hierarchy.ledger import field_buckets
from hierarchy.segmentation import BoundaryConfig, supplied_partition
from hierarchy.wire import envelope, put_u

from search_diagnosis import kernels as K


def pair_archive(n: int, rules, start) -> bytes:
    body = put_u(len(rules)) + b"".join(put_u(a) + put_u(b) for a, b in rules)
    body += put_u(len(start)) + b"".join(put_u(s) for s in start)
    return envelope(C.CODEC_PAIR, n, body)


# -- period ---------------------------------------------------------------------

def test_period_ragged_tail_bytes_by_hand():
    bits = "011" * 3 + "01"                         # n = 11, p = 3, q = 3, tail 2
    src = encode_baseline(bits, "period")
    assert src.hex() == "4953443104" "0b" "02" "03" "60"
    info, arc = K.translate_period(bits, src)
    # rule0 LITERAL 3 '011' | rule1 REPEAT 0 x3 | rule2 LITERAL 2 '01' | rule3 CONCAT 1,2
    want = "4953443101" "0b" "0e" "04" "000360" "020003" "000240" "01020102"
    assert arc.hex() == want and decode_archive(arc) == bits
    assert (info["period"], info["copies"], info["tail_bits"], info["shape"]) == \
        (3, 3, 2, "repeat + tail literal")
    assert 8 * len(arc) - 8 * len(src) == 168 - 72


def test_period_exact_and_literal_cases():
    info, arc = K.translate_period("10" * 8, encode_baseline("10" * 8, "period"))
    assert info["shape"] == "repeat" and info["tail_bits"] == 0
    assert decode_archive(arc) == "10" * 8
    bits = "0010111"                                 # aperiodic: p = n, one copy
    info, arc = K.translate_period(bits, encode_baseline(bits, "period"))
    assert info["period"] == 7 and info["shape"].startswith("literal")
    assert decode_archive(arc) == bits


def test_period_refuses_a_foreign_input():
    src = encode_baseline("01" * 8, "period")
    with pytest.raises(Exception):
        K.translate_period("01" * 7 + "11", src)


def test_period_not_restricted_to_search_grid():
    w = "1" + "0" * 299                               # p = 300 > 256
    bits = w * 2 + w[:5]
    info, arc = K.translate_period(bits, encode_baseline(bits, "period"))
    assert info["period"] == 300 and info["status"] == "ok" and decode_archive(arc) == bits


# -- pair grammar ------------------------------------------------------------------

def test_pair_sharing_and_start_order_bytes_by_hand():
    src = pair_archive(6, [(0, 1), (2, 2)], [3, 2])  # '0101' + '01'
    assert decode_archive(src) == "010101"
    info, arc = K.translate_pair("010101", src)
    # r0 LIT '0' | r1 LIT '1' | r2 CONCAT 0,1 | r3 CONCAT 2,2 | r4 CONCAT 3,2
    want = "4953443101" "06" "13" "05" "000100" "000180" "01020001" "01020202" "01020302"
    assert arc.hex() == want
    assert info["symbol_to_rule"] == [0, 1, 2, 3] and info["unreachable_symbols"] == 0
    other = pair_archive(6, [(0, 1), (2, 2)], [2, 3])  # '01' + '0101': same string
    info2, arc2 = K.translate_pair("010101", other)
    assert arc2.hex().endswith("01020203") and arc2 != arc   # start order is transmitted
    assert decode_archive(arc2) == "010101"


def test_pair_unused_terminal_is_pruned():
    src = pair_archive(4, [(1, 1), (2, 2)], [3])     # '1111'
    info, arc = K.translate_pair("1111", src)
    assert info["unreachable_symbols"] == 1 and info["symbol_to_rule"][0] is None
    assert decode_archive(arc) == "1111"


def test_pair_graph_limit_is_unavailable_not_failure():
    rules = [(0, 1)] + [(k - 1, 1) for k in range(3, 67)]       # depth 66 chain
    n = 2 + 64
    src = pair_archive(n, rules, [66])
    bits = decode_archive(src)
    info, arc = K.translate_pair(bits, src)
    assert arc is None and info["status"] == "unavailable_graph_limit"
    assert info["dag_depth"] > K.MAX_DEPTH


def test_translate_ledgers_and_identity():
    bits = "0110" * 40 + "011"
    out, arcs = K.translate(bits, encode_baseline(bits, "period"),
                            encode_baseline(bits, "pair_grammar"))
    for m in ("period", "pair_grammar"):
        o = out[m]
        assert sum(o["translated_buckets"].values()) == o["translated_bits"]
        assert sum(o["baseline_buckets"].values()) == o["baseline_bits"]
        assert field_buckets(arcs[m]) == o["translated_buckets"]
        H = 999
        T, Cb = o["translated_bits"], o["baseline_bits"]
        assert H - Cb == (H - T) + (T - Cb)
        assert o["raw_clipped_bits"] == min(T, o["raw_bits"])


# -- boundary configurations and D3 pricing ------------------------------------------

def test_b8_differs_from_b0_only_in_three_caps():
    b0, b8 = K.CONFIGS["B0"], K.CONFIGS["B8"]
    assert b0 == BoundaryConfig()
    diff = {f.name for f in fields(BoundaryConfig) if getattr(b0, f.name) != getattr(b8, f.name)}
    assert diff == {"root_trial_cap", "cached_leaf_cap", "length_charge_multiplier"}
    assert (b8.root_trial_cap, b8.cached_leaf_cap, b8.length_charge_multiplier) == \
        (4096, 16384, 2048)


def test_boundary_job_receives_only_bits_and_name():
    bits = "0" * 200 + "01" * 100
    info, arcs = K.boundary(bits, "B0")
    assert decode_archive(arcs["output"]) == bits
    assert set(K.DETERMINISTIC_B) <= set(info)


def test_subsets_order_and_reference_reproduction():
    assert K.subsets_in_order([30, 10, 20]) == [(), (10,), (20,), (30,), (10, 20), (10, 30),
                                                (20, 30), (10, 20, 30)]
    bits = "0" * 100 + "1" * 100 + "10" * 50
    info, arcs = K.supplied_subsets(bits, [100, 200])
    assert [s["subset"] for s in info["subsets"]] == [[], [100], [200], [100, 200]]
    full = info["subsets"][-1]
    ref = supplied_partition(bits, [100, 200])["archive"]
    assert full["archive_bits"] == 8 * len(ref) and arcs[full["archive_sha256"]] == ref
    assert info["charges"]["root_trials"] == 4 and info["charges"]["leaf_cache"] <= 6


def test_subsets_refuse_bad_cuts():
    with pytest.raises(ValueError):
        K.supplied_subsets("01" * 50, [0, 10])
