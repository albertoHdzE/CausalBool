"""Cover, serialization, proposal and leakage tests.

Acceptance-matrix checks covered here: C16 exact cover and serialization
mutations, C17 threshold ties and control denominators, C18 an interrupted
construction, C19 an exact cover of observed elites discovering nothing, C20
hidden-label isolation, and C21 novelty and duplicate accounting.

The decisive one is C19. Plan section 7: "An exact cover of a finite observed
set generates only that set." If that ever fails, the distinction between
lossless deconvolution and discovery has collapsed.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import schema_index as si  # noqa: E402

from research import structural_encoding as se  # noqa: E402
from research import structural_models as sm  # noqa: E402
from research import structural_oracle as so  # noqa: E402
from research import run_structural_experiments as runner  # noqa: E402


FIXTURES = json.loads((ROOT / "plan" / "phase2" / "FIXTURES.json").read_text())["fixtures"]
CONTRACT = runner.Contract(ROOT / "plan" / "phase2")


def elite_indices(record, codec="structural_rank"):
    domain = se.Domain.from_record(record)
    bits = se.layout(domain, codec).width
    enumeration = so.enumerate_feasible(record, 65536)
    indices = sorted(
        se.encode(domain, json.loads(entry["identity"]), codec)
        for entry in enumeration["feasible"]
    )
    return domain, bits, indices, enumeration


class ExactCover(unittest.TestCase):
    """C16 and C18: exactness, disjointness, determinism and interruption."""

    def test_cover_is_exact_and_disjoint_on_every_fixture(self):
        for record in FIXTURES:
            _, bits, indices, _ = elite_indices(record)
            with self.subTest(fixture=record["id"]):
                cover = sm.exact_cover(indices, bits, 65536, 10)
                self.assertEqual(cover.status, "COMPLETE")
                self.assertTrue(cover.exact)
                self.assertTrue(cover.disjoint)
                self.assertEqual(sm.cover_members(cover.cubes), sorted(set(indices)))

    def test_cover_is_deterministic(self):
        for record in FIXTURES[:4]:
            _, bits, indices, _ = elite_indices(record)
            first = sm.exact_cover(indices, bits, 65536, 10)
            second = sm.exact_cover(list(reversed(indices)), bits, 65536, 10)
            self.assertEqual(first.as_pairs(), second.as_pairs(), record["id"])

    def test_empty_set_and_single_member(self):
        self.assertEqual(sm.exact_cover([], 4, 100, 1).cubes, ())
        cover = sm.exact_cover([5], 4, 100, 1)
        self.assertEqual(len(cover.cubes), 1)
        self.assertEqual(cover.cubes[0].free_mask, 0)

    def test_a_full_universe_collapses_to_one_cube(self):
        cover = sm.exact_cover(range(16), 4, 100, 1)
        self.assertEqual(len(cover.cubes), 1)
        self.assertEqual(cover.cubes[0].free_mask, 15)
        self.assertTrue(cover.exact)

    def test_index_outside_the_universe_is_refused(self):
        with self.assertRaises(ValueError):
            sm.exact_cover([16], 4, 100, 1)

    def test_an_interrupted_construction_is_inconclusive(self):
        """C18: never exact evidence, never a compression success."""

        cover = sm.exact_cover(range(256), 8, 65536, 0.0)
        self.assertEqual(cover.status, "INCONCLUSIVE")
        self.assertIsNone(cover.exact)
        self.assertIn("budget", cover.reason)

    def test_a_cube_budget_is_inconclusive_not_a_partial_claim(self):
        cover = sm.exact_cover(range(16), 4, 4, 10)
        self.assertEqual(cover.status, "INCONCLUSIVE")
        self.assertIsNone(cover.exact)


class Serialisation(unittest.TestCase):
    """C16: the byte format rejects every mutation the contract names."""

    def setUp(self):
        _, self.bits, self.indices, _ = elite_indices(FIXTURES[0])
        self.cover = sm.exact_cover(self.indices, self.bits, 65536, 10)
        self.blob = sm.serialise_cover(self.cover.cubes, self.bits)

    def test_round_trip(self):
        cubes, bits = sm.deserialise_cover(self.blob)
        self.assertEqual(bits, self.bits)
        self.assertEqual(cubes, self.cover.cubes)

    def test_a_cover_is_shorter_than_its_minterms(self):
        minterms = tuple(si.Cube(self.bits, index, 0) for index in sorted(set(self.indices)))
        self.assertLess(
            len(self.blob), len(sm.serialise_cover(minterms, self.bits))
        )

    def test_rejects_extra_bytes(self):
        with self.assertRaises(sm.SerialisationError):
            sm.deserialise_cover(self.blob + b"\x00")

    def test_rejects_a_truncated_stream(self):
        with self.assertRaises(sm.SerialisationError):
            sm.deserialise_cover(self.blob[:-1])
        with self.assertRaises(sm.SerialisationError):
            sm.deserialise_cover(b"")

    def test_rejects_an_overlong_varint(self):
        # 0x80 0x00 encodes zero in two bytes; the shortest form is 0x00.
        overlong = b"\x80\x00" + self.blob[1:]
        with self.assertRaises(sm.SerialisationError):
            sm.deserialise_cover(overlong)

    def test_rejects_nonzero_padding(self):
        bits = 4
        cover = (si.Cube(bits, 1, 0),)
        blob = bytearray(sm.serialise_cover(cover, bits))
        # One byte per integer at four bits; set a bit above the declared width.
        blob[2] = 0xFF
        with self.assertRaises(sm.SerialisationError):
            sm.deserialise_cover(bytes(blob))

    def test_rejects_unsorted_or_duplicated_cubes(self):
        bits = 4
        blob = sm.serialise_cover((si.Cube(bits, 1, 0), si.Cube(bits, 2, 0)), bits)
        swapped = bytearray(blob)
        swapped[2], swapped[4] = swapped[4], swapped[2]
        with self.assertRaises(sm.SerialisationError):
            sm.deserialise_cover(bytes(swapped))
        with self.assertRaises(sm.SerialisationError):
            sm.serialise_cover((si.Cube(bits, 1, 0), si.Cube(bits, 1, 0)), bits)

    def test_rejects_a_cube_of_the_wrong_width(self):
        with self.assertRaises(sm.SerialisationError):
            sm.serialise_cover((si.Cube(4, 1, 0),), 5)

    def test_altering_a_free_mask_changes_the_denoted_set(self):
        cubes, bits = sm.deserialise_cover(self.blob)
        original = set(sm.cover_members(cubes))
        mutated = tuple(
            si.Cube(bits, cube.anchor, cube.free_mask | (1 << (bits - 1)))
            if not cube.free_mask & (1 << (bits - 1)) and
            not cube.anchor & (1 << (bits - 1))
            else cube
            for cube in cubes
        )
        self.assertNotEqual(set(sm.cover_members(mutated)), original)

    def test_zero_width_universe(self):
        blob = sm.serialise_cover((si.Cube(0, 0, 0),), 0)
        cubes, bits = sm.deserialise_cover(blob)
        self.assertEqual(bits, 0)
        self.assertEqual(cubes, (si.Cube(0, 0, 0),))


class EliteThresholdAndControls(unittest.TestCase):
    """C17: ties at the threshold are included and controls keep their count."""

    def test_threshold_includes_all_ties(self):
        products = [1, 1, 1, 2, 2, 3, 3, 3, 3, 4]
        threshold = runner._elite_threshold(products, 0.1)
        self.assertEqual(threshold, 1)
        self.assertEqual(sum(1 for value in products if value <= threshold), 3)

    def test_threshold_on_all_equal_objectives(self):
        products = [5] * 10
        self.assertEqual(runner._elite_threshold(products, 0.1), 5)

    def test_threshold_of_an_empty_set_is_undefined(self):
        self.assertIsNone(runner._elite_threshold([], 0.1))

    def test_controls_keep_all_one_hundred_even_when_two_coincide(self):
        record = FIXTURES[0]
        _, _, indices, enumeration = elite_indices(record)
        identities = sorted(entry["identity"] for entry in enumeration["feasible"])
        rng = random.Random(CONTRACT.seeds["structure_controls"])
        controls = [rng.sample(identities, 2) for _ in range(100)]
        self.assertEqual(len(controls), 100)
        # Duplicates are expected on a small universe and are retained.
        distinct = len({tuple(sorted(subset)) for subset in controls})
        self.assertLessEqual(distinct, 100)

    def test_controls_are_reproducible_from_the_frozen_seed(self):
        record = FIXTURES[0]
        _, _, _, enumeration = elite_indices(record)
        identities = sorted(entry["identity"] for entry in enumeration["feasible"])
        first = [random.Random(20260924).sample(identities, 2) for _ in range(1)]
        second = [random.Random(20260924).sample(identities, 2) for _ in range(1)]
        self.assertEqual(first, second)

    def test_the_same_physical_subset_maps_into_every_codec(self):
        record = FIXTURES[0]
        domain = se.Domain.from_record(record)
        enumeration = so.enumerate_feasible(record, 65536)
        subset = sorted(entry["identity"] for entry in enumeration["feasible"])[:3]
        per_codec = {
            codec: sorted(se.encode(domain, json.loads(item), codec) for item in subset)
            for codec in ("absolute", "static_rank", "structural_rank")
        }
        # The objects are identical; only their coordinates differ.
        self.assertEqual(len({len(value) for value in per_codec.values()}), 1)
        self.assertNotEqual(per_codec["absolute"], per_codec["structural_rank"])


class Expansion(unittest.TestCase):
    """C19 and C21: what a cover can and cannot produce, and how it is counted."""

    def test_an_exact_cover_denotes_exactly_the_observed_set(self):
        for record in FIXTURES:
            _, bits, indices, _ = elite_indices(record)
            cover = sm.exact_cover(indices, bits, 65536, 10)
            with self.subTest(fixture=record["id"]):
                self.assertEqual(sm.cover_members(cover.cubes), sorted(set(indices)))

    def test_empirical_cover_yields_no_unseen_index_and_exhausts(self):
        """C19: the arm exists to demonstrate that it cannot discover."""

        for record in FIXTURES[:4]:
            _, bits, indices, _ = elite_indices(record)
            observed = set(indices)
            cover = sm.exact_cover(indices, bits, 65536, 10)
            produced = list(
                sm.proposals("empirical_cover", bits, indices, cover.cubes, observed, None)
            )
            with self.subTest(fixture=record["id"]):
                self.assertTrue(produced)
                self.assertEqual({index for index, _ in produced}, observed)
                self.assertTrue(all(duplicate for _, duplicate in produced))

    def test_model_expand_frees_exactly_one_coordinate_per_cube(self):
        bits = 4
        cubes = (si.Cube(bits, 0b0101, 0),)
        expanded = sm.expand_cubes(cubes, bits)
        self.assertEqual(len(expanded), bits)
        for cube in expanded:
            self.assertEqual(bin(cube.free_mask).count("1"), 1)
        self.assertEqual(
            sorted((cube.anchor, cube.free_mask) for cube in expanded),
            [(1, 4), (4, 1), (5, 2), (5, 8)],
        )

    def test_model_expand_deduplicates_and_visits_in_ascending_order(self):
        bits = 3
        cubes = (si.Cube(bits, 0b000, 0), si.Cube(bits, 0b001, 0))
        expanded = sm.expand_cubes(cubes, bits)
        pairs = [(cube.anchor, cube.free_mask) for cube in expanded]
        self.assertEqual(len(pairs), len(set(pairs)))
        members = sm.cover_members(expanded)
        self.assertEqual(members, sorted(members))

    def test_model_expand_can_produce_unseen_indices(self):
        found = 0
        for record in FIXTURES:
            _, bits, indices, _ = elite_indices(record)
            cover = sm.exact_cover(indices, bits, 65536, 10)
            unseen = set(sm.cover_members(sm.expand_cubes(cover.cubes, bits))) - set(indices)
            if unseen:
                found += 1
        self.assertEqual(found, len(FIXTURES))

    def test_one_bit_visits_ascending_distinct_flips(self):
        bits = 4
        produced = [
            index for index, _ in sm.proposals("one_bit", bits, [0b0000], (), set(), None)
        ]
        self.assertEqual(produced, [1, 2, 4, 8])
        self.assertEqual(len(produced), len(set(produced)))

    def test_uniform_bits_is_seeded_and_counts_every_draw(self):
        bits = 6
        first = [
            value for value, _ in
            _take(sm.proposals("uniform_bits", bits, [], (), set(), 20261001), 20)
        ]
        second = [
            value for value, _ in
            _take(sm.proposals("uniform_bits", bits, [], (), set(), 20261001), 20)
        ]
        other = [
            value for value, _ in
            _take(sm.proposals("uniform_bits", bits, [], (), set(), 20261002), 20)
        ]
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(all(0 <= value < (1 << bits) for value in first))
        # A repeat is yielded, not skipped, so every draw stays in the denominator.
        repeated = [
            duplicate for _, duplicate in
            _take(sm.proposals("uniform_bits", bits, [], (), {first[0]}, 20261001), 1)
        ]
        self.assertEqual(repeated, [True])

    def test_uniform_bits_requires_a_seed(self):
        with self.assertRaises(ValueError):
            next(sm.proposals("uniform_bits", 4, [], (), set(), None))

    def test_an_unknown_arm_is_refused(self):
        with self.assertRaises(ValueError):
            next(sm.proposals("clairvoyance", 4, [], (), set(), None))

    def test_excluded_indices_are_reported_as_duplicates_not_skipped(self):
        """C21: a repeat stays in the denominator."""

        bits = 4
        produced = list(sm.proposals("one_bit", bits, [0], (), {1, 2}, None))
        indices = [index for index, _ in produced]
        duplicates = [index for index, duplicate in produced if duplicate]
        self.assertEqual(indices, [1, 2, 4, 8])
        self.assertEqual(duplicates, [1, 2])


def _take(iterator, count):
    result = []
    for item in iterator:
        result.append(item)
        if len(result) >= count:
            break
    return result


class HiddenLabelIsolation(unittest.TestCase):
    """C20: the learner never receives the hidden evaluation mapping."""

    def test_proposals_cannot_see_the_hidden_evaluation(self):
        import inspect

        signature = inspect.signature(sm.proposals)
        self.assertEqual(
            list(signature.parameters),
            ["arm", "bits", "elite", "cover", "excluded", "search_seed",
             "budget_check"],
        )
        source = inspect.getsource(sm)
        self.assertNotIn("hidden_evaluation", source)
        self.assertNotIn("structural_oracle", source)

    def test_the_model_module_does_not_import_the_oracle(self):
        import research.structural_models as module

        self.assertFalse(hasattr(module, "so"))
        self.assertFalse(hasattr(module, "structural_oracle"))

    def test_a_split_partitions_the_feasible_set_exactly(self):
        for record in FIXTURES:
            enumeration = so.enumerate_feasible(record, 65536)
            split = runner.split_fixture(enumeration, 20260925, 10, 5)
            with self.subTest(fixture=record["id"]):
                combined = split["train"] + split["validation"] + split["test"]
                self.assertEqual(len(combined), len(set(combined)))
                self.assertEqual(
                    sorted(combined),
                    sorted(entry["identity"] for entry in enumeration["feasible"]),
                )
                self.assertEqual(split["n_train"], split["total"] // 2)
                self.assertEqual(split["n_validation"], split["total"] // 4)

    def test_a_split_is_reproducible_and_reinitialised_per_fixture(self):
        enumeration = so.enumerate_feasible(FIXTURES[0], 65536)
        first = runner.split_fixture(enumeration, 20260925, 10, 5)
        second = runner.split_fixture(enumeration, 20260925, 10, 5)
        self.assertEqual(first["train"], second["train"])
        self.assertEqual(first["test"], second["test"])

    def test_a_split_too_small_is_reported_not_reallocated(self):
        enumeration = so.enumerate_feasible(FIXTURES[0], 65536)
        split = runner.split_fixture(enumeration, 20260925, 10, 5)
        self.assertFalse(split["informative"])
        self.assertIn("train", split["reason"])
        # It is reported, and the partitions are left exactly as they were.
        self.assertEqual(
            split["n_train"] + split["n_validation"] + split["n_test"], split["total"]
        )

    def test_training_indices_can_never_become_test_discoveries(self):
        record = FIXTURES[3]
        enumeration = so.enumerate_feasible(record, 65536)
        split = runner.split_fixture(enumeration, 20260925, 1, 1)
        domain = se.Domain.from_record(record)
        codec = "structural_rank"
        train = {se.encode(domain, json.loads(item), codec) for item in split["train"]}
        test = {se.encode(domain, json.loads(item), codec) for item in split["test"]}
        self.assertEqual(train & test, set())


if __name__ == "__main__":
    unittest.main()
