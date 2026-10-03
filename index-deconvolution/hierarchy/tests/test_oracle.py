"""Tiny bounded oracle (protocol 5.3): exact language, minima, and search gaps."""
from __future__ import annotations

import re

from hierarchy.decode import decode_archive
from hierarchy.infer import FULL, RESTRICTED_ORACLE, infer
from hierarchy.model import Concat, Literal, Model, Repeat
from hierarchy.tests import oracle
from hierarchy.wire import encode_literal, serialize_model


def _model(prog: str) -> Model:
    m = re.fullmatch(r"L\((\w+)\)", prog)
    if m:
        return Model((Literal(m[1]),))
    m = re.fullmatch(r"R\(L\((\w+)\),(\d+)\)", prog)
    if m:
        return Model((Literal(m[1]), Repeat(0, int(m[2]))))
    m = re.fullmatch(r"R\(R\(L\((\w+)\),(\d+)\),(\d+)\)", prog)
    if m:
        return Model((Literal(m[1]), Repeat(0, int(m[2])), Repeat(1, int(m[3]))))
    m = re.fullmatch(r"C\(L\((\w+)\),L\((\w+)\)\)", prog)
    return Model((Literal(m[1]), Literal(m[2]), Concat((0, 1))))


def test_oracle_serializer_agrees_with_the_production_serializer():
    k = 0
    for prog, out, arc in oracle.tree_archives(oracle.all_words(1, 3), 12):
        assert serialize_model(_model(prog), len(out)) == arc
        assert decode_archive(arc) == out
        k += 1
    assert k > 100
    assert oracle.raw_archive("0110") == encode_literal("0110")


def test_n8_oracle_covers_every_target_and_restricted_search_is_never_below_it():
    table = oracle.oracle_n8()
    assert len(table) == 511
    worse = 0
    for s, row in table.items():
        r = infer(s, RESTRICTED_ORACLE)
        assert r.archive_bits >= row["raw_inclusive_bits"]
        worse += r.archive_bits > row["raw_inclusive_bits"]
    assert worse == 0          # measured gap on n <= 8; reported, see SEARCH_SPEC.md


def test_repetition_changes_the_winner_for_64_identical_bits():
    table = oracle.oracle_generated64()
    row = table["1" * 64]
    assert row["grammar_only_bits"] < row["raw_bits"]
    assert row["raw_inclusive_mode"] == "hid"
    assert row["grammar_only_bits"] == 8 * 14       # R(L(1),64): 4+1+1+1 + 1+3+3
    r = infer("1" * 64, RESTRICTED_ORACLE)
    assert r.mode == "hid" and r.archive_bits == row["raw_inclusive_bits"]
    assert infer("1" * 64, FULL).archive_bits <= row["raw_inclusive_bits"]


def test_generated64_targets_bound_the_restricted_search_from_below():
    table = oracle.oracle_generated64()
    assert len(table) > 500
    for s in table:
        r = infer(s, RESTRICTED_ORACLE)
        assert r.archive_bits >= table[s]["raw_inclusive_bits"]
