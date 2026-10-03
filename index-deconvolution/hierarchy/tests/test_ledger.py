"""Ledgers are cut from archive bytes and always reassemble them."""
from __future__ import annotations

import random

from hierarchy.baselines import BASELINE_METHODS, encode_baseline
from hierarchy.decode import decode_archive
from hierarchy.infer import ABLATIONS, infer
from hierarchy.ledger import archive_ledger, explain_model
from hierarchy.model import Model, SchemaUnion


def test_every_codec_ledger_reassembles_and_hid_models_reexpand():
    rng = random.Random(12)
    strings = ["1", "0" * 100, ("011" * 50)[:149], "".join(rng.choice("01") for _ in range(300)),
               ("1" * 8 + "0") * 30 + "0110"]
    for s in strings:
        archives = [encode_baseline(s, m) for m in BASELINE_METHODS]
        archives += [infer(s, cfg).archive for cfg in ABLATIONS.values()]
        for a in archives:
            led = archive_ledger(a)
            assert sum(f["bytes"] for f in led["fields"]) == len(a)
            if led["model"] is not None:
                assert led["model"].expand() == decode_archive(a) == s
                assert explain_model(led["model"])


def test_schema_explanation_lists_anchor_free_coordinates_and_clipped_count():
    m = Model((SchemaUnion(6, 1, ((1, 1), (6, 2))),))
    rows = explain_model(m)[0]["schemata"]
    assert rows[0]["free_coordinates"] == [1, 2] and rows[0]["decimal_anchor"] == 1
    assert rows[0]["addresses_after_clipping"] == 3          # 1, 3, 5 (7 clipped)
    assert rows[1]["free_coordinates"] == [0] and rows[1]["addresses_after_clipping"] == 2
