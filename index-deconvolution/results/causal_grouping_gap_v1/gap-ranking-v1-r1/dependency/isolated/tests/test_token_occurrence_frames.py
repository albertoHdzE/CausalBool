"""Tests for token_occurrence_frames (causal-grouping-gap-v1, ticket U2)."""

from __future__ import annotations

import pytest

from seqdecon.operators import (
    OPERATOR_GROUP,
    OPERATOR_GROUP_VERSION,
    gaps,
    operator_group_hash,
    token_occurrence_frames,
)


def test_frames_of_a_value_and_their_gaps():
    frames = token_occurrence_frames([2, 1, 2, 2, 1, 2], 2)
    assert frames == [0, 2, 3, 5]
    assert gaps(frames) == [2, 1, 2]


def test_constant_tokens_keep_every_frame_not_only_transitions():
    assert token_occurrence_frames([3, 3, 3, 3], 3) == [0, 1, 2, 3]


def test_absent_value_and_empty_tokens_give_empty():
    assert token_occurrence_frames([0, 1, 0], 5) == []
    assert token_occurrence_frames([], 0) == []


def test_tuple_and_generator_inputs_are_accepted():
    assert token_occurrence_frames((1, 0, 1), 1) == [0, 2]
    assert token_occurrence_frames((t for t in (1, 0, 1)), 0) == [1]


@pytest.mark.parametrize(
    "tokens, value",
    [
        ([1, 2, -1], 1),          # negative token
        ([1, True, 2], 1),        # bool token
        ([1, 2.0, 2], 1),         # float token
        ([1, "2"], 1),            # string token
        ("12", 1),                # string sequence
        ([1, 2], -1),             # negative value
        ([1, 2], True),           # bool value
        ([1, 2], 1.0),            # float value
        (5, 1),                   # not a sequence
    ],
)
def test_malformed_input_is_refused(tokens, value):
    with pytest.raises(ValueError):
        token_occurrence_frames(tokens, value)


def test_whole_input_validated_before_any_result():
    # The target occurs before the malformed token; no partial result may escape.
    with pytest.raises(ValueError):
        token_occurrence_frames([1, 1, 1, -3], 1)


def test_registry_declares_the_extractor_under_the_new_version():
    assert OPERATOR_GROUP_VERSION == "causal-grouping-gap-v1"
    assert OPERATOR_GROUP["version"] == "causal-grouping-gap-v1"
    decl = OPERATOR_GROUP["occurrence_frame_extractors"]["token_occurrence_frames"]
    assert "value" in decl["params"]
    # the previous members are preserved
    assert set(OPERATOR_GROUP["occurrence_extractors"]) == {
        "directional_change_pivots",
        "binary_flip_times",
    }
    assert operator_group_hash() != (
        "5d11bddea00fb1f16c5a01694f3fd49c9a3a7ad9ed703a506a6e894937e5ad3e"
    )
