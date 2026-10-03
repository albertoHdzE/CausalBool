"""H2: bounded discovery -- determinism, blindness, caps, fallback, invariants."""
from __future__ import annotations

import ast
import inspect
import itertools
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from hierarchy import infer as infer_mod
from hierarchy.candidates import schema_pairs
from hierarchy.decode import decode_archive
from hierarchy.infer import ABLATIONS, RESTRICTED_ORACLE, SearchConfig, infer
from hierarchy.model import Model, NodeFactory, Literal, Xform, apply_xform, to_model
from hierarchy.wire import encode_literal, serialize_model

PKG = Path(infer_mod.__file__).resolve().parent
ALL8 = ["".join(t) for k in range(9) for t in itertools.product("01", repeat=k)]


def _rand(rng, n):
    return "".join(rng.choice("01") for _ in range(n))


@pytest.mark.parametrize("name", sorted(ABLATIONS))
def test_every_arm_round_trips_all_short_strings_and_never_beats_literal_by_loss(name):
    cfg = ABLATIONS[name]
    for s in ALL8:
        r = infer(s, cfg)
        assert decode_archive(r.archive) == s
        assert r.archive_bits <= 8 * len(encode_literal(s))
        assert r.archive_bits == 8 * len(r.archive)


def test_seeded_larger_suite_round_trips_in_every_arm():
    rng = random.Random(4242)
    suite = [_rand(rng, rng.randint(9, 700)) for _ in range(6)]
    suite += [("0110" * 200)[:777], ("1" * 9 + "0") * 50, "0" * 1000 + "1"]
    for s in suite:
        for cfg in list(ABLATIONS.values()) + [RESTRICTED_ORACLE]:
            r = infer(s, cfg)
            assert decode_archive(r.archive) == s
            assert r.archive_bits <= r.literal_bits
            if r.mode == "hid":
                assert serialize_model(r.model, len(s)) == r.archive
                assert r.dag_depth <= cfg.max_depth and r.rule_count <= cfg.max_rules


def test_equal_length_ties_choose_literal():
    # Eight ones: the repeat graph (14 bytes) loses to raw (8 bytes) -- annex W8.
    r = infer("1" * 8)
    assert r.mode == "literal" and r.archive == encode_literal("1" * 8)


def test_caps_stop_the_search_and_keep_a_valid_fallback():
    s = ("10110" * 300)[:1400] + _rand(random.Random(1), 600)
    r = infer(s, SearchConfig(max_candidates=3))
    assert r.stop_reason == "candidate_cap" and r.candidate_counts["serialized_unique"] == 3
    assert decode_archive(r.archive) == s
    r = infer(s, SearchConfig(work_cap=1000))
    assert r.stop_reason == "work_cap" and r.mode == "literal"
    assert decode_archive(r.archive) == s


def test_restricted_and_flat_arms_respect_their_languages():
    s = ("0010111" * 40)[:270]
    r = infer(s, ABLATIONS["flat"])
    if r.mode == "hid":
        root = r.model.rules[-1]
        prims = (0, 3, 4)
        inner = r.model.rules[root.child] if root.op == 5 else root
        kids = inner.refs()
        assert inner.op in prims or all(r.model.rules[c].op in prims for c in kids)
        # no cross-child sharing: every record referenced at most once
        refs = [c for rule in r.model.rules for c in rule.refs()]
        assert len(refs) == len(set(refs))
    r = infer("1" * 64, RESTRICTED_ORACLE)
    assert r.mode == "hid" and len(r.model.rules) <= 3


def test_ablation_arms_never_emit_their_disabled_opcode():
    rng = random.Random(8)
    strings = [("110" * 100)[:300], _rand(rng, 256), ("0" * 31 + "1") * 8]
    for s in strings:
        for name, banned in (("no_schema", 4), ("no_arithmetic", 3), ("no_transform", 6)):
            r = infer(s, ABLATIONS[name])
            if r.model:
                assert all(rule.op != banned for rule in r.model.rules)


# --- determinism in fresh processes ----------------------------------------

def _run_fresh(hashseed: str, s: str, cfgname: str) -> dict:
    code = ("import json,sys; from hierarchy.infer import infer, ABLATIONS;"
            "r=infer(sys.stdin.read(), ABLATIONS[sys.argv[1]]);"
            "print(json.dumps({'a': r.archive.hex(), 'c': r.candidate_counts, 'w': r.work,"
            "'s': r.stop_reason, 't': r.trace}))")
    env = dict(os.environ, PYTHONHASHSEED=hashseed,
               PYTHONPATH=f"{PKG.parent}{os.pathsep}{PKG.parents[1] / 'src'}")
    out = subprocess.run([sys.executable, "-c", code, cfgname], input=s, env=env,
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize("cfgname", ["full", "fixed8"])
def test_identical_bytes_and_counters_under_different_hash_seeds(cfgname):
    rng = random.Random(55)
    s = ("0110" * 60 + _rand(rng, 100) + "1" * 77)[:420]
    a = _run_fresh("0", s, cfgname)
    b = _run_fresh("12345", s, cfgname)
    assert a == b


# --- metadata blindness -----------------------------------------------------

INFERENCE_MODULES = ("infer.py", "candidates.py", "model.py", "wire.py", "decode.py",
                     "codes.py", "baselines.py")


def test_inference_modules_do_not_import_corpus_benchmark_or_reporting():
    banned = {"corpus", "benchmark", "report", "diagnostics", "cli"}
    for name in INFERENCE_MODULES:
        tree = ast.parse((PKG / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mods = {(node.module or "").split(".")[-1]}
            elif isinstance(node, ast.Import):
                mods = {a.name.split(".")[-1] for a in node.names}
            else:
                continue
            assert not (mods & banned), (name, mods)


def test_infer_signature_has_no_metadata_arguments():
    params = list(inspect.signature(infer).parameters)
    assert params == ["bits", "config"]
    fields = set(SearchConfig.__dataclass_fields__)
    assert not fields & {"family", "seed", "period", "mask", "truth", "case_id", "split"}


def test_renaming_input_files_cannot_change_the_archive(tmp_path):
    s = ("1" * 8 + "0") * 30 + "1101"
    for name in ("F01-periodic.txt", "x.txt"):
        (tmp_path / name).write_text(s + "\n")
    outs = []
    for name in ("F01-periodic.txt", "x.txt"):
        env = dict(os.environ, PYTHONPATH=f"{PKG.parent}{os.pathsep}{PKG.parents[1] / 'src'}")
        subprocess.run([sys.executable, "-m", "hierarchy.cli", "encode", "--input",
                        str(tmp_path / name), "--output", str(tmp_path / (name + ".isd"))],
                       env=env, check=True, capture_output=True)
        outs.append((tmp_path / (name + ".isd")).read_bytes())
    assert outs[0] == outs[1]


# --- scientific invariants ----------------------------------------------------

def test_joint_reuse_on_an_automatically_inferred_example():
    rng = random.Random(21)
    a = _rand(rng, 128)
    s = _rand(rng, 128) + a + _rand(rng, 128) + a + _rand(rng, 128) + a
    r = infer(s)
    assert r.mode == "hid"
    refs = [c for rule in r.model.rules for c in rule.refs()]
    shared = [c for c in set(refs) if refs.count(c) >= 2]
    assert shared, "no rule is referenced twice"
    exps = r.model.expansions()
    assert any(a in exps[c] for c in shared), "the repeated block is not a shared rule"
    # sharing pays: the same graph written without sharing is longer
    f = NodeFactory()
    root = _to_nodes(r.model, f)
    assert len(serialize_model(to_model(root, share=False), len(s))) > len(r.archive)


def _to_nodes(model, f):
    from hierarchy import codes as C
    nodes = []
    for r in model.rules:
        if r.op == C.OP_LITERAL:
            nodes.append(f.literal(r.bits))
        elif r.op == C.OP_CONCAT:
            nodes.append(f.concat([nodes[c] for c in r.children]))
        elif r.op == C.OP_REPEAT:
            nodes.append(f.repeat(nodes[r.child], r.copies))
        elif r.op == C.OP_AP_UNION:
            nodes.append(f.ap_union(r.length, r.foreground, r.aps))
        elif r.op == C.OP_SCHEMA_UNION:
            nodes.append(f.schema_union(r.length, r.foreground, r.pairs))
        elif r.op == C.OP_PATCH:
            nodes.append(f.patch(nodes[r.child], r.positions))
        else:
            nodes.append(f.xform(nodes[r.child], r.flags, r.rotation))
    return nodes[-1]


def test_rebuild_replaces_every_occurrence_together():
    f = NodeFactory()
    a, b = f.literal("0101"), f.literal("111")
    root = f.concat([a, b, a, f.repeat(a, 3)])
    new = f.rebuild(root, {a.uid: f.repeat(f.literal("01"), 2)})
    assert f.expand(new) == f.expand(root)
    assert "LITERAL" not in repr([c for c in new.children if c.length == 4])
    assert all(c is not a for c in new.children)


def test_schema_cover_keeps_dont_cares_on_participating_coordinates_and_clips():
    coords = (1, 3, 4)                               # pattern order
    pats = ("01*", "10*", "*10")

    def member(i):
        return any(all(ch == "*" or ((i >> c) & 1) == int(ch) for ch, c in zip(p, coords))
                   for p in pats)
    for length in (32, 27):                          # power of two and a clipped domain
        s = "".join("1" if member(i) else "0" for i in range(length))
        for pad in (0, 1):
            pairs = schema_pairs(s, "1", pad)
            assert pairs is not None
            d = (length - 1).bit_length()
            filled = set()
            for mask, value in pairs:
                free = [j for j in range(d) if not (mask >> j) & 1]
                for k in range(1 << len(free)):
                    i = value + sum(((k >> t) & 1) << j for t, j in enumerate(free))
                    if i < length:
                        filled.add(i)
            assert filled == {i for i in range(length) if s[i] == "1"}
            participating_free = [(m, v) for m, v in pairs
                                  if any(not (m >> c) & 1 for c in coords)]
            assert participating_free, "a don't-care on a connected coordinate was lost"


def test_schema_owner_is_the_index_deconvolution_source():
    from hierarchy.candidates import owner_source_path
    assert Path(owner_source_path()).parts[-3:] == ("index-deconvolution", "src",
                                                     "deconvolution.py")


def test_a64_zero_support_has_no_hamming_one_edge():
    a64 = "".join("1" * i + "0" + "1" * (7 - i) for i in range(8))
    zeros = [i for i, c in enumerate(a64) if c == "0"]
    assert zeros == list(range(0, 64, 9))
    assert not [(x, y) for x in zeros for y in zeros if bin(x ^ y).count("1") == 1]
    # Kept separate: the complementary/other representation is a search question.
    r = infer(a64)
    assert decode_archive(r.archive) == a64


def test_order_is_transmitted():
    cases = ["1" * 8] + ["1" * i + "0" + "1" * (7 - i) for i in range(8)]
    ax = "".join(cases[j - 1] for j in range(1, 9))
    axm = "".join(cases[j - 1] for j in (8, 1, 6, 7, 2, 4, 3, 5))
    ra, rm = infer(ax), infer(axm)
    assert ra.archive != rm.archive
    assert decode_archive(ra.archive) == ax and decode_archive(rm.archive) == axm


def test_fixed_transforms_are_exactly_invertible_by_the_decoder():
    rng = random.Random(6)
    for _ in range(200):
        s = _rand(rng, rng.randint(1, 40))
        flags = rng.randint(0, 3)
        r = rng.randrange(len(s))
        if flags == 0 and r == 0:
            continue
        t = decode_archive(serialize_model(Model((Literal(s), Xform(0, flags, r))), len(s)))
        assert t == apply_xform(s, flags, r)
        # invert: undo rotation, then reversal, then complement
        u = t[r:] + t[:r] if r else t
        if flags & 2:
            u = u[::-1]
        if flags & 1:
            u = u.translate(str.maketrans("01", "10"))
        assert u == s


def test_candidate_expansion_mismatch_raises_instead_of_rejecting(monkeypatch):
    from hierarchy import infer as I
    orig = I._Search.local_props

    def bad(self, s, allow_split=True):
        out = orig(self, s, allow_split)
        if s == self.x:
            flip = "1" if s[0] == "0" else "0"
            out = out + [("injected", self.f.literal(flip + s[1:]))]
        return out
    monkeypatch.setattr(I._Search, "local_props", bad)
    with pytest.raises(I.CandidateExpansionMismatch, match="global:injected"):
        I.infer("0110" * 20)
    monkeypatch.undo()
    # legitimate exclusions keep their behaviour: a candidate cap still returns a result
    r = I.infer("0110" * 20, I.SearchConfig(max_candidates=1))
    assert r.stop_reason == "candidate_cap" and r.candidate_counts["rejected_verify"] == 0
